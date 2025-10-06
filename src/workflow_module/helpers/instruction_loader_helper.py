#!/usr/bin/env python3
"""
Instruction Loader Helper Module

This module handles loading instruction definitions and extracting values
from objective data. It prepares all necessary data for the workflow engine
to execute actions.

Responsibilities:
- Load instruction JSON files for supported objectives
- Extract required values from objective data
- Extract optional values from objective data  
- Return organized data structure for workflow execution
"""

import json
import os
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from src.notification_module import notify_error


def load_instruction_file(objective_type: str, 
                         actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Load the instruction definition JSON file for a specific objective type.
    
    This function locates and reads the JSON file containing action steps
    for the given objective type.
    
    Args:
        objective_type: The type of objective (e.g., "make_file", "edit_copy_instruction")
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, instruction_data or error_message)
        
    Example JSON structure:
    {
        "Instructions": {
            "make_file": [
                {
                    "action_type": "open_file_menu",
                    "description": "Open the File menu",
                    "parameters": {}
                }
            ]
        }
    }
    """
    # Construct file path
    json_file = Path(actions_dir) / f"{objective_type}_actions.json"
    
    print(f"[LOADER] Loading instruction file: {json_file}")
    
    # Check if file exists
    if not json_file.exists():
        error_msg = f"Instruction file not found: {json_file}"
        print(f"[LOADER ERROR] {error_msg}")
        notify_error(error_msg, "instruction_loader.load_instruction_file",
                    {"objective_type": objective_type})
        return False, error_msg
    
    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            instruction_data = json.load(f)
        
        print(f"[LOADER SUCCESS] Instruction file loaded successfully")
        return True, instruction_data
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in instruction file: {e}"
        print(f"[LOADER ERROR] {error_msg}")
        notify_error(error_msg, "instruction_loader.load_instruction_file",
                    {"objective_type": objective_type, "file": str(json_file)})
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Error reading instruction file: {e}"
        print(f"[LOADER ERROR] {error_msg}")
        notify_error(error_msg, "instruction_loader.load_instruction_file",
                    {"objective_type": objective_type})
        return False, error_msg


def extract_instructions_list(instruction_data: Dict[str, Any], 
                              objective_type: str) -> Tuple[bool, Any]:
    """
    Extract the instruction list from loaded JSON data.
    
    This validates the JSON structure and retrieves the action steps
    for the specified objective type.
    
    Args:
        instruction_data: Loaded JSON data from instruction file
        objective_type: The objective type to extract instructions for
        
    Returns:
        Tuple of (success: bool, instructions_list or error_message)
    """
    # Validate JSON has "Instructions" key
    if "Instructions" not in instruction_data:
        error_msg = "Instruction file missing 'Instructions' key"
        print(f"[LOADER ERROR] {error_msg}")
        return False, error_msg
    
    instructions_dict = instruction_data["Instructions"]
    
    # Validate objective type exists in Instructions
    if objective_type not in instructions_dict:
        error_msg = f"No instructions found for objective type: {objective_type}"
        print(f"[LOADER ERROR] {error_msg}")
        return False, error_msg
    
    instructions_list = instructions_dict[objective_type]
    
    # Validate it's a list
    if not isinstance(instructions_list, list):
        error_msg = f"Instructions must be a list, got: {type(instructions_list)}"
        print(f"[LOADER ERROR] {error_msg}")
        return False, error_msg
    
    print(f"[LOADER] Extracted {len(instructions_list)} instruction steps")
    return True, instructions_list


def extract_and_organize_values(objective_values: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Extract and organize required and optional values from objective data.
    
    This function handles both new format (with required/optional keys) and
    legacy format (flat structure). It returns both value sets for the
    workflow to use.
    
    Args:
        objective_values: Single value set from objectives file
        
    Returns:
        Tuple of (required_values, optional_values)
        
    Example input (new format):
    {
        "required": {
            "advertiser_name": "Acme Corp",
            "agency_name": "MediaWorks",
            "order_number": "ORD-001"
        },
        "optional": {
            "isci_2": "ACME5678",
            "rotation_percent_isci_2": "50"
        }
    }
    
    Example input (legacy format):
    {
        "file_name": "Report.txt",
        "text": "Content"
    }
    
    Returns (new format):
    (
        {"advertiser_name": "Acme Corp", "agency_name": "MediaWorks", "order_number": "ORD-001"},
        {"isci_2": "ACME5678", "rotation_percent_isci_2": "50"}
    )
    
    Returns (legacy format):
    (
        {"file_name": "Report.txt", "text": "Content"},
        {}
    )
    """
    required_values: dict[str, Any] = {}
    optional_values: dict[str, Any] = {}

    if not objective_values.get("required") :
        print("Required value are missing")
        return False, {}, {}
    print("Getting required values")
    required_values = objective_values.get("required", {})
    if objective_values.get("optional"):
        print("Optional values found")
        optional_values = objective_values.get("optional", {})
    
    return required_values, optional_values


