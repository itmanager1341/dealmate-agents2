"""
Tests for the WhisperTranscribeTool.
"""

import os
import pytest
from pydub import AudioSegment
from orchestrator.tools.whisper_transcribe import WhisperTranscribeTool


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file with test content."""
    # Create a silent audio segment (1 second)
    audio = AudioSegment.silent(duration=1000)  # 1000ms = 1s
    
    # Add some text (this will be inaudible but valid audio)
    audio_path = tmp_path / "test.mp3"
    audio.export(str(audio_path), format="mp3")
    
    return str(audio_path)


def test_whisper_transcribe_tool(sample_audio):
    """Test that WhisperTranscribeTool correctly transcribes audio."""
    # Initialize the tool
    tool = WhisperTranscribeTool()
    
    # Run the tool
    result = tool.run(file_path=sample_audio)
    
    # Verify the result structure
    assert "text" in result
    assert "segments" in result
    assert "duration" in result
    assert "cost_estimate" in result
    
    # Verify duration and cost
    assert result["duration"] > 0
    assert result["cost_estimate"] > 0
    
    # Clean up
    os.remove(sample_audio) 