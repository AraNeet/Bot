
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

# ============================================================================
# TEMPORARY FUNCTION FOR TESTING
# ============================================================================

def remove_inc_from_advertiser(advertiser_name: str) -> str:
    """
    Temporary function to remove ", inc." (case-insensitive) from advertiser name.
    
    This is a test-specific function that strips the ", inc." suffix from advertiser names
    to handle variations in naming format.
    
    Args:
        advertiser_name: The original advertiser name string
        
    Returns:
        The advertiser name with ", inc." removed if present (case-insensitive)
        
    Examples:
        remove_inc_from_advertiser("Chattem, Inc.") -> "Chattem"
        remove_inc_from_advertiser("Chattem, inc.") -> "Chattem"
        remove_inc_from_advertiser("Chattem") -> "Chattem"
    """
    if not advertiser_name:
        return advertiser_name
    
    # Case-insensitive check and removal of ", inc." suffix
    advertiser_lower = advertiser_name.lower()
    if advertiser_lower.endswith(", inc."):
        # Find the index where ", inc." starts in the original string (preserving case)
        index = advertiser_lower.rfind(", inc.")
        return advertiser_name[:index].strip()
    
    return advertiser_name.strip()

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
    
    Supports two JSON formats:
    1. Legacy format: Dictionary with objective_type keys and values_list arrays
    2. New format: Dictionary with 'alerts' array containing 'instruction_set' arrays
    
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
    
    # Check if this is the new format (has 'alerts' array)
    if "alerts" in objectives and isinstance(objectives.get("alerts"), list):
        print("\n[DETECTED] New JSON format with alerts array")
        return _parse_new_format(objectives, config)
    else:
        print("\n[DETECTED] Legacy JSON format")
        return _parse_legacy_format(objectives, config)


