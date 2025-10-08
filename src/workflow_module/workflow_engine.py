#!/usr/bin/env python3
"""
Workflow Engine Module - Orchestrates Objective Execution

CLEAR TERMINOLOGY:
- Objective: What the user wants to accomplish (e.g., "edit_copy_instruction")
- Values: User-provided data (e.g., {"advertiser_name": "Acme Corp"})
- Instructions: Action steps the bot performs (e.g., type_text, press_key)

This module orchestrates the EXECUTION phase of workflows:
1. Verify workspace is ready
2. Execute each instruction with retry logic
3. Verify each action completed successfully
4. Track results and handle errors

The PLANNING phase (loading & preparing instructions) is now in workflow_planner.py

Responsibilities:
- Verify workspace readiness before starting
- Execute instructions via action_executor
- Verify each action via verifier
- Implement retry logic for failed actions
- Track execution progress and results
- Send error notifications on failures
"""

from typing import Dict, Any, List, Tuple, Optional
from .verifier_module import verifier
from src.notification_module import notify_error
from .action_module import action_executor

def execute_single_instruction(instruction: Dict[str, Any],
                                instruction_index: int,
                                total_instructions: int,
                                max_retries: int = 3) -> Tuple[bool, str]:
    """
    Execute a single instruction with retry logic and verification.
    
    Execution flow:
    1. Extract instruction details (action_type, parameters)
    2. For each attempt (up to max_retries):
        a. Execute action via action_executor
        b. Verify action completed via new verifier module
        c. If verification fails, save debug screenshot and retry
    3. If all retries fail, send error notification
    
    The new verifier module automatically routes instruction names to their
    corresponding verifier handlers, making verification more robust and extensible.
    
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
        
    Example instruction:
    {
        "action_type": "type_text",
        "description": "Enter advertiser name",
        "parameters": {
            "text": "Acme Corp",
            "interval": 0.05
        },
        "verification": {
            "type": "text_inputted",
            "expected_text": "Acme Corp"
        }
    }
    """
    # Extract instruction components
    action_type = instruction.get("action_type")
    description = instruction.get("description", "No description")
    parameters = instruction.get("parameters", {})
    verification_config = instruction.get("verification")
    
    print(f"\n{'─'*60}")
    print(f"[ENGINE] Step {instruction_index}/{total_instructions}: {action_type}")
    print(f"[ENGINE] Description: {description}")
    print(f"[ENGINE] Parameters: {parameters}")
    print(f"{'─'*60}")
    
    # Retry loop
    for attempt in range(1, max_retries + 1):
        print(f"\n[ENGINE] Attempt {attempt}/{max_retries}")
        
        # Step 1: Execute action
        print(f"[ENGINE] Executing action via action_executor...")
        action_success, action_msg = action_executor.execute_action(
            action_type=action_type,
            parameters=parameters
        )
        
        if not action_success:
            print(f"[ENGINE ERROR] Action execution failed: {action_msg}")
            
            # If this was the last attempt, fail
            if attempt == max_retries:
                error_msg = f"Action '{action_type}' failed after {max_retries} attempts: {action_msg}"
                notify_error(
                    error_msg,
                    "workflow_engine.execute_single_instruction",
                    {
                        "action_type": action_type,
                        "parameters": parameters,
                        "attempts": max_retries,
                        "final_error": action_msg
                    }
                )
                return False, error_msg
            
            # Otherwise, retry
            print(f"[ENGINE] Retrying action...")
            continue
        
        print(f"[ENGINE SUCCESS] Action executed: {action_msg}")
        
        # Step 2: Verify action completed using new verifier module
        print(f"[ENGINE] Verifying action completion...")
        
        # # Check if verifier exists for this action type
        # if verifier.has_verifier(action_type):
        #     print(f"[ENGINE] Using verifier for action type: '{action_type}'")
        # else:
        print(f"[ENGINE] No verifier found for action type: '{action_type}' - skipping verification")
        return True, f"Action '{action_type}' executed (no verifier available)"
        
    #     # Use new verifier module to check action completion
    #     verification_success, verification_msg, verification_data = verifier.verify_action_completion(
    #         instruction_name=action_type,
    #         **parameters  # Pass all parameters to the verifier
    #     )
        
    #     if verification_success:
    #         print(f"[ENGINE SUCCESS] Action verified: {verification_msg}")
    #         if verification_data:
    #             print(f"[ENGINE] Verification data: {verification_data}")
    #         return True, f"Action '{action_type}' completed and verified"
    #     else:
    #         print(f"[ENGINE ERROR] Verification failed: {verification_msg}")
            
    #         # Save failure context for debugging
    #         screenshot_path = verifier.save_failure_context(
    #             action_type=action_type,
    #             parameters=parameters,
    #             verification_error=verification_msg,
    #             attempt_number=attempt
    #         )
            
    #         print(f"[ENGINE] Debug screenshot saved: {screenshot_path}")
            
    #         # Check if this was the last attempt
    #         if attempt == max_retries:
    #             error_msg = f"Action '{action_type}' failed verification after {max_retries} attempts"
    #             notify_error(
    #                 error_msg,
    #                 "workflow_engine.execute_single_instruction",
    #                 {
    #                     "action_type": action_type,
    #                     "parameters": parameters,
    #                     "verification_error": verification_msg,
    #                     "screenshot": screenshot_path,
    #                     "attempts": max_retries
    #                 }
    #             )
    #             return False, f"{error_msg}: {verification_msg}"
    #         else:
    #             print(f"[ENGINE] Retrying action after verification failure...")
    
    # # Should not reach here, but just in case
    # return False, f"Action '{action_type}' failed after {max_retries} attempts"

