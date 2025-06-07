# chart_agent.py
# Agent to extract and analyze charts, graphs, and tables from CIM documents

from orchestrator.base_agent import BaseAgent
from orchestrator.tools import Tool, TOOL_REGISTRY
import re
import json
from typing import Optional, Dict, List

class ChartAgent(BaseAgent):
    """
    Agent that extracts and analyzes charts, graphs, and tables from CIM documents.
    Outputs structured data about visual elements and their relationships to text.
    """

    def __init__(
        self,
        agent_name: str = "chart_agent",
        user_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        toolbox: Dict[str, Tool] = None
    ):
        """
        Initialize the chart agent.
        
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
        Generates a prompt for the AI to analyze charts that matches the chart_elements table structure.
        """
        return f"""You are a chart analysis expert. Analyze the following CIM document for charts, graphs, and tables.

The output MUST follow this EXACT structure to match our database schema:

{{
    "deal_id": "string", // Will be added by the system
    "agent_type": "chart_agent", // Fixed value
    "output_json": {{
        "chart_elements": [
            {{
                "chart_type": "string", // One of: "bar", "line", "pie", "table", "other"
                "title": "string", // Chart title or caption
                "description": "string", // Description of the chart's content
                "data_points": {{}}, // Structured data from the chart
                "source_page": integer, // Page number where chart appears
                "confidence_score": float, // 0.0 to 1.0
                "metadata": {{
                    "axis_labels": [], // Array of axis labels
                    "units": [], // Array of units
                    "categories": [], // Array of categories
                    "time_period": "string", // Time period covered
                    "source": "string" // Data source if mentioned
                }}
            }}
        ],
        "chart_relationships": [
            {{
                "chart_id": "string", // Reference to chart element
                "related_text": "string", // Related text section
                "relationship_type": "string", // One of: "explanation", "reference", "data_source"
                "confidence_score": float // 0.0 to 1.0
            }}
        ],
        "analysis_summary": "string", // Overall analysis of charts
        "confidence_score": float // 0.0 to 1.0 indicating confidence in the analysis
    }}
}}

IMPORTANT:
- All fields must be present
- Chart types must be one of: bar, line, pie, table, other
- Confidence scores must be between 0.0 and 1.0
- Data points should be structured based on chart type
- Metadata should include all available chart information

CIM Document:
{context}

Analyze the document for charts following the structure above. Focus on:
1. Chart identification and classification
2. Data point extraction and structuring
3. Chart context and relationships
4. Metadata extraction
5. Confidence scoring

Return ONLY the JSON object with no additional text or explanation."""

    def parse_response(self, raw_response):
        """
        Parses the response into a chart analysis object that exactly matches the chart_elements table structure.
        """
        try:
            parsed = self._extract_json_block(raw_response)
            
            # Transform to match chart_elements table structure
            output = {
                "agent_type": "chart_agent",
                "output_json": {
                    "chart_elements": [
                        {
                            "chart_type": str(chart.get("chart_type", "other")).lower(),
                            "title": str(chart.get("title", "")),
                            "description": str(chart.get("description", "")),
                            "data_points": chart.get("data_points", {}),
                            "source_page": int(chart.get("source_page", 0)),
                            "confidence_score": float(chart.get("confidence_score", 0.0)),
                            "metadata": chart.get("metadata", {})
                        }
                        for chart in parsed.get("chart_elements", [])
                    ],
                    "chart_relationships": [
                        {
                            "chart_id": str(rel.get("chart_id", "")),
                            "related_text": str(rel.get("related_text", "")),
                            "relationship_type": str(rel.get("relationship_type", "reference")).lower(),
                            "confidence_score": float(rel.get("confidence_score", 0.0))
                        }
                        for rel in parsed.get("chart_relationships", [])
                    ],
                    "analysis_summary": str(parsed.get("analysis_summary", "")),
                    "confidence_score": float(parsed.get("confidence_score", 0.0))
                }
            }
            
            # Validate and normalize confidence scores
            for chart in output["output_json"]["chart_elements"]:
                chart["confidence_score"] = max(0.0, min(1.0, chart["confidence_score"]))
                
            for rel in output["output_json"]["chart_relationships"]:
                rel["confidence_score"] = max(0.0, min(1.0, rel["confidence_score"]))
                
            output["output_json"]["confidence_score"] = max(0.0, min(1.0, output["output_json"]["confidence_score"]))
            
            return output

        except Exception as e:
            # Return a valid structure even in error case
            return {
                "agent_type": "chart_agent",
                "output_json": {
                    "chart_elements": [],
                    "chart_relationships": [],
                    "analysis_summary": "",
                    "confidence_score": 0.0,
                    "error": f"Could not parse chart analysis: {str(e)}"
                }
            }

    def _extract_json_block(self, text):
        """
        Extracts and parses a JSON object from raw model response.
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())

    def _validate_output_type(self, output):
        """
        Validates that the output matches the chart_elements table structure exactly.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        # Check required fields
        if "agent_type" not in output or output["agent_type"] != "chart_agent":
            return False
            
        if "output_json" not in output or not isinstance(output["output_json"], dict):
            return False
            
        output_json = output["output_json"]
        
        # Check required output_json fields
        required_fields = {
            "chart_elements": list,
            "chart_relationships": list,
            "analysis_summary": str,
            "confidence_score": (int, float)
        }
        
        for field, expected_type in required_fields.items():
            if field not in output_json:
                return False
            if not isinstance(output_json[field], expected_type):
                return False
                
        # Validate chart elements
        valid_chart_types = ["bar", "line", "pie", "table", "other"]
        for chart in output_json["chart_elements"]:
            if not isinstance(chart, dict):
                return False
            if not all(k in chart for k in ["chart_type", "title", "description", "data_points", "source_page", "confidence_score", "metadata"]):
                return False
            if chart["chart_type"] not in valid_chart_types:
                return False
            if not 0.0 <= chart["confidence_score"] <= 1.0:
                return False
                
        # Validate chart relationships
        valid_relationship_types = ["explanation", "reference", "data_source"]
        for rel in output_json["chart_relationships"]:
            if not isinstance(rel, dict):
                return False
            if not all(k in rel for k in ["chart_id", "related_text", "relationship_type", "confidence_score"]):
                return False
            if rel["relationship_type"] not in valid_relationship_types:
                return False
            if not 0.0 <= rel["confidence_score"] <= 1.0:
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
