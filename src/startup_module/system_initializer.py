"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import os
import re
from typing import Dict, Any, Optional, Tuple
import pygetwindow
from src.startup_module.helpers import computer_vision_utils
from src.startup_module.application_launcher import startup_sequence
from src.notification_module.error_notifier import notify_error
from dotenv import load_dotenv


def update_app_name_from_window(env_file_path: str = "bot.env") -> Tuple[bool, Optional[str]]:
    """
    Find the Crossroad application window and update the APP_NAME in bot.env
    with the current window title.
    
    The window title has a pattern like:
    "Crossroad 2025.6.0.509021444 [Crossroad DSHSTG] - <dynamic_part> - \\Remote"
    
    Where <dynamic_part> changes based on context (e.g., "BeIN Sports / Sports", 
    "Animal Planet / Adult", "ESPN / Sports").
    
    Args:
        env_file_path: Path to the .env file
        
    Returns:
        Tuple of (success: bool, new_app_name: Optional[str])
    """
    try:
        # Pattern to match the static parts of the window title
        # Matches: "Crossroad" at start and "\\Remote" at end
        window_pattern = re.compile(r'^Crossroad.*\\\\Remote$', re.IGNORECASE)
        
        # Get all windows and find the one matching our pattern
        all_windows = pygetwindow.getAllWindows()
        crossroad_window = None
        
        for window in all_windows:
            if window.title and window_pattern.match(window.title):
                crossroad_window = window
                break
        
        if not crossroad_window:
            print("[UPDATE APP NAME] Crossroad window not found")
            return False, None
        
        new_app_name = crossroad_window.title
        print(f"[UPDATE APP NAME] Found window: {new_app_name}")
        
        # Read current env file
        if not os.path.exists(env_file_path):
            print(f"[UPDATE APP NAME] Environment file not found: {env_file_path}")
            return False, None
        
        with open(env_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Update the APP_NAME line
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith('APP_NAME='):
                old_app_name = line.strip().split('=', 1)[1]
                if old_app_name != new_app_name:
                    new_lines.append(f'APP_NAME={new_app_name}\n')
                    print(f"[UPDATE APP NAME] Updated APP_NAME from: {old_app_name}")
                    print(f"[UPDATE APP NAME] Updated APP_NAME to:   {new_app_name}")
                    updated = True
                else:
                    new_lines.append(line)
                    print(f"[UPDATE APP NAME] APP_NAME already up to date")
            else:
                new_lines.append(line)
        
        # Write back to file if there was a change
        if updated:
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            # Reload the environment variable
            os.environ['APP_NAME'] = new_app_name
            print(f"[UPDATE APP NAME] Environment variable reloaded")
        
        return True, new_app_name
        
    except Exception as e:
        print(f"[UPDATE APP NAME ERROR] Failed to update app name: {e}")
        return False, None


def refresh_app_window_state(env_file_path: str = "bot.env") -> Tuple[bool, Optional[pygetwindow.Window]]:
    """
    Update the APP_NAME and return the current window handle.
    This should be called at the start of every objective to ensure
    the system has the correct window reference.
    
    Args:
        env_file_path: Path to the .env file
        
    Returns:
        Tuple of (success: bool, window: Optional[pygetwindow.Window])
    """
    print("\n" + "="*50)
    print("[REFRESH] Refreshing application window state...")
    print("="*50)
    
    # Update APP_NAME from current window title
    success, app_name = update_app_name_from_window(env_file_path)
    
    if not success or not app_name:
        print("[REFRESH ERROR] Failed to update APP_NAME")
        return False, None
    
    # Get the window handle with the updated name
    from src.startup_module.helpers.window_utils import get_window_handle
    window = get_window_handle(app_name)
    
    if window:
        print(f"[REFRESH SUCCESS] Window handle obtained for: {app_name}")
        return True, window
    else:
        print(f"[REFRESH ERROR] Could not get window handle for: {app_name}")
        return False, None


def load_config(env_file_path: str = "bot.env") -> Optional[Dict[str, Any]]:
    """
    Load basic application configuration from environment variables.
    
    Args:
        env_file_path: Path to .env file
    
    Returns:
        Basic configuration dictionary, or None if failed
    """
    try:
        # Load environment variables
        if os.path.exists(env_file_path):
            load_dotenv(env_file_path)
            print(f"Environment variables loaded from {env_file_path}")

        else:
            print(f"Environment file not found: {env_file_path}")

        if not all([os.getenv('APP_NAME'), os.getenv('APP_PATH'), os.getenv('PROCESS_NAME')]):
            print("Missing one or more required environment variables: APP_NAME, APP_PATH, or PROCESS_NAME")
            return None

        # Build basic config from environment
        config = {
            'app_name': os.getenv('APP_NAME'),
            'app_path': os.getenv('APP_PATH'),
            'process_name': os.getenv('PROCESS_NAME'),
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        }

        print("Configuration loaded successfully")
        return config

    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def initialize_system() -> bool:
    """
    Initialize the system with configuration.
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """
    
    # Step 0: Try to update APP_NAME from current window before loading config
    # This handles the case where the window is already open but with a different
    # dynamic part in the title (e.g., "ESPN / Sports" instead of "BeIN Sports / Sports")
    print("="*50)
    print("CHECKING FOR EXISTING CROSSROAD WINDOW")
    print("="*50)
    success, updated_app_name = update_app_name_from_window("bot.env")
    if success:
        print(f"[SUCCESS] APP_NAME synced with current window: {updated_app_name}")
    else:
        print("[INFO] No Crossroad window found yet, will use APP_NAME from bot.env")

    # Load basic config (will use updated APP_NAME if it was refreshed above)
    config = load_config("bot.env")

    if not config:
        error_msg = "Could not load basic configuration"
        print(f"[FAILED] {error_msg}")
        notify_error(error_msg, "runner.initialize_system")
        return False

    # Load templates
    corner_templates = computer_vision_utils.load_templates("config/template_paths.json")

    # If the templates aren't loaded the program closed
    if not corner_templates:
        error_msg = "Could not load corner templates"
        print(f"[FAILED] {error_msg}")
        notify_error(error_msg, "runner.initialize_system")
        return False

    config['corner_templates'] = corner_templates

    print("="*50)
    print("APPLICATION STARTUP")

    # Get corner templates from config (already loaded)
    corner_templates = config.get('corner_templates', {})

    # Run startup sequence
    success = startup_sequence(
        app_name=config['app_name'],
        app_path=config.get('app_path'),
        process_name=config.get('process_name'),
        corner_templates=corner_templates,
        max_retries=config.get('max_retries', 3)
    )

    # Display standard mode results
    print("\n" + "="*50)
    if success:
        print("[SUCCESS] SUCCESS: Application is now open, in foreground, and maximized!")
        return True

    else:
        error_msg = "Could not complete the startup sequence"
        print("[FAILED] FAILED: Could not complete the sequence.")
        notify_error(error_msg, "run_startup", 
                                    {"app_name": config.get("app_name", "unknown")})
        return False