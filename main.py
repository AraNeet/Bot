#!/usr/bin/env python3
"""
Application Manager Bot - Main Entry Point

This is the primary entry point for the Application Manager Bot system, which provides
automated application window management with corner-based template matching and 
workflow support.

The system operates in two modes:
1. Standard Mode: Basic application startup sequence (open, maximize, verify)
2. Workflow Mode: Execute complex sequences of objectives defined in JSON

Architecture Overview:
- main.py: Entry point and configuration management
- bot/: Core application management functionality
- orchestrator/: High-level workflow orchestration  
- workflow/: JSON-based workflow processing
- utils/: Image processing and window management utilities
- config/: Logging and configuration management

Usage Examples:
    # Standard mode with defaults
    main()
    
    # Standard mode with custom config
    config = {"app_name": "Calculator", "app_path": "calc.exe"}
    main(config_json=config)
    
    # Workflow mode from file
    run_workflow("my_workflow.json")
    
    # Workflow mode from dictionary
    workflow_data = {"name": "Test", "objectives": [...]}
    run_workflow_from_dict(workflow_data)

Author: Application Manager Bot System
Version: 2.0 - Added workflow support and corner-based template matching
"""

import sys
import os
import logging
from pathlib import Path
import json
from typing import Dict, Any, Optional

# Add src directory to Python path for imports
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Import core system components
from bot import ApplicationManagerBot                # Core bot functionality
from orchestrator import ApplicationOrchestrator    # Workflow orchestration
from workflow import WorkflowManager                 # JSON workflow processing
from config import setup_logging                    # Logging configuration
from utils import WindowHelper                      # Window management utilities


