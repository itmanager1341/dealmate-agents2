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

    def execute(self, document_text, deal_id="unknown", context={}):
        """
        Execute the full agent run: prompt build → model call → response parse → output return.

        Returns:
            {
                "agent": self.agent_name,
                "deal_id": ...,
                "output": parsed output,
                "raw": raw response,
                "log": internal trace log,
                "success": True|False
            }
        """

        try:
            self.log(f"Starting execution for {self.agent_name}")

            # Build prompt
            messages = self.build_prompt(document_text, context)
            self.log(f"Prompt built with {len(messages)} messages")

            # Model call
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=3000
            )
            raw_output = response.choices[0].message.content
            self.log("Model response received")

            # Parse and return
            parsed = self.parse_response(raw_output)
            self.log("Response parsed successfully")

            return {
                "agent": self.agent_name,
                "deal_id": deal_id,
                "output": parsed,
                "raw": raw_output,
                "log": self.logs,
                "success": True
            }

        except Exception as e:
            error_id = str(uuid.uuid4())[:8]
            tb = traceback.format_exc()
            self.log(f"ERROR [{error_id}]: {str(e)}\n{tb}")
            return {
                "agent": self.agent_name,
                "deal_id": deal_id,
                "output": None,
                "raw": None,
                "log": self.logs,
                "success": False,
                "error": str(e),
                "trace": tb,
                "error_id": error_id
            }
