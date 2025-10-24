#!/usr/bin/env python3
"""
Workflow Planner Module - RESILIENT VERSION

This module handles the PLANNING phase of workflow execution with resilient error handling.
If some objectives fail to prepare, it:
- Continues preparing the rest
- Notifies user about failures
- Returns successfully prepared objectives
- Only fails if ALL objectives fail to prepare

Key Change: Graceful failure handling - partial success is still success!
"""

from typing import Dict, Any, List, Tuple
import instruction_loader
from src.notification_module import notify_error


# ============================================================================
# SINGLE OBJECTIVE PREPARATION
# ============================================================================

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
        return False, error_msg
    
    # Validate the loaded data structure
    instructions = loaded_data.get("instructions", [])
    
    if not instructions:
        error_msg = f"No instructions found for objective type: {objective_type}"
        print(f"[PLANNER ERROR] {error_msg}")
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


# ============================================================================
# BATCH PREPARATION (RESILIENT VERSION)
# ============================================================================

def prepare_all_objectives(supported_objectives: List[Dict[str, Any]],
                           actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Dict[str, Any]]:
    """
    Prepare all supported objectives from parser results - RESILIENT VERSION.
    
    This function is RESILIENT to partial failures:
    - If some objectives fail, it continues with the rest
    - Tracks which objectives succeeded and which failed
    - Sends notifications for failures
    - Returns success if AT LEAST ONE objective prepared successfully
    - Only fails if ALL objectives fail
    
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
        Tuple of (success: bool, results_dict)
        
    Results dictionary structure:
    {
        "prepared_objectives": [...],  # Successfully prepared objectives
        "failed_objectives": [...],    # Failed objectives with error details
        "total_requested": 5,
        "total_prepared": 3,
        "total_failed": 2
    }
    
    Example:
        success, results = prepare_all_objectives(supported_objectives)
        
        if success:
            print(f"Prepared: {results['total_prepared']}/{results['total_requested']}")
            
            if results['failed_objectives']:
                print("Some objectives failed:")
                for failed in results['failed_objectives']:
                    print(f"  - {failed['objective_type']}: {failed['error']}")
    """
    print("\n" + "="*70)
    print("[PLANNER] PREPARING ALL OBJECTIVES")
    print("="*70)
    
    # Validate input
    if not isinstance(supported_objectives, list):
        error_msg = f"'supported_objectives' must be a list, got: {type(supported_objectives)}"
        print(f"[PLANNER ERROR] {error_msg}")
        return False, {"error": error_msg}
    
    if not supported_objectives:
        warning_msg = "No supported objectives to prepare"
        print(f"[PLANNER WARNING] {warning_msg}")
        return True, {
            "prepared_objectives": [],
            "failed_objectives": [],
            "total_requested": 0,
            "total_prepared": 0,
            "total_failed": 0
        }
    
    # Initialize tracking
    prepared_objectives = []
    failed_objectives = []
    total_value_sets = sum(len(obj.get("values_list", [])) for obj in supported_objectives)
    
    print(f"[PLANNER] Total objective types: {len(supported_objectives)}")
    print(f"[PLANNER] Total value sets to prepare: {total_value_sets}")
    
    # Iterate through each objective type
    for obj_index, objective in enumerate(supported_objectives, start=1):
        objective_type = objective.get("objective_type")
        values_list = objective.get("values_list", [])
        
        if not objective_type:
            error_msg = f"Objective {obj_index} missing 'objective_type'"
            print(f"[PLANNER ERROR] {error_msg}")
            failed_objectives.append({
                "objective_type": "unknown",
                "value_set_index": None,
                "error": error_msg,
                "error_type": "missing_objective_type"
            })
            continue
        
        print(f"\n[PLANNER] Processing '{objective_type}':")
        print(f"  - Value sets to prepare: {len(values_list)}")
        
        # Prepare each value set for this objective type
        for val_index, objective_values in enumerate(values_list, start=1):
            print(f"\n[PLANNER] Preparing value set {val_index}/{len(values_list)}...")
            
            try:
                success, prepared_data = prepare_single_objective(
                    objective_type=objective_type,
                    objective_values=objective_values,
                    actions_dir=actions_dir
                )
                
                if success:
                    # Preparation succeeded
                    prepared_data["value_set_index"] = val_index
                    prepared_objectives.append(prepared_data)
                    print(f"[PLANNER] ✓ Value set {val_index} prepared successfully")
                else:
                    # Preparation failed
                    error_msg = prepared_data  # prepared_data contains error message
                    print(f"[PLANNER ERROR] ✗ Value set {val_index} failed: {error_msg}")
                    
                    failed_objectives.append({
                        "objective_type": objective_type,
                        "value_set_index": val_index,
                        "error": error_msg,
                        "error_type": "preparation_failed"
                    })
                    
                    # Send notification for this failure
                    notify_error(
                        f"Failed to prepare '{objective_type}' value set {val_index}",
                        "workflow_planner.prepare_all_objectives",
                        {
                            "objective_type": objective_type,
                            "value_set_index": val_index,
                            "total_value_sets": len(values_list),
                            "error": error_msg
                        }
                    )
                    
            except Exception as e:
                # Unexpected exception during preparation
                error_msg = f"Exception during preparation: {str(e)}"
                print(f"[PLANNER ERROR] ✗ Value set {val_index} exception: {error_msg}")
                
                failed_objectives.append({
                    "objective_type": objective_type,
                    "value_set_index": val_index,
                    "error": error_msg,
                    "error_type": "exception"
                })
                
                # Send notification for exception
                notify_error(
                    f"Exception preparing '{objective_type}' value set {val_index}",
                    "workflow_planner.prepare_all_objectives",
                    {
                        "objective_type": objective_type,
                        "value_set_index": val_index,
                        "exception": str(e)
                    }
                )
    
    # Build results dictionary
    results = {
        "prepared_objectives": prepared_objectives,
        "failed_objectives": failed_objectives,
        "total_requested": total_value_sets,
        "total_prepared": len(prepared_objectives),
        "total_failed": len(failed_objectives)
    }
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"[PLANNER] PREPARATION COMPLETE")
    print(f"{'='*70}")
    print(f"  Total requested:  {results['total_requested']}")
    print(f"  Successfully prepared: {results['total_prepared']} ✓")
    print(f"  Failed:           {results['total_failed']} {'✗' if results['total_failed'] > 0 else ''}")
    print(f"{'='*70}")
    
    # Print failure details if any
    if failed_objectives:
        print(f"\n[PLANNER] Failed Objectives Details:")
        for failed in failed_objectives:
            print(f"  ✗ {failed['objective_type']} (set #{failed['value_set_index']})")
            print(f"    Error: {failed['error']}")
    
    # Determine overall success
    if results['total_prepared'] == 0:
        # ALL objectives failed
        print(f"\n[PLANNER ERROR] All objectives failed to prepare!")
        return False, results
    elif results['total_failed'] > 0:
        # PARTIAL success
        print(f"\n[PLANNER WARNING] Partial success - some objectives failed")
        print(f"[PLANNER] Continuing with {results['total_prepared']} successfully prepared objectives")
        return True, results
    else:
        # COMPLETE success
        print(f"\n[PLANNER SUCCESS] All objectives prepared successfully!")
        return True, results