def load_config(config_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load and merge configuration from multiple sources with smart defaults.
    
    Configuration Priority (highest to lowest):
    1. Provided config_json parameter
    2. config.json file (if exists)
    3. Built-in defaults
    
    Args:
        config_json: Optional configuration dictionary to override defaults
    
    Returns:
        Dict[str, Any]: Merged configuration dictionary with all required settings
        
    Configuration Keys:
        app_name: Window title or partial title to search for
        icon_template_path: Legacy icon template (optional, for backward compatibility)
        app_path: Full path to application executable
        process_name: Process name for detection (e.g., 'notepad.exe')
        max_retries: Maximum retry attempts for operations
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_to_file: Whether to write logs to file
        top_left_template_path: Template for top-left corner detection
        top_right_template_path: Template for top-right corner detection  
        bottom_right_template_path: Template for bottom-right corner detection
    """
    # Default configuration with corner-based template matching support
    # Resolve template paths relative to the main.py file location
    main_dir = Path(__file__).parent
    default_config = {
        'app_name': "Notepad",                                      # Target application name
        'app_path': "notepad.exe",                                 # Application executable path
        'process_name': "notepad.exe",                             # Process name for detection
        'max_retries': 5,                                          # Maximum retry attempts
        'log_level': "INFO",                                       # Logging verbosity
        'log_to_file': True,                                       # Enable file logging
        'top_left_template_path': str(main_dir / "assets" / "Icon.png"),       # Notepad icon template
        'top_right_template_path': str(main_dir / "assets" / "close_x.png"),           # Close button template
        'bottom_right_template_path': str(main_dir / "assets" / "bottom_right_element.png")  # Bottom corner template
    }
    
    if config_json is not None:
        # Override defaults with provided configuration
        default_config.update(config_json)
        print("Configuration loaded from provided JSON dictionary")
    else:
        # Attempt to load from config.json file
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                    # Resolve template paths relative to main.py directory if they are relative
                    for key in ['top_left_template_path', 'top_right_template_path', 'bottom_right_template_path', 'icon_template_path']:
                        if key in loaded_config and loaded_config[key]:
                            config_path = Path(loaded_config[key])
                            # If path is relative, make it relative to main.py directory
                            if not config_path.is_absolute():
                                absolute_path = main_dir / config_path
                                loaded_config[key] = str(absolute_path)
                                print(f"Resolved {key}: {loaded_config[key]}")
                    
                    default_config.update(loaded_config)
                    print(f"Configuration loaded from {config_file}")
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                print("Using default configuration")
        else:
            # Create example config file if it doesn't exist
            try:
                # Ensure config directory exists
                os.makedirs("config", exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                    print(f"Default configuration saved to {config_file}")
            except Exception as e:
                print(f"Could not save default config: {e}")
    
    return default_config



def main(config_json: Optional[Dict[str, Any]] = None, workflow_path: Optional[str] = None, workflow_data: Optional[Dict[str, Any]] = None):
    """
    Main execution function for the Application Manager Bot system.
    
    This function coordinates the entire system lifecycle:
    1. Configuration loading and validation
    2. Logging setup and initialization  
    3. Component initialization (Bot, Orchestrator, WorkflowManager)
    4. Mode detection (Standard vs Workflow)
    5. Execution and result reporting
    
    Execution Modes:
        Standard Mode: Basic application startup sequence
            - Opens target application
            - Maximizes window
            - Verifies state using corner templates
            
        Workflow Mode: JSON-defined objective sequences
            - Loads objectives from file or dictionary
            - Classifies supported vs unsupported objectives
            - Executes in sequence with error handling
            - Provides comprehensive status reporting
    
    Args:
        config_json: Optional configuration dictionary to override defaults
        workflow_path: Optional path to JSON workflow file
        workflow_data: Optional workflow dictionary (alternative to file)
        
    Returns:
        None (exits with status code 0 for success, 1 for failure)
        
    Raises:
        SystemExit: With appropriate exit code based on execution results
        KeyboardInterrupt: Gracefully handled for user cancellation
    """
    # Step 1: Load and validate configuration
    config = load_config(config_json=config_json)
    
    # Step 2: Initialize logging subsystem
    log_level_obj = getattr(logging, config.get('log_level', 'INFO'))
    log_to_file_setting = config.get('log_to_file', True)
    
    log_file = setup_logging(
        log_level=log_level_obj,
        log_to_file=log_to_file_setting
    )
    
    logger = logging.getLogger(__name__)
    
    # Step 3: Log configuration for debugging and audit trail
    logger.info("="*50)
    logger.info("APPLICATION MANAGER BOT SYSTEM STARTUP")
    logger.info("="*50)
    logger.info("Configuration:")
    logger.info("-" * 30)
    for key, value in config.items():
        if key not in ['log_level', 'log_to_file']:  # Skip logging config to avoid redundancy
            logger.info(f"  {key}: {value}")
    logger.info("-" * 30)
    
    try:
        # Step 4: Initialize core system components
        logger.info("Initializing Application Manager Bot...")
        bot = ApplicationManagerBot(
            app_name=config['app_name'],
            app_path=config.get('app_path'),
            process_name=config.get('process_name'),
            max_retries=config.get('max_retries', 5),
            top_left_template_path=config.get('top_left_template_path'),
            top_right_template_path=config.get('top_right_template_path'),
            bottom_right_template_path=config.get('bottom_right_template_path')
        )
        
        logger.info("Creating orchestrator...")
        orchestrator = ApplicationOrchestrator(bot)
        
        # Ensure application is ready (startup sequence)
        logger.info("\nEnsuring application is ready...")
        if not orchestrator.run_startup_sequence():
            logger.error("Failed to prepare application - cannot proceed with workflow")
            return False
        
        logger.info("Application is ready - proceeding...")
        

        # Step 5: Determine execution mode and proceed accordingly
        if workflow_path or workflow_data:
            # === WORKFLOW MODE EXECUTION ===
            logger.info("Workflow mode detected - initializing workflow manager...")
            workflow_manager = WorkflowManager(orchestrator)
            
            # Load workflow from file or dictionary
            if workflow_path:
                logger.info(f"Loading workflow from file: {workflow_path}")
                if not workflow_manager.load_workflow_from_json(workflow_path):
                    print(f"[FAILED] Could not load workflow from {workflow_path}")
                    sys.exit(1)
            elif workflow_data:
                logger.info("Loading workflow from provided data...")
                if not workflow_manager.load_workflow_from_dict(workflow_data):
                    print("[FAILED] Could not load workflow from provided data")
                    sys.exit(1)
            
            # Execute the loaded workflow sequence
            logger.info("Starting workflow execution...")
            success = workflow_manager.execute_workflow()
            
            # Display comprehensive workflow results
            print("\n" + "="*60)
            if success:
                print("[SUCCESS] WORKFLOW COMPLETED SUCCESSFULLY!")
                
                # Display detailed workflow statistics
                status = workflow_manager.get_workflow_status()
                print("\nWorkflow Status Report:")
                print("-" * 40)
                print(f"  Total Objectives: {status['total_objectives']}")
                print(f"  Supported: {status['supported_objectives']}")
                print(f"  Unsupported: {status['unsupported_objectives']}")
                print(f"  Completed: {status['completed_objectives']}")
                print(f"  Failed: {status['failed_objectives']}")
                print(f"  Success Rate: {status['success_rate']:.1f}%")
                
                # Display final application state
                app_status = orchestrator.get_status_report()
                print("\nApplication Status:")
                print("-" * 30)
                for key, value in app_status.items():
                    status_str = "[SUCCESS]" if value else "[FAILED]" if value is False else "N/A"
                    print(f"  {key.replace('_', ' ').title()}: {status_str}")
            else:
                print("[FAILED] WORKFLOW EXECUTION FAILED")
                print("Some objectives could not be completed. Please check the logs for details.")
                
                if log_file:
                    print(f"\nLog file: {log_file}")
            
            print("="*60 + "\n")
            
        else:
            # === STANDARD MODE EXECUTION ===
            logger.info("Standard mode - running startup sequence...")
            success = orchestrator.run_startup_sequence()
            
            # Display standard mode results
            print("\n" + "="*50)
            if success:
                print("[SUCCESS] SUCCESS: Application is now open, in foreground, and maximized!")
                
                # Display application state verification
                status = orchestrator.get_status_report()
                print("\nStatus Report:")
                print("-" * 30)
                for key, value in status.items():
                    status_str = "[SUCCESS]" if value else "[FAILED]" if value is False else "N/A"
                    print(f"  {key.replace('_', ' ').title()}: {status_str}")
            else:
                print("[FAILED] FAILED: Could not complete the sequence.")
                print("Please check the logs for details.")
                
                if log_file:
                    print(f"\nLog file: {log_file}")
            
            print("="*50 + "\n")
        
        # Step 6: Exit with appropriate status code
        logger.info(f"System execution completed with {'success' if success else 'failure'}")
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        # Handle graceful shutdown on user interrupt (Ctrl+C)
        logger.info("Operation cancelled by user")
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        # Handle any unexpected errors with full stack trace logging
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n[FAILED] Unexpected error: {e}")
        print("Please check the logs for details.")
        
        if log_file:
            print(f"\nLog file: {log_file}")
        
        sys.exit(1)


def run_workflow(workflow_path: str, config_json: Optional[Dict[str, Any]] = None):
    """
    Convenience function to execute a workflow from a JSON file.
    
    This is a simplified interface for workflow execution that handles
    the main() function call with appropriate parameters.
    
    Usage Example:
        run_workflow("my_workflow.json")
        run_workflow("complex_flow.json", {"app_name": "Calculator"})
    
    Args:
        workflow_path: Path to the JSON workflow file
        config_json: Optional configuration dictionary to override defaults
        
    Raises:
        SystemExit: With appropriate exit code based on workflow execution results
    """
    main(config_json=config_json, workflow_path=workflow_path)


def run_workflow_from_dict(workflow_data: Dict[str, Any], config_json: Optional[Dict[str, Any]] = None):
    """
    Convenience function to execute a workflow from a dictionary.
    
    This allows programmatic workflow creation and execution without
    requiring a JSON file.
    
    Usage Example:
        workflow = {
            "name": "Test Workflow",
            "objectives": [
                {"id": "1", "name": "Open App", "type": "startup_sequence", "parameters": {}}
            ]
        }
        run_workflow_from_dict(workflow)
    
    Args:
        workflow_data: Dictionary containing workflow structure and objectives
        config_json: Optional configuration dictionary to override defaults
        
    Raises:
        SystemExit: With appropriate exit code based on workflow execution results
    """
    main(config_json=config_json, workflow_data=workflow_data)


# Entry point for direct script execution
if __name__ == "__main__":
    # When run directly, execute the test workflow for demonstration
    run_workflow("test/test_workflow.json")