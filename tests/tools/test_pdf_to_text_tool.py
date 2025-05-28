"""
Tests for the PDFToTextTool.
"""

import os
import pytest
from fitz import Document
from orchestrator.tools.pdf_to_text import PDFToTextTool


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file with test content."""
    # Create a new PDF document
    doc = Document()
    page = doc.new_page()
    
    # Add some text to the page
    page.insert_text((50, 50), "Lorem ipsum dolor sit amet")
    
    # Save the PDF
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    return str(pdf_path)


def test_pdf_to_text_tool(sample_pdf):
    """Test that PDFToTextTool correctly extracts text from a PDF."""
    # Initialize the tool
    tool = PDFToTextTool()
    
    # Run the tool
    result = tool.run(file_path=sample_pdf)
    
    # Verify the result
    assert "text" in result
    assert "Lorem ipsum" in result["text"]
    
    # Clean up
    os.remove(sample_pdf) 