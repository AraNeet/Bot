#!/usr/bin/env python3
"""
Application Manager Bot - Main Entry Point

This is the primary entry point for the Application Manager Bot system, which provides
automated application window management with corner-based template matching.

The system operates in standard mode: Basic application startup sequence (open, maximize, verify)

Architecture Overview:
- main.py: Entry point
- manager.py: System initialization and high-level management
- startup.py: Application startup sequence functions
- parser.py: Configuration loading and parsing
- window_helper.py: Window management functions
- image_helper.py: Image processing and template matching functions

Usage Examples:
    # Standard mode with defaults
    main()
    
    # Standard mode with custom config
    config = {"app_name": "Calculator", "app_path": "calc.exe"}
    main(config_json=config)

Author: Application Manager Bot System
Version: 3.0 - Refactored to modular architecture
"""

from typing import Dict, Any, Optional
import manager


def main(config_json: Optional[Dict[str, Any]] = None):
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
    
    Args:
        config_json: Optional configuration dictionary to override defaults
        
    Returns:
        None (exits with status code 0 for success, 1 for failure)
        
    Raises:
        SystemExit: With appropriate exit code based on execution results
        KeyboardInterrupt: Gracefully handled for user cancellation
    """
    try:
        # Initialize system with configuration
        config = manager.initialize_system(config_json=config_json)
        if not config:
            manager.handle_system_exit(False, {})
            return
        
        # Execute standard mode
        success = manager.run_standard_mode(config)
        
        # Exit with appropriate status code
        manager.handle_system_exit(success, config)
        
    except KeyboardInterrupt:
        # Handle graceful shutdown on user interrupt (Ctrl+C)
        manager.handle_keyboard_interrupt()
    except Exception as e:
        # Handle any unexpected errors
        config = config if 'config' in locals() else None
        manager.handle_unexpected_error(e, config)


# Entry point for direct script execution
if __name__ == "__main__":
    # When run directly, execute with default configuration
    main()