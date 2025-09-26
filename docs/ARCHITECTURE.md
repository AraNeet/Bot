# Application Manager Bot - System Architecture

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Template Matching System](#template-matching-system)
6. [Workflow System](#workflow-system)
7. [Configuration Management](#configuration-management)
8. [Error Handling](#error-handling)
9. [Extensibility](#extensibility)

## Overview

The Application Manager Bot is a sophisticated Python-based system for automated application window management. It uses advanced computer vision techniques with corner-based template matching to reliably detect application states and execute complex workflows.

### Key Features
- **Corner-Based Detection**: Revolutionary 3-point template matching system
- **Workflow Engine**: JSON-driven objective sequencing with error handling
- **Dual Mode Operation**: Standard startup sequences and complex workflows
- **Robust Error Handling**: Comprehensive logging and graceful failure recovery
- **Modular Architecture**: Clean separation of concerns with extensible design

### Target Applications
- Automated testing environments
- Application state verification
- Workflow automation for desktop applications
- Quality assurance and monitoring systems

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION MANAGER BOT                      │
├─────────────────────────────────────────────────────────────────┤
│                          main.py                               │
│               ┌─────────────────────────────────┐               │
│               │     Entry Point & Config        │               │
│               │   - Configuration loading       │               │
│               │   - Mode detection              │               │
│               │   - Component orchestration     │               │
│               └─────────────────┬───────────────┘               │
│                                 │                               │
├─────────────────────────────────┼─────────────────────────────────┤
│                                 ▼                               │
│    ┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐│
│    │   bot/          │    │orchestrator/ │    │   workflow/     ││
│    │ApplicationBot   │◄───┤Orchestrator  │◄───┤WorkflowManager  ││
│    │                 │    │              │    │                 ││
│    │- Window mgmt    │    │- Step logic  │    │- JSON parsing   ││
│    │- Process ctrl   │    │- Sequences   │    │- Objective exec ││
│    │- Template ops   │    │- Validation  │    │- Status reports ││
│    └─────────┬───────┘    └──────────────┘    └─────────────────┘│
│              │                                                  │
├──────────────┼──────────────────────────────────────────────────┤
│              ▼                                                  │
│    ┌─────────────────┐              ┌─────────────────┐         │
│    │   utils/        │              │   config/       │         │
│    │                 │              │                 │         │
│    │┌───────────────┐│              │┌───────────────┐│         │
│    ││ImageMatcher   ││              ││logging_config ││         │
│    ││- Template     ││              ││- Log setup    ││         │
│    ││  matching     ││              ││- File handling││         │
│    ││- Region search││              │└───────────────┘│         │
│    ││- Corner detect││              └─────────────────┘         │
│    │└───────────────┘│                                          │
│    │┌───────────────┐│                                          │
│    ││WindowHelper   ││                                          │
│    ││- Focus mgmt   ││                                          │
│    ││- Maximize ops ││                                          │
│    ││- Window utils ││                                          │
│    │└───────────────┘│                                          │
│    └─────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Entry Point (`main.py`)
**Purpose**: System initialization, configuration management, and execution coordination.

**Responsibilities**:
- Load and merge configuration from multiple sources
- Initialize logging subsystem
- Create and configure core components
- Detect execution mode (Standard vs Workflow)
- Coordinate execution flow
- Handle errors and exit codes

**Key Functions**:
- `load_config()`: Multi-source configuration loading with priority
- `main()`: Primary execution coordinator
- `run_workflow()`: Workflow execution convenience function

### 2. Core Bot (`bot/application_bot.py`)
**Purpose**: Direct application management and control operations.

**Responsibilities**:
- Process detection and management
- Application launching and window control
- Template loading and management
- Visual verification using corner templates
- Basic window operations (maximize, focus, etc.)

**Key Methods**:
- `is_application_open()`: Process-based application detection
- `open_application()`: Application launching with timeout
- `get_window_handle()`: Window reference acquisition
- `maximize_application()`: Window maximization
- `bring_to_foreground()`: Focus management
- `check_visual_open()`: Template-based open verification
- `check_maximized_visually()`: Corner-based maximization detection

### 3. Orchestrator (`orchestrator/application_orchestrator.py`)
**Purpose**: High-level workflow logic and step sequencing.

**Responsibilities**:
- Execute multi-step application startup sequences
- Coordinate between bot operations
- Implement retry logic and error recovery
- Provide status reporting and verification
- Manage application state transitions

**Key Steps**:
1. **Step 1**: Ensure application is open (with retry logic)
2. **Step 2**: Maximize application window
3. **Step 3**: Verify and fix state (visual confirmation)

**Key Methods**:
- `run_startup_sequence()`: Complete startup workflow
- `get_status_report()`: Current application state summary

### 4. Workflow Manager (`workflow/workflow_manager.py`)
**Purpose**: JSON-based workflow processing and objective management.

**Responsibilities**:
- Parse and validate JSON workflow definitions
- Classify objectives as supported/unsupported
- Execute objectives in sequence with error handling
- Provide comprehensive status reporting
- Integrate with orchestrator for application readiness

**Supported Objective Types**:
- `startup_sequence`: Complete application startup
- `open_application`: Ensure application is running
- `maximize_window`: Window maximization
- `bring_to_foreground`: Focus management
- `visual_verification`: Template-based verification
- `wait`: Timing control

### 5. Image Processing (`utils/image_utils.py`)
**Purpose**: Advanced template matching and visual verification.

**Responsibilities**:
- Screenshot capture and processing
- Template loading and validation
- Region-based template matching
- Corner detection algorithms
- Maximization verification logic

**Key Features**:
- **Region-Based Matching**: Search only in specific screen areas
- **Corner Detection**: 3-point verification system
- **Confidence Thresholds**: Adjustable matching sensitivity
- **Global Coordinate Translation**: Convert region coordinates to screen coordinates

### 6. Window Management (`utils/window_utils.py`)
**Purpose**: Platform-specific window operations and utilities.

**Responsibilities**:
- Window enumeration and search
- Focus management with multiple fallback methods
- Window state detection
- Safe window operation wrappers

## Data Flow

### Standard Mode Execution Flow
```
main() → load_config() → ApplicationManagerBot() → ApplicationOrchestrator() →
run_startup_sequence() → [Step 1, 2, 3] → get_status_report() → exit
```

### Workflow Mode Execution Flow
```
main() → load_config() → ApplicationManagerBot() → ApplicationOrchestrator() →
WorkflowManager() → load_workflow_from_json() → execute_workflow() →
[for each objective] → _execute_objective() → get_workflow_status() → exit
```

### Template Matching Flow
```
check_maximized_visually() → ImageMatcher.check_maximized_by_corners() →
take_screenshot() → get_corner_regions() → find_template_in_region() × 3 →
evaluate_all_corners_found() → return boolean
```

## Template Matching System

### Corner-Based Detection Algorithm

The system uses a revolutionary 3-point corner detection method that is more reliable than traditional dimension-based approaches.

#### Corner Regions
```
┌─────────────────────────────────────┐
│ TOP-LEFT      │         │ TOP-RIGHT │
│ (200x200)     │         │ (200x200) │
│ notepad_icon  │         │ close_x   │
├───────────────┼─────────┼───────────┤
│               │         │           │
│               │ SCREEN  │           │
│               │         │           │
├───────────────┼─────────┼───────────┤
│               │         │ BOTTOM-   │
│               │         │ RIGHT     │
│               │         │ (200x200) │
│               │         │ element   │
└─────────────────────────┴───────────┘
```

#### Detection Logic
1. **Screenshot Capture**: Full screen capture using pyautogui
2. **Region Extraction**: Extract 200x200 pixel corners
3. **Template Matching**: OpenCV template matching in each region
4. **Confidence Evaluation**: Check against threshold (default 0.8)
5. **Result Aggregation**: Application is maximized only if ALL 3 corners match

#### Advantages Over Dimension-Based Detection
- **Resolution Independent**: Works across different screen sizes
- **DPI Agnostic**: Not affected by display scaling
- **Visual Accuracy**: Confirms actual application appearance
- **State Specific**: Detects true maximized state vs. fullscreen
- **Robust**: Handles partial occlusion and variable window decorations

## Workflow System

### JSON Workflow Structure
```json
{
    "name": "Workflow Name",
    "description": "Workflow description",
    "version": "1.0",
    "objectives": [
        {
            "id": "unique_id",
            "name": "Human readable name",
            "description": "Detailed description",
            "type": "objective_type",
            "parameters": {
                "key": "value"
            }
        }
    ]
}
```

### Objective Lifecycle
1. **Loading**: Parse JSON and create WorkflowObjective objects
2. **Classification**: Determine supported vs unsupported objectives
3. **Preparation**: Ensure application readiness via orchestrator
4. **Execution**: Sequential processing with error handling
5. **Reporting**: Comprehensive status and statistics

### Error Handling Strategy
- **Unsupported Objectives**: Logged as warnings, execution continues
- **Failed Objectives**: Logged as errors, execution continues
- **Critical Failures**: Application readiness failures stop execution
- **Exception Handling**: Full stack traces logged, graceful recovery

## Configuration Management

### Configuration Sources (Priority Order)
1. **Function Parameters**: Direct config_json parameter
2. **config/config.json**: Persistent configuration file
3. **Built-in Defaults**: Fallback configuration

### Configuration Structure
```json
{
    "app_name": "Target application window title",
    "app_path": "Path to application executable",
    "process_name": "Process name for detection",
    "max_retries": 5,
    "log_level": "INFO",
    "log_to_file": true,
    "top_left_template_path": "assets/notepad_icon.png",
    "top_right_template_path": "assets/close_x.png",
    "bottom_right_template_path": "assets/bottom_right_element.png"
}
```

## Error Handling

### Logging Strategy
- **Structured Logging**: Consistent format with timestamps and levels
- **File and Console**: Dual output for debugging and monitoring
- **Exception Tracking**: Full stack traces for debugging
- **Performance Metrics**: Execution timing and success rates

### Error Categories
1. **Configuration Errors**: Missing files, invalid JSON, missing templates
2. **Application Errors**: Failed launches, missing processes, window issues
3. **Template Errors**: Missing templates, failed matches, region issues
4. **Workflow Errors**: Invalid objectives, execution failures, timeout issues
5. **System Errors**: Permission issues, resource constraints, platform problems

### Recovery Mechanisms
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Fallback Methods**: Alternative approaches for critical operations
- **Graceful Degradation**: Continue execution when possible
- **User Notification**: Clear error messages and resolution guidance

## Extensibility

### Adding New Objective Types
1. Add type to `supported_objective_types` dictionary
2. Implement `_execute_<type_name>()` method
3. Add parameter validation if needed
4. Update documentation and examples

### Custom Template Matching
- Extend `ImageMatcher` class with new algorithms
- Add custom region definitions
- Implement confidence calculation methods
- Integrate with existing workflow

### Platform Extensions
- Implement platform-specific window operations
- Add OS-specific application detection
- Extend template matching for different environments
- Add platform-specific configuration options

### Integration Points
- **Database Integration**: Store workflow results and metrics
- **API Integration**: Remote workflow triggering and monitoring
- **Notification Systems**: Alert on workflow completion or failure
- **CI/CD Integration**: Automated testing and deployment verification

## Performance Considerations

### Optimization Strategies
- **Region-Based Matching**: Reduce search areas for faster processing
- **Template Caching**: Avoid repeated template loading
- **Screenshot Optimization**: Minimize capture frequency
- **Parallel Processing**: Consider concurrent objective execution

### Resource Management
- **Memory Usage**: Efficient image handling and cleanup
- **CPU Usage**: Optimize template matching algorithms
- **Disk I/O**: Efficient logging and configuration management
- **Network**: Consider remote template storage and caching

## Security Considerations

### Template Security
- **Template Validation**: Verify template integrity
- **Path Validation**: Prevent directory traversal attacks
- **File Permissions**: Appropriate access controls

### Process Security
- **Process Isolation**: Safe application launching
- **Resource Limits**: Prevent resource exhaustion
- **Permission Management**: Minimal required privileges

This architecture provides a robust, extensible foundation for automated application management with advanced visual verification capabilities.
