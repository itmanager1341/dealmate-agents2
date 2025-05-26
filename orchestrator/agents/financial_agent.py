# financial_agent.py
# Agent to extract normalized KPIs and deal metrics from unstructured CIM text

from orchestrator.base_agent import BaseAgent
import re
import json

class FinancialAgent(BaseAgent):
    """
    Agent to extract key financial metrics from CIM documents using GPT-4o.
    Output is parsed into metric blocks compatible with the `deal_metrics` Supabase table.
    """

    def __init__(self):
        super().__init__(agent_name="financial_agent", model="gpt-4o")

    def _get_prompt(self, context):
        """
        Generates a prompt for the AI to extract financial metrics that match the deal_metrics table structure.
        """
        return f"""You are a financial analyst. Extract key financial metrics from the following CIM document.

The metrics MUST follow this EXACT structure to match our database schema:

[
    {{
        "deal_id": "string", // Will be added by the system
        "metric_name": "string", // Name of the metric (e.g., "Revenue", "EBITDA", "Gross Margin")
        "metric_value": "string", // The actual value (e.g., "$10M", "15%", "2.5x")
        "metric_type": "string", // One of: "revenue", "profitability", "growth", "multiple", "other"
        "time_period": "string", // The period this metric applies to (e.g., "2023", "LTM", "5Y CAGR")
        "source_section": "string", // Where in the document this was found
        "confidence_score": float // 0.0 to 1.0 indicating confidence in the extraction
    }}
]

IMPORTANT:
- Each metric must have all fields
- metric_type must be one of: revenue, profitability, growth, multiple, other
- confidence_score must be between 0.0 and 1.0
- metric_value should preserve units (%, $, x, etc.)
- time_period should be specific when available

CIM Document:
{context}

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
                    "metric_value": str(metric.get("metric_value", "")),
                    "metric_type": str(metric.get("metric_type", "other")).lower(),
                    "time_period": str(metric.get("time_period", "")),
                    "source_section": str(metric.get("source_section", "")),
                    "confidence_score": float(metric.get("confidence_score", 0.0))
                }
                
                # Validate metric_type
                if transformed["metric_type"] not in ["revenue", "profitability", "growth", "multiple", "other"]:
                    transformed["metric_type"] = "other"
                    
                # Validate confidence_score
                transformed["confidence_score"] = max(0.0, min(1.0, transformed["confidence_score"]))
                
                metrics.append(transformed)
                
            return metrics

        except Exception as e:
            # Return empty list in error case
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
            "metric_value": str,
            "metric_type": str,
            "time_period": str,
            "source_section": str,
            "confidence_score": (int, float)
        }
        
        valid_metric_types = ["revenue", "profitability", "growth", "multiple", "other"]
        
        for metric in output:
            if not isinstance(metric, dict):
                return False
                
            # Check all required fields exist and have correct types
            for field, expected_type in required_fields.items():
                if field not in metric:
                    return False
                if not isinstance(metric[field], expected_type):
                    return False
                    
            # Validate metric_type
            if metric["metric_type"].lower() not in valid_metric_types:
                return False
                
            # Validate confidence_score range
            if not 0.0 <= metric["confidence_score"] <= 1.0:
                return False
                
        return True
