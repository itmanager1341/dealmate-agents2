"""
Tools package for DealMate agents.

This package contains the core Tool class and various tool implementations
for document processing, transcription, and data extraction.
"""

from typing import Dict
from .core_tool import Tool, ModelUseCase
from .pdf_to_text import PDFToTextTool
from .excel_to_json import ExcelToJSONTool
from .whisper_transcribe import WhisperTranscribeTool

# Registry of all available tools
# The TOOL_REGISTRY is a centralized dictionary that maps tool names to their
# instantiated implementations. This registry is used by agents to access tools
# without needing to know their implementation details.
#
# Available tools:
# - pdf_to_text: Extracts text content from PDF documents
# - excel_to_json: Converts Excel files to structured JSON data
# - whisper_transcribe: Transcribes audio files using OpenAI's Whisper model
#
# Each tool is instantiated once at module load time and reused across all
# agent instances. Tools are stateless and thread-safe.
TOOL_REGISTRY: Dict[str, Tool] = {
    'pdf_to_text': PDFToTextTool(),
    'excel_to_json': ExcelToJSONTool(),
    'whisper_transcribe': WhisperTranscribeTool(),
}

__all__ = ['TOOL_REGISTRY'] 