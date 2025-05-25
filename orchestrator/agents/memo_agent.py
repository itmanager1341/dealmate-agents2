# memo_agent.py
# Agent to generate a structured investment memo based on extracted CIM content

from orchestrator.base_agent import BaseAgent
import re
import json

class MemoAgent(BaseAgent):
    """
    Agent that synthesizes a CIM investment memo using financial data, risk analysis,
    and narrative context. Outputs sections aligned with private equity memo format.
    """

    def __init__(self):
        super().__init__(agent_name="memo_agent", model="gpt-4o")

    def build_prompt(self, document_text, context={}):
        """
        Builds a comprehensive prompt to generate an IC-ready memo.
        Optionally passes in context such as extracted KPIs or red flags.
        """
        financials = context.get("financial_metrics", [])
        risks = context.get("risks", [])

        return [
            {
                "role": "system",
                "content": (
                    "You are a private equity associate drafting an internal investment memo "
                    "for an M&A deal. Your goal is to synthesize the CIM content into a memo-style summary, "
                    "using any available financial metrics and risk flags. Be concise and analytical. "
                    "Return a JSON object with structured sections."
                )
            },
            {
                "role": "user",
                "content": (
                    "Generate a memo with the following fields:\n"
                    "{\n"
                    '  "executive_summary": "...",\n'
                    '  "investment_grade": "A+ | A | B+ | B | C",\n'
                    '  "business_model": "...",\n'
                    '  "financial_summary": "...",\n'
                    '  "investment_highlights": [ "...", "..." ],\n'
                    '  "key_risks": [ "...", "..." ],\n'
                    '  "recommendation": { "action": "...", "rationale": "..." }\n'
                    "}\n\n"
                    "You may use the following context:\n\n"
                    f"Financial Metrics: {json.dumps(financials, indent=2)}\n\n"
                    f"Risks: {json.dumps(risks, indent=2)}\n\n"
                    f"CIM Text:\n{document_text[:10000]}"
                )
            }
        ]

    def parse_response(self, raw_response):
        """
        Parses the response into a structured investment memo object.
        """
        try:
            parsed = self._extract_json_block(raw_response)

            # Enforce required fields
            return {
                "executive_summary": parsed.get("executive_summary", ""),
                "investment_grade": parsed.get("investment_grade", "B"),
                "business_model": parsed.get("business_model", ""),
                "financial_summary": parsed.get("financial_summary", ""),
                "investment_highlights": parsed.get("investment_highlights", []),
                "key_risks": parsed.get("key_risks", []),
                "recommendation": parsed.get("recommendation", {}),
                "raw_ai_response": raw_response  # for debug or re-display
            }

        except Exception as e:
            return {
                "error": "Could not parse memo response.",
                "exception": str(e),
                "raw_output": raw_response
            }

    def _extract_json_block(self, text):
        """
        Extract and parse first valid JSON block from response
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())
