"""
Workflow Manager - Handles JSON-based workflow processing and objective management.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

# Import type for type hints without circular dependency
if TYPE_CHECKING:
    from orchestrator.application_orchestrator import ApplicationOrchestrator


class ObjectiveStatus(Enum):
    """Status of workflow objectives."""
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class WorkflowObjective:
    """Represents a single workflow objective."""
    id: str
    name: str
    description: str
    type: str
    parameters: Dict[str, Any]
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    error_message: Optional[str] = None


class WorkflowManager:
    """
    Manages JSON-based workflows and interacts with the orchestrator to execute objectives.
    """
    
    def __init__(self, orchestrator: 'ApplicationOrchestrator'):
        """
        Initialize the workflow manager.
        
        Args:
            orchestrator: Instance of ApplicationOrchestrator to manage application state
        """
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self.objectives: List[WorkflowObjective] = []
        self.supported_objective_types = {
            'open_application': self._execute_open_application,
            'maximize_window': self._execute_maximize_window,
            'bring_to_foreground': self._execute_bring_to_foreground,
            'visual_verification': self._execute_visual_verification,
            'wait': self._execute_wait,
            'startup_sequence': self._execute_startup_sequence
        }
        
        self.logger.info("Workflow Manager initialized")
    
    def load_workflow_from_json(self, json_path: str) -> bool:
        """
        Load workflow objectives from a JSON file.
        
        Args:
            json_path: Path to the JSON file containing workflow objectives
            
        Returns:
            True if successfully loaded, False otherwise
        """
        try:
            json_file = Path(json_path)
            if not json_file.exists():
                self.logger.error(f"Workflow JSON file not found: {json_path}")
                return False
            
            with open(json_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            self.logger.info(f"Loading workflow from: {json_path}")
            return self._parse_workflow_data(workflow_data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in {json_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading workflow file {json_path}: {e}")
            return False
    
    def load_workflow_from_dict(self, workflow_data: Dict[str, Any]) -> bool:
        """
        Load workflow objectives from a dictionary.
        
        Args:
            workflow_data: Dictionary containing workflow data
            
        Returns:
            True if successfully loaded, False otherwise
        """
        try:
            self.logger.info("Loading workflow from dictionary")
            return self._parse_workflow_data(workflow_data)
        except Exception as e:
            self.logger.error(f"Error loading workflow from dictionary: {e}")
            return False
    
    def _parse_workflow_data(self, workflow_data: Dict[str, Any]) -> bool:
        """
        Parse workflow data and create objective objects.
        
        Args:
            workflow_data: Raw workflow data dictionary
            
        Returns:
            True if successfully parsed, False otherwise
        """
        try:
            # Clear existing objectives
            self.objectives.clear()
            
            # Extract workflow metadata
            workflow_name = workflow_data.get('name', 'Unnamed Workflow')
            workflow_description = workflow_data.get('description', '')
            objectives_data = workflow_data.get('objectives', [])
            
            self.logger.info(f"Parsing workflow: {workflow_name}")
            self.logger.info(f"Description: {workflow_description}")
            self.logger.info(f"Number of objectives: {len(objectives_data)}")
            
            # Parse each objective
            for idx, obj_data in enumerate(objectives_data):
                try:
                    objective = WorkflowObjective(
                        id=obj_data.get('id', f'objective_{idx}'),
                        name=obj_data.get('name', f'Objective {idx + 1}'),
                        description=obj_data.get('description', ''),
                        type=obj_data.get('type', ''),
                        parameters=obj_data.get('parameters', {})
                    )
                    
                    # Determine if objective is supported
                    if objective.type in self.supported_objective_types:
                        objective.status = ObjectiveStatus.SUPPORTED
                        self.logger.info(f"[SUPPORTED] Objective '{objective.name}' (type: {objective.type})")
                    else:
                        objective.status = ObjectiveStatus.UNSUPPORTED
                        self.logger.warning(f"[UNSUPPORTED] Objective '{objective.name}' (type: {objective.type})")
                    
                    self.objectives.append(objective)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing objective {idx}: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(self.objectives)} objectives")
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing workflow data: {e}")
            return False
    
    def get_supported_objectives(self) -> List[WorkflowObjective]:
        """
        Get list of all supported objectives.
        
        Returns:
            List of supported WorkflowObjective objects
        """
        return [obj for obj in self.objectives if obj.status == ObjectiveStatus.SUPPORTED]
    
    def get_unsupported_objectives(self) -> List[WorkflowObjective]:
        """
        Get list of all unsupported objectives.
        
        Returns:
            List of unsupported WorkflowObjective objects
        """
        return [obj for obj in self.objectives if obj.status == ObjectiveStatus.UNSUPPORTED]
    
    def print_objective_summary(self):
        """Print a summary of all objectives and their support status."""
        supported = self.get_supported_objectives()
        unsupported = self.get_unsupported_objectives()
        
        self.logger.info("="*60)
        self.logger.info("WORKFLOW OBJECTIVE SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Total Objectives: {len(self.objectives)}")
        self.logger.info(f"Supported: {len(supported)}")
        self.logger.info(f"Unsupported: {len(unsupported)}")
        
        if unsupported:
            self.logger.warning("\nUnsupported Objectives:")
            for obj in unsupported:
                self.logger.warning(f"  - {obj.name} (type: {obj.type})")
        
        if supported:
            self.logger.info("\nSupported Objectives (will be executed):")
            for obj in supported:
                self.logger.info(f"  - {obj.name} (type: {obj.type})")
        
        self.logger.info("="*60)
    
    def execute_workflow(self) -> bool:
        """
        Execute all supported objectives in sequence.
        Ensures the application is ready before processing.
        
        Returns:
            True if all supported objectives completed successfully, False otherwise
        """
        supported_objectives = self.get_supported_objectives()
        
        if not supported_objectives:
            self.logger.warning("No supported objectives to execute")
            return True
        
        self.logger.info("="*60)
        self.logger.info("STARTING WORKFLOW EXECUTION")
        self.logger.info("="*60)
        
        # Print summary first
        self.print_objective_summary()
        
        # Execute each supported objective in sequence
        success_count = 0
        total_count = len(supported_objectives)
        
        for idx, objective in enumerate(supported_objectives, 1):
            self.logger.info(f"\n{'-'*40}")
            self.logger.info(f"Executing Objective {idx}/{total_count}: {objective.name}")
            self.logger.info(f"Type: {objective.type}")
            self.logger.info(f"Description: {objective.description}")
            self.logger.info(f"{'-'*40}")
            
            try:
                # Execute the objective
                if self._execute_objective(objective):
                    objective.status = ObjectiveStatus.COMPLETED
                    success_count += 1
                    self.logger.info(f"[SUCCESS] Objective '{objective.name}' completed successfully")
                else:
                    objective.status = ObjectiveStatus.FAILED
                    self.logger.error(f"[FAILED] Objective '{objective.name}' failed")
                    
            except Exception as e:
                objective.status = ObjectiveStatus.FAILED
                objective.error_message = str(e)
                self.logger.error(f"[FAILED] Objective '{objective.name}' failed with error: {e}")
        
        # Print final results
        self.logger.info("\n" + "="*60)
        self.logger.info("WORKFLOW EXECUTION COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Results: {success_count}/{total_count} objectives completed successfully")
        
        if success_count == total_count:
            self.logger.info("All supported objectives completed successfully!")
            return True
        else:
            self.logger.warning(f"WARNING: {total_count - success_count} objectives failed")
            return False
    
    def _execute_objective(self, objective: WorkflowObjective) -> bool:
        """
        Execute a single objective.
        
        Args:
            objective: WorkflowObjective to execute
            
        Returns:
            True if successful, False otherwise
        """
        if objective.type not in self.supported_objective_types:
            self.logger.error(f"Unsupported objective type: {objective.type}")
            return False
        
        try:
            executor_func = self.supported_objective_types[objective.type]
            return executor_func(objective)
        except Exception as e:
            self.logger.error(f"Error executing objective {objective.name}: {e}")
            return False
    
    # Objective execution methods
    def _execute_open_application(self, objective: WorkflowObjective) -> bool:
        """Execute open_application objective."""
        self.logger.info("Executing open application...")
        success, window = self.orchestrator.step1_ensure_application_open()
        return success and window is not None
    
    def _execute_maximize_window(self, objective: WorkflowObjective) -> bool:
        """Execute maximize_window objective."""
        self.logger.info("Executing maximize window...")
        window = self.orchestrator.bot.get_window_handle()
        if window:
            return self.orchestrator.step2_maximize_application(window)
        return False
    
    def _execute_bring_to_foreground(self, objective: WorkflowObjective) -> bool:
        """Execute bring_to_foreground objective."""
        self.logger.info("Executing bring to foreground...")
        window = self.orchestrator.bot.get_window_handle()
        if window:
            return self.orchestrator.bot.bring_to_foreground(window)
        return False
    
    def _execute_visual_verification(self, objective: WorkflowObjective) -> bool:
        """Execute visual_verification objective."""
        self.logger.info("Executing visual verification...")
        return self.orchestrator.bot.check_maximized_visually()
    
    def _execute_wait(self, objective: WorkflowObjective) -> bool:
        """Execute wait objective."""
        import time
        duration = objective.parameters.get('duration', 1)
        self.logger.info(f"Waiting for {duration} seconds...")
        time.sleep(duration)
        return True
    
    def _execute_startup_sequence(self, objective: WorkflowObjective) -> bool:
        """Execute startup_sequence objective."""
        self.logger.info("Executing full startup sequence...")
        return self.orchestrator.run_startup_sequence()
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.
        
        Returns:
            Dictionary containing workflow status information
        """
        total = len(self.objectives)
        supported = len(self.get_supported_objectives())
        unsupported = len(self.get_unsupported_objectives())
        completed = len([obj for obj in self.objectives if obj.status == ObjectiveStatus.COMPLETED])
        failed = len([obj for obj in self.objectives if obj.status == ObjectiveStatus.FAILED])
        
        return {
            'total_objectives': total,
            'supported_objectives': supported,
            'unsupported_objectives': unsupported,
            'completed_objectives': completed,
            'failed_objectives': failed,
            'success_rate': (completed / supported * 100) if supported > 0 else 0
        }
