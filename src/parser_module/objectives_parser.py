
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
from typing import Dict, Any, Tuple, List, Optional
from src.notification_module import notify_error

class ObjectiveType(Enum):
    """Enumeration of supported objective types."""
    EDIT_COPY_INSTRUCTION = "edit_copy_instruction"
    DO_NOT_AIR_INSTRUCTION = "do_not_air_instruction"
    OPEN_MULTINETWORK_INSTRUCTIONS_PAGE = "open_multinetwork_instructions_page"

# Global variable to store objectives configuration
_objectives_config = None

def load_objectives_config(config_file_path: str = "objectives_config.json") -> Tuple[bool, Any]:
    """
    Load objectives configuration from JSON file.
    
    Args:
        config_file_path: Path to the objectives configuration file
        
    Returns:
        Tuple of (success: bool, config or error_message)
    """
    global _objectives_config
    
    try:
        # Check if file exists
        if not os.path.exists(config_file_path):
            return False, f"Objectives config file not found: {config_file_path}"
        
        # Load JSON data
        with open(config_file_path, 'r', encoding='utf-8') as file:
            _objectives_config = json.load(file)
            return True, _objectives_config
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in objectives config file: {e}"
        notify_error(error_msg, "load_objectives_config")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading objectives config file: {e}"
        notify_error(error_msg, "load_objectives_config")
        return False, error_msg

def get_objective_config(objective_type: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific objective type.
    
    Args:
        objective_type: The objective type to get config for
        
    Returns:
        Configuration dict or None if not found
    """
    global _objectives_config
    
    if _objectives_config is None:
        # Try to load config if not already loaded
        success, config = load_objectives_config()
        if not success:
            return None
    
    objectives = _objectives_config.get("objectives", {})
    return objectives.get(objective_type)

def validate_objective_values(objective_type: str, values: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate objective values against the configuration schema.
    
    Args:
        objective_type: The type of objective being validated
        values: The values to validate
        
    Returns:
        Tuple of (is_valid: bool, error_messages: List[str])
    """
    config = get_objective_config(objective_type)
    if config is None:
        return False, [f"Unknown objective type: {objective_type}"]
    
    errors = []
    
    # Check required fields
    required_fields = config.get("required_fields", {})
    for field_name, field_config in required_fields.items():
        if field_name not in values:
            errors.append(f"Missing required field: {field_name}")
        elif values[field_name] is None or values[field_name] == "":
            errors.append(f"Required field '{field_name}' cannot be empty")
    
    # Check optional fields (validate type if provided)
    optional_fields = config.get("optional_fields", {})
    for field_name, field_config in optional_fields.items():
        if field_name in values:
            value = values[field_name]
            expected_type = field_config.get("type")
            
            # Type validation
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field_name}' must be a number")
            
            # Range validation for numbers
            if expected_type == "number" and isinstance(value, (int, float)):
                min_val = field_config.get("min")
                max_val = field_config.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"Field '{field_name}' must be >= {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"Field '{field_name}' must be <= {max_val}")
    
    # Check for unknown fields
    all_known_fields = set(required_fields.keys()) | set(optional_fields.keys())
    unknown_fields = set(values.keys()) - all_known_fields
    if unknown_fields:
        errors.append(f"Unknown fields: {', '.join(unknown_fields)}")
    
    return len(errors) == 0, errors

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


def _merge_objective_values(values: Dict[str, Any]) -> Dict[str, Any]:
    """Merge required and optional values from objective instance."""
    if "required" in values and "optional" in values:
        return {**values.get("required", {}), **values.get("optional", {})}
    return values

def _check_required_fields(objective_type: str, merged_values: Dict[str, Any]) -> List[str]:
    """Check for missing required fields and return list of missing fields."""
    config = get_objective_config(objective_type)
    if not config:
        return []
    
    required_fields = config.get("required_fields", {})
    missing_fields = []
    
    for field_name in required_fields.keys():
        if field_name not in merged_values or merged_values[field_name] in [None, ""]:
            missing_fields.append(field_name)
    
    return missing_fields

