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

Next Steps (TODO):
- Add Parser mode for instruction analysis.
- Add a Instruction executer module for task execution.
"""

from src.StartupModule import runner
from src.ParsingModule import parser


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
    # Getting config
    config = runner.initialize_system()
    # Fails gracefully if config is invalid
    if config is None:
        exit(1)

    # Running Startup
    success, program = runner.run_startup(config)
    if not success:
        exit(1)
    # Test the instruction parser
    success, results = parser.process_instruction_file("example_instructions.json")
    if not success:
        print(f"Parser Error: {results}")
        exit(1)
    print(f"Parser Results: {results}")

    print("\nSupported objectives ready to pass to workflow module.")

# Entry point for direct script execution
if __name__ == "__main__":
    main()