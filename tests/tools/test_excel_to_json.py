"""
Unit tests for the ExcelToJSONTool.
"""

import pytest
import pandas as pd
import os
import tempfile
from orchestrator.tools.excel_to_json import ExcelToJSONTool

@pytest.fixture
def sample_excel_file():
    """Create a sample Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        # Create sample data
        df1 = pd.DataFrame({
            'Metric': ['Revenue', 'EBITDA', 'Net Income'],
            '2022': [1000000, 200000, 150000],
            '2023': [1200000, 250000, 180000]
        })
        
        df2 = pd.DataFrame({
            'Category': ['Product A', 'Product B', 'Product C'],
            'Sales': [500000, 300000, 400000],
            'Growth': [0.15, 0.10, 0.20]
        })
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
            df1.to_excel(writer, sheet_name='Financials', index=False)
            df2.to_excel(writer, sheet_name='Products', index=False)
            
        yield tmp.name
        
        # Cleanup
        os.unlink(tmp.name)

def test_initialization():
    """Test tool initialization."""
    tool = ExcelToJSONTool()
    assert tool.name == "excel_to_json"
    assert tool.description == "Convert Excel files to JSON format using pandas"
    assert tool.cost_estimate == 0.0
    assert tool.model_use_case == "EXCEL_ANALYSIS"
    assert tool.version == "1.0.0"

def test_conversion(sample_excel_file):
    """Test Excel to JSON conversion."""
    tool = ExcelToJSONTool()
    result = tool.run(file_path=sample_excel_file)
    
    # Check structure
    assert isinstance(result, dict)
    assert "sheets" in result
    assert isinstance(result["sheets"], list)
    assert len(result["sheets"]) == 2
    
    # Check sheets data
    sheets = {sheet["name"]: sheet["data"] for sheet in result["sheets"]}
    
    # Check Financials sheet
    assert "Financials" in sheets
    financials = sheets["Financials"]
    assert len(financials) == 3  # 3 rows
    assert financials[0]["Metric"] == "Revenue"
    assert financials[0]["2022"] == 1000000
    assert financials[0]["2023"] == 1200000
    
    # Check Products sheet
    assert "Products" in sheets
    products = sheets["Products"]
    assert len(products) == 3  # 3 rows
    assert products[0]["Category"] == "Product A"
    assert products[0]["Sales"] == 500000
    assert products[0]["Growth"] == 0.15

def test_missing_file_path():
    """Test handling of missing file_path parameter."""
    tool = ExcelToJSONTool()
    with pytest.raises(ValueError):
        tool.run()  # No file_path provided

def test_invalid_file():
    """Test handling of invalid file."""
    tool = ExcelToJSONTool()
    with pytest.raises(RuntimeError):
        tool.run(file_path="nonexistent_file.xlsx")

def test_nan_handling():
    """Test handling of NaN values in Excel data."""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        # Create DataFrame with NaN values
        df = pd.DataFrame({
            'A': [1, None, 3],
            'B': ['x', 'y', None]
        })
        
        # Write to Excel
        with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Test', index=False)
        
        try:
            # Test conversion
            tool = ExcelToJSONTool()
            result = tool.run(file_path=tmp.name)
            
            # Check NaN handling
            data = result["sheets"][0]["data"]
            assert data[1]["A"] is None  # NaN should be converted to None
            assert data[2]["B"] is None  # NaN should be converted to None
            
        finally:
            os.unlink(tmp.name) 