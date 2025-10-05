"""
WorkflowModule - Action Execution and Workflow Orchestration

This module handles the execution of parsed objectives by coordinating
action sequences and managing the workflow lifecycle.

Main Components:
- workflow: Main orchestration functions for executing objective sequences
- action_executor: Individual action execution with three-step pattern
  (verify prerequisites, perform pre-requirements, execute action)

The workflow system is designed to be:
- Functional (no classes)
- Error-handled with if/else statements
- Well-commented for clarity
- Separated between workflow orchestration and action execution

Usage:
    from src.WorkflowModule import workflow, action_executor
    
    # Start workflow from parser results
    success, results = workflow.start_workflow_from_parser_results(
        parser_results=parser_results,
        action_executor=action_executor
    )
"""

from . import workflow_engine
from . import action_executor
from . import verifier

__all__ = [
    'workflow_engine',
    'action_executor',
    'verifier'
]

__version__ = "1.0.0"