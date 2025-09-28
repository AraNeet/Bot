"""
Startup process functions for application management.
Contains step-by-step functions for the application startup sequence.
"""

import time
import subprocess
import os
from typing import Tuple, Optional, Dict, Any
import pygetwindow as gw
import window_helper
import image_helper


def open_application(app_path: str) -> bool:
    """
    Open the application.
    
    Args:
        app_path: Path to the application executable
    
    Returns:
        True if successfully opened, False otherwise
    """
    if not app_path:
        print("No application path provided")
        return False
    
    try:
        subprocess.Popen(app_path)
        print(f"Launched application: {app_path}")
        
        # Wait for application to start
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"Error opening application: {e}")
        return False


def step1_ensure_application_open(app_name: str, app_path: str, process_name: str, max_retries: int = 3) -> Tuple[bool, Optional[gw.Window]]:
    """
    Step 1: Check if the application is already open.
    Step 1.1: If not open then open it (iterate until open).
    
    Args:
        app_name: The window title or partial title of the application
        app_path: Path to the application executable
        process_name: Name of the process to check (e.g., 'notepad.exe')
        max_retries: Maximum number of attempts for each operation
    
    Returns:
        Tuple of (success, window_handle) - True if application is successfully opened, False otherwise
    """
    print("="*30)
    print("Step 1: Checking if application is open")
    
    is_open = window_helper.is_application_open(process_name)
    if is_open:
        print("[SUCCESS] Application is already open")
        window = window_helper.get_window_handle(app_name)
        if window:
            print("[SUCCESS] Window handle obtained")
            return True, window
        else:
            print("Failed to get application window handle")
            return False, None

    # Step 1.1: Iteratively try to open
    print("Step 1.1: Application not open, attempting to open...")
    
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        print(f"Opening attempt {attempts}/{max_retries}")
        
        success = open_application(app_path)
        if success:
            window = window_helper.get_window_handle(app_name)
            if window:
                print("[SUCCESS] Application successfully opened")
                return True, window
            else:
                print("Failed to get application window handle after opening")
        
        time.sleep(1)  # Wait before retry
    
    print("[FAILED] Failed to open application")
    return False, None


def step2_maximize_application(window: gw.Window) -> bool:
    """
    Step 2: Maximize the application.
    Also ensures the application is in the foreground.
    
    Args:
        window: Window object to maximize
    
    Returns:
        True if successfully maximized, False otherwise
    """
    print("="*30)
    print("Step 2: Maximizing application")
    

    # First bring to foreground
    if not window_helper.bring_to_foreground(window):
        print("Could not bring to foreground, attempting to continue...")
    
    # Attempt to maximize
    if window_helper.maximize_application(window):
        print("[SUCCESS] Maximize command sent")
        return True
    else:
        print("[FAILED] Initial maximize attempt failed")
        return False


def step3_verify_and_fix_state(window: gw.Window, corner_templates: Dict[str, Any], max_retries: int = 3) -> bool:
    """
    Step 3: Check if the application is open and maximised.
    
    Args:
        window: Window object to verify
        corner_templates: Dictionary with corner templates for visual verification
        max_retries: Maximum number of attempts for operations
    
    Returns:
        True if application is verified open and maximized, False otherwise
    """
    print("="*30)
    print("Step 3: Verifying application state")
    
    # Step 3.1: Visual check for open state
    print("Step 3.1/2/3: Visual verification of open state and maximized state")
    visual_open = image_helper.check_maximized_by_corners(corner_templates)
    if not visual_open: 
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            print("[FAILED] Visual open check failed")
            print("Retrying Step 2.")
            step2_maximize_application(window)
        return False
    else:
        print("[SUCCESS] Visual open check and maximized state passed")
        return True


def run_startup_sequence(app_name: str, app_path: str, process_name: str, corner_templates: Dict[str, Any], max_retries: int = 3) -> bool:
    """
    Execute the complete sequence following all specified steps.
    
    Args:
        app_name: The window title or partial title of the application
        app_path: Path to the application executable
        process_name: Name of the process to check (e.g., 'notepad.exe')
        corner_templates: Dictionary with corner templates for visual verification
        max_retries: Maximum number of attempts for operations
    
    Returns:
        True if all steps completed successfully, False otherwise
    """
    print("="*50)
    print("STARTING APPLICATION MANAGEMENT SEQUENCE")
    print("="*50)
    
    start_time = time.time()
    
    # Execute Step 1
    process_found, window = step1_ensure_application_open(app_name, app_path, process_name, max_retries)
    if not process_found or window is None:
        return False
    
    # Execute Step 2
    if not step2_maximize_application(window):
        print("Step 2 had issues, continuing to verification...")
    
    # Execute Step 3
    if not step3_verify_and_fix_state(window, corner_templates, max_retries):
        print("Sequence failed at Step 3")
        return False
    
    # Final verification
    print("="*30)
    print("Final verification...")
    
    # Ensure still in foreground
    if window and not window_helper.is_foreground(window):
        print("Bringing back to foreground...")
        window_helper.bring_to_foreground(window)
    
    elapsed_time = time.time() - start_time
    
    print("="*50)
    print("[SUCCESS] APPLICATION MANAGEMENT SEQUENCE COMPLETED")
    print(f"[SUCCESS] Total time: {elapsed_time:.2f} seconds")
    print("[SUCCESS] Application is: OPEN | FOREGROUND | MAXIMIZED")
    print("="*50)
    
    return True


def get_status_report(app_name: str, process_name: str, corner_templates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a status report of the current application state.
    
    Args:
        app_name: The window title or partial title of the application
        process_name: Name of the process to check (e.g., 'notepad.exe')
        corner_templates: Dictionary with corner templates for visual verification
    
    Returns:
        Dictionary containing current status information
    """
    is_open = window_helper.is_application_open(process_name)
    window = window_helper.get_window_handle(app_name) if is_open else None
    status = {
        'process_running': is_open,
        'window_exists': window is not None,
        'is_foreground': window_helper.is_foreground(window) if window else False,
        'is_maximized': image_helper.check_maximized_visually(corner_templates) if window else False
    }
    
    return status
