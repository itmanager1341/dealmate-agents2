# quote_agent.py
# Agent to extract and analyze quotes, testimonials, and key statements from CIM documents

from orchestrator.base_agent import BaseAgent
from orchestrator.tools import Tool, TOOL_REGISTRY
import re
import json
from typing import Optional, Dict, List

class QuoteAgent(BaseAgent):
    """
    Agent that extracts and analyzes quotes, testimonials, and key statements
    from CIM documents. Identifies speaker context and statement significance.
    """

    def __init__(
        self,
        agent_name: str = "quote_agent",
        user_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        toolbox: Dict[str, Tool] = None
    ):
        """
        Initialize the quote agent.
        
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
        Generates a prompt for the AI to analyze quotes that matches the document_quotes table structure.
        """
        return f"""You are a quote analysis expert. Analyze the following CIM document for quotes, testimonials, and key statements.

The output MUST follow this EXACT structure to match our database schema:

{{
    "deal_id": "string", // Will be added by the system
    "agent_type": "quote_agent", // Fixed value
    "output_json": {{
        "quotes": [
            {{
                "quote_text": "string", // The actual quote
                "speaker": "string", // Name of the person quoted
                "speaker_title": "string", // Speaker's title/position
                "context": "string", // Surrounding context
                "significance_score": float, // 0.0 to 1.0
                "quote_type": "string", // One of: "testimonial", "executive", "customer", "expert", "other"
                "metadata": {{
                    "sentiment": "string", // One of: "positive", "negative", "neutral"
                    "topics": [], // Array of topics discussed
                    "key_points": [], // Array of key points made
                    "source_section": "string" // Section where quote appears
                }}
            }}
        ],
        "quote_relationships": [
            {{
                "quote_id": "string", // Reference to quote
                "related_metric": "string", // Related metric or KPI
                "relationship_type": "string", // One of: "supports", "contradicts", "contextualizes"
                "confidence_score": float // 0.0 to 1.0
            }}
        ],
        "analysis_summary": "string", // Overall analysis of quotes
        "confidence_score": float // 0.0 to 1.0 indicating confidence in the analysis
    }}
}}

IMPORTANT:
- All fields must be present
- Quote types must be one of: testimonial, executive, customer, expert, other
- Significance and confidence scores must be between 0.0 and 1.0
- Sentiment must be one of: positive, negative, neutral
- Metadata should include all available quote information

CIM Document:
{context}

Analyze the document for quotes following the structure above. Focus on:
1. Quote identification and extraction
2. Speaker identification and context
3. Quote significance and sentiment
4. Relationship to metrics and KPIs
5. Overall analysis and insights

Return ONLY the JSON object with no additional text or explanation."""

    def parse_response(self, raw_response):
        """
        Parses the response into a quote analysis object that exactly matches the document_quotes table structure.
        """
        try:
            parsed = self._extract_json_block(raw_response)
            
            # Transform to match document_quotes table structure
            output = {
                "agent_type": "quote_agent",
                "output_json": {
                    "quotes": [
                        {
                            "quote_text": str(quote.get("quote_text", "")),
                            "speaker": str(quote.get("speaker", "")),
                            "speaker_title": str(quote.get("speaker_title", "")),
                            "context": str(quote.get("context", "")),
                            "significance_score": float(quote.get("significance_score", 0.0)),
                            "quote_type": str(quote.get("quote_type", "other")).lower(),
                            "metadata": quote.get("metadata", {})
                        }
                        for quote in parsed.get("quotes", [])
                    ],
                    "quote_relationships": [
                        {
                            "quote_id": str(rel.get("quote_id", "")),
                            "related_metric": str(rel.get("related_metric", "")),
                            "relationship_type": str(rel.get("relationship_type", "contextualizes")).lower(),
                            "confidence_score": float(rel.get("confidence_score", 0.0))
                        }
                        for rel in parsed.get("quote_relationships", [])
                    ],
                    "analysis_summary": str(parsed.get("analysis_summary", "")),
                    "confidence_score": float(parsed.get("confidence_score", 0.0))
                }
            }
            
            # Validate and normalize scores
            for quote in output["output_json"]["quotes"]:
                quote["significance_score"] = max(0.0, min(1.0, quote["significance_score"]))
                
            for rel in output["output_json"]["quote_relationships"]:
                rel["confidence_score"] = max(0.0, min(1.0, rel["confidence_score"]))
                
            output["output_json"]["confidence_score"] = max(0.0, min(1.0, output["output_json"]["confidence_score"]))
            
            return output

        except Exception as e:
            # Return a valid structure even in error case
            return {
                "agent_type": "quote_agent",
                "output_json": {
                    "quotes": [],
                    "quote_relationships": [],
                    "analysis_summary": "",
                    "confidence_score": 0.0,
                    "error": f"Could not parse quote analysis: {str(e)}"
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
        Validates that the output matches the document_quotes table structure exactly.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, dict):
            return False
            
        # Check required fields
        if "agent_type" not in output or output["agent_type"] != "quote_agent":
            return False
            
        if "output_json" not in output or not isinstance(output["output_json"], dict):
            return False
            
        output_json = output["output_json"]
        
        # Check required output_json fields
        required_fields = {
            "quotes": list,
            "quote_relationships": list,
            "analysis_summary": str,
            "confidence_score": (int, float)
        }
        
        for field, expected_type in required_fields.items():
            if field not in output_json:
                return False
            if not isinstance(output_json[field], expected_type):
                return False
                
        # Validate quotes
        valid_quote_types = ["testimonial", "executive", "customer", "expert", "other"]
        valid_sentiments = ["positive", "negative", "neutral"]
        
        for quote in output_json["quotes"]:
            if not isinstance(quote, dict):
                return False
            if not all(k in quote for k in ["quote_text", "speaker", "speaker_title", "context", "significance_score", "quote_type", "metadata"]):
                return False
            if quote["quote_type"] not in valid_quote_types:
                return False
            if not 0.0 <= quote["significance_score"] <= 1.0:
                return False
            if quote["metadata"].get("sentiment") not in valid_sentiments:
                return False
                
        # Validate quote relationships
        valid_relationship_types = ["supports", "contradicts", "contextualizes"]
        for rel in output_json["quote_relationships"]:
            if not isinstance(rel, dict):
                return False
            if not all(k in rel for k in ["quote_id", "related_metric", "relationship_type", "confidence_score"]):
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
