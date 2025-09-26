# Workflow Manager

The Workflow Manager module provides JSON-based workflow processing for the Application Manager Bot system. It allows you to define complex sequences of objectives that can be executed automatically.

## Features

- **JSON-based Configuration**: Define workflows using structured JSON files
- **Objective Classification**: Automatically identifies supported vs unsupported objectives
- **Sequential Execution**: Executes supported objectives in sequence
- **Application Readiness**: Ensures the target application is ready before processing objectives
- **Comprehensive Logging**: Detailed logging of workflow execution and results
- **Status Reporting**: Provides detailed status information for workflow execution

## Supported Objective Types

The workflow manager currently supports the following objective types:

### Core Application Management
- **`open_application`**: Ensures the application is running and opens it if necessary
- **`maximize_window`**: Maximizes the application window to full screen
- **`bring_to_foreground`**: Brings the application window to the foreground and gives it focus
- **`startup_sequence`**: Executes the complete startup sequence (open, maximize, verify)

### Verification and Control
- **`visual_verification`**: Performs visual verification that the application is properly displayed
- **`wait`**: Pauses execution for a specified duration (useful for timing control)

## JSON Workflow Format

Workflows are defined using JSON files with the following structure:

```json
{
    "name": "Workflow Name",
    "description": "Description of what this workflow does",
    "version": "1.0",
    "objectives": [
        {
            "id": "unique_objective_id",
            "name": "Human-readable objective name",
            "description": "Description of what this objective does",
            "type": "objective_type",
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    ]
}
```

### Example Workflow

See `examples/sample_workflow.json` for a complete example that demonstrates all supported objective types.

## Usage

### From Python Code

```python
from main import run_workflow, run_workflow_from_dict

# Run workflow from JSON file
run_workflow("path/to/workflow.json")

# Run workflow from dictionary
workflow_data = {
    "name": "My Workflow",
    "objectives": [
        {
            "id": "obj1",
            "name": "Open App",
            "type": "startup_sequence",
            "parameters": {}
        }
    ]
}
run_workflow_from_dict(workflow_data)
```

### Direct API Usage

```python
from workflow import WorkflowManager
from orchestrator import ApplicationOrchestrator
from bot import ApplicationManagerBot

# Initialize components
bot = ApplicationManagerBot("MyApp", app_path="myapp.exe")
orchestrator = ApplicationOrchestrator(bot)
workflow_manager = WorkflowManager(orchestrator)

# Load and execute workflow
workflow_manager.load_workflow_from_json("workflow.json")
success = workflow_manager.execute_workflow()
```

## Objective Parameters

### wait
- **`duration`** (number): Duration to wait in seconds

### Example Objectives

```json
{
    "id": "wait_example",
    "name": "Wait 3 Seconds",
    "type": "wait",
    "parameters": {
        "duration": 3
    }
}
```

## Workflow Execution Process

1. **Initialization**: The workflow manager loads and parses the JSON workflow
2. **Classification**: Each objective is classified as supported or unsupported
3. **Summary**: A summary is displayed showing which objectives will be executed
4. **Application Readiness**: The orchestrator ensures the target application is ready
5. **Sequential Execution**: Each supported objective is executed in sequence
6. **Status Reporting**: Final results are displayed with success/failure counts

## Error Handling

- **Unsupported Objectives**: Logged as warnings but don't stop execution
- **Failed Objectives**: Logged as errors and marked as failed, but execution continues
- **Critical Failures**: Application readiness failures will stop the entire workflow

## Extending with New Objective Types

To add support for new objective types:

1. Add the new type to `supported_objective_types` dictionary in `WorkflowManager.__init__()`
2. Implement the execution method following the pattern `_execute_<type_name>()`
3. Add appropriate parameter validation if needed

Example:
```python
def _execute_my_new_type(self, objective: WorkflowObjective) -> bool:
    """Execute my_new_type objective."""
    param_value = objective.parameters.get('my_parameter', 'default')
    # Implementation here
    return True  # or False if failed
```

## Testing

Use the provided test script to verify workflow functionality:

```bash
python test_workflow.py
```

This will run both file-based and dictionary-based workflow tests.