def _parse_new_format(objectives: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Parse the new JSON format:
    - alerts (groups of objectives)
    - instruction_set (objectives/instructions within each alert)
    - action field maps to objective type (E -> edit_copy_definition, D -> unsupported)
    
    Args:
        objectives: The loaded JSON dictionary
        config: The objectives configuration
        
    Returns:
        Tuple of (success: bool, supported_objectives or error_message)
    """
    alerts = objectives.get("alerts", [])
    agency = objectives.get("agency", "")
    revision_number = objectives.get("revision_number", "")
    
    if not alerts:
        return False, "No alerts found in objectives file"
    
    print(f"\n[PARSER] Found {len(alerts)} alert(s)")
    print(f"[PARSER] Agency: {agency}")
    print(f"[PARSER] Revision Number: {revision_number}")
    
    supported_objectives = []
    objectives_config = config.get("objectives", {})
    
    # Action type mapping
    ACTION_TYPE_MAP = {
        "E": "edit_copy_definition",
        "D": None  # Unsupported - will be skipped
    }
    
    # Track objectives by type
    objectives_by_type: Dict[str, List[Dict[str, Any]]] = {}
    
    # Process each alert
    for alert_idx, alert in enumerate(alerts, 1):
        advertiser_raw = alert.get("advertiser", "")
        # Apply temporary function to remove ", inc." from advertiser name for testing
        advertiser = remove_inc_from_advertiser(advertiser_raw)
        order_id = alert.get("order_id", "")
        instruction_set = alert.get("instruction_set", [])
        
        print(f"\n[PARSER] Alert {alert_idx}:")
        print(f"  - Advertiser (original): {advertiser_raw}")
        print(f"  - Advertiser (cleaned): {advertiser}")
        print(f"  - Order ID: {order_id}")
        print(f"  - Instructions: {len(instruction_set)}")
        
        # Process each instruction in the instruction_set
        for inst_idx, instruction in enumerate(instruction_set, 1):
            action_code = instruction.get("action", "")
            flight_start_date = instruction.get("flight_start_date", "")
            flight_end_date = instruction.get("flight_end_date", "")
            copy_instructions = instruction.get("copy_instructions", [])
            
            # Map action code to objective type
            objective_type = ACTION_TYPE_MAP.get(action_code)
            
            if objective_type is None:
                if action_code == "D":
                    print(f"  [SKIP] Instruction {inst_idx}: Action 'D' (duplicate) is unsupported")
                else:
                    print(f"  [SKIP] Instruction {inst_idx}: Unknown action '{action_code}'")
                continue
            
            # Check if objective type is supported
            if objective_type not in objectives_config:
                print(f"  [NOT SUPPORTED] Instruction {inst_idx}: Objective type '{objective_type}' not in config")
                notify_error(f"Unsupported objective type: {objective_type}", "parse_objectives")
                continue
            
            # Map fields from new format to expected format
            # Convert order_id to number for estimate_number
            estimate_number_value = int(order_id) if order_id and order_id.isdigit() else order_id
            
            # Extract isci_1 from first copy_instruction if available
            # The copy_id in copy_instructions might be the ISCI code
            isci_1_value = ""
            isci_list = []
            assignment_data = {}  # Maps alias (A, B, C...) to rotation percentage
            
            if copy_instructions and len(copy_instructions) > 0:
                first_copy = copy_instructions[0]
                isci_1_value = first_copy.get("copy_id", "")
                # Extract all ISCI values as a list for edit_media_details
                isci_list = [copy.get("copy_id", "") for copy in copy_instructions if copy.get("copy_id")]
                
                # Extract rotation_percent for assignment_data
                # Maps alias letters (A, B, C...) to percentage values
                for idx, copy in enumerate(copy_instructions):
                    rotation_percent = copy.get("rotation_percent", "")
                    if rotation_percent:
                        # Convert index to letter (0=A, 1=B, 2=C, etc.)
                        alias_letter = chr(ord('A') + idx)
                        # Remove % sign if present and store just the number
                        percent_value = rotation_percent.replace("%", "").strip()
                        assignment_data[alias_letter] = percent_value
                        print(f"    [ASSIGNMENT] {alias_letter} -> {percent_value}%")
            
            mapped_values = {
                "agency_name": agency,
                "advertiser_name": advertiser,
                "begin_date": flight_start_date,
                "end_date": flight_end_date,
                # Note: estimate_number uses order_id from alert level
                # isci_1 extracted from first copy_instruction's copy_id if available
                "estimate_number": estimate_number_value,  # Use order_id as estimate_number
                "isci_1": isci_1_value,
                "isci_list": isci_list,  # List of all ISCI values for edit_media_details
                "assignment_data": assignment_data,  # Maps alias (A, B, C...) to rotation percentage for edit_assignment_percentage
                "revision_number": revision_number,
                "agent_name": "test agent",
                "valid_flight_start": flight_start_date,
                "valid_flight_end": flight_end_date
            }
            
            # Check requirements
            has_all_required, missing_fields = check_objective_requirements(objective_type, mapped_values, config)
            
            if has_all_required:
                # Add to objectives list for this type
                if objective_type not in objectives_by_type:
                    objectives_by_type[objective_type] = []
                objectives_by_type[objective_type].append(mapped_values)
                print(f"  [VALID] Instruction {inst_idx}: {objective_type} (dates: {flight_start_date} to {flight_end_date})")
            else:
                print(f"  [MISSING] Instruction {inst_idx}: Missing fields: {', '.join(missing_fields)}")
                # Send error notification but don't fail completely - continue processing
                error_message = f"Missing required fields for {objective_type} in alert {alert_idx}, instruction {inst_idx}: {', '.join(missing_fields)}"
                error_details = {
                    "objective_type": objective_type,
                    "alert_index": alert_idx,
                    "instruction_index": inst_idx,
                    "missing_fields": missing_fields
                }
                notify_error(error_message, "parse_objectives", error_details)
    
    # Convert objectives_by_type to supported_objectives format
    for objective_type, values_list in objectives_by_type.items():
        supported_objectives.append({
            "objective_type": objective_type,
            "values_list": values_list
        })
        print(f"\n[OK] {objective_type}: {len(values_list)} valid instances")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Supported objectives: {len(supported_objectives)}")
    
    if not supported_objectives:
        return False, "No valid objectives found"
    
    print("[SUCCESS] All objectives validated successfully!")
    print("="*50)
    
    return True, supported_objectives


def _parse_legacy_format(objectives: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Parse the legacy JSON format:
    - Dictionary with objective_type keys
    - Values are lists of value dictionaries
    
    Args:
        objectives: The loaded JSON dictionary
        config: The objectives configuration
        
    Returns:
        Tuple of (success: bool, supported_objectives or error_message)
    """
    supported_objectives = []
    
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