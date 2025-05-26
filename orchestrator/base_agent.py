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

    @abstractmethod
    def _get_prompt(self, context):
        """
        Generates the prompt for the AI model.
        
        Args:
            context: The context to use for generating the prompt
            
        Returns:
            str: The prompt to send to the AI model
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
    def _validate_output_type(self, output):
        """
        Validates that the output matches the expected structure.
        
        Args:
            output: The output to validate
            
        Returns:
            bool: True if the output is valid, False otherwise
        """
        pass

    def execute(self, document_text, context={}):
        """
        Executes the agent's analysis on the given document text.
        
        Args:
            document_text: The text of the document to analyze
            context: Additional context for the analysis
            
        Returns:
            dict: The analysis results
        """
        try:
            # Generate prompt
            prompt = self.build_prompt(document_text, context)
            
            # Call AI model
            response = self._call_ai_model(prompt)
            
            # Parse response
            parsed = self.parse_response(response)
            
            # Validate output
            if not self._validate_output_type(parsed):
                raise ValueError(f"Invalid output structure from {self.agent_name}")
                
            return parsed
            
        except Exception as e:
            self.logger.error(f"Error in {self.agent_name}: {str(e)}")
            raise

    def _call_ai_model(self, prompt):
        """
        Calls the AI model with the given prompt.
        
        Args:
            prompt: The prompt to send to the AI model
            
        Returns:
            str: The response from the AI model
        """
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional M&A analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
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
