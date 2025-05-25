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
        Uses PyMuPDF to extract full text from a PDF CIM.
        """
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text

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
            output["status"] = "text_extracted"

            # Step 2: Run financial agent
            result_fin = self.agents["financial"].execute(cim_text, deal_id)
            output["results"]["financial"] = result_fin
            output["logs"]["financial"] = result_fin.get("log", [])

            # Step 3: Run risk agent
            result_risk = self.agents["risk"].execute(cim_text, deal_id)
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
            output["results"]["memo"] = result_memo
            output["logs"]["memo"] = result_memo.get("log", [])

            output["status"] = "complete"

        except Exception as e:
            output["status"] = "error"
            output["errors"].append(str(e))

        return output
