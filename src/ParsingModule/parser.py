#!/usr/bin/env python3
"""
Instruction Parser Module

This module handles parsing of JSON instruction files and validates them against
supported objectives. It identifies required and optional fields for each objective
type and separates supported from unsupported instructions.

The parser works with a simple functional approach without global variables or classes.
"""

import json
import os
from enum import Enum
from typing import Dict, Any, Tuple


class ObjectiveType(Enum):
    """Enumeration of supported objective types."""
    MAKE_FILE_INSTRUCTION = "make_file_instruction"

def load_instructions(instruction_file_path: str) -> Tuple[bool, Any]:
    """
    Load instructions from a JSON file.
    
    Args:
        instruction_file_path: Path to the JSON instruction file
        
    Returns:
        Tuple of (success: bool, instructions or error_message)
    """
    try:
        if not os.path.exists(instruction_file_path):
            return False, f"Instruction file not found: {instruction_file_path}"
            
        with open(instruction_file_path, 'r', encoding='utf-8') as file:
            instructions = json.load(file)
            return True, instructions
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in instruction file: {e}"
    except Exception as e:
        return False, f"Error loading instruction file: {e}"

def parse_objectives(instructions: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Parse objectives from instructions and separate supported from unsupported.
    
    Args:
        instructions: Dictionary containing instruction data
        
    Returns:
        Tuple of (success: bool, parsing_results or error_message)
    """
    if not isinstance(instructions, dict):
        return False, "Instructions must be a dictionary"
    
    # Get supported objectives from enum
    supported_objectives = {objective.value for objective in ObjectiveType}
    
    supported = []
    unsupported = []
    
    # Process each objective in the instructions
    for objective_type, objective_list in instructions.items():
        if not isinstance(objective_list, list):
            continue
            
        # Check if objective type is supported
        if objective_type in supported_objectives:
            supported.append({
                "objective_type": objective_type,
                "instructions": objective_list
            })
        else:
            unsupported.append({
                "objective_type": objective_type,
                "instructions": objective_list
            })
    
    results = {
        "supported": supported,
        "unsupported": unsupported
    }
    
    return True, results

def process_instruction_file(instruction_file_path: str) -> Tuple[bool, Any]:
    """
    Complete processing pipeline for an instruction file.
    
    This is the main function that orchestrates the entire parsing process:
    1. Load the instruction file
    2. Parse objectives and check if supported
    
    Args:
        instruction_file_path: Path to the JSON instruction file
        
    Returns:
        Tuple of (success: bool, results or error_message)
    """
    # Load instructions
    success, data = load_instructions(instruction_file_path)
    if not success:
        return False, data
    
    instructions = data
    
    # Running parser
    success, parsing_results = parse_objectives(instructions)
    if not success:
        return False, parsing_results  # parsing_results is error message

    # Display summary of parsing results
    if parsing_results['supported']:
        print("\nSupported Objectives:")
        for obj in parsing_results['supported']:
            print(f"  - {obj['objective_type']}: {len(obj['instructions'])} instructions")
    
    if parsing_results['unsupported']:
        print("\nUnsupported Objectives:")
        for obj in parsing_results['unsupported']:
            print(f"  - {obj['objective_type']}: {len(obj['instructions'])} instructions")
    
    # Returning Supported and Unsupported objectives to be used by workflow module
    results = {
        "supported_objectives": parsing_results["supported"],
        "unsupported_objectives": parsing_results["unsupported"]
    }
    
    return True, results
