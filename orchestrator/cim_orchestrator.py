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

    def run_all_agents(self, document_text, deal_id):
        """
        Runs all agents in sequence on the provided document text.
        
        Args:
            document_text: The text of the document to analyze
            deal_id: The ID of the deal being analyzed
            
        Returns:
            dict: Results from all agents with structure:
            {
                "status": "complete" | "error",
                "results": {
                    "financial": {
                        "output": [...],  # List of financial metrics
                        "status": "success" | "error",
                        "error": str  # If status is error
                    },
                    "risk": {
                        "output": {...},  # Risk analysis object
                        "status": "success" | "error",
                        "error": str  # If status is error
                    },
                    "consistency": {
                        "output": {...},  # Consistency analysis object
                        "status": "success" | "error",
                        "error": str  # If status is error
                    },
                    "memo": {
                        "output": {...},  # Investment memo object
                        "status": "success" | "error",
                        "error": str  # If status is error
                    }
                },
                "errors": [],  # List of any errors that occurred
                "logs": []  # List of execution logs
            }
        """
        results = {
            "status": "complete",
            "results": {
                "financial": {"output": [], "status": "success"},
                "risk": {"output": {}, "status": "success"},
                "consistency": {"output": {}, "status": "success"},
                "memo": {"output": {}, "status": "success"}
            },
            "errors": [],
            "logs": []
        }
        
        try:
            # Run financial agent
            try:
                financial_result = self.agents["financial"].execute(document_text, deal_id)
                results["results"]["financial"]["output"] = financial_result
            except Exception as e:
                results["results"]["financial"]["status"] = "error"
                results["results"]["financial"]["error"] = str(e)
                results["errors"].append(f"Financial agent error: {str(e)}")
            
            # Run risk agent
            try:
                risk_result = self.agents["risk"].execute(document_text, deal_id)
                results["results"]["risk"]["output"] = risk_result
            except Exception as e:
                results["results"]["risk"]["status"] = "error"
                results["results"]["risk"]["error"] = str(e)
                results["errors"].append(f"Risk agent error: {str(e)}")
            
            # Run consistency agent
            try:
                consistency_result = self.agents["consistency"].execute(
                    document_text,
                    deal_id=deal_id,
                    context={
                        "financial_metrics": results["results"]["financial"]["output"],
                        "risks": results["results"]["risk"]["output"].get("items", [])
                    }
                )
                results["results"]["consistency"]["output"] = consistency_result
            except Exception as e:
                results["results"]["consistency"]["status"] = "error"
                results["results"]["consistency"]["error"] = str(e)
                results["errors"].append(f"Consistency agent error: {str(e)}")
            
            # Run memo agent with context from other agents
            try:
                context = {
                    "financial_metrics": results["results"]["financial"]["output"],
                    "risks": results["results"]["risk"]["output"].get("items", []),
                    "consistency_analysis": results["results"]["consistency"]["output"]
                }
                memo_result = self.agents["memo"].execute(document_text, deal_id=deal_id, context=context)
                results["results"]["memo"]["output"] = memo_result
            except Exception as e:
                results["results"]["memo"]["status"] = "error"
                results["results"]["memo"]["error"] = str(e)
                results["errors"].append(f"Memo agent error: {str(e)}")
            
            # Update overall status if any agents failed
            if any(result["status"] == "error" for result in results["results"].values()):
                results["status"] = "error"
            
            return results
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Orchestrator error: {str(e)}")
            return results
