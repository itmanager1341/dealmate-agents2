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

    def _get_prompt(self, context):
        """
        Generates a prompt for the AI to create an investment memo that matches the cim_analysis table structure.
        """
        return f"""You are an expert investment analyst. Create a comprehensive investment memo for the following CIM document.

The memo MUST follow this EXACT structure to match our database schema:

{{
    "investment_grade": "A+", // One of: A+, A, B+, B, C
    "executive_summary": "string", // Brief overview of the investment opportunity
    "business_model": {{}}, // JSON object describing the business model
    "financial_metrics": {{}}, // JSON object with key financial metrics
    "key_risks": {{}}, // JSON object detailing major risks
    "competitive_position": {{}}, // JSON object analyzing market position
    "recommendation": {{}}, // JSON object with investment recommendation
    "investment_highlights": [], // Array of key investment points
    "management_questions": [] // Array of questions for management
}}

IMPORTANT:
- All fields must be present
- investment_grade must be one of: A+, A, B+, B, C
- business_model, financial_metrics, key_risks, competitive_position, and recommendation must be JSON objects
- investment_highlights and management_questions must be arrays
- executive_summary must be a string

CIM Document:
{context}

Generate a detailed investment memo following the structure above. Focus on:
1. Clear investment grade based on risk/reward
2. Comprehensive business model analysis
3. Detailed financial metrics
4. Thorough risk assessment
5. Strong competitive analysis
6. Clear investment recommendation
7. Key investment highlights
8. Critical management questions

Return ONLY the JSON object with no additional text or explanation."""

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
        Parses the response into a structured investment memo object that exactly matches the cim_analysis table.
        """
        try:
            parsed = self._extract_json_block(raw_response)

            # Ensure investment_grade is always provided with a default
            investment_grade = parsed.get("investment_grade", "B")
            if not isinstance(investment_grade, str) or investment_grade not in ["A+", "A", "B+", "B", "C"]:
                investment_grade = "B"  # Default to B if invalid

            # Transform to match cim_analysis table structure exactly
            return {
                # Required fields
                "investment_grade": investment_grade,
                "executive_summary": parsed.get("executive_summary", ""),
                
                # JSONB fields
                "business_model": parsed.get("business_model", {}),
                "financial_metrics": parsed.get("financial_metrics", {}),
                "key_risks": parsed.get("key_risks", {}),
                "competitive_position": parsed.get("competitive_position", {}),
                "recommendation": parsed.get("recommendation", {}),
                
                # Array fields
                "investment_highlights": parsed.get("investment_highlights", []),
                "management_questions": parsed.get("management_questions", []),
                
                # Debug field
                "raw_ai_response": raw_response
            }

        except Exception as e:
            # Return a valid structure even in error case
            return {
                # Required fields
                "investment_grade": "B",  # Default grade
                "executive_summary": "",
                
                # JSONB fields
                "business_model": {},
                "financial_metrics": {},
                "key_risks": {},
                "competitive_position": {},
                "recommendation": {},
                
                # Array fields
                "investment_highlights": [],
                "management_questions": [],
                
                # Debug field
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
        Validates that the output matches the cim_analysis table structure exactly.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        # Check required fields
        required_fields = {
            "investment_grade": str,
            "executive_summary": str,
            "business_model": dict,
            "financial_metrics": dict,
            "key_risks": dict,
            "competitive_position": dict,
            "recommendation": dict,
            "investment_highlights": list,
            "management_questions": list
        }
        
        # Validate all required fields exist and have correct types
        for field, expected_type in required_fields.items():
            if field not in output:
                return False
            if not isinstance(output[field], expected_type):
                return False
                
        # Validate investment_grade values
        if output["investment_grade"] not in ["A+", "A", "B+", "B", "C"]:
            return False
                
        return True
