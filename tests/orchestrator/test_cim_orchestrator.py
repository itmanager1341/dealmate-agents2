"""
Tests for the CIMOrchestrator toolbox integration.
"""

import pytest
import os
import tempfile
from orchestrator.cim_orchestrator import CIMOrchestrator
from orchestrator.tools import TOOL_REGISTRY


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Create a minimal PDF file
        tmp.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF')
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def sample_excel():
    """Create a sample Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        # Create a minimal Excel file
        tmp.write(b'PK\x03\x04\x14\x00\x00\x00\x08\x00')
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def sample_audio():
    """Create a sample audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        # Create a minimal MP3 file
        tmp.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


def test_orchestrator_toolbox_initialization():
    """Test that orchestrator initializes with toolbox."""
    orchestrator = CIMOrchestrator()
    assert orchestrator.toolbox == TOOL_REGISTRY
    assert 'pdf_to_text' in orchestrator.toolbox
    assert 'excel_to_json' in orchestrator.toolbox
    assert 'whisper_transcribe' in orchestrator.toolbox


def test_orchestrator_pdf_processing(sample_pdf):
    """Test PDF processing through toolbox."""
    orchestrator = CIMOrchestrator()
    with pytest.raises(Exception):  # Should fail with minimal PDF
        orchestrator.load_pdf_text(sample_pdf)


def test_orchestrator_excel_processing(sample_excel):
    """Test Excel processing through toolbox."""
    orchestrator = CIMOrchestrator()
    with pytest.raises(Exception):  # Should fail with minimal Excel
        orchestrator.process_excel(sample_excel)


def test_orchestrator_audio_processing(sample_audio):
    """Test audio processing through toolbox."""
    orchestrator = CIMOrchestrator()
    with pytest.raises(Exception):  # Should fail with minimal audio
        orchestrator.transcribe_audio(sample_audio)


def test_orchestrator_agent_toolbox_injection():
    """Test that agents receive the toolbox."""
    orchestrator = CIMOrchestrator()
    for agent in orchestrator.agents.values():
        assert agent.toolbox == TOOL_REGISTRY 