def merge_values_into_instructions(instructions_list: List[Dict[str, Any]],
                                   required_values: Dict[str, Any],
                                   optional_values: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Merge required and optional values into instruction parameters.
    
    This function takes the instruction templates from JSON (with empty parameters)
    and fills them with actual values from the objective data.
    
    Args:
        instructions_list: List of instruction templates from JSON
        required_values: Required field values to merge
        optional_values: Optional field values to merge
        
    Returns:
        List of instructions with parameters filled in
        
    Example:
        Input instruction template:
        {
            "action_type": "enter_advertiser_name",
            "parameters": {"advertiser_name": ""}
        }
        
        Required values: {"advertiser_name": "Acme Corp"}
        
        Output:
        {
            "action_type": "enter_advertiser_name",
            "parameters": {"advertiser_name": "Acme Corp"}
        }
    """
    # Combine required and optional values for easy lookup
    all_values = {**required_values, **optional_values}
    
    merged_instructions = []
    
    for instruction in instructions_list:
        # Create a copy to avoid modifying the original
        merged_instruction = instruction.copy()
        template_params = merged_instruction.get("parameters", {}).copy()
        
        # Fill in each parameter with matching value
        for param_key in template_params.keys():
            # Check if we have a value for this parameter
            if param_key in all_values:
                template_params[param_key] = all_values[param_key]
                print(f"[LOADER] Merged '{param_key}' = '{all_values[param_key]}'")
            else:
                # Parameter remains empty (will be handled by action_executor)
                print(f"[LOADER] Parameter '{param_key}' left empty (not in values)")
        
        # Update the instruction with filled parameters
        merged_instruction["parameters"] = template_params
        merged_instructions.append(merged_instruction)
    
    print(f"[LOADER] Merged values into {len(merged_instructions)} instructions")
    return merged_instructions


def load_objective_data(objective_type: str,
                       objective_values: Dict[str, Any],
                       actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Complete loading process for a single objective execution.
    
    This is the main function that coordinates all loading steps:
    1. Load instruction definition file
    2. Extract instruction list
    3. Extract required values
    4. Extract optional values
    5. Return organized data structure
    
    Args:
        objective_type: The type of objective (e.g., "make_file")
        objective_values: Single value set from objectives file
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, loaded_data or error_message)
        
    Success returns dictionary structure:
    {
        "objective_type": "edit_copy_instruction",
        "instructions": [...],  # List of action steps
        "required_values": {...},  # Required field values
        "optional_values": {...}   # Optional field values
    }
    """
    print(f"\n[LOADER] Starting load process for objective: {objective_type}")
    
    # Step 1: Load instruction file
    success, file_data = load_instruction_file(objective_type, actions_dir)
    if not success:
        return False, file_data  # file_data contains error message
    
    # Step 2: Extract instructions list
    success, instructions_list = extract_instructions_list(file_data, objective_type)
    if not success:
        return False, instructions_list  # Contains error message
    
    # Step 3: Extract and organize required/optional values
    success, required_values, optional_values = extract_and_organize_values(objective_values)
    if not success:
        return False, "Failed to get or Missing required values"
    
    # Step 4: Merge values into instruction parameters
    merged_instructions = merge_values_into_instructions(
        instructions_list,
        required_values,
        optional_values
    )
    
    # Step 5: Build organized data structure
    loaded_data = {
        "objective_type": objective_type,
        "instructions": merged_instructions,  # Now with filled parameters!
    }
    
    print(f"[LOADER SUCCESS] Load completed")
    
    return True, loaded_data