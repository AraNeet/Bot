"""
Manager functions for system initialization and management logic.
Contains high-level orchestration functions that coordinate between different components.
"""

import os
from typing import Dict, Any, Optional, Tuple
from .helpers import image_helper
from src.notification_module import notify_error
from dotenv import load_dotenv


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


def initialize_system() -> Optional[Dict[str, Any]]:
    """
    Initialize the system with configuration.
    
    Returns:
        Configuration dictionary if successful, None otherwise
    """

    # Load basic config
    config = load_config("bot.env")

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