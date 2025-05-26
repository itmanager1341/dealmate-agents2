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

            # Ensure investment_grade is always provided with a default
            investment_grade = parsed.get("investment_grade", "B")
            if not isinstance(investment_grade, str) or investment_grade not in ["A+", "A", "B+", "B", "C"]:
                investment_grade = "B"  # Default to B if invalid

            # Enforce required fields with defaults
            return {
                "investment_grade": investment_grade,
                "company_overview": parsed.get("business_model", ""),  # Map business_model to company_overview
                "market_analysis": parsed.get("market_analysis", ""),
                "financial_analysis": parsed.get("financial_summary", ""),  # Map financial_summary to financial_analysis
                "risk_analysis": "\n".join(parsed.get("key_risks", [])),  # Convert list to string
                "investment_thesis": parsed.get("executive_summary", ""),  # Map executive_summary to investment_thesis
                "deal_considerations": parsed.get("recommendation", {}).get("rationale", ""),  # Extract rationale
                "raw_ai_response": raw_response  # for debug or re-display
            }

        except Exception as e:
            # Return a valid structure even in error case
            return {
                "investment_grade": "B",  # Default grade
                "company_overview": "",
                "market_analysis": "",
                "financial_analysis": "",
                "risk_analysis": "",
                "investment_thesis": "",
                "deal_considerations": "",
                "raw_ai_response": raw_response,
                "error": f"Could not parse memo response: {str(e)}"
            }

    def _extract_json_block(self, text):
        """
        Extract and parse first valid JSON block from response
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())

    def _validate_output_type(self, output):
        """
        Validates that the output is a dictionary with memo sections.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        required_sections = [
            "investment_grade",
            "company_overview",
            "market_analysis",
            "financial_analysis",
            "risk_analysis",
            "investment_thesis",
            "deal_considerations"
        ]
        
        # Check all required sections exist and are strings
        if not all(section in output for section in required_sections):
            return False
            
        for section in required_sections:
            if not isinstance(output[section], str):
                return False
                
        # Validate investment_grade specifically
        if output["investment_grade"] not in ["A+", "A", "B+", "B", "C"]:
            return False
                
        return True
