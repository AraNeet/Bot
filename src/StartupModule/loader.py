"""
Parser functions for configuration loading and processing.
Contains config loading logic and other parsing utilities.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from . import image_helper


def load_config(config_file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_file_path: Path to the configuration JSON file
    
    Returns:
        Dict[str, Any]: Configuration dictionary from file, or None if file doesn't exist
    """
    if not os.path.exists(config_file_path):
        print(f"Config file not found: {config_file_path}")
        return None
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"Configuration loaded from {config_file_path}")
            return config
    except Exception as e:
        print(f"Error loading config file {config_file_path}: {e}")
        return None

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration dictionary for required fields.
    
    Args:
        config: Configuration dictionary to validate
    
    Returns:
        True if configuration is valid, False otherwise
    """
    required_fields = ['app_name', 'app_path', 'process_name']
    
    for field in required_fields:
        if field not in config:
            print(f"Missing required configuration field: {field}")
            return False
        if not config[field]:
            print(f"Empty value for required configuration field: {field}")
            return False
    return True

def load_corner_templates(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load corner templates from configuration into a dictionary.
    
    Args:
        config: Configuration dictionary containing templates section
    
    Returns:
        Dictionary with loaded corner templates (numpy arrays or None for failed loads)
    """
    corner_templates = {}
    
    # Get templates section from config
    templates = config.get('templates', {})
    
    if not templates:
        print("No templates section found in configuration")
        return None
    
    # Load each template
    for corner_name, template_path in templates.items():
        print(f"Loading {corner_name} template from: {template_path}")
        template = image_helper.load_template(template_path, corner_name)
        corner_templates[corner_name] = template
    
    return corner_templates


def load_and_validate_config(config_file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load configuration from file and validate it.
    
    Args:
        config_file_path: Path to the configuration JSON file
    
    Returns:
        Valid configuration dictionary, or None if loading/validation failed
    """
    try:
        config = load_config(config_file_path)
        
        if config is None:
            return None
            
        if not validate_config(config):
            print("Configuration validation failed")
            return None
        
        return config
    except Exception as e:
        print(f"Error loading and validating config: {e}")
        return None
