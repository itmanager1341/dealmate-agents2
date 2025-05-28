"""
Integration tests for CIMOrchestrator toolbox usage.
"""

import pytest
import os
import tempfile
from typing import Dict, Any
from orchestrator.cim_orchestrator import CIMOrchestrator
from orchestrator.tools import Tool, TOOL_REGISTRY
from orchestrator.agents.financial_agent import FinancialAgent


class MockPDFTool(Tool):
    """Mock PDF tool for testing."""
    
    def __init__(self):
        super().__init__(
            name="pdf_to_text",
            description="Mock PDF tool for testing",
            cost_estimate=0.0,
            required_kwargs=["file_path"],
            model_use_case="DOCUMENT_ANALYSIS",
            version="1.0.0"
        )
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Return mock PDF text."""
        return {"text": "Mock PDF content with financial metrics: Revenue $1M, EBITDA $200K"}


@pytest.fixture
def mock_toolbox():
    """Create a mock toolbox with stub tools."""
    return {
        "pdf_to_text": MockPDFTool(),
        # Add other mock tools as needed
    }


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Create a minimal PDF file
        tmp.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


def test_orchestrator_with_mock_toolbox(mock_toolbox, sample_pdf):
    """Test that CIMOrchestrator uses mock toolbox and passes it to agents."""
    # Create orchestrator with mock toolbox
    orchestrator = CIMOrchestrator()
    orchestrator.toolbox = mock_toolbox
    
    # Verify toolbox is passed to agents
    assert isinstance(orchestrator.agents['financial'], FinancialAgent)
    assert orchestrator.agents['financial'].toolbox == mock_toolbox
    
    # Test PDF processing with mock tool
    text = orchestrator.load_pdf_text(sample_pdf)
    assert text == "Mock PDF content with financial metrics: Revenue $1M, EBITDA $200K"
    
    # Test agent execution with mock tool
    results = orchestrator.run_all_agents(text)
    assert 'financial' in results
    assert results['financial']['status'] == 'success'  # Assuming agent handles mock text successfully


def test_orchestrator_with_real_toolbox():
    """Test that CIMOrchestrator initializes with real toolbox by default."""
    orchestrator = CIMOrchestrator()
    assert orchestrator.toolbox == TOOL_REGISTRY
    assert 'pdf_to_text' in orchestrator.toolbox
    assert 'excel_to_json' in orchestrator.toolbox
    assert 'whisper_transcribe' in orchestrator.toolbox


def test_agent_toolbox_access(mock_toolbox):
    """Test that agents can access tools from the toolbox."""
    orchestrator = CIMOrchestrator()
    orchestrator.toolbox = mock_toolbox
    
    # Verify each agent has access to the toolbox
    for agent_name, agent in orchestrator.agents.items():
        assert agent.toolbox == mock_toolbox
        assert isinstance(agent.get_tool("pdf_to_text"), MockPDFTool) 