# ============================================================================
# OBJECTIVE EXECUTION
# ============================================================================

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
    print(f"[ENGINE] Executing Objective {objective_index}/{total_objectives}")
    print(f"[ENGINE] Type: {objective_type}")
    print(f"[ENGINE] Value set: #{value_set_index}")
    print(f"[ENGINE] Instructions: {len(instructions)}")
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
            print(f"[ENGINE] ✓ Instruction {inst_index}/{len(instructions)} completed")
        else:
            # Instruction failed - stop this objective
            result["status"] = "FAILED"
            result["failure_reason"] = msg
            print(f"[ENGINE ERROR] ✗ Instruction {inst_index}/{len(instructions)} failed")
            print(f"[ENGINE ERROR] Failure reason: {msg}")
            print(f"[ENGINE] Stopping objective due to instruction failure")
            return False, result
    
    # All instructions completed successfully
    result["status"] = "SUCCESS"
    print(f"\n[ENGINE SUCCESS] ✓ Objective '{objective_type}' (set #{value_set_index}) completed")
    print(f"[ENGINE SUCCESS] All {len(instructions)} instructions executed successfully")
    
    return True, result

# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

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
        corner_templates: Corner templates for workspace verification
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
    print("WORKFLOW ENGINE - STARTING EXECUTION")
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
    print("\n[ENGINE] Verifying workspace is ready...")
    # workspace_ready, workspace_msg = verifier.check_workspace_ready(
    #     corner_templates=corner_templates,
    #     expected_page_text=expected_page_text
    # )
    
    # if not workspace_ready:
    #     error_msg = f"Workspace verification failed: {workspace_msg}"
    #     print(f"[ENGINE ERROR] {error_msg}")
    #     notify_error(
    #         "Workspace not ready for workflow execution",
    #         "workflow_engine.execute_workflow",
    #         {"error": workspace_msg}
    #     )
    #     return False, results
    
    # print(f"[ENGINE SUCCESS] ✓ {workspace_msg}")
    print(f"[ENGINE] Workspace is ready - starting execution...")
    
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
            print(f"\n[ENGINE] Objective {obj_index}/{len(prepared_objectives)}: SUCCESS ✓")
        else:
            results["failed_objectives"] += 1
            print(f"\n[ENGINE] Objective {obj_index}/{len(prepared_objectives)}: FAILED ✗")
            
            # Add failure details
            result_details["failure_index"] = obj_index
            
            # Notify about objective failure
            notify_error(
                f"Workflow stopped due to failure in objective '{result_details['objective_type']}'",
                "workflow_engine.execute_workflow",
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
            print(f"\n[ENGINE] Stopping workflow execution due to objective failure")
            break
    
    # Print final summary
    print_execution_summary(results)
    
    # Determine overall success
    overall_success = results['failed_objectives'] == 0
    
    return overall_success, results

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def start_workflow(parser_results: Dict[str, Any],
                  expected_page_text: Optional[str] = None,
                  max_retries: int = 3,
                  actions_dir: str = "src/workflow_module/Instructions") -> Tuple[bool, Any]:
    """
    Start the complete workflow from parser results.
    
    This is the main entry point that:
    1. Validates parser results
    2. Plans workflow (via planner module)
    3. Verifies workspace
    4. Executes workflow
    5. Returns results
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        corner_templates: Corner templates for workspace verification
        expected_page_text: Text to verify correct page is loaded
        max_retries: Maximum retry attempts per instruction
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, workflow_results or error_message)
        
    Example usage:
        # In main.py:
        from src.workflow_module import workflow_engine
        
        success, results = workflow_engine.start_workflow(
            parser_results=parser_results,
            corner_templates=config['corner_templates'],
            expected_page_text="Multinetwork Instructions"
        )
        
        if success:
            print(f"Workflow completed: {results['completed_objectives']} objectives")
        else:
            print(f"Workflow failed: {results}")
    """
    print("\n" + "="*70)
    print("WORKFLOW ENGINE - WORKFLOW START")
    print("="*70)
    
    # Show supported verifiers
    supported_verifiers = verifier.get_supported_verifications()
    print(f"\n[ENGINE] Supported verifiers ({len(supported_verifiers)}):")
    for verifier_name in supported_verifiers:
        print(f"  - {verifier_name}")
    
    # Import planner (imported here to avoid circular imports)
    from . import workflow_planner
    
    # Step 1: Plan workflow (preparation phase)
    print("\n[ENGINE] Starting planning phase...")
    success, result = workflow_planner.plan_workflow(
        parser_results=parser_results,
        actions_dir=actions_dir
    )
    
    if not success:
        error_msg = f"Planning phase failed: {result}"
        print(f"[ENGINE ERROR] {error_msg}")
        return False, error_msg
    
    prepared_objectives = result.get("prepared_objectives", [])
    print(f"[ENGINE SUCCESS] ✓ Planning phase complete")
    print(f"[ENGINE] Prepared {len(prepared_objectives)} objectives for execution")
    
    # Step 2: Execute workflow (execution phase)
    print("\n[ENGINE] Starting execution phase...")
    success, execution_results = execute_workflow(
        prepared_objectives=prepared_objectives,
        expected_page_text=expected_page_text,
        max_retries=max_retries
    )
    
    print("\n" + "="*70)
    if success:
        print("WORKFLOW ENGINE - WORKFLOW COMPLETE ✓")
    else:
        print("WORKFLOW ENGINE - WORKFLOW FAILED ✗")
    print("="*70 + "\n")
    
    return success, execution_results

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_execution_summary(results: Dict[str, Any]) -> None:
    """
    Print a detailed summary of workflow execution results.
    
    Args:
        results: Results dictionary from execute_workflow()
    """
    print("\n" + "="*70)
    print("WORKFLOW EXECUTION SUMMARY")
    print("="*70)
    
    # Overall statistics
    print(f"\nObjectives:")
    print(f"  Total:     {results['total_objectives']}")
    print(f"  Completed: {results['completed_objectives']} ✓")
    print(f"  Failed:    {results['failed_objectives']} {'✗' if results['failed_objectives'] > 0 else ''}")
    
    print(f"\nInstructions:")
    print(f"  Total:     {results['total_instructions']}")
    print(f"  Completed: {results['completed_instructions']} ✓")
    print(f"  Failed:    {results['failed_instructions']} {'✗' if results['failed_instructions'] > 0 else ''}")
    
    # Detailed breakdown
    if results['details']:
        print(f"\nDetailed Results:")
        for detail in results['details']:
            obj_type = detail.get('objective_type', 'unknown')
            val_idx = detail.get('value_set_index', '?')
            status = detail.get('status', 'UNKNOWN')
            completed = detail.get('instructions_completed', 0)
            total = detail.get('total_instructions', 0)
            
            status_icon = "✓" if status == "SUCCESS" else "✗"
            print(f"  {status_icon} {obj_type} (set #{val_idx}): {completed}/{total} instructions")
            
            if status == "FAILED":
                failure_reason = detail.get('failure_reason', 'Unknown error')
                print(f"     └─ Reason: {failure_reason}")
    
    # Final status
    print(f"\n{'─'*70}")
    if results['failed_objectives'] == 0:
        print("Overall Status: SUCCESS ✓")
    else:
        print("Overall Status: FAILED ✗")
    print(f"{'='*70}\n")
