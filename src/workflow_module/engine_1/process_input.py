#!/usr/bin/env python3
"""
Process Input Module - Main Entry Point for Workflow Execution

This module provides the main entry point for starting workflows:
1. Validates parser results
2. Plans workflow (via planner module)
3. Executes workflow (via executor module)
4. Prints execution summary
5. Returns results

Functions:
- process_input_workflow(): Main entry point to start complete workflow with summary printing
"""

from typing import Dict, Any, Optional, Tuple
from src.workflow_module.engine_1 import workflow_planner
from src.workflow_module.engine_1 import workflow_executor


def process_input_workflow(parser_results: Dict[str, Any],
                           expected_page_text: Optional[str] = None,
                           max_retries: int = 3,
                           actions_dir: str = "src/workflow_module/objective_definitions") -> Tuple[bool, Any]:
    """
    Process input and execute the complete workflow from parser results.
    
    This is the main entry point that:
    1. Validates parser results
    2. Plans workflow (via planner module)
    3. Verifies workspace
    4. Executes workflow
    5. Prints detailed execution summary
    6. Returns results
    
    Args:
        parser_results: Results from parser.process_objectives_file()
        expected_page_text: Text to verify correct page is loaded
        max_retries: Maximum retry attempts per instruction
        actions_dir: Directory containing instruction JSON files
        
    Returns:
        Tuple of (success: bool, workflow_results or error_message)
        
    Example usage:
        # In main.py:
        from src.workflow_module.engine.process_input import process_input_workflow
        
        success, results = process_input_workflow(
            parser_results=parser_results,
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
    success, execution_results = workflow_executor.execute_workflow(
        prepared_objectives=prepared_objectives,
        expected_page_text=expected_page_text,
        max_retries=max_retries
    )
    
    # Step 3: Print detailed execution summary
    print("\n" + "="*70)
    print("WORKFLOW EXECUTION SUMMARY")
    print("="*70)
    
    # Overall statistics
    print(f"\nObjectives:")
    print(f"  Total:     {execution_results['total_objectives']}")
    print(f"  Completed: {execution_results['completed_objectives']} ✓")
    print(f"  Failed:    {execution_results['failed_objectives']} {'✗' if execution_results['failed_objectives'] > 0 else ''}")
    
    print(f"\nInstructions:")
    print(f"  Total:     {execution_results['total_instructions']}")
    print(f"  Completed: {execution_results['completed_instructions']} ✓")
    print(f"  Failed:    {execution_results['failed_instructions']} {'✗' if execution_results['failed_instructions'] > 0 else ''}")
    
    # Detailed breakdown
    if execution_results['details']:
        print(f"\nDetailed Results:")
        for detail in execution_results['details']:
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
    if execution_results['failed_objectives'] == 0:
        print("Overall Status: SUCCESS ✓")
    else:
        print("Overall Status: FAILED ✗")
    print(f"{'='*70}\n")
    
    # Final workflow completion message
    print("\n" + "="*70)
    if success:
        print("WORKFLOW ENGINE - WORKFLOW COMPLETE ✓")
    else:
        print("WORKFLOW ENGINE - WORKFLOW FAILED ✗")
    print("="*70 + "\n")
    
    return success, execution_results

