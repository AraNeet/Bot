#!/usr/bin/env python3
"""
Main entry point for the Application Manager Bot system.
Demonstrates how to use the bot and orchestrator together.
"""

import sys
import os
from pathlib import Path
import argparse
import json
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bot import ApplicationManagerBot
from orchestrator import ApplicationOrchestrator
from config import setup_logging
from utils import WindowHelper


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_file: Path to configuration file
    
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


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Application Manager Bot - Automated window management'
    )
    
    parser.add_argument(
        '--app-name',
        type=str,
        help='Name of the application window'
    )
    
    parser.add_argument(
        '--app-path',
        type=str,
        help='Path to the application executable'
    )
    
    parser.add_argument(
        '--icon-template',
        type=str,
        help='Path to icon template image for visual verification'
    )
    
    parser.add_argument(
        '--process-name',
        type=str,
        help='Process name to monitor (e.g., notepad.exe)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=5,
        help='Maximum number of retry attempts'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--list-windows',
        action='store_true',
        help='List all available windows and exit'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--no-log-file',
        action='store_true',
        help='Disable logging to file'
    )
    
    return parser.parse_args()


def list_available_windows():
    """List all available windows for debugging."""
    print("\n" + "="*50)
    print("Available Windows:")
    print("="*50)
    
    window_helper = WindowHelper()
    windows = window_helper.list_all_windows()
    
    if windows:
        for i, title in enumerate(windows, 1):
            if title.strip():  # Only show windows with titles
                print(f"{i}. {title}")
    else:
        print("No windows found")
    
    print("="*50 + "\n")


def main():
    """
    Main function to run the Application Manager Bot system.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Handle window listing
    if args.list_windows:
        list_available_windows()
        sys.exit(0)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.app_name:
        config['app_name'] = args.app_name
    if args.app_path:
        config['app_path'] = args.app_path
    if args.icon_template:
        config['icon_template_path'] = args.icon_template
    if args.process_name:
        config['process_name'] = args.process_name
    if args.max_retries:
        config['max_retries'] = args.max_retries
    
    # Setup logging
    import logging
    log_level = logging.DEBUG if args.verbose else getattr(logging, config.get('log_level', 'INFO'))
    log_to_file = not args.no_log_file and config.get('log_to_file', True)
    
    log_file = setup_logging(
        log_level=log_level,
        log_to_file=log_to_file
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
        success = orchestrator.run_complete_sequence()
        
        # Display results
        print("\n" + "="*50)
        if success:
            print("✓ SUCCESS: Application is now open, in foreground, and maximized!")
            
            # Get and display status report
            status = orchestrator.get_status_report()
            print("\nStatus Report:")
            print("-" * 30)
            for key, value in status.items():
                status_str = "✓" if value else "✗" if value is False else "N/A"
                print(f"  {key.replace('_', ' ').title()}: {status_str}")
        else:
            print("✗ FAILED: Could not complete the sequence.")
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
        print(f"\n✗ Unexpected error: {e}")
        print("Please check the logs for details.")
        
        if log_file:
            print(f"\nLog file: {log_file}")
        
        sys.exit(1)


if __name__ == "__main__":
    main()