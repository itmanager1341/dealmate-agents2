"""
Excel to JSON conversion tool for DealMate agents.

This tool converts Excel files to JSON format using pandas and openpyxl.
"""

import pandas as pd
from typing import Dict, Any, List
from .core_tool import Tool, ModelUseCase
import logging

logger = logging.getLogger(__name__)

class ExcelToJSONTool(Tool):
    """
    Tool for converting Excel files to JSON format.
    
    This tool uses pandas with openpyxl engine to read Excel files
    and convert each sheet to a list of records in JSON format.
    """
    
    def __init__(self) -> None:
        """Initialize the ExcelToJSONTool with its configuration."""
        super().__init__(
            name="excel_to_json",
            description="Convert Excel files to JSON format using pandas",
            cost_estimate=0.0,  # CPU-only operation
            required_kwargs=["file_path"],
            model_use_case=ModelUseCase.EXCEL_ANALYSIS,  # Updated to match spec
            version="1.0.0"
        )
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Convert Excel file to JSON format.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dict containing sheets data in JSON format:
            {
                "sheets": [
                    {
                        "name": "Sheet1",
                        "data": [{"col1": "val1", ...}, ...]
                    },
                    ...
                ]
            }
            
        Raises:
            ValueError: If file_path is missing or invalid
            RuntimeError: If Excel processing fails
        """
        self.validate_kwargs(**kwargs)
        file_path = kwargs["file_path"]
        
        try:
            # Read all sheets from Excel
            excel_data = pd.read_excel(file_path, engine='openpyxl', sheet_name=None)
            
            # Convert each sheet to JSON records
            sheets_data = []
            for sheet_name, df in excel_data.items():
                # Convert DataFrame to list of records with proper NaN handling
                records = df.replace({pd.NA: None}).to_dict(orient='records')
                
                sheets_data.append({
                    "name": sheet_name,
                    "data": records
                })
            
            logger.info(f"Successfully processed Excel file: {file_path} with {len(sheets_data)} sheets")
            return {"sheets": sheets_data}
            
        except Exception as e:
            logger.error(f"Failed to process Excel file {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to process Excel file: {str(e)}") 