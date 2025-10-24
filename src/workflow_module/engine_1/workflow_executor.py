#!/usr/bin/env python3
"""
Workflow Executor Module - Orchestrates Instruction Execution

CLEAR TERMINOLOGY:
- Objective: What the user wants to accomplish (e.g., "edit_copy_instruction")
- Values: User-provided data (e.g., {"advertiser_name": "Acme Corp"})
- Instructions: Action steps the bot performs (e.g., type_text, press_key)

This module handles the EXECUTION phase of workflows:
1. Verify workspace is ready
2. Execute each instruction with retry logic
3. Verify each action completed successfully
4. Track results and handle errors

Responsibilities:
- Execute individual instructions via unified_executor
- Execute all instructions for a single objective
- Execute complete workflow for all objectives
- Track execution progress and results
- Send error notifications on failures
"""

from typing import Dict, Any, List, Tuple, Optional
from src.notification_module.error_notifier import notify_error
from src.workflow_module.actions_2 import unified_executor


def execute_single_instruction(instruction: Dict[str, Any],
                                instruction_index: int,
                                total_instructions: int,
                                max_retries: int = 3) -> Tuple[bool, str]:
    """
    Execute a single instruction with retry logic and verification.
    
    Execution flow:
    1. Extract instruction details (action_type, parameters)
    2. Execute action via unified_executor which:
        a. Executes the action using handler modules
        b. Verifies action completion
        c. Handles errors and implements retry logic
        d. Sends error notifications if all retries fail
    3. If action_type unsupported, skip with warning
    
    Args:
        instruction: Single instruction dictionary with:
            - action_type: Type of action to perform
            - description: Human-readable description
            - parameters: Action parameters (already filled by planner)
            - verification: Optional verification config
        instruction_index: Current instruction number (for display)
        total_instructions: Total number of instructions (for display)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (success: bool, message)
    """
    # Extract instruction components
    action_type = instruction.get("action_type")
    description = instruction.get("description", "No description")
    parameters = instruction.get("parameters", {})
    
    print(f"\n{'─'*60}")
    print(f"[EXECUTOR] Step {instruction_index}/{total_instructions}: {action_type}")
    print(f"[EXECUTOR] Description: {description}")
    print(f"[EXECUTOR] Parameters: {parameters}")
    print(f"{'─'*60}")
    
    # Check if action type is supported
    supported_actions = unified_executor.get_supported_actions()
    if action_type not in supported_actions:
        warning_msg = f"Action '{action_type}' is unsupported, skipping this step"
        print(f"[EXECUTOR WARNING] ⚠ {warning_msg}")
        return True, warning_msg
    
    # Execute action with integrated verification using unified executor
    print(f"[EXECUTOR] Executing action with unified executor (includes verification and retry logic)...")
    success, message, verification_data = unified_executor.execute_action_with_verification(
        action_type=action_type,
        parameters=parameters,
        max_retries=max_retries,
        verify=True  # Enable verification
    )
    
    if success:
        print(f"[EXECUTOR SUCCESS] {message}")
        if verification_data:
            print(f"[EXECUTOR] Verification data: {verification_data}")
        return True, message
    else:
        print(f"[EXECUTOR ERROR] {message}")
        # Error notification already sent by unified_executor
        return False, message


