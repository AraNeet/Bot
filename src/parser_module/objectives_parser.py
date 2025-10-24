
#!/usr/bin/env python3
"""
Objectives Parser Module

Simple parser that loads objectives, checks if they're supported, validates required values,
and returns supported objectives with their values.

Functions:
1. load_objectives_config() - Load configuration from JSON
2. read_objectives_file() - Read objectives from JSON file  
3. check_objective_requirements() - Validate required values
4. parse_objectives() - Main function that orchestrates the process
"""

import json
import os
from typing import Dict, Any, Tuple, List, Optional
from src.notification_module.error_notifier import notify_error

def load_objectives_config(config_file_path: str = "objectives_config.json") -> Tuple[bool, Any]:
    """
    Function 1: Load objectives configuration from JSON file.
    
    Args:
        config_file_path: Path to the objectives configuration file
        
    Returns:
        Tuple of (success: bool, config or error_message)
    """
    try:
        if not os.path.exists(config_file_path):
            return False, f"Objectives config file not found: {config_file_path}"
        
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            return True, config
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in objectives config file: {e}"
        notify_error(error_msg, "load_objectives_config")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading objectives config file: {e}"
        notify_error(error_msg, "load_objectives_config")
        return False, error_msg

def read_objectives_file(objectives_file_path: str) -> Tuple[bool, Any]:
    """
    Function 2: Read objectives from JSON file.
    
    Args:
        objectives_file_path: Path to the objectives JSON file
        
    Returns:
        Tuple of (success: bool, objectives or error_message)
    """
    try:
        if not os.path.exists(objectives_file_path):
            return False, f"Objectives file not found: {objectives_file_path}"
        
        with open(objectives_file_path, 'r', encoding='utf-8') as file:
            objectives = json.load(file)
            return True, objectives
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in objectives file: {e}"
        notify_error(error_msg, "read_objectives_file")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading objectives file: {e}"
        notify_error(error_msg, "read_objectives_file")
        return False, error_msg

def check_objective_requirements(objective_type: str, values: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Function 3: Check if objective has all required values.
    
    Args:
        objective_type: The type of objective to check
        values: The values to validate
        config: The objectives configuration
        
    Returns:
        Tuple of (has_all_required: bool, missing_fields: List[str])
    """
    if config is None:
        return False, ["Configuration not provided"]
    
    objectives = config.get("objectives", {})
    objective_config = objectives.get(objective_type)
    
    if objective_config is None:
        return False, [f"Objective type '{objective_type}' not supported"]
    
    required_fields = objective_config.get("required_fields", {})
    missing_fields = []
    
    for field_name in required_fields.keys():
        if field_name not in values or values[field_name] in [None, ""]:
            missing_fields.append(field_name)
    
    return len(missing_fields) == 0, missing_fields

def parse_objectives(objectives_file_path: str) -> Tuple[bool, Any]:
    """
    Function 4: Main function that orchestrates the parsing process.
    
    Args:
        objectives_file_path: Path to the objectives JSON file
        
    Returns:
        Tuple of (success: bool, supported_objectives or error_message)
    """
    # Step 1: Load configuration
    success, config = load_objectives_config()
    if not success:
        return False, f"Failed to load configuration: {config}"
    
    # Step 2: Read objectives file
    success, objectives = read_objectives_file(objectives_file_path)
    if not success:
        return False, f"Failed to read objectives file: {objectives}"
    
    if not isinstance(objectives, dict):
        return False, "Objectives must be a dictionary"
    
    supported_objectives = []
    
    print("\n" + "="*50)
    print("OBJECTIVE VALIDATION")
    print("="*50)
    
    # Step 3: Check each objective
    for objective_type, values_list in objectives.items():
        if not isinstance(values_list, list):
            continue
        
        print(f"\n[CHECK] {objective_type}")
        
        # Check if objective type is supported
        objectives_config = config.get("objectives", {})
        if objective_type not in objectives_config:
            print(f"   [NOT SUPPORTED]")
            notify_error(f"Unsupported objective type: {objective_type}", "parse_objectives")
            continue
        
        # Check each instance
        valid_instances = []
        for i, values in enumerate(values_list):
            if not isinstance(values, dict):
                print(f"   [INVALID] Instance {i+1}: Invalid format")
                continue
            
            # Merge required and optional values
            if "required" in values and "optional" in values:
                merged_values = {**values.get("required", {}), **values.get("optional", {})}
            else:
                merged_values = values
            
            # Check requirements
            has_all_required, missing_fields = check_objective_requirements(objective_type, merged_values, config)
            
            if has_all_required:
                valid_instances.append(merged_values)
                print(f"   [VALID] Instance {i+1}")
            else:
                print(f"   [MISSING] Instance {i+1}: {', '.join(missing_fields)}")
                # Send error notification
                error_message = f"Missing required fields for {objective_type}[{i}]: {', '.join(missing_fields)}"
                error_details = {
                    "objective_type": objective_type,
                    "instance": i,
                    "missing_fields": missing_fields
                }
                notify_error(error_message, "parse_objectives", error_details)
                return False, f"Missing required values: {error_message}"
        
        if valid_instances:
            supported_objectives.append({
                "objective_type": objective_type,
                "values_list": valid_instances
            })
            print(f"   [OK] {objective_type}: {len(valid_instances)} valid instances")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Supported objectives: {len(supported_objectives)}")
    
    if not supported_objectives:
        return False, "No valid objectives found"
    
    print("[SUCCESS] All objectives validated successfully!")
    print("="*50)
    
    return True, supported_objectives