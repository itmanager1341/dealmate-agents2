# consistency_agent.py
# Agent to identify inconsistencies between CIM narrative, financials, and risk disclosures

from orchestrator.base_agent import BaseAgent
import re
import json

class ConsistencyAgent(BaseAgent):
    """
    Agent that cross-analyzes CIM content for logical consistency between
    narrative claims, financial performance, and risk disclosures.
    """

    def __init__(self):
        super().__init__(agent_name="consistency_agent", model="gpt-4o")

    def build_prompt(self, document_text, context={}):
        """
        Builds a prompt that passes CIM text along with known financial metrics and risks,
        then asks the model to flag inconsistencies or contradictions.
        """
        financials = context.get("financial_metrics", [])
        risks = context.get("risks", [])

        return [
            {
                "role": "system",
                "content": (
                    "You are a private equity analyst. Cross-check the narrative, financial metrics, and known risks "
                    "to flag inconsistencies, contradictions, or unrealistic claims. Be specific and objective. "
                    "Return a structured JSON list of consistency issues with severity and rationale."
                )
            },
            {
                "role": "user",
                "content": (
                    "Compare the following:\n\n"
                    f"Financial Metrics: {json.dumps(financials, indent=2)}\n\n"
                    f"Risks: {json.dumps(risks, indent=2)}\n\n"
                    "CIM Narrative:\n" + document_text[:10000] + "\n\n"
                    "Output format:\n"
                    "{\n"
                    '  "inconsistencies": [\n'
                    "    {\n"
                    '      "issue": "Contradictory statements or red flags",\n'
                    '      "severity": "High | Medium | Low",\n'
                    '      "rationale": "Explanation with example text"\n'
                    "    }\n"
                    "  ]\n"
                    "}"
                )
            }
        ]

    def parse_response(self, raw_response):
        """
        Parses JSON block from model response into a list of inconsistencies.
        """
        try:
            parsed_json = self._extract_json_block(raw_response)
            issues = parsed_json.get("inconsistencies", [])

            normalized = []
            for item in issues:
                normalized.append({
                    "issue": item.get("issue", "").strip(),
                    "severity": item.get("severity", "Medium").strip(),
                    "rationale": item.get("rationale", "").strip()
                })

            return {
                "output_type": "consistency_issues",
                "items": normalized
            }

        except Exception as e:
            return {
                "error": "Could not parse consistency output.",
                "exception": str(e),
                "raw_output": raw_response
            }

    def _extract_json_block(self, text):
        """
        Extracts and parses a JSON object from raw model response.
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())
