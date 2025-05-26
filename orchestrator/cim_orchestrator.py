# cim_orchestrator.py
# Coordinates multi-agent analysis of CIM documents

import fitz  # PyMuPDF
from orchestrator.agents.financial_agent import FinancialAgent
from orchestrator.agents.risk_agent import RiskAgent
from orchestrator.agents.memo_agent import MemoAgent
from orchestrator.agents.consistency_agent import ConsistencyAgent
from typing import List, Optional, Dict, Any
import logging

class CIMOrchestrator:
    """
    Orchestrates the execution of all agents on CIM documents.
    Manages the flow of data between agents and handles error cases.
    """

    def __init__(self, user_id: Optional[str] = None, deal_id: Optional[str] = None):
        """
        Initialize the orchestrator.
        
        Args:
            user_id: Optional user ID for model configuration
            deal_id: Optional deal ID for model configuration
        """
        self.logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.deal_id = deal_id
        self.agents = {
            'financial': FinancialAgent(user_id=user_id, deal_id=deal_id),
            'risk': RiskAgent(user_id=user_id, deal_id=deal_id),
            'memo': MemoAgent(user_id=user_id, deal_id=deal_id),
            'consistency': ConsistencyAgent(user_id=user_id, deal_id=deal_id)
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

    def run_all_agents(self, document_text: str) -> Dict[str, Any]:
        """
        Run all agents on the provided document text.
        
        Args:
            document_text: The text content of the CIM document
            
        Returns:
            Dictionary containing the results from each agent
        """
        results = {}
        for agent_name, agent in self.agents.items():
            try:
                self.logger.info(f"Running {agent_name} agent")
                result = agent.execute(document_text)
                results[agent_name] = result
            except Exception as e:
                self.logger.error(f"Error running {agent_name} agent: {str(e)}")
                results[agent_name] = {
                    'status': 'error',
                    'error': str(e)
                }
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
