# cim_orchestrator.py
# Coordinates multi-agent analysis of CIM documents

import fitz  # PyMuPDF
from orchestrator.agents.financial_agent import FinancialAgent
from orchestrator.agents.risk_agent import RiskAgent
from orchestrator.agents.memo_agent import MemoAgent
from orchestrator.agents.consistency_agent import ConsistencyAgent
from typing import List

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
                financial_result = self.agents["financial"].execute(document_text, context={"deal_id": deal_id})
                results["results"]["financial"]["output"] = financial_result
            except Exception as e:
                results["results"]["financial"]["status"] = "error"
                results["results"]["financial"]["error"] = str(e)
                results["errors"].append(f"Financial agent error: {str(e)}")
            
            # Run risk agent
            try:
                risk_result = self.agents["risk"].execute(document_text, context={"deal_id": deal_id})
                results["results"]["risk"]["output"] = risk_result
            except Exception as e:
                results["results"]["risk"]["status"] = "error"
                results["results"]["risk"]["error"] = str(e)
                results["errors"].append(f"Risk agent error: {str(e)}")
            
            # Run consistency agent
            try:
                consistency_result = self.agents["consistency"].execute(
                    document_text,
                    context={
                        "deal_id": deal_id,
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
                    "deal_id": deal_id,
                    "financial_metrics": results["results"]["financial"]["output"],
                    "risks": results["results"]["risk"]["output"].get("items", []),
                    "consistency_analysis": results["results"]["consistency"]["output"]
                }
                memo_result = self.agents["memo"].execute(document_text, context=context)
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

    async def create_chunks(self, text: str, document_id: str, deal_id: str) -> List[dict]:
        """
        Splits document text into chunks with metadata.
        """
        # Split text into sections based on headers
        sections = self._split_into_sections(text)
        chunks = []
        
        for idx, section in enumerate(sections):
            chunk = {
                "document_id": document_id,
                "deal_id": deal_id,
                "chunk_text": section["text"],
                "chunk_index": idx,
                "chunk_size": len(section["text"]),
                "start_page": section.get("start_page"),
                "end_page": section.get("end_page"),
                "section_type": section.get("type"),
                "section_title": section.get("title"),
                "metadata": section.get("metadata", {}),
                "processed_by_ai": False
            }
            chunks.append(chunk)
        
        return chunks

    async def store_chunks(self, chunks: List[dict]) -> List[dict]:
        """
        Stores chunks in the document_chunks table.
        """
        stored_chunks = []
        for chunk in chunks:
            result = await supabase.table("document_chunks").insert(chunk).execute()
            stored_chunks.append(result.data[0])
        return stored_chunks

    async def create_chunk_relationships(self, chunks: List[dict]):
        """
        Creates relationships between chunks.
        """
        for i in range(len(chunks) - 1):
            relationship = {
                "parent_chunk_id": chunks[i]["id"],
                "child_chunk_id": chunks[i + 1]["id"],
                "relationship_type": "sequential",
                "strength": 1.0
            }
            await supabase.table("chunk_relationships").insert(relationship).execute()

    async def process_chunks_with_agents(self, chunks: List[dict]):
        """
        Processes chunks with AI agents.
        """
        for chunk in chunks:
            try:
                # Process with each agent
                for agent_name, agent in self.agents.items():
                    result = await agent.process_chunk(chunk)
                    
                    # Store agent output
                    output = {
                        "deal_id": chunk["deal_id"],
                        "document_id": chunk["document_id"],
                        "chunk_id": chunk["id"],
                        "agent_type": agent_name,
                        "output_type": "chunk_analysis",
                        "output_json": result
                    }
                    await supabase.table("ai_outputs").insert(output).execute()
                
                # Update chunk processing status
                await supabase.table("document_chunks")\
                    .update({"processed_by_ai": True})\
                    .eq("id", chunk["id"])\
                    .execute()
                    
            except Exception as e:
                logger.error(f"Error processing chunk {chunk['id']}: {str(e)}")
                continue

    def _split_into_sections(self, text: str) -> List[dict]:
        """
        Splits text into logical sections based on headers and content.
        """
        # TODO: Implement more sophisticated section detection
        # For now, split by double newlines
        sections = []
        current_section = {"text": "", "type": None, "title": None}
        
        for line in text.split("\n\n"):
            if line.strip():
                if line.isupper() and len(line) < 100:  # Likely a header
                    if current_section["text"]:
                        sections.append(current_section)
                    current_section = {
                        "text": line,
                        "type": self._detect_section_type(line),
                        "title": line
                    }
                else:
                    current_section["text"] += "\n" + line
        
        if current_section["text"]:
            sections.append(current_section)
        
        return sections

    def _detect_section_type(self, header: str) -> str:
        """
        Detects the type of section based on header text.
        """
        header = header.lower()
        if "executive" in header or "summary" in header:
            return "executive_summary"
        elif "financial" in header:
            return "financial_metrics"
        elif "risk" in header:
            return "risk_analysis"
        elif "business" in header or "model" in header:
            return "business_model"
        elif "management" in header:
            return "management"
        elif "market" in header:
            return "market_analysis"
        else:
            return "other"

    async def process_document(self, document_id: str, deal_id: str):
        """
        Main method to process a document.
        """
        try:
            # Extract text from PDF
            text = await self.load_pdf_text(document_id)
            
            # Create and store chunks
            chunks = await self.create_chunks(text, document_id, deal_id)
            stored_chunks = await self.store_chunks(chunks)
            
            # Create relationships
            await self.create_chunk_relationships(stored_chunks)
            
            # Process chunks
            await self.process_chunks_with_agents(stored_chunks)
            
            return {"status": "success", "chunks_processed": len(stored_chunks)}
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            return {"status": "error", "error": str(e)}
