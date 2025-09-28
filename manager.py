"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import sys
from typing import Dict, Any, Optional
import parser
import startup
import image_helper




def initialize_system(config_json: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Initialize the system with configuration.
    
    Args:
        config_json: Optional configuration dictionary to override defaults
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """
    # Step 1: Load and validate configuration
    config = parser.load_and_validate_config(config_json=config_json)
    if not config:
        print("[FAILED] Could not load valid configuration")
        return None
    
    # Step 2: Display configuration for debugging and audit trail
    print("="*50)
    print("APPLICATION MANAGER BOT SYSTEM STARTUP")
    print("="*50)
    print("Configuration:")
    print("-" * 30)
    for key, value in config.items():
        if key not in ['log_level', 'log_to_file']:  # Skip logging config to avoid redundancy
            print(f"  {key}: {value}")
    print("-" * 30)
    
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
    corner_templates = parser.load_corner_templates(config)
    
    # Display template loading status
    for corner_name, template in corner_templates.items():
        status = "[SUCCESS]" if template is not None else "[FAILED]"
        print(f"  {corner_name}: {status}")
    
    return corner_templates


def run_standard_mode(config: Dict[str, Any]) -> bool:
    """
    Execute standard mode application startup sequence.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare corner templates
        corner_templates = prepare_corner_templates(config)
        
        # Run startup sequence
        print("Standard mode - running startup sequence...")
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
            
            # Display application state verification
            status = startup.get_status_report(
                config['app_name'],
                config.get('process_name'),
                corner_templates
            )
            print("\nStatus Report:")
            print("-" * 30)
            for key, value in status.items():
                status_str = "[SUCCESS]" if value else "[FAILED]" if value is False else "N/A"
                print(f"  {key.replace('_', ' ').title()}: {status_str}")
        else:
            print("[FAILED] FAILED: Could not complete the sequence.")
        
        print("="*50 + "\n")
        
        return success
        
    except Exception as e:
        print(f"Error in standard mode execution: {e}")
        return False


def get_application_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current application status.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Dictionary containing current application status
    """
    corner_templates = prepare_corner_templates(config)
    
    return startup.get_status_report(
        config['app_name'],
        config.get('process_name'),
        corner_templates
    )


def handle_system_exit(success: bool, config: Dict[str, Any]):
    """
    Handle system exit with appropriate status code and cleanup.
    
    Args:
        success: Whether the operation was successful
        config: Configuration dictionary
    """
    print(f"System execution completed with {'success' if success else 'failure'}")
    
    sys.exit(0 if success else 1)


def handle_keyboard_interrupt():
    """
    Handle graceful shutdown on user interrupt (Ctrl+C).
    """
    print("Operation cancelled by user")
    print("\n\nOperation cancelled by user.")
    sys.exit(0)


def handle_unexpected_error(e: Exception, config: Optional[Dict[str, Any]] = None):
    """
    Handle any unexpected errors.
    
    Args:
        e: The exception that occurred
        config: Optional configuration dictionary
    """
    print(f"\n[FAILED] Unexpected error: {e}")
    
    sys.exit(1)
