#!/usr/bin/env python3
"""
Automation Bot - Main Entry Point

This is the primary entry point for the Automation Bot system, which provides
automated application task management.

On startup, the system performs the following steps:
!. Load Config, Check if program is running
2. Open application if not running it open the application
3. Maximize application window if the is not maximized it tries 3 times
4. Then it checks if the application is open and maximized using corner templates
After successful startup, the system is ready. And proceeds to instruction parsing.
1. Load instruction file
2. Parse objectives and check if supported
3. Then email the unsupported objectives if any
4. Pass supported objectives to workflow module (not implemented yet).

Next Steps (TODO):
- Add a Instruction executer module for task execution.
"""

from src.startup_module import system_initializer
from src.parser_module import process_objectives_file
from src.workflow_module import start_workflow_from_parser_results


def main():
    """
    Main execution function for the Application Manager Bot system.
    
    This function coordinates the entire system lifecycle:
    1. System initialization (configuration and validation)
    2. Standard mode execution (application startup sequence)
    3. Result reporting and system exit
    
    Standard Mode: Basic application startup sequence
        - Opens target application
        - Maximizes window
        - Verifies state using corner templates
        
    Returns:
        None (exits with status code 0 for success, 1 for failure)
    """
    # # Getting config (includes email configuration)
    # config = system_initializer.initialize_system()

    # # Fails gracefully if config is invalid
    # if config is None:
    #     exit(1)

    # # Running Startup
    # success = system_initializer.run_startup(config)
    # if not success:
    #     exit(1)

    # Parser instruction file. and return supported
    success, results = process_objectives_file("objective_file.json")
    if not success:
        print(f"Parser Error: {results}")
        exit(1)

    print(f"Parser Results: {results}")
    print("\nSupported objectives ready to pass to workflow module.")

    success, results = start_workflow_from_parser_results(results)
    if not success:
        print(f"Workflow Error: {results}")
        exit(1)


if __name__ == "__main__":
    main()