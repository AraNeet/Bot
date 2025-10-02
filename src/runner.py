"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import sys
from typing import Dict, Any, Optional
from . import parser
from . import startup
from . import image_helper




def initialize_system() -> Optional[Dict[str, Any]]:
    """
    Initialize the system with configuration.
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """
    # Load Config
    config = parser.load_and_validate_config("config.json")
    if not config:
        print("[FAILED] Could not load valid configuration")
        return None
    
    print("="*50)
    print("APPLICATION STARTUP")    
    return config


def prepare_corner_templates(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load and prepare corner templates for visual verification.
    
    Args:
        config: Configuration dictionary containing template paths
    
    Returns:
        Dictionary with loaded corner templates
    """
    print("Loading corner templates...")
    corner_templates: Dict[str, Any] = parser.load_corner_templates(config)
    
    # Display template loading status
    for corner_name, template in corner_templates.items():
        status = "[SUCCESS]" if template is not None else "[FAILED]"
        print(f"  {corner_name}: {status}")
    
    return corner_templates


def run_startup(config: Dict[str, Any]) -> bool:
    """
    Execute standard mode application startup sequence.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare corner templates
        corner_templates: Dict[str, Any] = prepare_corner_templates(config)
        
        # Run startup sequence
        success = startup.run_startup_sequence(
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
        
        return success
        
    except Exception as e:
        print(f"Error in standard mode execution: {e}")
        return False