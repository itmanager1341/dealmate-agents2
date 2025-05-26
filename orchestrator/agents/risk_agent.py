# risk_agent.py
# Agent to extract red flags, risk factors, and vulnerabilities from CIM narratives

from orchestrator.base_agent import BaseAgent
import re
import json

class RiskAgent(BaseAgent):
    """
    Agent that identifies key business or investment risks from CIM documents.
    Returns structured JSON with risk description, severity, and impact.
    """

    def __init__(self):
        super().__init__(agent_name="risk_agent", model="gpt-4o")

    def build_prompt(self, document_text, context={}):
        """
        Build prompt to identify risks that could impact investment decisions.
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are an M&A analyst. Read the CIM and identify any business, market, or operational risks that "
                    "could negatively impact an investor's decision to pursue this deal. Focus on risks mentioned explicitly "
                    "in the text, and output each risk as a structured object including severity and potential impact."
                )
            },
            {
                "role": "user",
                "content": (
                    "From the following CIM text, extract risks with the following JSON format:\n\n"
                    "{\n"
                    '  "risks": [\n'
                    "    {\n"
                    '      "risk": "Description of the risk",\n'
                    '      "severity": "High | Medium | Low",\n'
                    '      "impact": "Impact on investment or operations",\n'
                    '      "source_text": "Original sentence or paragraph where this risk is described"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n\n"
                    "CIM TEXT:\n" + document_text[:10000]
                )
            }
        ]

    def parse_response(self, raw_response):
        """
        Parses model output into a clean JSON structure with a list of risk entries.
        """
        try:
            # Extract and parse JSON block from raw response
            parsed_json = self._extract_json_block(raw_response)
            risks = parsed_json.get("risks", [])

            # Clean formatting, enforce required fields
            normalized = []
            for r in risks:
                normalized.append({
                    "risk": r.get("risk", "").strip(),
                    "severity": r.get("severity", "Medium").strip(),
                    "impact": r.get("impact", "").strip(),
                    "source_text": r.get("source_text", "").strip()
                })

            return {
                "output_type": "risk_summary",
                "items": normalized
            }

        except Exception as e:
            return {
                "error": "Could not parse model response.",
                "raw_output": raw_response,
                "exception": str(e)
            }

    def _extract_json_block(self, text):
        """
        Extract the first valid JSON object in the response
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())

    def _validate_output_type(self, output):
        """
        Validates that the output is a dictionary with risk items.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        if "output_type" not in output or output["output_type"] != "risk_summary":
            return False
            
        if "items" not in output or not isinstance(output["items"], list):
            return False
            
        for item in output["items"]:
            if not isinstance(item, dict):
                return False
            if not all(k in item for k in ["risk_type", "description", "severity"]):
                return False
                
        return True