def _validate_objective_instance(objective_type: str, values: Dict[str, Any], instance_index: int) -> Tuple[bool, Dict[str, Any], List[str]]:
    """Validate a single objective instance and return validation results."""
    if not isinstance(values, dict):
        error_msg = f"Invalid values format for {objective_type}[{instance_index}]: must be a dictionary"
        return False, {}, [error_msg]
    
    # Merge required and optional values
    merged_values = _merge_objective_values(values)
    
    # Check for missing required fields
    missing_required = _check_required_fields(objective_type, merged_values)
    
    if missing_required:
        error_msg = f"Missing required fields for {objective_type}[{instance_index}]: {', '.join(missing_required)}"
        return False, merged_values, [error_msg]
    
    # Validate the merged values
    is_valid, errors = validate_objective_values(objective_type, merged_values)
    
    if not is_valid:
        error_msg = f"Validation errors for {objective_type}[{instance_index}]: {'; '.join(errors)}"
        return False, merged_values, [error_msg]
    
    return True, merged_values, []

def _process_supported_objective(objective_type: str, values_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Process a supported objective type and return validated values and errors."""
    validated_values_list = []
    validation_errors = []
    
    print(f"\n📋 Objective: {objective_type}")
    print(f"   Total instances: {len(values_list)}")
    
    for i, values in enumerate(values_list):
        print(f"\n   Instance {i+1}:")
        
        is_valid, merged_values, errors = _validate_objective_instance(objective_type, values, i)
        
        if is_valid:
            validated_values_list.append(merged_values)
            print(f"      ✅ Validation: PASSED")
        else:
            validation_errors.extend(errors)
            print(f"      ❌ Validation: FAILED")
            for error in errors:
                print(f"         - {error}")
    
    # Check if any instances failed validation
    if validation_errors:
        print(f"\n   ⚠️  {objective_type}: {len(validated_values_list)}/{len(values_list)} instances valid")
        # Send email notification for missing required values
        _send_missing_values_email(objective_type, validation_errors)
        return [], validation_errors  # Return empty list to fail the entire objective
    
    print(f"\n   ✅ {objective_type}: All {len(values_list)} instances valid")
    return validated_values_list, []

def _send_missing_values_email(objective_type: str, errors: List[str]) -> None:
    """Send email notification when required values are missing."""
    try:
        error_message = f"Missing required values for {objective_type}: {'; '.join(errors)}"
        error_details = {
            "objective_type": objective_type,
            "missing_fields": errors,
            "error_type": "missing_required_values"
        }
        
        notify_error(error_message, "parse_objectives", error_details)
        print(f"      📧 Email notification sent for missing required values")
        
    except Exception as e:
        print(f"      ⚠️  Failed to send email notification: {e}")

def parse_objectives(objectives: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Parse objectives and validate required fields. Errors out if any required values are missing.
    
    Args:
        objectives: Dictionary containing objective data
        
    Returns:
        Tuple of (success: bool, parsing_results or error_message)
    """
    if not isinstance(objectives, dict):
        return False, "Objectives must be a dictionary"
    
    # Load objectives configuration if not already loaded
    if _objectives_config is None:
        success, config = load_objectives_config()
        if not success:
            return False, f"Failed to load objectives configuration: {config}"
    
    supported = []
    unsupported = []
    all_validation_errors = []
    
    print("\n" + "="*60)
    print("OBJECTIVE VALIDATION REPORT")
    print("="*60)
    
    # Process each objective type in the file
    for objective_type, values_list in objectives.items():
        if not isinstance(values_list, list):
            continue
        
        # Check if objective type is supported
        is_supported = any(obj.value == objective_type for obj in ObjectiveType)
        
        if is_supported:
            validated_values, validation_errors = _process_supported_objective(objective_type, values_list)
            
            if validation_errors:
                # If any validation errors, fail the entire objective
                all_validation_errors.extend(validation_errors)
                print(f"\n❌ {objective_type}: FAILED - Missing required values")
                return False, f"Missing required values for {objective_type}: {'; '.join(validation_errors)}"
            
            supported.append({
                "objective_type": objective_type,
                "values_list": validated_values
            })
                
        else:
            unsupported.append({
                "objective_type": objective_type,
                "values_list": values_list
            })
            print(f"\n❌ Unsupported objective: {objective_type}")
            print(f"   Instances: {len(values_list)}")
            notify_error(
                f"Unsupported objective type: {objective_type}", 
                "parser.parse_objectives", 
                {"objective_type": objective_type}
            )
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Supported objectives: {len(supported)}")
    print(f"Unsupported objectives: {len(unsupported)}")
    
    if not supported:
        notify_error(
            "There were no supported objectives given",
            "parse_objectives",
            {"supported_objectives": supported, "unsupported_objectives": unsupported}
        )
        return False, "No supported objectives found"

    print("✅ All objectives validated successfully!")
    print("="*60)

    results = {
        "supported": supported,
        "unsupported": unsupported
    }
    
    return True, results