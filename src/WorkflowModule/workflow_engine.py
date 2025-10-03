#!/usr/bin/env python3
"""
Workflow Module - Main Orchestration

This module receives parsed objectives from the parser and executes them
by coordinating with the action executor module. It manages the workflow
sequence and handles any errors that occur during execution.

The workflow follows this pattern:
1. Receive list of supported objectives from parser
2. For each objective, load the required action steps
3. Pass each action to the action executor
4. Track success/failure and continue or stop accordingly
"""

import time
from typing import Dict, Any, List, Tuple, Optional
from src.NotificationModule import email_notifier



def load_action_steps(objective_type: str, instruction_data: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Load the list of actions required for a specific objective type.
    
    This function determines what actions need to be performed based on
    the objective type and creates a workflow of steps to execute.
    
    Args:
        objective_type: The type of objective (e.g., "make_file_instruction")
        instruction_data: Dictionary containing the instruction parameters
        
    Returns:
        Tuple of (success: bool, action_steps or error_message)
    """
    # Validate inputs
    # Check if objective_type is provided
    if not objective_type:
        return False, "No objective type provided"
    
    # Check if instruction_data is a dictionary
    if not isinstance(instruction_data, dict):
        return False, "Instruction data must be a dictionary"
    
    # Define action steps for each objective type
    action_steps = []
    
    # Check which objective type we're handling
    if objective_type == "make_file_instruction":
        # For making a file, we need these steps:
        # 1. Verify application is ready
        # 2. Open File menu
        # 3. Click New
        # 4. Wait for new file to open
        # 5. Enter filename
        # 6. Enter text content
        # 7. Save file
        
        action_steps = [
            {
                "action_type": "open_file_menu",
                "description": "Open the File menu",
                "parameters": {}
            },
            {
                "action_type": "click_new_file",
                "description": "Click New to create new file",
                "parameters": {}
            },
            {
                "action_type": "wait_for_new_file",
                "description": "Wait for new file window to be ready",
                "parameters": {"timeout": 5}
            },
            {
                "action_type": "enter_filename",
                "description": "Enter the filename",
                "parameters": {"filename": instruction_data.get("file_name", "Untitled")}
            },
            {
                "action_type": "enter_text",
                "description": "Enter the text content",
                "parameters": {"text": instruction_data.get("text", "")}
            },
            {
                "action_type": "save_file",
                "description": "Save the file",
                "parameters": {}
            }
        ]
    else:
        # If objective type is not recognized
        error_msg = f"Unknown objective type: {objective_type}"
        email_notifier.notify_error(error_msg, "workflow.load_action_steps", 
                                    {"objective_type": objective_type})
        return False, error_msg
    
    print(f"Loaded {len(action_steps)} action steps for objective: {objective_type}")
    return True, action_steps


def execute_single_objective(objective_type: str, 
                            instruction_data: Dict[str, Any],
                            action_executor) -> Tuple[bool, str]:
    """
    Execute all actions for a single objective.
    
    This function loads the action steps for an objective and then
    executes each action in sequence. If any action fails, it stops
    and reports the error.
    
    Args:
        objective_type: The type of objective to execute
        instruction_data: Dictionary containing the instruction parameters
        action_executor: The action executor module to use for performing actions
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    print(f"\n{'='*50}")
    print(f"Executing objective: {objective_type}")
    print(f"{'='*50}")
    
    # Load the action steps for this objective
    success, action_data = load_action_steps(objective_type, instruction_data)
    # Check if action steps were loaded successfully
    if not success:
        error_msg = f"Failed to load action steps: {action_data}"
        print(f"[FAILED] {error_msg}")
        email_notifier.notify_error(error_msg, "workflow.execute_single_objective",
                                    {"objective_type": objective_type})
        return False, error_msg
    
    action_steps = action_data
    
    # Execute each action step in sequence
    for step_index, action_step in enumerate(action_steps, start=1):
        print(f"\nStep {step_index}/{len(action_steps)}: {action_step['description']}")
        
        # Execute the action using the action executor
        action_success, action_result = action_executor.execute_action(
            action_type=action_step['action_type'],
            parameters=action_step['parameters']
        )
        
        # Check if action was successful
        if not action_success:
            error_msg = f"Action failed at step {step_index}: {action_result}"
            print(f"[FAILED] {error_msg}")
            email_notifier.notify_error(error_msg, "workflow.execute_single_objective",
                                        {"objective_type": objective_type,
                                         "step_index": step_index,
                                         "action_type": action_step['action_type']})
            return False, error_msg

        print(f"[SUCCESS] {action_result}")

    
    success_msg = f"Successfully completed objective: {objective_type}"
    print(f"\n[SUCCESS] {success_msg}")
    return True, success_msg


def execute_workflow(supported_objectives: List[Dict[str, Any]], 
                     action_executor) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute the complete workflow for all supported objectives.
    
    This is the main workflow orchestration function that receives the
    parsed objectives from the parser module and executes them one by one.
    
    Args:
        supported_objectives: List of supported objectives from parser
        action_executor: The action executor module to use
        
    Returns:
        Tuple of (success: bool, results_summary)
    """
    print("\n" + "="*60)
    print("STARTING WORKFLOW")
    print("="*60)
    
    # Initialize results tracking
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    # Execute each objective
    for objective_index, objective in enumerate(supported_objectives, start=1):
        objective_type = objective.get("objective_type")
        instructions = objective.get("instructions", [])
        
        print(f"\n{'='*60}")
        print(f"Processing objective {objective_index}/{len(supported_objectives)}")
        print(f"Type: {objective_type}")
        print(f"Number of instructions: {len(instructions)}")
        print(f"{'='*60}")
        
        # Execute each instruction for this objective type
        for instruction_index, instruction_data in enumerate(instructions, start=1):
            results["total"] += 1
            
            print(f"\nInstruction {instruction_index}/{len(instructions)}")
            
            # Execute the single objective
            success, result_msg = execute_single_objective(
                objective_type=objective_type,
                instruction_data=instruction_data,
                action_executor=action_executor
            )
            
            # Track the result
            # Check if execution was successful
            if success:
                results["successful"] += 1
                status = "SUCCESS"
            else:
                results["failed"] += 1
                status = "FAILED"
                
            results["details"].append({
                "objective_type": objective_type,
                "instruction_index": instruction_index,
                "status": status,
                "message": result_msg
            })
            
            # Check if we should continue after failure
            if not success:
                email_notifier.notify_error(
                    f"Stopping workflow due to failure in instruction {instruction_index} of objective {objective_type}",
                    "workflow.execute_workflow",
                    {"results": results}
                )
                print("Stopping workflow due to failure.")
                return False, results

    # Print final summary
    print("\n" + "="*60)
    print("WORKFLOW EXECUTION COMPLETE")
    print("="*60)
    print(f"Total objectives: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print("="*60 + "\n")
    
    # Determine overall success
    # Check if any objectives failed
    if results['failed'] > 0:
        overall_success = False
        email_notifier.notify_error(
            f"Workflow completed with {results['failed']} failures",
            "workflow.execute_workflow",
            {"results": results}
        )
    else:
        overall_success = True
    
    return overall_success, results


def start_workflow_from_parser_results(parser_results: Dict[str, Any],
                                       action_executor) -> Tuple[bool, Any]:
    """
    Start the workflow execution from parser results.
    
    This is the main entry point that receives results from the parser
    and begins workflow execution.
    
    Args:
        parser_results: Results dictionary from parser.process_instruction_file()
        action_executor: The action executor module to use
        
    Returns:
        Tuple of (success: bool, workflow_results)
    """
    # Check if parser results are valid
    if not isinstance(parser_results, dict):
        return False, "Invalid parser results format"
    
    # Check if parser results contain supported objectives
    if "supported_objectives" not in parser_results:
        return False, "Parser results missing 'supported_objectives' key"
    
    supported_objectives = parser_results["supported_objectives"]
    
    # Execute the workflow
    success, results = execute_workflow(supported_objectives, action_executor)
    
    return success, results