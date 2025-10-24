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

from src.startup_module.system_initializer import initialize_system
from src.parser_module.objectives_processer import process_objectives_file
from src.workflow_module.engine_1.process_input import process_input_workflow
import time
import subprocess
import sys


def main():
    """
    Main execution function for the Application Manager Bot system.
    
    This function coordinates the entire system lifecycle:
    1. Generate objectives config from definitions
    2. System initialization (configuration and validation)
    3. Standard mode execution (application startup sequence)
    4. Result reporting and system exit
    
    Standard Mode: Basic application startup sequence
        - Opens target application
        - Maximizes window
        - Verifies state using corner templates
        
    Returns:
        None (exits with status code 0 for success, 1 for failure)
    """
    
    # Step 0: Generate objectives config from definitions
    print("\n" + "="*70)
    print("STEP 0: GENERATING OBJECTIVES CONFIG")
    print("="*70)
    try:
        result = subprocess.run(
            [sys.executable, "generate_objectives_config.py"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("[SUCCESS] Objectives config generated")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to generate objectives config:")
        print(e.stdout)
        print(e.stderr)
        print("[WARNING] Continuing with existing config...")
    except Exception as e:
        print(f"[ERROR] Unexpected error generating config: {e}")
        print("[WARNING] Continuing with existing config...")
    
    print("="*70 + "\n")

    # success = initialize_system()
    # if not success:
    #     print("Failed startup sequence.")
    #     exit(1)

    # Parser instruction file. and return supported
    success, results = process_objectives_file("objective_file.json")
    if not success:
        print(f"Parser Error: {results}")
        exit(1)

    print(f"Parser Results: {results}")
    print("\nSupported objectives ready to pass to workflow module.")

    time.sleep(1)
    success, results = process_input_workflow(results)
    if not success:
        print(f"Workflow Error: {results}")
        exit(1)


if __name__ == "__main__":
    main()