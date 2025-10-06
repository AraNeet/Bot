
#!/usr/bin/env python3
"""
Objectives Parser Module

This module handles parsing of JSON objectives files and validates them against
supported objective types. It separates supported from unsupported objectives.

TERMINOLOGY:
- Objective Type: What you want to accomplish (e.g., "make_file", "send_email")
- Values: User-provided data for an objective (e.g., {"file_name": "test.txt"})
- Instructions: Action steps the bot performs (e.g., "open_menu", "type_text")
"""

import json
import os
from enum import Enum
from typing import Dict, Any, Tuple
from src.notification_module import notify_error

class ObjectiveType(Enum):
    """Enumeration of supported objective types."""
    EDIT_COPY_INSTRUCTION = "edit_copy_instruction"
    DO_NOT_AIR_INSTRUCTION = "do_not_air_instruction"

def load_objectives(objectives_file_path: str) -> Tuple[bool, Any]:
    """
    Load objectives from a JSON file.
    
    Args:
        objectives_file_path: Path to the JSON objectives file
        
    Returns:
        Tuple of (success: bool, objectives or error_message)
        
    Example file structure:
    {
        "make_file": [
            {
                "file_name": "Report.txt",
                "text": "Q4 Sales Report"
            }
        ]
    }
    """
    try:
        # Check if file exists
        if not os.path.exists(objectives_file_path):
            return False, f"Objectives file not found: {objectives_file_path}"
        
        # Load JSON data
        with open(objectives_file_path, 'r', encoding='utf-8') as file:
            objectives = json.load(file)
            return True, objectives
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in objectives file: {e}"
        notify_error(error_msg, "load_objectives")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading objectives file: {e}"
        notify_error(error_msg, "load_objectives")
        return False, error_msg


def parse_objectives(objectives: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Parse objectives and separate supported from unsupported.
    
    Args:
        objectives: Dictionary containing objective data
        
    Returns:
        Tuple of (success: bool, parsing_results or error_message)
        
    Example input:
    {
        "make_file": [{"file_name": "test.txt", "text": "content"}],
        "send_email": [{"to": "user@example.com", "subject": "Hi"}]
    }
    
    Example output:
    {
        "supported": [
            {
                "objective_type": "make_file",
                "values_list": [{"file_name": "test.txt", "text": "content"}]
            }
        ],
        "unsupported": [...]
    }
    """
    if not isinstance(objectives, dict):
        return False, "Objectives must be a dictionary"
    
    supported = []
    unsupported = []
    
    # Process each objective type in the file
    for objective_type, values_list in objectives.items():
        if not isinstance(values_list, list):
            continue
        
        # Check if objective type is supported
        is_supported = any(obj.value == objective_type for obj in ObjectiveType)
        
        if is_supported:
            supported.append({
                "objective_type": objective_type,
                "values_list": values_list  # Renamed from "instructions"
            })
        else:
            unsupported.append({
                "objective_type": objective_type,
                "values_list": values_list
            })
            notify_error(
                f"Unsupported objective type: {objective_type}", 
                "parser.parse_objectives", 
                {"objective_type": objective_type}
            )
    
    if supported is None:
        notify_error(
            "There were no supported objective given",
            "parse_objectives",
            {"Support_Objectives": supported, "Unsupported": unsupported}
        )
        return False, {}

    results = {
        "supported": supported,
        "unsupported": unsupported
    }
    
    return True, results