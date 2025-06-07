import pytest
from unittest.mock import Mock, patch
from orchestrator.agents.quote_agent import QuoteAgent
from models.quote import DocumentQuote, QuoteRelationship

@pytest.fixture
def mock_toolbox():
    return {
        'text_extraction': Mock(),
        'sentiment_analysis': Mock(),
        'entity_recognition': Mock()
    }

@pytest.fixture
def quote_agent(mock_toolbox):
    return QuoteAgent(
        agent_name="test_quote_agent",
        user_id="test_user",
        deal_id="test_deal",
        toolbox=mock_toolbox
    )

def test_quote_agent_initialization(quote_agent):
    """Test that the quote agent initializes correctly."""
    assert quote_agent.agent_name == "test_quote_agent"
    assert quote_agent.user_id == "test_user"
    assert quote_agent.deal_id == "test_deal"
    assert quote_agent.toolbox is not None

def test_get_use_case(quote_agent):
    """Test that the use case is correctly returned."""
    assert quote_agent._get_use_case() == "cim_analysis"

def test_build_prompt(quote_agent):
    """Test that the prompt is built correctly."""
    document_text = "Test document text"
    prompt = quote_agent.build_prompt(document_text)
    
    assert isinstance(prompt, str)
    assert "You are a quote analysis expert" in prompt
    assert document_text in prompt
    assert "quote_text" in prompt
    assert "speaker" in prompt
    assert "significance_score" in prompt

def test_parse_response_valid(quote_agent):
    """Test parsing a valid response."""
    valid_response = """
    {
        "quotes": [
            {
                "quote_text": "Test quote",
                "speaker": "John Doe",
                "speaker_title": "CEO",
                "context": "Test context",
                "significance_score": 0.8,
                "quote_type": "executive",
                "metadata": {
                    "sentiment": "positive",
                    "topics": ["growth", "strategy"],
                    "key_points": ["market expansion"],
                    "source_section": "Executive Summary"
                }
            }
        ],
        "quote_relationships": [
            {
                "quote_id": "123",
                "related_metric": "Revenue Growth",
                "relationship_type": "supports",
                "confidence_score": 0.9
            }
        ],
        "analysis_summary": "Test analysis",
        "confidence_score": 0.85
    }
    """
    
    result = quote_agent.parse_response(valid_response)
    
    assert result["agent_type"] == "quote_agent"
    assert "output_json" in result
    assert len(result["output_json"]["quotes"]) == 1
    assert len(result["output_json"]["quote_relationships"]) == 1
    assert result["output_json"]["analysis_summary"] == "Test analysis"
    assert result["output_json"]["confidence_score"] == 0.85

def test_parse_response_invalid(quote_agent):
    """Test parsing an invalid response."""
    invalid_response = "Invalid JSON"
    
    result = quote_agent.parse_response(invalid_response)
    
    assert result["agent_type"] == "quote_agent"
    assert "output_json" in result
    assert len(result["output_json"]["quotes"]) == 0
    assert len(result["output_json"]["quote_relationships"]) == 0
    assert result["output_json"]["analysis_summary"] == ""
    assert result["output_json"]["confidence_score"] == 0.0
    assert "error" in result["output_json"]

def test_validate_output_type_valid(quote_agent):
    """Test validation of a valid output type."""
    valid_output = {
        "agent_type": "quote_agent",
        "output_json": {
            "quotes": [
                {
                    "quote_text": "Test quote",
                    "speaker": "John Doe",
                    "speaker_title": "CEO",
                    "context": "Test context",
                    "significance_score": 0.8,
                    "quote_type": "executive",
                    "metadata": {
                        "sentiment": "positive",
                        "topics": ["growth"],
                        "key_points": ["expansion"],
                        "source_section": "Summary"
                    }
                }
            ],
            "quote_relationships": [
                {
                    "quote_id": "123",
                    "related_metric": "Growth",
                    "relationship_type": "supports",
                    "confidence_score": 0.9
                }
            ],
            "analysis_summary": "Test analysis",
            "confidence_score": 0.85
        }
    }
    
    assert quote_agent._validate_output_type(valid_output) is True

def test_validate_output_type_invalid(quote_agent):
    """Test validation of an invalid output type."""
    invalid_outputs = [
        {},  # Empty dict
        {"agent_type": "wrong_agent"},  # Wrong agent type
        {"agent_type": "quote_agent"},  # Missing output_json
        {
            "agent_type": "quote_agent",
            "output_json": {
                "quotes": [],
                "quote_relationships": [],
                "analysis_summary": "Test",
                "confidence_score": 1.5  # Invalid confidence score
            }
        }
    ]
    
    for invalid_output in invalid_outputs:
        assert quote_agent._validate_output_type(invalid_output) is False

def test_extract_json_block(quote_agent):
    """Test extraction of JSON block from text."""
    text = """
    Some text before
    {
        "key": "value"
    }
    Some text after
    """
    
    result = quote_agent._extract_json_block(text)
    assert result == {"key": "value"}

def test_extract_json_block_no_json(quote_agent):
    """Test extraction when no JSON block is present."""
    text = "No JSON here"
    
    with pytest.raises(ValueError):
        quote_agent._extract_json_block(text) 