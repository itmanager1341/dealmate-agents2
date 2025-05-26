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

# Initialize OpenAI client (expects OPENAI_API_KEY in env)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BaseAgent(ABC):
    """
    Abstract base class for DealMate AI agents.
    Subclasses must implement `build_prompt()` and `parse_response()` methods.
    """

    def __init__(self, agent_name, model="gpt-4o"):
        self.agent_name = agent_name
        self.model = model
        self.logs = []

    @abstractmethod
    def build_prompt(self, document_text, context={}):
        """
        Build the prompt for the OpenAI chat model.
        Must return a list of messages: [ {role, content}, ... ]
        """
        pass

    @abstractmethod
    def parse_response(self, raw_response):
        """
        Parse the raw model response into structured output.
        Returns a dict or json-serializable object.
        """
        pass

    def log(self, message):
        """
        Add a timestamped message to the internal log for traceability.
        """
        self.logs.append(f"[{datetime.now().isoformat()}] {message}")

    def execute(self, text, deal_id="unknown", context=None):
        """
        Executes the agent's analysis on the provided text.
        
        Args:
            text (str): The text to analyze
            deal_id (str): Unique identifier for the deal
            context (dict, optional): Additional context from other agents
            
        Returns:
            dict: Analysis results with structure:
                {
                    "success": bool,
                    "output": Any,  # Type depends on agent
                    "error": str,   # If success=False
                    "log": list     # Execution logs
                }
        """
        log = []
        try:
            # Log start
            log.append(f"Starting {self.agent_name} analysis for deal {deal_id}")
            
            # Validate input
            if not isinstance(text, str):
                raise ValueError(f"Expected string input, got {type(text)}")
            
            # Execute analysis
            result = self.analyze(text, context)
            
            # Validate output
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict output from analyze(), got {type(result)}")
            
            # Parse and validate response
            try:
                parsed = self.parse_response(result)
                if not self._validate_output_type(parsed):
                    raise ValueError(f"Invalid output type from {self.agent_name}")
                output = {
                    "success": True,
                    "output": parsed,
                    "log": log
                }
            except Exception as e:
                log.append(f"Error parsing response: {str(e)}")
                output = {
                    "success": False,
                    "error": f"Failed to parse response: {str(e)}",
                    "log": log
                }
            
        except Exception as e:
            log.append(f"Error in {self.agent_name}: {str(e)}")
            output = {
                "success": False,
                "error": str(e),
                "log": log
            }
            
        return output

    def _validate_output_type(self, output):
        """
        Validates that the output matches the expected type for this agent.
        Override in subclasses to implement specific validation.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        return True  # Base implementation accepts any output type
