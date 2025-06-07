import pytest
from unittest.mock import MagicMock
from orchestrator.agents.chart_agent import ChartAgent

@pytest.fixture
def mock_toolbox():
    """Create a mock toolbox with required tools."""
    return {
        "pdf_to_text": MagicMock(),
        "text_extraction": MagicMock(),
        "entity_recognition": MagicMock()
    }

@pytest.fixture
def chart_agent(mock_toolbox):
    """Create a ChartAgent instance with mock toolbox."""
    return ChartAgent(
        agent_name="chart_agent",
        user_id="test_user",
        deal_id="test_deal",
        toolbox=mock_toolbox
    )

def test_chart_agent_initialization(chart_agent):
    """Test that the agent initializes correctly."""
    assert chart_agent.agent_name == "chart_agent"
    assert chart_agent.user_id == "test_user"
    assert chart_agent.deal_id == "test_deal"
    assert chart_agent.toolbox is not None

def test_get_use_case(chart_agent):
    """Test that the use case is correctly returned."""
    assert chart_agent._get_use_case() == "cim_analysis"

def test_build_prompt(chart_agent):
    """Test that the prompt is built correctly."""
    document_text = "Sample document text with charts and graphs."
    prompt = chart_agent.build_prompt(document_text)
    assert isinstance(prompt, str)
    assert "chart" in prompt.lower()
    assert "graph" in prompt.lower()
    assert "table" in prompt.lower()

def test_parse_response_valid(chart_agent):
    """Test parsing of a valid response."""
    valid_response = """
    {
        "charts": [
            {
                "chart_type": "line_graph",
                "title": "Revenue Growth",
                "description": "Annual revenue growth over 5 years",
                "data_points": {
                    "years": [2019, 2020, 2021, 2022, 2023],
                    "values": [100, 120, 150, 180, 220]
                },
                "source_page": 5,
                "confidence_score": 0.95,
                "relationships": [
                    {
                        "related_text": "Revenue grew 20% YoY",
                        "relationship_type": "confirmation",
                        "confidence_score": 0.9
                    }
                ]
            }
        ]
    }
    """
    result = chart_agent.parse_response(valid_response)
    assert isinstance(result, dict)
    assert "charts" in result
    assert len(result["charts"]) == 1
    assert result["charts"][0]["chart_type"] == "line_graph"
    assert result["charts"][0]["confidence_score"] == 0.95
    assert len(result["charts"][0]["relationships"]) == 1

def test_parse_response_invalid(chart_agent):
    """Test parsing of an invalid response."""
    invalid_response = "Invalid JSON response"
    result = chart_agent.parse_response(invalid_response)
    assert isinstance(result, dict)
    assert "charts" in result
    assert len(result["charts"]) == 0

def test_validate_output_type_valid(chart_agent):
    """Test validation of a valid output type."""
    valid_output = {
        "charts": [
            {
                "chart_type": "bar_chart",
                "title": "Market Share",
                "description": "Market share by region",
                "data_points": {"regions": ["NA", "EU", "APAC"], "values": [40, 30, 30]},
                "source_page": 10,
                "confidence_score": 0.85,
                "relationships": []
            }
        ]
    }
    assert chart_agent._validate_output_type(valid_output) is True

def test_validate_output_type_invalid(chart_agent):
    """Test validation of various invalid output types."""
    invalid_outputs = [
        {},  # Missing charts
        {"charts": []},  # Empty charts
        {"charts": [{"title": "Missing required fields"}]},  # Missing required fields
        {"charts": [{"chart_type": "invalid", "title": "Test", "confidence_score": 2.0}]},  # Invalid confidence score
        {"charts": [{"chart_type": "pie_chart", "title": "Test", "confidence_score": 0.5, "relationships": [{"invalid": "structure"}]}]}  # Invalid relationship structure
    ]
    
    for output in invalid_outputs:
        assert chart_agent._validate_output_type(output) is False

def test_extract_json_block(chart_agent):
    """Test extraction of JSON block from text."""
    text = """
    Some text before
    ```json
    {
        "charts": [{"title": "Test Chart"}]
    }
    ```
    Some text after
    """
    result = chart_agent._extract_json_block(text)
    assert isinstance(result, dict)
    assert "charts" in result
    assert len(result["charts"]) == 1

def test_extract_json_block_no_json(chart_agent):
    """Test extraction when no JSON block is present."""
    text = "No JSON block here"
    with pytest.raises(ValueError):
        chart_agent._extract_json_block(text) 