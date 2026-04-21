"""
Startup process functions for application management.
Contains step-by-step functions for the application startup sequence.
"""

from re import L
import time
from typing import Tuple, Optional, Dict, Any
import pygetwindow
from pyotp import otp
from src.startup_module.helpers import computer_vision_utils, window_utils
from src.notification_module.error_notifier import notify_error
from src.startup_module.login_application import login_system, open_network_app


def ensure_application_open(app_name: str, app_path: str, process_name: str,login_app_name: str, app_open_path: str, 
                            username_citrix: str, password_citrix: str, otp_secret: str, login_templates: Dict[str, Any],
                            max_retries: int = 3) -> Tuple[bool, Optional[pygetwindow.Window]]:
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
    
    is_open = window_utils.is_application_open(process_name)
    if is_open:
        print("[SUCCESS] Application is already open")
        window = window_utils.get_window_handle(app_name)
        if window:
            print("[SUCCESS] Window handle obtained")
            return True, window
        # If we can't get the window handle, Application name is likely incorrect/ not matching
        else:
            print("Failed to get application window handle")
            return False, None
    else:
        print("Application is not open, attempting to open...")
        success = window_utils.open_application(app_path, app_open_path)
        if success:
            window = window_utils.get_window_handle(login_app_name)
            if window:
                print("[SUCCESS] Application successfully opened")
                success = login_system(username_citrix, password_citrix, otp_secret, login_templates)
                if not success:
                    return False, None
                success = open_network_app(login_templates)
                if not success:
                    return False, None
                return True, window
            else:
                print("Failed to get application window handle after opening")
                return False, None
        else:
            print("Failed to open application")
            return False, None

def maximize_application(window: pygetwindow.Window) -> bool:
    """
    Also ensures the application is in the foreground.
    
    Args:
        window: Window object to maximize
    
    Returns:
        True if successfully maximized, False otherwise
    """
    print("="*30)
    print("Step 2: Maximizing application")
    

    # Attempt to bring to foreground
    if not window_utils.window_focus(window):
        print("Could not bring to foreground, attempting to continue...")
    
    # Attempt to maximize
    if window_utils.maximize_application(window):
        print("[SUCCESS] Maximize command sent")
        return True
    else:
        print("[FAILED] Initial maximize attempt failed")
        notify_error("Could not maximize application", "startup.maximize_application", 
                                {"window_title": window.title})
        return False

def verify_window_state(window: pygetwindow.Window, corner_templates: Dict[str, Any], max_retries: int = 3) -> bool:
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
    visual_open = computer_vision_utils.check_maximized_by_corners(corner_templates)
    if not visual_open:
        print("[FAILED] Visual open check failed")
        print("Attempting to check if window is maximized and in foreground with alternative methods")
        time.sleep(.5)
        
        # If templates are not provided, System fallback to window state checks
        if not (window_utils.is_window_maximized(window) and window_utils.is_foreground(window)):
            print("Could not maximize application during verification")

            attempts = 0
            while attempts < max_retries:
                attempts += 1
                print(f"Failed alternative maximized check. Attempt {attempts}/{max_retries}")
                print("Retrying Step 2.")
                maximize_application(window)
                time.sleep(.5)

                if window_utils.is_window_maximized(window) and window_utils.is_foreground(window):
                    print("[SUCCESS] Application is maximized and in foreground after retry")
                    return True

            return False
        else:
            print("[SUCCESS] Application is maximized and in foreground by alternative check")
            return True
    else:
        print("[SUCCESS] Visual open check and maximized state passed")
        return True

def startup_sequence(app_name: str, app_path: str, process_name: str,
                    login_app_name: str, app_open_path: str, username_citrix: str, password_citrix: str, otp_secret: str,
                    corner_templates: Dict[str, Any], login_templates: Dict[str, Any], max_retries: int = 3) -> bool:
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
    print("STARTING APPLICATION STARTUP SEQUENCE")
    print("="*50)
    
    # Execute Step 1
    process_found, window = ensure_application_open(app_name, app_path, process_name, login_app_name, app_open_path, 
                                                    username_citrix, password_citrix, otp_secret, login_templates, max_retries)
    if not process_found or window is None:
        notify_error("Could not ensure application is open", "ensure_application_open", 
                                    {"app_name": app_name, "process_name": process_name})
        return False
    
    # Execute Step 2
    if not verify_window_state(window, corner_templates, max_retries):
        print("Sequence failed at Step 2")
        notify_error("Could not verify and fix application state", "verify_window_state", 
                                    {"app_name": app_name, "process_name": process_name})
        return False

    print("="*50)
    print("[SUCCESS] APPLICATION STARTUP SEQUENCE COMPLETED")
    print("[SUCCESS] Application is: OPEN | FOREGROUND | MAXIMIZED")
    print("="*50)
    
    return True
