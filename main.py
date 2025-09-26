#!/usr/bin/env python3
"""
Main entry point for the Application Manager Bot system.
Ultra-simplified interface - configure only via JSON dictionary or config.json file.

Usage:
    # Run with defaults from config.json
    main()
    
    # Run with JSON configuration dictionary
    config = {"app_name": "Calculator", "app_path": "calc.exe", "max_retries": 3}
    main(config_json=config)
"""

import sys
import os
from pathlib import Path
import json
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bot import ApplicationManagerBot
from orchestrator import ApplicationOrchestrator
from config import setup_logging
from utils import WindowHelper


def load_config(config_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON dictionary or default to config.json file.
    
    Args:
        config_json: Configuration dictionary (if None, loads from config.json)
    
    Returns:
        Configuration dictionary
    """
    default_config = {
        'app_name': "Notepad",
        'icon_template_path': None,
        'app_path': "notepad.exe",
        'process_name': "notepad.exe",
        'max_retries': 5,
        'log_level': "INFO",
        'log_to_file': True
    }
    
    if config_json is not None:
        # Use provided JSON configuration
        default_config.update(config_json)
        print("Configuration loaded from provided JSON dictionary")
    else:
        # Load from config.json file
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
                    print(f"Configuration loaded from {config_file}")
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                print("Using default configuration")
        else:
            # Save default config as example
            try:
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                    print(f"Default configuration saved to {config_file}")
            except Exception as e:
                print(f"Could not save default config: {e}")
    
    return default_config



def main(config_json: Optional[Dict[str, Any]] = None):
    """
    Main function to run the Application Manager Bot system.
    
    Args:
        config_json: Configuration dictionary (if None, loads from config.json)
    """
    # Load configuration 
    config = load_config(config_json=config_json)
    
    # Setup logging
    import logging
    log_level_obj = getattr(logging, config.get('log_level', 'INFO'))
    log_to_file_setting = config.get('log_to_file', True)
    
    log_file = setup_logging(
        log_level=log_level_obj,
        log_to_file=log_to_file_setting
    )
    
    logger = logging.getLogger(__name__)
    
    # Print configuration
    logger.info("Configuration:")
    logger.info("-" * 30)
    for key, value in config.items():
        if key not in ['log_level', 'log_to_file']:
            logger.info(f"  {key}: {value}")
    logger.info("-" * 30)
    
    try:
        # Initialize the bot
        logger.info("Initializing Application Manager Bot...")
        bot = ApplicationManagerBot(
            app_name=config['app_name'],
            icon_template_path=config.get('icon_template_path'),
            app_path=config.get('app_path'),
            process_name=config.get('process_name'),
            max_retries=config.get('max_retries', 5)
        )
        
        # Create orchestrator
        logger.info("Creating orchestrator...")
        orchestrator = ApplicationOrchestrator(bot)
        
        # Run the complete sequence
        logger.info("Starting automated sequence...")
        success = orchestrator.run_startup_sequence()
        
        # Display results
        print("\n" + "="*50)
        if success:
            print("[SUCCESS] SUCCESS: Application is now open, in foreground, and maximized!")
            
            # Get and display status report
            status = orchestrator.get_status_report()
            print("\nStatus Report:")
            print("-" * 30)
            for key, value in status.items():
                status_str = "[SUCCESS]" if value else "[FAILED]" if value is False else "N/A"
                print(f"  {key.replace('_', ' ').title()}: {status_str}")
        else:
            print("[FAILED] FAILED: Could not complete the sequence.")
            print("Please check the logs for details.")
            
            if log_file:
                print(f"\nLog file: {log_file}")
        
        print("="*50 + "\n")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n[FAILED] Unexpected error: {e}")
        print("Please check the logs for details.")
        
        if log_file:
            print(f"\nLog file: {log_file}")
        
        sys.exit(1)


if __name__ == "__main__":
    # When running as script, use defaults from config file
    main()