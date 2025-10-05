"""
ParsingModule - Simple JSON Instruction Parser Package

This module provides simple functionality for parsing JSON instruction files
and determining which objectives are supported by the automation system.

Main Components:
- SupportedObjectives: Enumeration of supported objective types
- load_instructions: Function to load and parse JSON instructions
- get_supported_types: Function to get list of supported types
- is_objective_supported: Function to check if a type is supported

Usage:
    from src.ParsingModule import parser
    
    # Load and parse instructions
    result = parser.load_instructions("path/to/instructions.json")
    
    # Check results
    if result["success"]:
        print(f"Found {len(result['supported'])} supported objectives")
        print(f"Found {len(result['unsupported'])} unsupported objectives")
"""

from .objective_processer import process_objectives_file
__all__ = [
    'process_objectives_file'
]

__version__ = "1.0.0"
