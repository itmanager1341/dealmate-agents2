"""
Audio transcription tool for DealMate agents.

This tool transcribes audio files using OpenAI's Whisper model.
"""

import os
import whisper
from typing import Dict, Any
from .core_tool import Tool, ModelUseCase


class WhisperTranscribeTool(Tool):
    """
    Tool for transcribing audio files using Whisper.
    
    This tool uses OpenAI's Whisper model to transcribe audio files
    and provides cost estimates based on audio duration.
    """
    
    def __init__(self) -> None:
        """Initialize the WhisperTranscribeTool with its configuration."""
        super().__init__(
            name="whisper_transcribe",
            description="Transcribe audio files using OpenAI Whisper",
            cost_estimate=0.006,  # Base cost for 15s of audio
            required_kwargs=["file_path"],
            model_use_case=ModelUseCase.TRANSCRIPTION,
            version="1.0.0"
        )
        # Load Whisper model on initialization
        self.model = whisper.load_model("base")
    
    def _estimate_cost(self, duration_seconds: float) -> float:
        """
        Estimate the cost of transcription based on audio duration.
        
        Args:
            duration_seconds: Duration of the audio in seconds
            
        Returns:
            Estimated cost in USD
        """
        # Cost is $0.006 per 15 seconds
        return (duration_seconds / 15.0) * 0.006
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Transcribe an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dict containing transcription data:
            {
                "text": "transcribed text",
                "segments": [...],
                "duration": duration in seconds,
                "cost_estimate": estimated cost in USD
            }
            
        Raises:
            ValueError: If file_path is missing or invalid
            RuntimeError: If transcription fails
        """
        self.validate_kwargs(**kwargs)
        file_path = kwargs["file_path"]
        
        try:
            # Transcribe audio
            result = self.model.transcribe(file_path)
            
            # Calculate duration and cost
            duration = result.get("duration", 0)
            cost_estimate = self._estimate_cost(duration)
            
            return {
                "text": result["text"],
                "segments": result.get("segments", []),
                "duration": duration,
                "cost_estimate": cost_estimate
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to transcribe audio: {str(e)}") 