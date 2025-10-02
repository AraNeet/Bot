"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import sys
from typing import Dict, Any, Optional
from . import loader
from . import startup
import pygetwindow
from typing import Tuple, Optional, Dict, Any




def initialize_system() -> Optional[Dict[str, Any]]:
    """
    Initialize the system with configuration.
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """
    # Load Config
    config = loader.load_and_validate_config("config.json")
    if not config:
        print("[FAILED] Could not load valid configuration")
        return None
    
    print("="*50)
    print("APPLICATION STARTUP")    
    return config

def run_startup(config: Dict[str, Any]) -> Tuple[bool, Optional[pygetwindow.Window]]:
    """
    Execute standard mode application startup sequence.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare corner templates
        corner_templates: Dict[str, Any] = loader.load_corner_templates(config)
        if corner_templates is None:
            print("[FAILED] Could not load corner templates")
        else:
            print("Corner templates loaded successfully.")

        # Run startup sequence
        success, window = startup.run_startup_sequence(
            app_name=config['app_name'],
            app_path=config.get('app_path'),
            process_name=config.get('process_name'),
            corner_templates=corner_templates,
            max_retries=config.get('max_retries', 5)
        )
        
        # Display standard mode results
        print("\n" + "="*50)
        if success:
            print("[SUCCESS] SUCCESS: Application is now open, in foreground, and maximized!")
        else:
            print("[FAILED] FAILED: Could not complete the sequence.")
        
        print("="*50 + "\n")
        
        return success, window
        
    except Exception as e:
        print(f"Error in standard mode execution: {e}")
        return False, None