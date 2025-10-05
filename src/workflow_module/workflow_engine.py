#!/usr/bin/env python3
"""
Workflow Engine Module - JSON-Based Instruction Loading

CLEAR TERMINOLOGY:
- Objective: What the user wants to accomplish (e.g., "make_file")
- Values: User-provided data (e.g., {"file_name": "test.txt", "text": "Hello"})
- Instructions: Action steps the bot performs (e.g., open_menu, type_text, save_file)

This module loads instruction sequences from JSON files and executes them.
Each objective type has its own JSON file defining the required instructions.
"""

import json
import os
import time
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from src.notification_module import email_sender


def load_instruction_definitions(objective_type: str, 
                                 actions_dir: str = "src/WorkflowModule/ActionInstructions") -> Tuple[bool, Any]:
    """
    Load instruction definitions from JSON file for a specific objective type.
    
    Instructions are the action steps the bot performs to complete an objective.
    
    Args:
        objective_type: The type of objective (e.g., "make_file")
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, instructions or error_message)
        
    Example JSON structure in make_file_actions.json:
    {
        "Instructions": {
            "make_file": [
                {
                    "action_type": "open_file_menu",
                    "description": "Open the File menu",
                    "parameters": {}
                },
                {
                    "action_type": "enter_filename",
                    "description": "Enter the filename",
                    "parameters": {"filename": ""}
                }
            ]
        }
    }
    """
    # Construct the path to the JSON file
    json_file = Path(actions_dir) / f"{objective_type}_actions.json"
    
    print(f"Loading instruction definitions from: {json_file}")
    
    # Check if file exists
    if not json_file.exists():
        error_msg = f"Instruction definition file not found: {json_file}"
        email_sender.notify_error(error_msg, "workflow.load_instruction_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg
    
    try:
        # Load JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            instruction_data = json.load(f)
        
        # Extract instruction list for this objective type
        instructions_dict = instruction_data.get("Instructions", {})
        instructions = instructions_dict.get(objective_type)
        
        if instructions is None:
            error_msg = f"No instructions found for objective type: {objective_type}"
            return False, error_msg
        
        if not isinstance(instructions, list):
            error_msg = f"Instructions must be an array, got: {type(instructions)}"
            return False, error_msg
        
        print(f"Successfully loaded {len(instructions)} instructions for {objective_type}")
        return True, instructions
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in instruction definition file: {e}"
        email_sender.notify_error(error_msg, "workflow.load_instruction_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg
    except Exception as e:
        error_msg = f"Error loading instruction definitions: {e}"
        email_sender.notify_error(error_msg, "workflow.load_instruction_definitions",
                                    {"objective_type": objective_type})
        return False, error_msg


def merge_values_into_instructions(instruction_template: Dict[str, Any], 
                                   objective_values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge objective values into instruction template parameters.
    
    Takes the template instructions from JSON and fills in values from the user.
    
    Args:
        instruction_template: Instruction from JSON (with empty/default parameters)
        objective_values: User-provided values for the objective
        
    Returns:
        Instruction dictionary with merged parameters
        
    Example:
        Template: {"action_type": "enter_filename", "parameters": {"filename": ""}}
        Values: {"file_name": "test.txt", "text": "Hello"}
        Result: {"action_type": "enter_filename", "parameters": {"filename": "test.txt"}}
    """
    merged_instruction = instruction_template.copy()
    template_params = merged_instruction.get("parameters", {})
    
    # Map objective value fields to instruction parameter fields
    # This handles cases where value keys differ from parameter keys
    field_mapping = {
        "filename": "file_name",  # parameter "filename" ← value "file_name"
        "text": "text",           # parameter "text" ← value "text"
    }
    
    # Fill in parameters from objective values
    for param_key, value_key in field_mapping.items():
        if param_key in template_params and value_key in objective_values:
            template_params[param_key] = objective_values[value_key]
    
    merged_instruction["parameters"] = template_params
    return merged_instruction


def prepare_instructions(objective_type: str, 
                        objective_values: Dict[str, Any],
                        actions_dir: str = "src/WorkflowModule/ActionInstructions") -> Tuple[bool, Any]:
    """
    Load and prepare instructions for a specific objective.
    
    This function:
    1. Loads instruction templates from JSON
    2. Merges user values into the templates
    3. Returns ready-to-execute instructions
    
    Args:
        objective_type: The type of objective (e.g., "make_file")
        objective_values: User-provided values for the objective
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, instructions or error_message)
    """
    # Validate inputs
    if not objective_type:
        return False, "No objective type provided"
    
    if not isinstance(objective_values, dict):
        return False, "Objective values must be a dictionary"
    
    # Load instruction definitions from JSON
    success, instruction_data = load_instruction_definitions(objective_type, actions_dir)
    if not success:
        return False, instruction_data  # instruction_data contains error message
    
    instruction_templates = instruction_data
    
    # Merge objective values into instruction templates
    prepared_instructions = []
    for instruction_template in instruction_templates:
        merged_instruction = merge_values_into_instructions(instruction_template, objective_values)
        prepared_instructions.append(merged_instruction)
    
    print(f"Prepared {len(prepared_instructions)} instructions for objective: {objective_type}")
    return True, prepared_instructions


def execute_single_objective(objective_type: str, 
                             objective_values: Dict[str, Any],
                             action_executor,
                             actions_dir: str = "src/WorkflowModule/ActionInstructions") -> Tuple[bool, str]:
    """
    Execute all instructions for a single objective.
    
    Args:
        objective_type: The type of objective to execute (e.g., "make_file")
        objective_values: User-provided values (e.g., {"file_name": "test.txt"})
        action_executor: The action executor module
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    print(f"\n{'='*50}")
    print(f"Executing objective: {objective_type}")
    print(f"Values: {objective_values}")
    print(f"{'='*50}")
    
    # Load and prepare instructions
    success, instruction_data = prepare_instructions(objective_type, objective_values, actions_dir)
    if not success:
        error_msg = f"Failed to prepare instructions: {instruction_data}"
        print(f"[FAILED] {error_msg}")
        email_sender.notify_error(error_msg, "workflow.execute_single_objective",
                                    {"objective_type": objective_type})
        return False, error_msg
    
    action_instructions = instruction_data
    
    # Execute each instruction in sequence
    for step_index, instruction in enumerate(action_instructions, start=1):
        print(f"\nInstruction {step_index}/{len(action_instructions)}: {instruction['description']}")
        
        # Execute the instruction using the action executor
        action_success, action_result = action_executor.execute_action(
            action_type=instruction['action_type'],
            parameters=instruction['parameters']
        )
        
        if not action_success:
            error_msg = f"Instruction failed at step {step_index}: {action_result}"
            print(f"[FAILED] {error_msg}")
            email_sender.notify_error(error_msg, "workflow.execute_single_objective",
                                        {"objective_type": objective_type,
                                         "step_index": step_index,
                                         "action_type": instruction['action_type']})
            return False, error_msg
        
        print(f"[SUCCESS] {action_result}")
    
    success_msg = f"Successfully completed objective: {objective_type}"
    print(f"\n[SUCCESS] {success_msg}")
    return True, success_msg


def execute_workflow(supported_objectives: List[Dict[str, Any]], 
                     action_executor,
                     actions_dir: str = "src/WorkflowModule/ActionInstructions") -> Tuple[bool, Dict[str, Any]]:
    """
    Execute the complete workflow for all supported objectives.
    
    Args:
        supported_objectives: List of supported objectives from parser
        action_executor: The action executor module
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, results_summary)
        
    Example supported_objectives:
    [
        {
            "objective_type": "make_file",
            "values_list": [
                {"file_name": "Report.txt", "text": "Q4 Sales"},
                {"file_name": "Notes.txt", "text": "Meeting notes"}
            ]
        }
    ]
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
        values_list = objective.get("values_list", [])
        
        print(f"\n{'='*60}")
        print(f"Processing objective {objective_index}/{len(supported_objectives)}")
        print(f"Type: {objective_type}")
        print(f"Number of value sets: {len(values_list)}")
        print(f"{'='*60}")
        
        # Execute the objective for each set of values
        for values_index, objective_values in enumerate(values_list, start=1):
            results["total"] += 1
            
            print(f"\nValue set {values_index}/{len(values_list)}")
            
            # Execute the objective with these values
            success, result_msg = execute_single_objective(
                objective_type=objective_type,
                objective_values=objective_values,
                action_executor=action_executor,
                actions_dir=actions_dir
            )
            
            # Track the result
            if success:
                results["successful"] += 1
                status = "SUCCESS"
            else:
                results["failed"] += 1
                status = "FAILED"
            
            results["details"].append({
                "objective_type": objective_type,
                "values_index": values_index,
                "status": status,
                "message": result_msg
            })
            
            # Stop workflow on failure
            if not success:
                email_sender.notify_error(
                    f"Stopping workflow due to failure in value set {values_index} of objective {objective_type}",
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
    if results['failed'] > 0:
        overall_success = False
        email_sender.notify_error(
            f"Workflow completed with {results['failed']} failures",
            "workflow.execute_workflow",
            {"results": results}
        )
    else:
        overall_success = True
    
    return overall_success, results


def start_workflow_from_parser_results(parser_results: Dict[str, Any],
                                       action_executor,
                                       actions_dir: str = "src/WorkflowModule/ActionInstructions") -> Tuple[bool, Any]:
    """
    Start the workflow execution from parser results.
    
    This is the main entry point that receives results from the parser
    and begins workflow execution.
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        action_executor: The action executor module
        actions_dir: Directory containing instruction definition JSON files
        
    Returns:
        Tuple of (success: bool, workflow_results)
    """
    # Validate parser results
    if not isinstance(parser_results, dict):
        return False, "Invalid parser results format"
    
    if "supported_objectives" not in parser_results:
        return False, "Parser results missing 'supported_objectives' key"
    
    supported_objectives = parser_results["supported_objectives"]
    
    # Execute the workflow
    success, results = execute_workflow(
        supported_objectives, 
        action_executor,
        actions_dir
    )
    
    return success, results