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
from typing import Optional, Any

# Initialize OpenAI client (expects OPENAI_API_KEY in env)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BaseAgent(ABC):
    """
    Abstract base class for all DealMate agents.
    Defines the interface and common functionality for agent implementations.
    """

    def __init__(self, agent_name, model="gpt-4o"):
        self.agent_name = agent_name
        self.model = model
        self.logger = logging.getLogger(f"dealmate.{agent_name}")
        self.logs = []
        self.openai_client = openai.OpenAI()

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

    async def _call_ai_model(self, prompt: str) -> str:
        """
        Calls the OpenAI API with the given prompt.
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a DealMate agent."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error calling AI model: {str(e)}")
            raise

    def log(self, message):
        """
        Add a timestamped message to the internal log for traceability.
        """
        self.logs.append(f"[{datetime.now().isoformat()}] {message}")
