# base_agent.py
# Abstract base class for DealMate multi-agent architecture
# Used to define the interface and shared behavior across all task-specific agents
# Compatible with GPT-4o and future drop-in models

from abc import ABC, abstractmethod
from datetime import datetime
import openai
import os
import traceback
import uuid
import logging
from typing import Optional, Any, List, Dict
import tiktoken
from supabase import create_client, Client

# Initialize OpenAI client (expects OPENAI_API_KEY in env)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
)

class BaseAgent(ABC):
    """
    Abstract base class for all DealMate agents.
    Defines the interface and common functionality for agent implementations.
    """

    def __init__(self, agent_name: str, user_id: Optional[str] = None, deal_id: Optional[str] = None):
        """
        Initialize the agent with user and deal context.
        
        Args:
            agent_name: Name of the agent
            user_id: Optional user ID for model configuration
            deal_id: Optional deal ID for model configuration
        """
        self.agent_name = agent_name
        self.user_id = user_id
        self.deal_id = deal_id
        self.logger = logging.getLogger(f"dealmate.{agent_name}")
        self.logs = []
        self.openai_client = openai.OpenAI()
        self._load_model_config()

    def _load_model_config(self):
        """
        Load the effective model configuration for this agent.
        Uses the get_effective_model_config function to determine which model to use.
        """
        try:
            # Log parameters
            self.logger.info(
                f"Calling get_effective_model_config with user_id={self.user_id}, deal_id={self.deal_id}, use_case={self._get_use_case()}"
            )
            response = supabase.rpc(
                'get_effective_model_config',
                {
                    'p_user_id': self.user_id,
                    'p_deal_id': self.deal_id,
                    'p_use_case': self._get_use_case()
                }
            ).execute()
            self.logger.info(f"Model config RPC response: {response.data} (type: {type(response.data)})")

            model_id = None
            # Handle the most common and robust cases
            if isinstance(response.data, list) and response.data:
                # Scalar return: [model_id]
                if isinstance(response.data[0], str):
                    model_id = response.data[0]
                # Record return: [{'model_id': ...}]
                elif isinstance(response.data[0], dict) and 'model_id' in response.data[0]:
                    model_id = response.data[0]['model_id']
            elif isinstance(response.data, str):
                model_id = response.data
            elif isinstance(response.data, dict) and 'model_id' in response.data:
                model_id = response.data['model_id']

            if not model_id:
                raise ValueError("No effective model configuration found")
            self.model_id = model_id
            # Get model details
            model_details = supabase.table('ai_models').select('*').eq('id', self.model_id).single().execute()
            if model_details.data:
                self.model_config = model_details.data
            else:
                raise ValueError(f"Model {self.model_id} not found")
        except Exception as e:
            self.logger.error(f"Error loading model configuration: {str(e)}")
            raise

    def _get_use_case(self) -> str:
        """
        Get the use case for this agent.
        Override in subclasses to specify the use case.
        """
        return "general_analysis"  # Default use case

    def _log_model_usage(self, input_tokens: int, output_tokens: int, processing_time_ms: int, success: bool, error_message: Optional[str] = None):
        """
        Log model usage to the model_usage_logs table.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            processing_time_ms: Processing time in milliseconds
            success: Whether the request was successful
            error_message: Optional error message
        """
        try:
            usage_log = {
                "deal_id": self.deal_id,
                "model_id": self.model_id,
                "use_case": self._get_use_case(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "processing_time_ms": processing_time_ms,
                "success": success,
                "error_message": error_message,
                "user_id": self.user_id
            }
            
            supabase.table('model_usage_logs').insert(usage_log).execute()
        except Exception as e:
            self.logger.error(f"Error logging model usage: {str(e)}")

    def _call_ai_model(self, prompt: str, operation: str = "default") -> str:
        """
        Calls the AI model with the given prompt and logs usage.
        
        Args:
            prompt: The prompt to send to the model
            operation: The operation being performed
            
        Returns:
            str: The model's response
        """
        start_time = datetime.now()
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model_config["model_id"],
                messages=[
                    {"role": "system", "content": "You are a DealMate agent."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Calculate usage
            input_tokens = len(tiktoken.encoding_for_model(self.model_config["model_id"]).encode(prompt))
            output_tokens = len(tiktoken.encoding_for_model(self.model_config["model_id"]).encode(response.choices[0].message.content))
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log usage
            self._log_model_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time_ms=int(processing_time),
                success=True
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._log_model_usage(
                input_tokens=0,
                output_tokens=0,
                processing_time_ms=int(processing_time),
                success=False,
                error_message=str(e)
            )
            self.logger.error(f"Error calling AI model: {str(e)}")
            raise

    @abstractmethod
    def _get_prompt(self, text: str, context: Optional[dict] = None) -> str:
        """
        Builds the prompt for the AI model.
        """
        pass

    def build_prompt(self, document_text, context={}):
        """
        Builds the prompt for the AI model using the document text and context.
        This is a wrapper around _get_prompt that handles the document text.
        
        Args:
            document_text: The text of the document to analyze
            context: Additional context for the analysis
            
        Returns:
            str: The prompt to send to the AI model
        """
        return self._get_prompt(document_text)

    @abstractmethod
    def parse_response(self, raw_response):
        """
        Parses the raw response from the AI model into a structured format.
        
        Args:
            raw_response: The raw response from the AI model
            
        Returns:
            dict: The parsed response in a structured format
        """
        pass

    @abstractmethod
    def _validate_output_type(self, output: Any) -> bool:
        """
        Validates that the output matches the expected type.
        """
        pass

    async def process_chunk(self, chunk: dict) -> dict:
        """
        Processes a single document chunk.
        
        Args:
            chunk: Dictionary containing chunk data
            
        Returns:
            dict: Processing results
        """
        try:
            # Get prompt for this chunk
            prompt = self._get_prompt(chunk["chunk_text"], {
                "chunk_id": chunk["id"],
                "section_type": chunk["section_type"],
                "section_title": chunk["section_title"]
            })
            
            # Call AI model
            response = await self._call_ai_model(prompt)
            
            # Parse and validate response
            result = self.parse_response(response)
            if not self._validate_output_type(result):
                raise ValueError("Invalid output type")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk['id']}: {str(e)}")
            return {
                "error": str(e),
                "status": "error",
                "chunk_id": chunk["id"]
            }

    def log(self, message):
        """
        Add a timestamped message to the internal log for traceability.
        """
        self.logs.append(f"[{datetime.now().isoformat()}] {message}")

    def _chunk_text(self, text: str, max_tokens: int = 15000) -> List[str]:
        """
        Split text into chunks that fit within token limits.
        
        Args:
            text: The text to chunk
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List[str]: List of text chunks
        """
        encoding = tiktoken.encoding_for_model(self.model_config["model_id"])
        tokens = encoding.encode(text)
        chunks = []
        
        current_chunk = []
        current_length = 0
        
        for token in tokens:
            if current_length + 1 > max_tokens:
                chunks.append(encoding.decode(current_chunk))
                current_chunk = [token]
                current_length = 1
            else:
                current_chunk.append(token)
                current_length += 1
                
        if current_chunk:
            chunks.append(encoding.decode(current_chunk))
            
        return chunks

    def execute(self, document_text: str, context: Optional[dict] = None) -> dict:
        """
        Execute the agent's analysis on the provided document text.
        
        Args:
            document_text: The text of the document to analyze
            context: Additional context for the analysis
            
        Returns:
            dict: Analysis results with status and output
        """
        try:
            # Split text into chunks using chunking model
            chunks = self._chunk_text(document_text)
            self.logger.info(f"Split document into {len(chunks)} chunks")
            
            results = []
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                # Build prompt for this chunk
                prompt = self.build_prompt(chunk, context)
                
                # Call AI model with analysis operation
                response = self._call_ai_model(prompt, operation="analysis")
                
                # Parse response
                result = self.parse_response(response)
                results.append(result)
            
            # Combine results from all chunks
            combined_result = self._combine_chunk_results(results)
            
            # Validate output using validation model
            if not self._validate_output_type(combined_result):
                raise ValueError("Invalid output type")
            
            return {
                "status": "success",
                "output": combined_result,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error executing {self.agent_name}: {str(e)}")
            return {
                "status": "error",
                "output": None,
                "error": str(e)
            }

    def _combine_chunk_results(self, results: List[dict]) -> dict:
        """
        Combine results from multiple chunks into a single result.
        Override this method in subclasses to implement specific combination logic.
        
        Args:
            results: List of results from individual chunks
            
        Returns:
            dict: Combined result
        """
        # Default implementation just returns the first result
        # Subclasses should override this to properly combine results
        return results[0] if results else {}
