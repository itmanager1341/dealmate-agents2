"""
Core Tool class for DealMate agents.

This module defines the abstract base class for all tools used in the DealMate
agent system. Tools are responsible for specific operations like document
processing, transcription, and data extraction.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class ModelUseCase(str, Enum):
    """Enum for different model use cases in the system."""
    EMBEDDING = "embedding"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSCRIPTION = "transcription"
    PLANNING = "planning"
    CRITIC = "critic"
    EXCEL_ANALYSIS = "excel_analysis"


class Tool(ABC):
    """
    Abstract base class for all tools in the DealMate system.
    
    Tools are responsible for specific operations and provide a standardized
    interface for agents to interact with various services and utilities.
    
    Attributes:
        name (str): Unique identifier for the tool
        description (str): Human-readable description of the tool's purpose
        cost_estimate (float): Estimated cost per run in USD
        required_kwargs (List[str]): List of required keyword arguments
        model_use_case (ModelUseCase): The primary use case for this tool
        version (str): Version of the tool implementation
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        cost_estimate: float,
        required_kwargs: List[str],
        model_use_case: ModelUseCase,
        version: str = "1.0.0"
    ) -> None:
        """
        Initialize a new Tool instance.
        
        Args:
            name: Unique identifier for the tool
            description: Human-readable description of the tool's purpose
            cost_estimate: Estimated cost per run in USD
            required_kwargs: List of required keyword arguments
            model_use_case: The primary use case for this tool
            version: Version of the tool implementation
        """
        self.name = name
        self.description = description
        self.cost_estimate = cost_estimate
        self.required_kwargs = required_kwargs
        self.model_use_case = model_use_case
        self.version = version
    
    def validate_kwargs(self, **kwargs) -> None:
        """
        Validate that all required keyword arguments are present.
        
        Args:
            **kwargs: Keyword arguments to validate
            
        Raises:
            ValueError: If any required kwargs are missing
        """
        missing_kwargs = [kw for kw in self.required_kwargs if kw not in kwargs]
        if missing_kwargs:
            raise ValueError(f"Missing required arguments: {', '.join(missing_kwargs)}")
    
    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool's main functionality.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Dict[str, Any]: Tool execution results
            
        Raises:
            NotImplementedError: Must be implemented by concrete tool classes
            ValueError: If required kwargs are missing
        """
        self.validate_kwargs(**kwargs)
        raise NotImplementedError("Tool.run() must be implemented by concrete tool classes")
    
    def __str__(self) -> str:
        """Return a string representation of the tool."""
        return f"{self.name} (v{self.version}) - {self.description}"
    
    def __repr__(self) -> str:
        """Return a concise string representation of the tool."""
        return f"Tool<name={self.name},v{self.version}>" 