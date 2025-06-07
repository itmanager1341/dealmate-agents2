# cim_orchestrator.py
# Coordinates multi-agent analysis of CIM documents

import logging
from typing import List, Optional, Dict, Any
from orchestrator.agents.financial_agent import FinancialAgent
from orchestrator.agents.risk_agent import RiskAgent
from orchestrator.agents.memo_agent import MemoAgent
from orchestrator.agents.consistency_agent import ConsistencyAgent
from orchestrator.agents.quote_agent import QuoteAgent
from orchestrator.agents.chart_agent import ChartAgent
from orchestrator.tools import TOOL_REGISTRY

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
        
        # Initialize toolbox once for all agents
        self.toolbox = TOOL_REGISTRY
        
        # Initialize agents with shared toolbox
        self.agents = {
            'financial': FinancialAgent(
                agent_name='financial',
                user_id=user_id,
                deal_id=deal_id,
                toolbox=self.toolbox
            ),
            'risk': RiskAgent(
                agent_name='risk',
                user_id=user_id,
                deal_id=deal_id,
                toolbox=self.toolbox
            ),
            'memo': MemoAgent(
                agent_name='memo',
                user_id=user_id,
                deal_id=deal_id,
                toolbox=self.toolbox
            ),
            'consistency': ConsistencyAgent(
                agent_name='consistency',
                user_id=user_id,
                deal_id=deal_id,
                toolbox=self.toolbox
            )
        }
        self.quote_agent = QuoteAgent(
            agent_name="quote_agent",
            user_id=user_id,
            deal_id=deal_id,
            toolbox=self.toolbox
        )
        self.chart_agent = ChartAgent(
            agent_name="chart_agent",
            user_id=user_id,
            deal_id=deal_id,
            toolbox=self.toolbox
        )

    def load_pdf_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file using the pdf_to_text tool.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        try:
            result = self.toolbox['pdf_to_text'].run(file_path=file_path)
            return result['text']
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def process_excel(self, file_path: str) -> Dict[str, Any]:
        """
        Process Excel file using the excel_to_json tool.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dict[str, Any]: Structured JSON data from Excel
        """
        try:
            result = self.toolbox['excel_to_json'].run(file_path=file_path)
            return result
        except Exception as e:
            self.logger.error(f"Error processing Excel file: {str(e)}")
            raise

    def transcribe_audio(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using the whisper_transcribe tool.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dict[str, Any]: Transcription results including text and metadata
        """
        try:
            result = self.toolbox['whisper_transcribe'].run(file_path=file_path)
            return result
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {str(e)}")
            raise

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
            
            # Process quotes
            quote_results = await self.quote_agent.process(text)
            if quote_results and "output_json" in quote_results:
                await self._save_quote_results(quote_results["output_json"], document_id)
            
            # Process chart
            chart_results = await self.chart_agent.process(text)
            if chart_results and "output_json" in chart_results:
                await self._save_chart_results(chart_results["output_json"], document_id)
            
            return {"status": "success", "chunks_processed": len(stored_chunks)}
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _save_quote_results(self, results: dict, document_id: str):
        """
        Save quote analysis results to the database.
        
        Args:
            results: The quote analysis results
            document_id: The ID of the document being processed
        """
        from models.quote import DocumentQuote, QuoteRelationship
        from models.document import Document
        
        document = await Document.get(document_id)
        if not document:
            return
            
        for quote_data in results.get("quotes", []):
            quote = DocumentQuote(
                deal_id=self.deal_id,
                document_id=document_id,
                quote_text=quote_data["quote_text"],
                speaker=quote_data["speaker"],
                speaker_title=quote_data["speaker_title"],
                context=quote_data["context"],
                significance_score=quote_data["significance_score"],
                quote_type=quote_data["quote_type"],
                metadata=quote_data["metadata"]
            )
            await quote.save()
            
            # Save quote relationships
            for rel_data in results.get("quote_relationships", []):
                if rel_data["quote_id"] == quote.id:
                    relationship = QuoteRelationship(
                        quote_id=quote.id,
                        related_metric=rel_data["related_metric"],
                        relationship_type=rel_data["relationship_type"],
                        confidence_score=rel_data["confidence_score"]
                    )
                    await relationship.save()

    async def _save_chart_results(self, results: dict, document_id: str):
        """Save chart analysis results to the database."""
        try:
            # Insert chart elements
            for chart in results.get("charts", []):
                chart["document_id"] = document_id
                chart["deal_id"] = self.deal_id
                
                # Insert chart element
                chart_response = self.supabase.table("chart_elements").insert(chart).execute()
                if not chart_response.data:
                    raise ValueError(f"Failed to insert chart: {chart}")
                
                chart_id = chart_response.data[0]["id"]
                
                # Insert relationships
                for relationship in chart.get("relationships", []):
                    relationship["chart_id"] = chart_id
                    rel_response = self.supabase.table("chart_relationships").insert(relationship).execute()
                    if not rel_response.data:
                        raise ValueError(f"Failed to insert chart relationship: {relationship}")
        
        except Exception as e:
            self.logger.error(f"Error saving chart results: {str(e)}")
            raise
