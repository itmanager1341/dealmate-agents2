"""
PDF to text conversion tool for DealMate agents.

This tool extracts text from PDF files using PyMuPDF (fitz).
"""

import fitz
from typing import Dict, Any
from .core_tool import Tool, ModelUseCase


class PDFToTextTool(Tool):
    """
    Tool for extracting text from PDF files.
    
    This tool uses PyMuPDF (fitz) to extract text from PDF files,
    concatenating the text from all pages into a single string.
    """
    
    def __init__(self) -> None:
        """Initialize the PDFToTextTool with its configuration."""
        super().__init__(
            name="pdf_to_text",
            description="Extract text from PDF files using PyMuPDF",
            cost_estimate=0.0,  # CPU-only operation
            required_kwargs=["file_path"],
            model_use_case=ModelUseCase.ANALYSIS,  # Preprocessing step
            version="1.0.0"
        )
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict containing the extracted text
            
        Raises:
            ValueError: If file_path is missing or invalid
            RuntimeError: If PDF processing fails
        """
        self.validate_kwargs(**kwargs)
        file_path = kwargs["file_path"]
        
        try:
            # Open PDF and extract text from each page
            doc = fitz.open(file_path)
            full_text = ""
            
            for page in doc:
                full_text += page.get_text()
            
            doc.close()
            
            return {"text": full_text}
            
        except Exception as e:
            raise RuntimeError(f"Failed to process PDF: {str(e)}") 