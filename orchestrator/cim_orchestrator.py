# cim_orchestrator.py
# Coordinates multi-agent analysis of CIM documents

import fitz  # PyMuPDF
from orchestrator.agents.financial_agent import FinancialAgent
from orchestrator.agents.risk_agent import RiskAgent
from orchestrator.agents.memo_agent import MemoAgent
from orchestrator.agents.consistency_agent import ConsistencyAgent

class CIMOrchestrator:
    """
    Coordinates execution of all core DealMate agents to process a CIM document.
    """

    def __init__(self):
        self.agents = {
            "financial": FinancialAgent(),
            "risk": RiskAgent(),
            "memo": MemoAgent(),
            "consistency": ConsistencyAgent()
        }

    def load_pdf_text(self, file_path):
        """
        Uses PyMuPDF to extract full text from a PDF CIM, handling complex layouts.
        """
        doc = fitz.open(file_path)
        full_text = []
        
        for page in doc:
            # Extract text with layout preservation
            blocks = page.get_text("blocks")
            
            for block in blocks:
                # block[4] contains the text
                text = block[4].strip()
                if text:
                    # Add page number for reference
                    full_text.append(f"[Page {page.number + 1}] {text}")
            
            # Extract tables if present
            tables = page.find_tables()
            if tables:
                for table in tables:
                    table_text = []
                    for row in table.extract():
                        table_text.append(" | ".join(str(cell) for cell in row))
                    full_text.append("\n".join(table_text))
        
        # Join all text with proper spacing
        return "\n\n".join(full_text)

    def run_all(self, file_path, deal_id="unknown"):
        """
        Runs all agents in sequence and returns a structured response object.
        """
        output = {
            "deal_id": deal_id,
            "status": "started",
            "results": {},
            "errors": [],
            "logs": {}
        }

        try:
            # Step 1: Extract CIM text
            cim_text = self.load_pdf_text(file_path)
            if not cim_text.strip():
                raise ValueError("No text could be extracted from the PDF")
            output["status"] = "text_extracted"
            output["logs"]["text_extraction"] = f"Extracted {len(cim_text.split())} words"

            # Step 2: Run financial agent
            result_fin = self.agents["financial"].execute(cim_text, deal_id)
            if result_fin.get("success"):
                if isinstance(result_fin.get("output"), list):
                    output["results"]["financial"] = result_fin
                    output["logs"]["financial"] = f"Extracted {len(result_fin['output'])} metrics"
                else:
                    output["errors"].append("Financial agent returned invalid output type")
                    result_fin["success"] = False
                    result_fin["error"] = "Invalid output type - expected list"
            output["results"]["financial"] = result_fin
            output["logs"]["financial"] = result_fin.get("log", [])

            # Step 3: Run risk agent
            result_risk = self.agents["risk"].execute(cim_text, deal_id)
            if result_risk.get("success"):
                if isinstance(result_risk.get("output"), dict) and "items" in result_risk.get("output", {}):
                    output["results"]["risk"] = result_risk
                    output["logs"]["risk"] = f"Identified {len(result_risk['output']['items'])} risks"
                else:
                    output["errors"].append("Risk agent returned invalid output type")
                    result_risk["success"] = False
                    result_risk["error"] = "Invalid output type - expected dict with items"
            output["results"]["risk"] = result_risk
            output["logs"]["risk"] = result_risk.get("log", [])

            # Step 4: Run consistency agent with context
            result_consistency = self.agents["consistency"].execute(
                cim_text,
                deal_id=deal_id,
                context={
                    "financial_metrics": result_fin.get("output", []),
                    "risks": result_risk.get("output", {}).get("items", [])
                }
            )
            if result_consistency.get("success"):
                if isinstance(result_consistency.get("output"), dict) and "items" in result_consistency.get("output", {}):
                    output["results"]["consistency"] = result_consistency
                    output["logs"]["consistency"] = f"Found {len(result_consistency['output']['items'])} inconsistencies"
                else:
                    output["errors"].append("Consistency agent returned invalid output type")
                    result_consistency["success"] = False
                    result_consistency["error"] = "Invalid output type - expected dict with items"
            output["results"]["consistency"] = result_consistency
            output["logs"]["consistency"] = result_consistency.get("log", [])

            # Step 5: Run memo agent last (context-aware)
            result_memo = self.agents["memo"].execute(
                cim_text,
                deal_id=deal_id,
                context={
                    "financial_metrics": result_fin.get("output", []),
                    "risks": result_risk.get("output", {}).get("items", [])
                }
            )
            if result_memo.get("success"):
                if isinstance(result_memo.get("output"), dict):
                    output["results"]["memo"] = result_memo
                    output["logs"]["memo"] = "Generated investment memo"
                else:
                    output["errors"].append("Memo agent returned invalid output type")
                    result_memo["success"] = False
                    result_memo["error"] = "Invalid output type - expected dict"
            output["results"]["memo"] = result_memo
            output["logs"]["memo"] = result_memo.get("log", [])

            output["status"] = "complete" if not output["errors"] else "error"

        except Exception as e:
            output["status"] = "error"
            output["errors"].append(str(e))
            output["logs"]["error"] = f"Failed with error: {str(e)}"

        return output
