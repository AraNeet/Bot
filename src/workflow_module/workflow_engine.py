#!/usr/bin/env python3
"""
Workflow Engine Module - Orchestrates Objective Execution

CLEAR TERMINOLOGY:
- Objective: What the user wants to accomplish (e.g., "make_file", "edit_copy_instruction")
- Values: User-provided data (e.g., {"file_name": "test.txt", "text": "Hello"})
- Instructions: Action steps the bot performs (e.g., open_menu, type_text, save_file)

This module orchestrates the execution of objectives by:
1. Loading instruction definitions and values using instruction_loader_helper
2. Verifying workspace is ready using verifier
3. Executing each instruction with retry logic
4. Verifying each action completed successfully

The workflow engine focuses on orchestration and uses verifier for all verification.
"""

from typing import Dict, Any, List, Tuple, Optional
from workflow_module.helpers import instruction_loader
from src.workflow_module import verifier
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
    success, loaded_data = instruction_loader.load_objective_data(
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


def execute_single_instruction(instruction: Dict[str, Any],
                               instruction_index: int,
                               total_instructions: int,
                               action_executor = None,
                               max_retries: int = 3) -> Tuple[bool, str]:
    """
    Execute a single instruction with retry logic and verification.
    
    Flow:
    1. Execute action (via action_executor - to be implemented)
    2. Verify action completed (via verifier)
    3. If verification fails, retry up to max_retries times
    4. Return success/failure
    
    Args:
        instruction: Single instruction dictionary with action_type, parameters, verification
        instruction_index: Current instruction number (for display)
        total_instructions: Total number of instructions (for display)
        action_executor: Action executor module (placeholder for now)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (success: bool, message)
    """
    action_type = instruction.get("action_type")
    description = instruction.get("description", "No description")
    parameters = instruction.get("parameters", {})
    verification_config = instruction.get("verification")
    
    print(f"\n{'─'*60}")
    print(f"Step {instruction_index}/{total_instructions}: {action_type}")
    print(f"Description: {description}")
    print(f"Parameters: {parameters}")
    print(f"{'─'*60}")
    
    # Retry loop
    for attempt in range(1, max_retries + 1):
        print(f"\n[WORKFLOW] Attempt {attempt}/{max_retries}")
        
        # Step 1: Execute action
        # TODO: Implement action_executor integration
        # For now, we'll simulate action execution
        print(f"[WORKFLOW] Executing action: {action_type}")
        if action_executor is None:
            print(f"[WORKFLOW] Action executor not implemented yet - simulating execution")
            action_success = True  # Simulate success
        else:
            # Will implement this later
            action_success = True
        
        if not action_success:
            print(f"[WORKFLOW] Action execution failed")
            continue  # Retry
        
        # Step 2: Verify action completed
        if verification_config:
            print(f"[WORKFLOW] Verifying action completion...")
            
            verification_success, verification_msg = verifier.verify_action_completed(
                action_type=action_type,
                parameters=parameters,
                verification_config=verification_config
            )
            
            if verification_success:
                print(f"[WORKFLOW SUCCESS] Action verified successfully")
                return True, f"Action '{action_type}' completed and verified"
            else:
                print(f"[WORKFLOW] Verification failed: {verification_msg}")
                
                # Save failure context
                screenshot_path = verifier.save_failure_context(
                    action_type=action_type,
                    parameters=parameters,
                    verification_error=verification_msg,
                    attempt_number=attempt
                )
                
                print(f"[WORKFLOW] Failure screenshot saved: {screenshot_path}")
                
                # Check if this was the last attempt
                if attempt == max_retries:
                    error_msg = f"Action '{action_type}' failed verification after {max_retries} attempts: {verification_msg}"
                    print(f"[WORKFLOW ERROR] {error_msg}")
                    
                    # Send error notification
                    notify_error(
                        f"Action failed after {max_retries} attempts",
                        "workflow.execute_single_instruction",
                        {
                            "action_type": action_type,
                            "parameters": parameters,
                            "verification_error": verification_msg,
                            "screenshot": screenshot_path,
                            "attempts": max_retries
                        }
                    )
                    
                    return False, error_msg
                else:
                    print(f"[WORKFLOW] Retrying action...")
        else:
            # No verification configured - assume success
            print(f"[WORKFLOW] No verification configured - assuming success")
            return True, f"Action '{action_type}' executed (no verification)"
    
    # Should not reach here, but just in case
    return False, f"Action '{action_type}' failed after {max_retries} attempts"


def execute_workflow(prepared_objectives: List[Dict[str, Any]],
                    corner_templates: Dict[str, Any],
                    expected_page_text: Optional[str] = None,
                    action_executor = None,
                    max_retries: int = 3) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute the complete workflow for all prepared objectives.
    
    Flow:
    1. Verify workspace is ready
    2. For each prepared objective:
       - For each instruction:
         - Execute with retry logic
         - Verify completion
    3. Track results and return summary
    
    Args:
        prepared_objectives: List of prepared objectives from prepare_workflow()
        corner_templates: Corner templates for workspace verification
        expected_page_text: Text to verify correct page is loaded
        action_executor: Action executor module (placeholder)
        max_retries: Maximum retry attempts per action
        
    Returns:
        Tuple of (success: bool, results_summary)
    """
    print("\n" + "="*60)
    print("WORKFLOW ENGINE - STARTING EXECUTION")
    print("="*60)
    
    # Initialize results tracking
    results = {
        "total_objectives": len(prepared_objectives),
        "completed_objectives": 0,
        "failed_objectives": 0,
        "total_instructions": 0,
        "completed_instructions": 0,
        "failed_instructions": 0,
        "details": []
    }
    
    # Step 1: Verify workspace is ready
    print("\n[WORKFLOW] Verifying workspace is ready...")
    workspace_ready, workspace_msg = verifier.check_workspace_ready(
        corner_templates=corner_templates,
        expected_page_text=expected_page_text
    )
    
    if not workspace_ready:
        error_msg = f"Workspace verification failed: {workspace_msg}"
        print(f"[WORKFLOW ERROR] {error_msg}")
        notify_error(
            "Workspace not ready for workflow execution",
            "workflow.execute_workflow",
            {"error": workspace_msg}
        )
        return False, results
    
    print(f"[WORKFLOW SUCCESS] {workspace_msg}")
    
    # Step 2: Execute each prepared objective
    for obj_index, prepared_obj in enumerate(prepared_objectives, start=1):
        objective_type = prepared_obj.get("objective_type")
        value_set_index = prepared_obj.get("value_set_index", obj_index)
        instructions = prepared_obj.get("instructions", [])
        
        results["total_instructions"] += len(instructions)
        
        print(f"\n{'='*60}")
        print(f"Executing Objective {obj_index}/{len(prepared_objectives)}")
        print(f"Type: {objective_type}")
        print(f"Value set: {value_set_index}")
        print(f"Instructions: {len(instructions)}")
        print(f"{'='*60}")
        
        objective_success = True
        
        # Execute each instruction
        for inst_index, instruction in enumerate(instructions, start=1):
            success, msg = execute_single_instruction(
                instruction=instruction,
                instruction_index=inst_index,
                total_instructions=len(instructions),
                action_executor=action_executor,
                max_retries=max_retries
            )
            
            if success:
                results["completed_instructions"] += 1
                print(f"[WORKFLOW] Instruction {inst_index}/{len(instructions)} completed")
            else:
                results["failed_instructions"] += 1
                objective_success = False
                print(f"[WORKFLOW ERROR] Instruction {inst_index}/{len(instructions)} failed: {msg}")
                
                # Stop this objective on first failure
                break
        
        # Track objective result
        if objective_success:
            results["completed_objectives"] += 1
            status = "SUCCESS"
            print(f"\n[WORKFLOW SUCCESS] Objective '{objective_type}' completed successfully")
        else:
            results["failed_objectives"] += 1
            status = "FAILED"
            print(f"\n[WORKFLOW ERROR] Objective '{objective_type}' failed")
        
        results["details"].append({
            "objective_type": objective_type,
            "value_set_index": value_set_index,
            "status": status,
            "instructions_completed": inst_index - (0 if objective_success else 1),
            "total_instructions": len(instructions)
        })
        
        # Stop workflow on objective failure (fail-fast)
        if not objective_success:
            error_context = {
                "objective_type": objective_type,
                "value_set_index": value_set_index,
                "completed_objectives": results["completed_objectives"],
                "failed_objectives": results["failed_objectives"]
            }
            notify_error(
                f"Workflow stopped due to failure in '{objective_type}'",
                "workflow.execute_workflow",
                error_context
            )
            print(f"\n[WORKFLOW STOPPED] Stopping execution due to objective failure")
            break
    
    # Print final summary
    print("\n" + "="*60)
    print("WORKFLOW ENGINE - EXECUTION COMPLETE")
    print("="*60)
    print(f"Objectives: {results['completed_objectives']}/{results['total_objectives']} completed")
    print(f"Instructions: {results['completed_instructions']}/{results['total_instructions']} completed")
    print(f"Failed objectives: {results['failed_objectives']}")
    print(f"Failed instructions: {results['failed_instructions']}")
    print("="*60 + "\n")
    
    # Determine overall success
    overall_success = results['failed_objectives'] == 0
    
    return overall_success, results


def start_workflow(parser_results: Dict[str, Any],
                                       corner_templates: Dict[str, Any],
                                       expected_page_text: Optional[str] = None,
                                       action_executor = None,
                                       max_retries: int = 3,
                                       actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Start the workflow execution from parser results.
    
    This is the main entry point that:
    1. Receives parser results
    2. Prepares all objectives
    3. Verifies workspace
    4. Executes workflow with retry logic
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        corner_templates: Corner templates for workspace verification
        expected_page_text: Text to verify correct page is loaded
        action_executor: Action executor module (placeholder)
        max_retries: Maximum retry attempts per action
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, workflow_results)
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
    
    # Step 1: Prepare all objectives
    print("\n" + "="*60)
    print("WORKFLOW ENGINE - PREPARING OBJECTIVES")
    print("="*60)
    
    prepared_objectives = []
    
    for obj_index, objective in enumerate(supported_objectives, start=1):
        objective_type = objective.get("objective_type")
        values_list = objective.get("values_list", [])
        
        print(f"\n[WORKFLOW] Preparing '{objective_type}' ({len(values_list)} value sets)")
        
        for val_index, objective_values in enumerate(values_list, start=1):
            success, prepared_data = prepare_single_objective(
                objective_type=objective_type,
                objective_values=objective_values,
                actions_dir=actions_dir
            )
            
            if not success:
                error_msg = f"Failed to prepare '{objective_type}' (value set {val_index}): {prepared_data}"
                print(f"[WORKFLOW ERROR] {error_msg}")
                notify_error(error_msg, "workflow.start_workflow_from_parser_results",
                           {"objective_type": objective_type, "value_set_index": val_index})
                return False, error_msg
            
            # Add value_set_index for tracking
            prepared_data["value_set_index"] = val_index
            prepared_objectives.append(prepared_data)
    
    print(f"\n[WORKFLOW SUCCESS] All objectives prepared: {len(prepared_objectives)} total")
    
    # Step 2: Execute the workflow
    success, results = execute_workflow(
        prepared_objectives=prepared_objectives,
        corner_templates=corner_templates,
        expected_page_text=expected_page_text,
        action_executor=action_executor,
        max_retries=max_retries
    )
    
    return success, results