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
        Constructs the prompt sent to the LLM. Focuses only on extracting structured KPIs.
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are a private equity analyst. Extract key financial metrics from the provided text. "
                    "Only use data explicitly found in the text. Do not assume values. Format the output as structured JSON. "
                    "Include the original sentence or source text next to each metric for traceability."
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
            unit = self._infer_unit(value)
            metric = {
                "metric_name": normalized_name,
                "metric_value": self._extract_numeric_value(value),
                "metric_unit": unit,
                "source_text": value if isinstance(value, str) else "",
                "pinned": True
            }
            metric_list.append(metric)
        return metric_list

    def _extract_numeric_value(self, val):
        """
        Extracts the first numeric value from a string like "$7.1M" or "21.4%"
        """
        if isinstance(val, (int, float)):
            return val
        match = re.search(r"[\d\.\,]+", val.replace(",", ""))
        if not match:
            return None
        try:
            return float(match.group())
        except:
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
