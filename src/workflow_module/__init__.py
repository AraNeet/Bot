"""
WorkflowModule - Action Execution and Workflow Orchestration

This module handles the execution of parsed objectives by coordinating
action sequences and managing the workflow lifecycle.

Main Components:
- workflow: Main manager functions for executing objective sequences

"""

from .workflow_engine import start_workflow as workflow

__all__ = [
    'workflow',
]

__version__ = "1.0.0"