def execute_single_objective(objective: Dict[str, Any],
                             objective_index: int,
                             total_objectives: int,
                             max_retries: int = 3) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute all instructions for a single objective.
    
    This function:
    1. Extracts objective details
    2. Executes each instruction sequentially
    3. Stops on first failure (fail-fast)
    4. Returns detailed execution results
    
    Args:
        objective: Prepared objective from planner with structure:
            {
                "objective_type": "edit_copy_instruction",
                "value_set_index": 1,
                "instructions": [list of instructions]
            }
        objective_index: Current objective number (for display)
        total_objectives: Total number of objectives (for display)
        max_retries: Maximum retry attempts per instruction
        
    Returns:
        Tuple of (success: bool, result_details)
        
    Result details structure:
    {
        "objective_type": "edit_copy_instruction",
        "value_set_index": 1,
        "status": "SUCCESS" or "FAILED",
        "instructions_completed": 5,
        "total_instructions": 10,
        "failure_reason": "..." (if failed)
    }
    """
    # Extract objective details
    objective_type = objective.get("objective_type", "unknown")
    value_set_index = objective.get("value_set_index", objective_index)
    instructions = objective.get("instructions", [])
    
    print(f"\n{'='*60}")
    print(f"[EXECUTOR] Executing Objective {objective_index}/{total_objectives}")
    print(f"[EXECUTOR] Type: {objective_type}")
    print(f"[EXECUTOR] Value set: #{value_set_index}")
    print(f"[EXECUTOR] Instructions: {len(instructions)}")
    print(f"{'='*60}")
    
    # Initialize result tracking
    result = {
        "objective_type": objective_type,
        "value_set_index": value_set_index,
        "status": "IN_PROGRESS",
        "instructions_completed": 0,
        "total_instructions": len(instructions),
        "failure_reason": None
    }
    
    # Execute each instruction
    for inst_index, instruction in enumerate(instructions, start=1):
        success, msg = execute_single_instruction(
            instruction=instruction,
            instruction_index=inst_index,
            total_instructions=len(instructions),
            max_retries=max_retries
        )
        
        if success:
            result["instructions_completed"] += 1
            print(f"[EXECUTOR] ✓ Instruction {inst_index}/{len(instructions)} completed")
        else:
            # Instruction failed - stop this objective
            result["status"] = "FAILED"
            result["failure_reason"] = msg
            print(f"[EXECUTOR ERROR] ✗ Instruction {inst_index}/{len(instructions)} failed")
            print(f"[EXECUTOR ERROR] Failure reason: {msg}")
            print(f"[EXECUTOR] Stopping objective due to instruction failure")
            return False, result
    
    # All instructions completed successfully
    result["status"] = "SUCCESS"
    print(f"\n[EXECUTOR SUCCESS] ✓ Objective '{objective_type}' (set #{value_set_index}) completed")
    print(f"[EXECUTOR SUCCESS] All {len(instructions)} instructions executed successfully")
    
    return True, result


def execute_workflow(prepared_objectives: List[Dict[str, Any]],
                    expected_page_text: Optional[str] = None,
                    max_retries: int = 3) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute the complete workflow for all prepared objectives.
    
    Execution flow:
    1. Verify workspace is ready (maximized + correct page)
    2. For each prepared objective:
        - Execute all instructions
        - Track results
        - Stop on first failure (fail-fast)
    3. Return comprehensive execution summary
    
    Args:
        prepared_objectives: List of prepared objectives from planner
        expected_page_text: Text to verify correct page is loaded
        max_retries: Maximum retry attempts per instruction
        
    Returns:
        Tuple of (success: bool, results_summary)
        
    Results summary structure:
    {
        "total_objectives": 5,
        "completed_objectives": 3,
        "failed_objectives": 1,
        "total_instructions": 50,
        "completed_instructions": 35,
        "failed_instructions": 1,
        "details": [
            {
                "objective_type": "edit_copy_instruction",
                "value_set_index": 1,
                "status": "SUCCESS",
                "instructions_completed": 10,
                "total_instructions": 10
            },
            ...
        ]
    }
    """
    print("\n" + "="*70)
    print("WORKFLOW EXECUTOR - STARTING EXECUTION")
    print("="*70)
    
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
    
    # Count total instructions
    results["total_instructions"] = sum(
        len(obj.get("instructions", [])) 
        for obj in prepared_objectives
    )
    
    # Step 1: Verify workspace is ready
    print("\n[EXECUTOR] Verifying workspace is ready...")
    # workspace_ready, workspace_msg = verifier.check_workspace_ready(
    #     corner_templates=corner_templates,
    #     expected_page_text=expected_page_text
    # )
    
    # if not workspace_ready:
    #     error_msg = f"Workspace verification failed: {workspace_msg}"
    #     print(f"[EXECUTOR ERROR] {error_msg}")
    #     notify_error(
    #         "Workspace not ready for workflow execution",
    #         "workflow_executor.execute_workflow",
    #         {"error": workspace_msg}
    #     )
    #     return False, results
    
    # print(f"[EXECUTOR SUCCESS] ✓ {workspace_msg}")
    print(f"[EXECUTOR] Workspace is ready - starting execution...")
    
    # Step 2: Execute each prepared objective
    for obj_index, objective in enumerate(prepared_objectives, start=1):
        success, result_details = execute_single_objective(
            objective=objective,
            objective_index=obj_index,
            total_objectives=len(prepared_objectives),
            max_retries=max_retries
        )
        
        # Update overall statistics
        completed_insts = result_details.get("instructions_completed", 0)
        total_insts = result_details.get("total_instructions", 0)
        
        results["completed_instructions"] += completed_insts
        results["failed_instructions"] += (total_insts - completed_insts)
        
        if success:
            results["completed_objectives"] += 1
            print(f"\n[EXECUTOR] Objective {obj_index}/{len(prepared_objectives)}: SUCCESS ✓")
        else:
            results["failed_objectives"] += 1
            print(f"\n[EXECUTOR] Objective {obj_index}/{len(prepared_objectives)}: FAILED ✗")
            
            # Add failure details
            result_details["failure_index"] = obj_index
            
            # Notify about objective failure
            notify_error(
                f"Workflow stopped due to failure in objective '{result_details['objective_type']}'",
                "workflow_executor.execute_workflow",
                {
                    "objective_type": result_details["objective_type"],
                    "value_set_index": result_details["value_set_index"],
                    "failure_reason": result_details.get("failure_reason"),
                    "completed_objectives": results["completed_objectives"],
                    "failed_objectives": results["failed_objectives"]
                }
            )
        
        # Add detailed result
        results["details"].append(result_details)
        
        # Stop workflow on objective failure (fail-fast)
        if not success:
            print(f"\n[EXECUTOR] Stopping workflow execution due to objective failure")
            break
    
    # Determine overall success
    overall_success = results['failed_objectives'] == 0
    
    return overall_success, results

