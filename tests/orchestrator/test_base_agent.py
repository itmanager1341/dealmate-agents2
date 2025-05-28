"""
Tests for the BaseAgent toolbox integration.
"""

import pytest
from orchestrator.base_agent import BaseAgent
from orchestrator.tools import PDFToTextTool, TOOL_REGISTRY


class TestAgent(BaseAgent):
    """Test agent implementation for toolbox testing."""
    
    def _get_use_case(self) -> str:
        return "test"
    
    def _get_prompt(self, text: str, context: dict = None) -> str:
        return "test prompt"
    
    def parse_response(self, raw_response):
        return {"result": raw_response}
    
    def _validate_output_type(self, output: any) -> bool:
        return isinstance(output, dict)


def test_agent_toolbox_default():
    """Test that agent uses TOOL_REGISTRY by default."""
    agent = TestAgent("test_agent")
    assert agent.toolbox == TOOL_REGISTRY
    assert isinstance(agent.get_tool("pdf_to_text"), PDFToTextTool)


def test_agent_custom_toolbox():
    """Test that agent can use custom toolbox."""
    custom_toolbox = {"test_tool": PDFToTextTool()}
    agent = TestAgent("test_agent", toolbox=custom_toolbox)
    assert agent.toolbox == custom_toolbox
    assert isinstance(agent.get_tool("test_tool"), PDFToTextTool)


def test_get_tool_missing():
    """Test that get_tool raises KeyError for missing tools."""
    agent = TestAgent("test_agent")
    with pytest.raises(KeyError):
        agent.get_tool("nonexistent_tool")


def test_run_with_tool():
    """Test that run_with_tool correctly executes tools."""
    agent = TestAgent("test_agent")
    # Note: This is a basic test that doesn't actually run the tool
    # since we don't have a real PDF file. In practice, you'd want to
    # test with actual files and verify the results.
    with pytest.raises(RuntimeError):  # Should fail without a real file
        agent.run_with_tool("pdf_to_text", file_path="nonexistent.pdf") 