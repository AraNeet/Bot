#!/usr/bin/env python3
"""
Workflow Engine Module - Orchestrates Objective Execution

CLEAR TERMINOLOGY:
- Objective: What the user wants to accomplish (e.g., "make_file", "edit_copy_instruction")
- Values: User-provided data (e.g., {"file_name": "test.txt", "text": "Hello"})
- Instructions: Action steps the bot performs (e.g., open_menu, type_text, save_file)

This module orchestrates the execution of objectives by:
1. Loading instruction definitions and values using instruction_loader_helper
2. Preparing instructions with merged values
3. Returning prepared data for action execution

The workflow engine focuses on data preparation and orchestration.
Action execution will be added in the next step.
"""

from typing import Dict, Any, List, Tuple
from src.workflow_module.helpers import instruction_loader_helper
from src.notification_module import notify_error


def prepare_single_objective(objective_type: str, 
                             objective_values: Dict[str, Any],
                             actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Prepare instruction data for a single objective execution.
    
    This function:
    1. Uses instruction_loader_helper to load and prepare all data
    2. Validates the loaded data
    3. Returns prepared instructions ready for execution
    
    Args:
        objective_type: The type of objective to prepare (e.g., "make_file")
        objective_values: User-provided values (e.g., {"file_name": "test.txt"})
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, prepared_data or error_message)
        
    Success returns:
    {
        "objective_type": "edit_copy_instruction",
        "instructions": [list of instructions with merged parameters],
        "required_values": {dict of required values},
        "optional_values": {dict of optional values}
    }
    """
    print(f"\n{'='*50}")
    print(f"Preparing objective: {objective_type}")
    print(f"{'='*50}")
    
    # Load instruction data using helper
    print(f"\n[WORKFLOW] Loading instruction data...")
    success, loaded_data = instruction_loader_helper.load_objective_data(
        objective_type=objective_type,
        objective_values=objective_values,
        actions_dir=actions_dir
    )
    
    if not success:
        error_msg = f"Failed to load instruction data: {loaded_data}"
        print(f"[WORKFLOW ERROR] {error_msg}")
        notify_error(error_msg, "workflow.prepare_single_objective",
                    {"objective_type": objective_type})
        return False, error_msg
    
    # Extract and validate prepared data
    instructions = loaded_data.get("instructions", [])
    required_values = loaded_data.get("required_values", {})
    optional_values = loaded_data.get("optional_values", {})
    
    # Validate instructions list
    if not instructions:
        error_msg = f"No instructions found for objective type: {objective_type}"
        print(f"[WORKFLOW ERROR] {error_msg}")
        return False, error_msg
    
    print(f"\n[WORKFLOW SUCCESS] Instruction data prepared successfully:")
    print(f"  - Total instructions: {len(instructions)}")
    print(f"  - Required fields: {len(required_values)}")
    print(f"  - Optional fields: {len(optional_values)}")
    
    return True, loaded_data


def prepare_workflow(supported_objectives: List[Dict[str, Any]], 
                    actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Prepare instruction data for all supported objectives.
    
    This function orchestrates the preparation of multiple objectives, each
    potentially having multiple value sets.
    
    Args:
        supported_objectives: List of supported objectives from parser
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, prepared_workflow or error_message)
        
    Example supported_objectives structure:
    [
        {
            "objective_type": "make_file",
            "values_list": [
                {"file_name": "Report.txt", "text": "Q4 Sales"},
                {"file_name": "Notes.txt", "text": "Meeting notes"}
            ]
        },
        {
            "objective_type": "edit_copy_instruction",
            "values_list": [
                {
                    "required": {"advertiser_name": "Acme", ...},
                    "optional": {"isci_2": "ABC123", ...}
                }
            ]
        }
    ]
    
    Success returns:
    {
        "total_objectives": 3,
        "prepared_objectives": [
            {
                "objective_type": "make_file",
                "value_set_index": 1,
                "instructions": [...],
                "required_values": {...},
                "optional_values": {...}
            },
            ...
        ]
    }
    """
    print("\n" + "="*60)
    print("WORKFLOW ENGINE - PREPARING OBJECTIVES")
    print("="*60)
    
    # Initialize preparation tracking
    preparation_results = {
        "total_objectives": 0,
        "prepared_objectives": []
    }
    
    # Prepare each objective type
    for objective_index, objective in enumerate(supported_objectives, start=1):
        objective_type = objective.get("objective_type")
        values_list = objective.get("values_list", [])
        
        print(f"\n{'='*60}")
        print(f"Processing Objective {objective_index}/{len(supported_objectives)}")
        print(f"Type: {objective_type}")
        print(f"Value sets to prepare: {len(values_list)}")
        print(f"{'='*60}")
        
        # Prepare the objective for each set of values
        for values_index, objective_values in enumerate(values_list, start=1):
            preparation_results["total_objectives"] += 1
            
            print(f"\n[WORKFLOW] Preparing value set {values_index}/{len(values_list)}")
            
            # Prepare single objective with these values
            success, prepared_data = prepare_single_objective(
                objective_type=objective_type,
                objective_values=objective_values,
                actions_dir=actions_dir
            )
            
            # Check if preparation was successful
            if not success:
                error_msg = f"Failed to prepare '{objective_type}' (value set {values_index}): {prepared_data}"
                print(f"[WORKFLOW ERROR] {error_msg}")
                notify_error(error_msg, "workflow.prepare_workflow",
                           {"objective_type": objective_type,
                            "values_index": values_index})
                return False, error_msg
            
            # Add value_set_index to prepared data for tracking
            prepared_data["value_set_index"] = values_index
            
            # Store prepared objective
            preparation_results["prepared_objectives"].append(prepared_data)
            
            print(f"[WORKFLOW SUCCESS] Value set {values_index} prepared successfully")
    
    # Print final summary
    print("\n" + "="*60)
    print("WORKFLOW ENGINE - PREPARATION COMPLETE")
    print("="*60)
    print(f"Total objectives prepared: {preparation_results['total_objectives']}")
    print(f"Ready for execution: {len(preparation_results['prepared_objectives'])}")
    print("="*60 + "\n")
    
    return True, preparation_results


def start_workflow_from_parser_results(parser_results: Dict[str, Any],
                                       actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Start the workflow preparation from parser results.
    
    This is the main entry point that receives results from the parser
    and prepares the workflow data.
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, prepared_workflow or error_message)
        
    Expected parser_results structure:
    {
        "supported_objectives": [
            {
                "objective_type": "make_file",
                "values_list": [...]
            }
        ],
        "unsupported_objectives": [...]
    }
    """
    print("\n[WORKFLOW] Received parser results, validating...")
    
    supported_objectives = parser_results["supported_objectives"]
    
    # Validate it's a list
    if not isinstance(supported_objectives, list):
        error_msg = f"'supported_objectives' must be a list, got: {type(supported_objectives)}"
        print(f"[WORKFLOW ERROR] {error_msg}")
        return False, error_msg
    
    print(f"[WORKFLOW] Validation successful")
    print(f"[WORKFLOW] Found {len(supported_objectives)} supported objective type(s)")
    
    # Prepare the workflow
    success, prepared_workflow = prepare_workflow(
        supported_objectives=supported_objectives,
        actions_dir=actions_dir
    )
    
    return success, prepared_workflow