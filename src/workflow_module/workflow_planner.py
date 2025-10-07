#!/usr/bin/env python3
"""
Workflow Planner Module

This module handles the PLANNING phase of workflow execution:
- Loading instruction definitions
- Merging user values into instruction templates  
- Preparing executable instruction sequences
- Validating all required data is present

The planner transforms parser output into execution-ready instructions.

Responsibilities:
- Load instruction JSON files for objective types
- Extract and organize required/optional values
- Merge values into instruction parameters
- Validate preparation succeeded
- Return organized instruction sequences

The workflow engine then executes what the planner prepares.
"""

from typing import Dict, Any, List, Tuple
from workflow_module.helpers import instruction_loader
from src.notification_module import notify_error


def prepare_single_objective(objective_type: str, 
                            objective_values: Dict[str, Any],
                            actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Prepare instruction data for a single objective execution.
    
    This function coordinates the entire preparation process:
    1. Load instruction definition JSON file
    2. Extract instruction steps list
    3. Extract required/optional values
    4. Merge values into instruction parameters
    5. Validate preparation succeeded
    
    Args:
        objective_type: The type of objective (e.g., "edit_copy_instruction")
        objective_values: User-provided values with required/optional fields
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, prepared_data or error_message)
        
    Success returns dictionary:
    {
        "objective_type": "edit_copy_instruction",
        "instructions": [
            {
                "action_type": "enter_advertiser_name",
                "description": "Enter advertiser name",
                "parameters": {"advertiser_name": "Acme Corp"},  # Merged!
                "verification": {
                    "type": "text_inputted",
                    "expected_text": "Acme Corp"  # Merged!
                }
            },
            ...
        ]
    }
    
    Example:
        objective_type = "edit_copy_instruction"
        objective_values = {
            "required": {
                "advertiser_name": "Acme Corp",
                "order_number": "ORD-001"
            },
            "optional": {
                "isci_2": "ACME5678"
            }
        }
        
        success, data = prepare_single_objective(objective_type, objective_values)
        if success:
            instructions = data["instructions"]  # Ready to execute!
    """
    print(f"\n{'='*50}")
    print(f"[PLANNER] Preparing objective: {objective_type}")
    print(f"{'='*50}")
    
    # Use instruction_loader to load and prepare all data
    print(f"[PLANNER] Loading instruction data...")
    success, loaded_data = instruction_loader.load_objective_data(
        objective_type=objective_type,
        objective_values=objective_values,
        actions_dir=actions_dir
    )
    
    if not success:
        error_msg = f"Failed to load instruction data: {loaded_data}"
        print(f"[PLANNER ERROR] {error_msg}")
        notify_error(
            error_msg, 
            "workflow_planner.prepare_single_objective",
            {"objective_type": objective_type}
        )
        return False, error_msg
    
    # Validate the loaded data structure
    instructions = loaded_data.get("instructions", [])
    
    if not instructions:
        error_msg = f"No instructions found for objective type: {objective_type}"
        print(f"[PLANNER ERROR] {error_msg}")
        notify_error(
            error_msg,
            "workflow_planner.prepare_single_objective",
            {"objective_type": objective_type, "loaded_data": loaded_data}
        )
        return False, error_msg
    
    # Validate each instruction has required fields
    for idx, instruction in enumerate(instructions, 1):
        if "action_type" not in instruction:
            error_msg = f"Instruction {idx} missing 'action_type' field"
            print(f"[PLANNER ERROR] {error_msg}")
            return False, error_msg
        
        if "parameters" not in instruction:
            error_msg = f"Instruction {idx} missing 'parameters' field"
            print(f"[PLANNER ERROR] {error_msg}")
            return False, error_msg
    
    print(f"[PLANNER SUCCESS] Objective prepared successfully:")
    print(f"  - Objective type: {objective_type}")
    print(f"  - Total instructions: {len(instructions)}")
    print(f"  - All instructions validated ✓")
    
    return True, loaded_data

def prepare_all_objectives(supported_objectives: List[Dict[str, Any]],
                           actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Prepare all supported objectives from parser results.
    
    This function:
    1. Iterates through all supported objective types
    2. For each objective, prepares all value sets
    3. Tracks which value set each preparation represents
    4. Returns list of all prepared objectives
    
    Args:
        supported_objectives: List from parser with structure:
            [
                {
                    "objective_type": "edit_copy_instruction",
                    "values_list": [
                        {"required": {...}, "optional": {...}},
                        {"required": {...}, "optional": {...}}
                    ]
                }
            ]
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, prepared_list or error_message)
        
    Success returns list of prepared objectives:
    [
        {
            "objective_type": "edit_copy_instruction",
            "value_set_index": 1,
            "instructions": [...]
        },
        {
            "objective_type": "edit_copy_instruction", 
            "value_set_index": 2,
            "instructions": [...]
        }
    ]
    
    Example:
        parser_results = {
            "supported_objectives": [...],
            "unsupported_objectives": [...]
        }
        
        success, prepared = prepare_all_objectives(
            parser_results["supported_objectives"]
        )
        
        if success:
            for prep_obj in prepared:
                print(f"Ready: {prep_obj['objective_type']} #{prep_obj['value_set_index']}")
    """
    print("\n" + "="*60)
    print("[PLANNER] PREPARING ALL OBJECTIVES")
    print("="*60)
    
    if not isinstance(supported_objectives, list):
        error_msg = f"'supported_objectives' must be a list, got: {type(supported_objectives)}"
        print(f"[PLANNER ERROR] {error_msg}")
        return False, error_msg
    
    if not supported_objectives:
        warning_msg = "No supported objectives to prepare"
        print(f"[PLANNER WARNING] {warning_msg}")
        return True, []  # Empty but successful
    
    prepared_objectives = []
    total_value_sets = 0
    
    # Iterate through each objective type
    for obj_index, objective in enumerate(supported_objectives, start=1):
        objective_type = objective.get("objective_type")
        values_list = objective.get("values_list", [])
        
        if not objective_type:
            error_msg = f"Objective {obj_index} missing 'objective_type'"
            print(f"[PLANNER ERROR] {error_msg}")
            return False, error_msg
        
        print(f"\n[PLANNER] Processing '{objective_type}':")
        print(f"  - Value sets to prepare: {len(values_list)}")
        
        # Prepare each value set for this objective type
        for val_index, objective_values in enumerate(values_list, start=1):
            total_value_sets += 1
            
            print(f"\n[PLANNER] Preparing value set {val_index}/{len(values_list)}...")
            
            success, prepared_data = prepare_single_objective(
                objective_type=objective_type,
                objective_values=objective_values,
                actions_dir=actions_dir
            )
            
            if not success:
                error_msg = f"Failed to prepare '{objective_type}' value set {val_index}: {prepared_data}"
                print(f"[PLANNER ERROR] {error_msg}")
                notify_error(
                    error_msg,
                    "workflow_planner.prepare_all_objectives",
                    {
                        "objective_type": objective_type,
                        "value_set_index": val_index,
                        "total_value_sets": len(values_list)
                    }
                )
                return False, error_msg
            
            # Add tracking information
            prepared_data["value_set_index"] = val_index
            prepared_objectives.append(prepared_data)
            
            print(f"[PLANNER] ✓ Value set {val_index} prepared successfully")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"[PLANNER SUCCESS] ALL OBJECTIVES PREPARED")
    print(f"{'='*60}")
    print(f"  - Objective types: {len(supported_objectives)}")
    print(f"  - Total value sets: {total_value_sets}")
    print(f"  - Prepared objectives: {len(prepared_objectives)}")
    print(f"{'='*60}\n")
    
    return True, prepared_objectives

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_parser_results(parser_results: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate parser results structure before planning.
    
    This ensures the planner receives correctly formatted data
    from the parser module.
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        
    Returns:
        Tuple of (valid: bool, error_message or success_message)
        
    Expected structure:
    {
        "supported_objectives": [...],
        "unsupported_objectives": [...]
    }
    """
    print("[PLANNER] Validating parser results...")
    
    # Check if it's a dictionary
    if not isinstance(parser_results, dict):
        error_msg = f"Parser results must be a dict, got: {type(parser_results)}"
        print(f"[PLANNER ERROR] {error_msg}")
        return False, error_msg
    
    # Check for required keys
    if "supported_objectives" not in parser_results:
        error_msg = "Parser results missing 'supported_objectives' key"
        print(f"[PLANNER ERROR] {error_msg}")
        return False, error_msg
    
    supported = parser_results["supported_objectives"]
    
    # Validate supported_objectives is a list
    if not isinstance(supported, list):
        error_msg = f"'supported_objectives' must be a list, got: {type(supported)}"
        print(f"[PLANNER ERROR] {error_msg}")
        return False, error_msg
    
    # Count total value sets
    total_value_sets = sum(
        len(obj.get("values_list", [])) 
        for obj in supported
    )
    
    success_msg = f"Parser results valid: {len(supported)} objective types, {total_value_sets} total value sets"
    print(f"[PLANNER] ✓ {success_msg}")
    
    return True, success_msg

def print_preparation_summary(prepared_objectives: List[Dict[str, Any]]) -> None:
    """
    Print a detailed summary of prepared objectives.
    
    Useful for debugging and verification before execution.
    
    Args:
        prepared_objectives: List of prepared objectives from prepare_all_objectives()
    """
    print("\n" + "="*60)
    print("PREPARATION SUMMARY")
    print("="*60)
    
    if not prepared_objectives:
        print("  No objectives prepared")
        print("="*60 + "\n")
        return
    
    # Group by objective type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for prep_obj in prepared_objectives:
        obj_type = prep_obj.get("objective_type", "unknown")
        if obj_type not in by_type:
            by_type[obj_type] = []
        by_type[obj_type].append(prep_obj)
    
    # Print summary for each type
    for obj_type, prep_list in by_type.items():
        print(f"\n{obj_type}:")
        print(f"  - Value sets: {len(prep_list)}")
        
        for prep_obj in prep_list:
            val_idx = prep_obj.get("value_set_index", "?")
            inst_count = len(prep_obj.get("instructions", []))
            print(f"    • Set #{val_idx}: {inst_count} instructions")
    
    total_instructions = sum(
        len(obj.get("instructions", [])) 
        for obj in prepared_objectives
    )
    
    print(f"\n{'─'*60}")
    print(f"Total prepared: {len(prepared_objectives)} objectives")
    print(f"Total instructions: {total_instructions}")
    print(f"{'='*60}\n")

# ============================================================================
# MAIN PLANNING FUNCTION
# ============================================================================

def plan_workflow(parser_results: Dict[str, Any],
                 actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Main planning function - validates and prepares all objectives.
    
    This is the primary entry point for the planner module.
    It orchestrates validation, preparation, and summary.
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, prepared_objectives or error_message)
        
    Example usage:
        # In workflow_engine.py:
        from workflow_module import planner
        
        success, prepared = planner.plan_workflow(parser_results)
        if success:
            # Execute prepared objectives
            execute_workflow(prepared, corner_templates)
    """
    print("\n" + "="*70)
    print("WORKFLOW PLANNER - STARTING PLANNING PHASE")
    print("="*70)
    
    # Step 1: Validate parser results
    valid, msg = validate_parser_results(parser_results)
    if not valid:
        return False, msg
    
    # Step 2: Prepare all objectives
    supported = parser_results["supported_objectives"]
    success, result = prepare_all_objectives(supported, actions_dir)
    
    if not success:
        return False, result
    
    prepared_objectives = result
    
    # Step 3: Print summary
    print_preparation_summary(prepared_objectives)
    
    print("="*70)
    print("WORKFLOW PLANNER - PLANNING COMPLETE ✓")
    print("="*70 + "\n")
    
    return True, prepared_objectives