def print_preparation_summary(prepared_objectives: List[Dict[str, Any]]) -> None:
    """
    Print a detailed summary of prepared objectives.
    
    Args:
        prepared_objectives: List of prepared objectives from prepare_all_objectives()
    """
    print("\n" + "="*70)
    print("PREPARATION SUMMARY")
    print("="*70)
    
    if not prepared_objectives:
        print("  No objectives prepared")
        print("="*70 + "\n")
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
    
    print(f"\n{'─'*70}")
    print(f"Total prepared: {len(prepared_objectives)} objectives")
    print(f"Total instructions: {total_instructions}")
    print(f"{'='*70}\n")

# ============================================================================
# MAIN PLANNING FUNCTION
# ============================================================================

def plan_workflow(parser_results: Dict[str, Any],
                 actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Main planning function - validates and prepares all objectives (RESILIENT).
    
    This function is RESILIENT:
    - Validates parser results
    - Prepares all objectives (continues on partial failures)
    - Returns success if at least one objective prepared
    - Provides detailed results including failures
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, results)
        
    Results structure on success:
    {
        "prepared_objectives": [...],
        "failed_objectives": [...],
        "total_requested": 5,
        "total_prepared": 3,
        "total_failed": 2
    }
    
    Example usage:
        success, results = planner.plan_workflow(parser_results)
        
        if success:
            # Use prepared objectives
            prepared = results["prepared_objectives"]
            
            # Warn about failures if any
            if results["failed_objectives"]:
                print(f"Warning: {results['total_failed']} objectives failed")
        else:
            # ALL objectives failed
            print("Planning failed completely")
    """
    print("\n" + "="*70)
    print("WORKFLOW PLANNER - STARTING PLANNING PHASE")
    print("="*70)

    supported = parser_results["supported_objectives"]
    success, results = prepare_all_objectives(supported, actions_dir)
    
    if not success:
        # ALL objectives failed to prepare
        print("="*70)
        print("WORKFLOW PLANNER - PLANNING FAILED ✗")
        print("="*70 + "\n")
        return False, results
    
    # Step 3: Print summary of prepared objectives
    if results["prepared_objectives"]:
        print_preparation_summary(results["prepared_objectives"])
    
    # Step 4: Provide warning if partial failure
    if results["failed_objectives"]:
        print("\n" + "!"*70)
        print("WARNING: PARTIAL PLANNING SUCCESS")
        print("!"*70)
        print(f"{results['total_prepared']} objectives prepared successfully")
        print(f"{results['total_failed']} objectives failed to prepare")
        print(f"Failed objectives have been logged and notifications sent")
        print("!"*70 + "\n")
    
    print("="*70)
    print("WORKFLOW PLANNER - PLANNING COMPLETE ✓")
    print(f"Ready to execute {results['total_prepared']} objectives")
    print("="*70 + "\n")
    
    return True, results