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

    def _get_prompt(self, context):
        """
        Generates a prompt for the AI to analyze risks that match the ai_outputs table structure.
        """
        return f"""You are a risk analyst. Analyze the following CIM document for potential risks and issues.

The output MUST follow this EXACT structure to match our database schema:

{{
    "deal_id": "string", // Will be added by the system
    "agent_type": "risk_agent", // Fixed value
    "output_json": {{
        "risk_summary": "string", // Overall risk assessment
        "risk_categories": {{
            "market_risks": [], // Array of market-related risks
            "financial_risks": [], // Array of financial risks
            "operational_risks": [], // Array of operational risks
            "regulatory_risks": [], // Array of regulatory risks
            "other_risks": [] // Array of other identified risks
        }},
        "risk_scores": {{
            "market_risk": float, // 0.0 to 1.0
            "financial_risk": float, // 0.0 to 1.0
            "operational_risk": float, // 0.0 to 1.0
            "regulatory_risk": float, // 0.0 to 1.0
            "overall_risk": float // 0.0 to 1.0
        }},
        "mitigation_strategies": [], // Array of suggested risk mitigation strategies
        "confidence_score": float // 0.0 to 1.0 indicating confidence in the analysis
    }}
}}

IMPORTANT:
- All fields must be present
- Risk scores must be between 0.0 and 1.0
- Each risk category must be an array
- confidence_score must be between 0.0 and 1.0
- risk_summary should be a concise overview

CIM Document:
{context}

Analyze the document for risks following the structure above. Focus on:
1. Market risks (competition, demand, pricing)
2. Financial risks (liquidity, leverage, growth)
3. Operational risks (execution, scalability, technology)
4. Regulatory risks (compliance, legal, policy)
5. Other significant risks
6. Potential mitigation strategies

Return ONLY the JSON object with no additional text or explanation."""

    def parse_response(self, raw_response):
        """
        Parses the response into a risk analysis object that exactly matches the ai_outputs table structure.
        """
        try:
            parsed = self._extract_json_block(raw_response)
            
            # Transform to match ai_outputs table structure
            output = {
                "agent_type": "risk_agent",
                "output_json": {
                    "risk_summary": str(parsed.get("risk_summary", "")),
                    "risk_categories": {
                        "market_risks": list(parsed.get("risk_categories", {}).get("market_risks", [])),
                        "financial_risks": list(parsed.get("risk_categories", {}).get("financial_risks", [])),
                        "operational_risks": list(parsed.get("risk_categories", {}).get("operational_risks", [])),
                        "regulatory_risks": list(parsed.get("risk_categories", {}).get("regulatory_risks", [])),
                        "other_risks": list(parsed.get("risk_categories", {}).get("other_risks", []))
                    },
                    "risk_scores": {
                        "market_risk": float(parsed.get("risk_scores", {}).get("market_risk", 0.0)),
                        "financial_risk": float(parsed.get("risk_scores", {}).get("financial_risk", 0.0)),
                        "operational_risk": float(parsed.get("risk_scores", {}).get("operational_risk", 0.0)),
                        "regulatory_risk": float(parsed.get("risk_scores", {}).get("regulatory_risk", 0.0)),
                        "overall_risk": float(parsed.get("risk_scores", {}).get("overall_risk", 0.0))
                    },
                    "mitigation_strategies": list(parsed.get("mitigation_strategies", [])),
                    "confidence_score": float(parsed.get("confidence_score", 0.0))
                }
            }
            
            # Validate and normalize risk scores
            for score in output["output_json"]["risk_scores"].values():
                score = max(0.0, min(1.0, score))
                
            # Validate confidence score
            output["output_json"]["confidence_score"] = max(0.0, min(1.0, output["output_json"]["confidence_score"]))
            
            return output

        except Exception as e:
            # Return a valid structure even in error case
            return {
                "agent_type": "risk_agent",
                "output_json": {
                    "risk_summary": "",
                    "risk_categories": {
                        "market_risks": [],
                        "financial_risks": [],
                        "operational_risks": [],
                        "regulatory_risks": [],
                        "other_risks": []
                    },
                    "risk_scores": {
                        "market_risk": 0.0,
                        "financial_risk": 0.0,
                        "operational_risk": 0.0,
                        "regulatory_risk": 0.0,
                        "overall_risk": 0.0
                    },
                    "mitigation_strategies": [],
                    "confidence_score": 0.0,
                    "error": f"Could not parse risk analysis: {str(e)}"
                }
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
        Validates that the output matches the ai_outputs table structure exactly.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        # Check required fields
        if "agent_type" not in output or output["agent_type"] != "risk_agent":
            return False
            
        if "output_json" not in output or not isinstance(output["output_json"], dict):
            return False
            
        output_json = output["output_json"]
        
        # Check required output_json fields
        required_fields = {
            "risk_summary": str,
            "risk_categories": dict,
            "risk_scores": dict,
            "mitigation_strategies": list,
            "confidence_score": (int, float)
        }
        
        for field, expected_type in required_fields.items():
            if field not in output_json:
                return False
            if not isinstance(output_json[field], expected_type):
                return False
                
        # Validate risk categories
        required_categories = ["market_risks", "financial_risks", "operational_risks", "regulatory_risks", "other_risks"]
        for category in required_categories:
            if category not in output_json["risk_categories"]:
                return False
            if not isinstance(output_json["risk_categories"][category], list):
                return False
                
        # Validate risk scores
        required_scores = ["market_risk", "financial_risk", "operational_risk", "regulatory_risk", "overall_risk"]
        for score in required_scores:
            if score not in output_json["risk_scores"]:
                return False
            if not isinstance(output_json["risk_scores"][score], (int, float)):
                return False
            if not 0.0 <= output_json["risk_scores"][score] <= 1.0:
                return False
                
        # Validate confidence score range
        if not 0.0 <= output_json["confidence_score"] <= 1.0:
            return False
                
        return True

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
