# financial_agent.py
# Agent to extract normalized KPIs and deal metrics from unstructured CIM text

from orchestrator.base_agent import BaseAgent
import re
import json
from typing import Optional

class FinancialAgent(BaseAgent):
    """
    Agent to extract key financial metrics from CIM documents.
    Output is parsed into metric blocks compatible with the `deal_metrics` Supabase table.
    """

    def __init__(self, user_id: Optional[str] = None, deal_id: Optional[str] = None):
        """
        Initialize the financial agent.
        
        Args:
            user_id: Optional user ID for model configuration
            deal_id: Optional deal ID for model configuration
        """
        super().__init__(agent_name="financial_agent", user_id=user_id, deal_id=deal_id)

    def _get_use_case(self) -> str:
        """
        Get the use case for this agent.
        """
        return "cim_analysis"

    def _get_prompt(self, text: str, context: Optional[dict] = None) -> str:
        """
        Generates a prompt for the AI to extract financial metrics that match the deal_metrics table structure.
        """
        return f"""You are a financial analyst. Extract key financial metrics from the following CIM document.

The metrics MUST follow this EXACT structure to match our database schema:

[
    {{
        "deal_id": "string", // Will be added by the system
        "metric_name": "string", // Name of the metric (e.g., "Revenue", "EBITDA", "Gross Margin")
        "metric_value": numeric, // The actual value (e.g., 1000000, 15.5, 2.5)
        "metric_unit": "string", // Unit of measurement (e.g., "$", "%", "x")
        "source_chunk_id": "string", // Will be added by the system
        "pinned": boolean // Whether this is a key metric
    }}
]

IMPORTANT:
- Each metric must have all fields
- metric_value must be a number (not a string)
- metric_unit should be appropriate for the metric
- pinned should be true for key metrics

CIM Document:
{text}

Extract all relevant financial metrics following the structure above. Focus on:
1. Revenue metrics
2. Profitability metrics
3. Growth rates
4. Valuation multiples
5. Key ratios
6. Market size metrics
7. Historical trends
8. Projections

Return ONLY the JSON array with no additional text or explanation."""

    def parse_response(self, raw_response):
        """
        Parses the response into a list of financial metrics that exactly match the deal_metrics table structure.
        """
        try:
            parsed = self._extract_json_block(raw_response)
            
            # Ensure we have a list of metrics
            if not isinstance(parsed, list):
                parsed = [parsed]
                
            # Transform each metric to match deal_metrics table structure
            metrics = []
            for metric in parsed:
                # Validate and transform each metric
                transformed = {
                    "metric_name": str(metric.get("metric_name", "")),
                    "metric_value": float(metric.get("metric_value", 0.0)),
                    "metric_unit": str(metric.get("metric_unit", "")),
                    "pinned": bool(metric.get("pinned", False))
                }
                
                metrics.append(transformed)
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error parsing financial metrics: {str(e)}")
            return []

    def _extract_json_block(self, text):
        """
        Extracts the first brace-to-brace block from LLM output (fallback-safe)
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

    def _normalize_output(self, parsed):
        """
        Converts raw GPT output to a list of clean metrics expected by the system.
        This is now handled by parse_response.
        """
        return parsed  # No longer needed as parse_response handles normalization

    def _infer_unit_from_name(self, metric_name):
        """
        Infers unit from metric name when value is already numeric
        """
        name_lower = metric_name.lower()
        if any(x in name_lower for x in ["revenue", "ebitda", "income", "cash flow"]):
            return "USD"
        if any(x in name_lower for x in ["margin", "growth", "cagr"]):
            return "%"
        if any(x in name_lower for x in ["multiple"]):
            return "Multiple"
        return ""

    def _extract_numeric_value(self, val):
        """
        Extracts the first numeric value from a string like "$7.1M" or "21.4%"
        """
        if isinstance(val, (int, float)):
            return val
            
        # Handle common number formats
        val = val.replace(",", "")
        
        # Handle currency values
        if "$" in val:
            val = val.replace("$", "")
            if "M" in val or "million" in val.lower():
                val = val.replace("M", "").replace("million", "")
                try:
                    return float(val) * 1000000
                except:
                    pass
            if "B" in val or "billion" in val.lower():
                val = val.replace("B", "").replace("billion", "")
                try:
                    return float(val) * 1000000000
                except:
                    pass
                    
        # Handle percentages
        if "%" in val:
            val = val.replace("%", "")
            try:
                return float(val) / 100
            except:
                pass
                
        # Handle multipliers
        if "x" in val:
            val = val.replace("x", "")
            try:
                return float(val)
            except:
                pass
                
        # Try to extract any number
        match = re.search(r"[\d\.]+", val)
        if match:
            try:
                return float(match.group())
            except:
                pass
                
        return None

    def _infer_unit(self, val):
        """
        Guesses the unit based on keywords in the value string
        """
        if not isinstance(val, str):
            return ""
        val = val.lower()
        if "%" in val:
            return "%"
        if "m" in val or "million" in val:
            return "USD"
        if "x" in val:
            return "Multiple"
        return ""

    def _validate_output_type(self, output):
        """
        Validates that the output matches the deal_metrics table structure exactly.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, list):
            return False
            
        required_fields = {
            "metric_name": str,
            "metric_value": (int, float),
            "metric_unit": str,
            "pinned": bool
        }
        
        for metric in output:
            if not isinstance(metric, dict):
                return False
                
            # Check all required fields exist and have correct types
            for field, expected_type in required_fields.items():
                if field not in metric:
                    return False
                if not isinstance(metric[field], expected_type):
                    return False
                    
        return True
