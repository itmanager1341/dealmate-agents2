# consistency_agent.py
# Agent to identify inconsistencies between CIM narrative, financials, and risk disclosures

from orchestrator.base_agent import BaseAgent
from orchestrator.tools import Tool, TOOL_REGISTRY
import re
import json
from typing import Optional, Dict

class ConsistencyAgent(BaseAgent):
    """
    Agent that cross-analyzes CIM content for logical consistency between
    narrative claims, financial performance, and risk disclosures.
    """

    def __init__(
        self,
        agent_name: str = "consistency_agent",
        user_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        toolbox: Dict[str, Tool] = None
    ):
        """
        Initialize the consistency agent.
        
        Args:
            agent_name: Name of the agent
            user_id: Optional user ID for model configuration
            deal_id: Optional deal ID for model configuration
            toolbox: Optional dictionary of tools to use. Defaults to TOOL_REGISTRY.
        """
        super().__init__(
            agent_name=agent_name,
            user_id=user_id,
            deal_id=deal_id,
            toolbox=toolbox
        )

    def _get_use_case(self) -> str:
        """
        Get the use case for this agent.
        """
        return "cim_analysis"

    def _get_prompt(self, context):
        """
        Generates a prompt for the AI to check consistency that matches the ai_outputs table structure.
        """
        return f"""You are a consistency analyst. Check the following CIM document for inconsistencies and contradictions.

The output MUST follow this EXACT structure to match our database schema:

{{
    "deal_id": "string", // Will be added by the system
    "agent_type": "consistency_agent", // Fixed value
    "output_json": {{
        "consistency_summary": "string", // Overall consistency assessment
        "inconsistencies": [
            {{
                "type": "string", // One of: "financial", "narrative", "metric", "timeline", "other"
                "description": "string", // Description of the inconsistency
                "location": "string", // Where in the document this was found
                "severity": "string", // One of: "high", "medium", "low"
                "impact": "string", // Impact on analysis
                "resolution": "string" // Suggested resolution
            }}
        ],
        "consistency_scores": {{
            "financial_consistency": float, // 0.0 to 1.0
            "narrative_consistency": float, // 0.0 to 1.0
            "metric_consistency": float, // 0.0 to 1.0
            "timeline_consistency": float, // 0.0 to 1.0
            "overall_consistency": float // 0.0 to 1.0
        }},
        "recommendations": [], // Array of recommendations to resolve inconsistencies
        "confidence_score": float // 0.0 to 1.0 indicating confidence in the analysis
    }}
}}

IMPORTANT:
- All fields must be present
- Consistency scores must be between 0.0 and 1.0
- Inconsistency types must be one of: financial, narrative, metric, timeline, other
- Severity must be one of: high, medium, low
- confidence_score must be between 0.0 and 1.0

CIM Document:
{context}

Analyze the document for inconsistencies following the structure above. Focus on:
1. Financial statement consistency
2. Narrative consistency across sections
3. Metric consistency and calculations
4. Timeline consistency
5. Other potential contradictions
6. Recommendations for resolution

Return ONLY the JSON object with no additional text or explanation."""

    def parse_response(self, raw_response):
        """
        Parses the response into a consistency analysis object that exactly matches the ai_outputs table structure.
        """
        try:
            parsed = self._extract_json_block(raw_response)
            
            # Transform to match ai_outputs table structure
            output = {
                "agent_type": "consistency_agent",
                "output_json": {
                    "consistency_summary": str(parsed.get("consistency_summary", "")),
                    "inconsistencies": [
                        {
                            "type": str(inc.get("type", "other")).lower(),
                            "description": str(inc.get("description", "")),
                            "location": str(inc.get("location", "")),
                            "severity": str(inc.get("severity", "medium")).lower(),
                            "impact": str(inc.get("impact", "")),
                            "resolution": str(inc.get("resolution", ""))
                        }
                        for inc in parsed.get("inconsistencies", [])
                    ],
                    "consistency_scores": {
                        "financial_consistency": float(parsed.get("consistency_scores", {}).get("financial_consistency", 0.0)),
                        "narrative_consistency": float(parsed.get("consistency_scores", {}).get("narrative_consistency", 0.0)),
                        "metric_consistency": float(parsed.get("consistency_scores", {}).get("metric_consistency", 0.0)),
                        "timeline_consistency": float(parsed.get("consistency_scores", {}).get("timeline_consistency", 0.0)),
                        "overall_consistency": float(parsed.get("consistency_scores", {}).get("overall_consistency", 0.0))
                    },
                    "recommendations": list(parsed.get("recommendations", [])),
                    "confidence_score": float(parsed.get("confidence_score", 0.0))
                }
            }
            
            # Validate and normalize consistency scores
            for score in output["output_json"]["consistency_scores"].values():
                score = max(0.0, min(1.0, score))
                
            # Validate confidence score
            output["output_json"]["confidence_score"] = max(0.0, min(1.0, output["output_json"]["confidence_score"]))
            
            # Validate inconsistency types and severities
            valid_types = ["financial", "narrative", "metric", "timeline", "other"]
            valid_severities = ["high", "medium", "low"]
            
            for inc in output["output_json"]["inconsistencies"]:
                if inc["type"] not in valid_types:
                    inc["type"] = "other"
                if inc["severity"] not in valid_severities:
                    inc["severity"] = "medium"
            
            return output

        except Exception as e:
            # Return a valid structure even in error case
            return {
                "agent_type": "consistency_agent",
                "output_json": {
                    "consistency_summary": "",
                    "inconsistencies": [],
                    "consistency_scores": {
                        "financial_consistency": 0.0,
                        "narrative_consistency": 0.0,
                        "metric_consistency": 0.0,
                        "timeline_consistency": 0.0,
                        "overall_consistency": 0.0
                    },
                    "recommendations": [],
                    "confidence_score": 0.0,
                    "error": f"Could not parse consistency analysis: {str(e)}"
                }
            }

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
        if "agent_type" not in output or output["agent_type"] != "consistency_agent":
            return False
            
        if "output_json" not in output or not isinstance(output["output_json"], dict):
            return False
            
        output_json = output["output_json"]
        
        # Check required output_json fields
        required_fields = {
            "consistency_summary": str,
            "inconsistencies": list,
            "consistency_scores": dict,
            "recommendations": list,
            "confidence_score": (int, float)
        }
        
        for field, expected_type in required_fields.items():
            if field not in output_json:
                return False
            if not isinstance(output_json[field], expected_type):
                return False
                
        # Validate inconsistencies
        valid_types = ["financial", "narrative", "metric", "timeline", "other"]
        valid_severities = ["high", "medium", "low"]
        
        for inc in output_json["inconsistencies"]:
            if not isinstance(inc, dict):
                return False
            if not all(k in inc for k in ["type", "description", "location", "severity", "impact", "resolution"]):
                return False
            if inc["type"] not in valid_types:
                return False
            if inc["severity"] not in valid_severities:
                return False
                
        # Validate consistency scores
        required_scores = ["financial_consistency", "narrative_consistency", "metric_consistency", "timeline_consistency", "overall_consistency"]
        for score in required_scores:
            if score not in output_json["consistency_scores"]:
                return False
            if not isinstance(output_json["consistency_scores"][score], (int, float)):
                return False
            if not 0.0 <= output_json["consistency_scores"][score] <= 1.0:
                return False
                
        # Validate confidence score range
        if not 0.0 <= output_json["confidence_score"] <= 1.0:
            return False
                
        return True

    def _extract_json_block(self, text):
        """
        Extracts and parses a JSON object from raw model response.
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())

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
