"""
Basic configuration loader.
Handles only core app configuration from environment variables.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from src.NotificationModule import email_notifier


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
