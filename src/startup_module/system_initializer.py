"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import sys
from typing import Dict, Any, Optional, Tuple
from . import application_launcher
from .helpers import image_helper
from src.notification_module import notify_error
from . import config_loader




def initialize_system() -> Optional[Dict[str, Any]]:
    """
    Initialize the system with configuration.
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """

    # Load basic config
    config = config_loader.load_config("bot.env")

    if not config:
        error_msg = "Could not load basic configuration"
        print(f"[FAILED] {error_msg}")
        notify_error(error_msg, "runner.initialize_system")
        return None

    # Load templates
    corner_templates = image_helper.load_templates("template.json")

    # Still deciding between failing hard here or just warning.
    if not corner_templates:
        error_msg = "Could not load corner templates"
        print(f"[FAILED] {error_msg}")
        notify_error(error_msg, "runner.initialize_system")
        return None

    config['corner_templates'] = corner_templates

    print("="*50)
    print("APPLICATION STARTUP")

    return config

def run_startup(config: Dict[str, Any]) -> bool:
    """
    Execute standard mode application startup sequence.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get corner templates from config (already loaded)
        corner_templates = config.get('corner_templates', {})

        # Run startup sequence
        success = application_launcher.run_startup_sequence(
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

        else:
            error_msg = "Could not complete the startup sequence"
            print("[FAILED] FAILED: Could not complete the sequence.")
            notify_error(error_msg, "runner.run_startup", 
                                        {"app_name": config.get("app_name", "unknown")})

        print("="*50 + "\n")

        return success

    except Exception as e:
        error_msg = f"Error in standard mode execution: {e}"
        print(error_msg)
        notify_error(error_msg, "runner.run_startup")
        return False, None