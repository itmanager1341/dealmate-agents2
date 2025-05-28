"""
Unit tests for the WhisperTranscribeTool.
"""

import pytest
import os
import tempfile
import wave
import numpy as np
from orchestrator.tools.whisper_transcribe import WhisperTranscribeTool

@pytest.fixture
def sample_audio_file():
    """Create a sample audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        # Create a simple sine wave audio file
        sample_rate = 44100
        duration = 1.0  # 1 second
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Write to WAV file
        with wave.open(tmp.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
            
        yield tmp.name
        
        # Cleanup
        os.unlink(tmp.name)

def test_initialization():
    """Test tool initialization."""
    tool = WhisperTranscribeTool()
    assert tool.name == "whisper_transcribe"
    assert tool.description == "Transcribe audio files using OpenAI Whisper"
    assert tool.cost_estimate == 0.006
    assert tool.model_use_case == "TRANSCRIPTION"
    assert tool.version == "1.0.0"
    assert tool.model is not None  # Model should be loaded

def test_transcription(sample_audio_file):
    """Test audio transcription."""
    tool = WhisperTranscribeTool()
    result = tool.run(file_path=sample_audio_file)
    
    # Check structure
    assert isinstance(result, dict)
    assert "text" in result
    assert "segments" in result
    assert "duration" in result
    assert "cost_estimate" in result
    
    # Check types
    assert isinstance(result["text"], str)
    assert isinstance(result["segments"], list)
    assert isinstance(result["duration"], (int, float))
    assert isinstance(result["cost_estimate"], float)
    
    # Check cost estimation
    expected_cost = (result["duration"] / 15.0) * 0.006
    assert abs(result["cost_estimate"] - expected_cost) < 0.0001

def test_missing_file_path():
    """Test handling of missing file_path parameter."""
    tool = WhisperTranscribeTool()
    with pytest.raises(ValueError):
        tool.run()  # No file_path provided

def test_invalid_file():
    """Test handling of invalid file."""
    tool = WhisperTranscribeTool()
    with pytest.raises(RuntimeError):
        tool.run(file_path="nonexistent_file.wav")

def test_empty_audio_file():
    """Test handling of empty audio file."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        # Create an empty WAV file
        with wave.open(tmp.name, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(b'')
        
        try:
            tool = WhisperTranscribeTool()
            with pytest.raises(RuntimeError):
                tool.run(file_path=tmp.name)
        finally:
            os.unlink(tmp.name) 