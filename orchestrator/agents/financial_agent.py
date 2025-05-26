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

    def build_prompt(self, document_text, context={}):
        """
        Constructs the prompt sent to the LLM. Focuses on extracting structured KPIs.
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are a private equity analyst. Extract key financial metrics from the provided text. "
                    "Pay special attention to tables and charts, which often contain the most important metrics. "
                    "Look for metrics in both narrative text and structured data. "
                    "Only use data explicitly found in the text. Do not assume values. "
                    "Format the output as structured JSON. "
                    "Include the original sentence, table row, or source text next to each metric for traceability."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extract the following from the CIM:\n"
                    "- Revenue (TTM or 2024E)\n"
                    "- EBITDA and EBITDA Margin\n"
                    "- Revenue CAGR (3–5 years)\n"
                    "- Deal size estimate (implied enterprise value)\n"
                    "- Revenue and EBITDA multiples\n"
                    "- Any available growth rates, net income, or free cash flow\n\n"
                    "Text:\n" + document_text[:10000]  # safely within GPT-4o context window
                )
            }
        ]

    def parse_response(self, raw_response):
        """
        Converts raw model output into a structured list of metrics.
        Accepts both JSON and JSON-like bullet formats and converts to uniform format.
        """
        try:
            # Try direct JSON block parsing
            parsed_json = self._extract_json_block(raw_response)
            return self._normalize_output(parsed_json)
        except Exception:
            return {
                "error": "Could not parse model response. Raw output:",
                "raw_output": raw_response
            }

    def _extract_json_block(self, text):
        """
        Extracts the first brace-to-brace block from LLM output (fallback-safe)
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in response.")
        return json.loads(match.group())

    def _normalize_output(self, parsed):
        """
        Converts raw GPT output to a list of clean metrics expected by the system
        """
        metric_list = []
        for key, value in parsed.items():
            # Normalize keys for standard metric naming
            normalized_name = key.replace("_", " ").title()
            
            # Handle both string and numeric values
            if isinstance(value, (int, float)):
                metric_value = value
                unit = self._infer_unit_from_name(normalized_name)
                source_text = f"Extracted from table or chart: {normalized_name}"
            else:
                metric_value = self._extract_numeric_value(value)
                unit = self._infer_unit(value)
                source_text = value if isinstance(value, str) else ""
            
            # Skip if no valid numeric value found
            if metric_value is None:
                continue
                
            metric = {
                "metric_name": normalized_name,
                "metric_value": metric_value,
                "metric_unit": unit,
                "source_text": source_text,
                "pinned": True
            }
            metric_list.append(metric)
        return metric_list

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
        Validates that the output is a list of metric dictionaries.
        
        Args:
            output: The parsed output to validate
            
        Returns:
            bool: True if output is valid, False otherwise
        """
        if not isinstance(output, list):
            return False
            
        for metric in output:
            if not isinstance(metric, dict):
                return False
            if not all(k in metric for k in ["metric_name", "metric_value"]):
                return False
                
        return True
