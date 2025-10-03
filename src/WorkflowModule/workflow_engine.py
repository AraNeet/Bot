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

import json
import os
import time
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from src.NotificationModule import email_notifier


def load_action_definitions(objective_type: str, 
                            actions_dir: str = "src/WorkflowModule/Instructions") -> Tuple[bool, Any]:
    """
    Load action definitions from JSON file for a specific objective type.
    
    This replaces the hardcoded action steps in the original implementation.
    Each objective type has its own JSON file: {objective_type}.json
    
    Args:
        objective_type: The type of objective (e.g., "make_file_instruction")
        actions_dir: Directory containing action definition JSON files
        
    Returns:
        Tuple of (success: bool, action_definitions or error_message)
        
    Example JSON structure:
    {
        "Action_Lists": {
            "make_file_instruction": [
                {
                    "action_type": "open_file_menu",
                    "description": "Open the File menu",
                    "parameters": {}
                },
                ...
            ]
        }
    }
    """
    # Construct the path to the JSON file
    json_file = Path(actions_dir) / f"{objective_type}.json"
    
    print(f"Loading action definitions from: {json_file}")
    
    # Check if file exists
    if not json_file.exists():
        error_msg = f"Action definition file not found: {json_file}"
        email_notifier.notify_error(error_msg, "workflow.load_action_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg
    
    try:
        # Load JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            action_data = json.load(f)
        
        # Extract action list for this objective type
        action_lists = action_data.get("Action_Lists", {})
        actions = action_lists.get(objective_type)
        
        if actions is None:
            error_msg = f"No action list found for objective type: {objective_type}"
            return False, error_msg
        
        if not isinstance(actions, list):
            error_msg = f"Action list must be an array, got: {type(actions)}"
            return False, error_msg
        
        print(f"Successfully loaded {len(actions)} actions for {objective_type}")
        return True, actions
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in action definition file: {e}"
        email_notifier.notify_error(error_msg, "workflow.load_action_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading action definitions: {e}"
        email_notifier.notify_error(error_msg, "workflow.load_action_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg


def merge_action_parameters(action_template: Dict[str, Any], 
                           instruction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge instruction-specific data into action template parameters.
    
    This function takes the template parameters from the JSON file and
    fills in values from the actual instruction data.
    
    Args:
        action_template: Action definition from JSON (with empty/default parameters)
        instruction_data: Actual instruction data from user (contains specific values)
        
    Returns:
        Action dictionary with merged parameters
        
    Example:
        Template: {"action_type": "enter_filename", "parameters": {"filename": ""}}
        Instruction: {"file_name": "test.txt", "text": "Hello"}
        Result: {"action_type": "enter_filename", "parameters": {"filename": "test.txt"}}
    """
    merged_action = action_template.copy()
    template_params = merged_action.get("parameters", {})

    # Define the field that might need to be filled from instruction data
    field_mapping = {
        "filename": "file_name",  # parameter "filename" comes from instruction "file_name"
        "text": "text"            # parameter "text" comes from instruction "text"
    }
    
    # Fill in parameters from instruction data
    for param_key, instruction_key in field_mapping.items():
        if param_key in template_params and instruction_key in instruction_data:
            template_params[param_key] = instruction_data[instruction_key]
    
    merged_action["parameters"] = template_params
    return merged_action


def load_action_steps(objective_type: str, 
                     instruction_data: Dict[str, Any],
                     actions_dir: str = "src/WorkflowModule/Instructions") -> Tuple[bool, Any]:
    """
    Load and prepare action steps for a specific objective.
    
    This is the new version that loads from JSON instead of hardcoding actions.
    It replaces the original hardcoded version in your workflow_engine.py.
    
    Args:
        objective_type: The type of objective (e.g., "make_file_instruction")
        instruction_data: Dictionary containing the instruction parameters
        actions_dir: Directory containing action definition JSON files
        
    Returns:
        Tuple of (success: bool, action_steps or error_message)
    """
    # Validate inputs
    if not objective_type:
        return False, "No objective type provided"
    
    if not isinstance(instruction_data, dict):
        return False, "Instruction data must be a dictionary"
    
    # Load action definitions from JSON
    success, action_data = load_action_definitions(objective_type, actions_dir)
    if not success:
        return False, action_data  # action_data contains error message
    
    action_templates = action_data
    
    # Merge instruction data into action templates
    action_steps = []
    for action_template in action_templates:
        merged_action = merge_action_parameters(action_template, instruction_data)
        action_steps.append(merged_action)
    
    print(f"Prepared {len(action_steps)} action steps for objective: {objective_type}")
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