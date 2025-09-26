# Application Manager Bot

A comprehensive Python system for automated application management with workflow support. This bot can open, maximize, focus applications and execute complex workflows defined in JSON files.

## Features

### Core Application Management
- **Automated Application Launch**: Open applications using executable paths
- **Window Management**: Maximize windows and bring them to foreground
- **Visual Verification**: Use image templates to verify application state
- **Process Monitoring**: Check if applications are running using process names
- **Robust Error Handling**: Retry mechanisms and comprehensive logging

### Workflow System (NEW!)
- **JSON-based Workflows**: Define complex sequences of objectives in JSON format
- **Objective Classification**: Automatically identifies supported vs unsupported objectives
- **Sequential Execution**: Execute objectives in order with proper error handling
- **Application Readiness**: Ensures target application is ready before processing
- **Comprehensive Status Reporting**: Detailed execution results and statistics

## Quick Start

### Basic Usage (Application Management)

```python
from main import main

# Use default configuration
main()

# Use custom configuration
config = {
    "app_name": "Calculator", 
    "app_path": "calc.exe", 
    "max_retries": 3
}
main(config_json=config)
```

### Workflow Usage (NEW!)

```python
from main import run_workflow, run_workflow_from_dict

# Run workflow from JSON file
run_workflow("examples/sample_workflow.json")

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

## Installation

1. Clone this repository
2. Install requirements:
```bash
pip install -r requirements.txt
```

## Configuration

### Application Configuration

Configure your target application in `config/config.json`:

```json
{
    "app_name": "YourApp",
    "icon_template_path": "assets/Icon.png",
    "app_path": "C:\\Path\\To\\YourApp.exe",
    "process_name": "yourapp.exe",
    "max_retries": 5,
    "log_level": "INFO",
    "log_to_file": true
}
```

### Workflow Configuration

Create workflow JSON files to define sequences of objectives:

```json
{
    "name": "Sample Workflow",
    "description": "Example workflow demonstrating objectives",
    "objectives": [
        {
            "id": "obj_001",
            "name": "Ensure Application is Open",
            "type": "open_application",
            "parameters": {}
        },
        {
            "id": "obj_002",
            "name": "Maximize Window",
            "type": "maximize_window",
            "parameters": {}
        },
        {
            "id": "obj_003",
            "name": "Wait for Stability",
            "type": "wait",
            "parameters": {
                "duration": 2
            }
        }
    ]
}
```

## Supported Workflow Objectives

- **`open_application`**: Ensures application is running
- **`maximize_window`**: Maximizes the application window
- **`bring_to_foreground`**: Brings window to foreground
- **`visual_verification`**: Performs visual verification
- **`wait`**: Pauses execution for specified duration
- **`startup_sequence`**: Executes complete startup sequence

## Project Structure

```
Bot/
├── main.py                    # Main entry point
├── config/                    # Configuration files
│   ├── config.json           # Application configuration
│   └── logging_config.py     # Logging setup
├── bot/                       # Core bot functionality
│   └── application_bot.py    # Application management logic
├── orchestrator/              # Workflow orchestration
│   └── application_orchestrator.py
├── workflow/                  # NEW! Workflow management
│   ├── workflow_manager.py   # Main workflow logic
│   └── README.md            # Workflow documentation
├── utils/                     # Utility functions
│   ├── image_utils.py        # Image processing
│   └── window_utils.py       # Window management
├── examples/                  # Example files
│   └── sample_workflow.json  # Sample workflow
├── assets/                    # Image templates
└── logs/                      # Log files
```

## Examples

### Basic Application Management

```python
# Open Notepad and maximize it
config = {
    "app_name": "Notepad",
    "app_path": "notepad.exe",
    "process_name": "notepad.exe"
}
main(config_json=config)
```

### Complex Workflow

```python
# Execute a complex workflow
run_workflow("examples/sample_workflow.json")
```

### Testing

Run the test script to verify workflow functionality:

```bash
python test_workflow.py
```

## Logging

All operations are logged with configurable levels. Log files are stored in the `logs/` directory by default.

## Visual Templates

Place reference images in the `assets/` directory for visual verification. See `assets/README.md` for guidelines on creating effective templates.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is open source. Please refer to the license file for details.

## Documentation

- [Workflow System Documentation](workflow/README.md)
- [Asset Guidelines](assets/README.md)

## Recent Updates

### Version 2.0 - Workflow System
- Added comprehensive JSON-based workflow management
- Implemented objective classification and sequential execution
- Enhanced status reporting and error handling
- Maintained backward compatibility with existing functionality
