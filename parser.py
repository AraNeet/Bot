"""
Parser functions for configuration loading and processing.
Contains config loading logic and other parsing utilities.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import image_helper


def load_config(config_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load and merge configuration from multiple sources with smart defaults.
    
    Configuration Priority (highest to lowest):
    1. Provided config_json parameter
    2. config.json file (if exists)
    3. Built-in defaults
    
    Args:
        config_json: Optional configuration dictionary to override defaults
    
    Returns:
        Dict[str, Any]: Merged configuration dictionary with all required settings
        
    Configuration Keys:
        app_name: Window title or partial title to search for
        icon_template_path: Legacy icon template (optional, for backward compatibility)
        app_path: Full path to application executable
        process_name: Process name for detection (e.g., 'notepad.exe')
        max_retries: Maximum retry attempts for operations
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_to_file: Whether to write logs to file
        top_left_template_path: Template for top-left corner detection
        top_right_template_path: Template for top-right corner detection  
        bottom_right_template_path: Template for bottom-right corner detection
    """
    # Default configuration with corner-based template matching support
    # Resolve template paths relative to the main.py file location
    main_dir = Path(__file__).parent
    default_config = {
        'app_name': "Notepad",                                      # Target application name
        'app_path': "notepad.exe",                                 # Application executable path
        'process_name': "notepad.exe",                             # Process name for detection
        'max_retries': 5,                                          # Maximum retry attempts
        'log_level': "INFO",                                       # Logging verbosity
        'log_to_file': True,                                       # Enable file logging
        'top_left_template_path': str(main_dir / "assets" / "Icon.png"),       # Notepad icon template
        'top_right_template_path': str(main_dir / "assets" / "close_x.png"),           # Close button template
        'bottom_right_template_path': str(main_dir / "assets" / "bottom_right_element.png")  # Bottom corner template
    }
    
    if config_json is not None:
        # Override defaults with provided configuration
        default_config.update(config_json)
        print("Configuration loaded from provided JSON dictionary")
    else:
        # Attempt to load from config.json file
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                    # Resolve template paths relative to main.py directory if they are relative
                    for key in ['top_left_template_path', 'top_right_template_path', 'bottom_right_template_path', 'icon_template_path']:
                        if key in loaded_config and loaded_config[key]:
                            config_path = Path(loaded_config[key])
                            # If path is relative, make it relative to main.py directory
                            if not config_path.is_absolute():
                                absolute_path = main_dir / config_path
                                loaded_config[key] = str(absolute_path)
                                print(f"Resolved {key}: {loaded_config[key]}")
                    
                    default_config.update(loaded_config)
                    print(f"Configuration loaded from {config_file}")
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                print("Using default configuration")
        else:
            # Create example config file if it doesn't exist
            try:
                # Ensure config directory exists
                os.makedirs("config", exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                    print(f"Default configuration saved to {config_file}")
            except Exception as e:
                print(f"Could not save default config: {e}")
    
    return default_config


def load_corner_templates(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load corner templates based on configuration paths.
    
    Args:
        config: Configuration dictionary containing template paths
    
    Returns:
        Dictionary with loaded corner templates
    """
    corner_templates = {}
    corner_templates['top_left'] = image_helper.load_template_safely(
        config.get('top_left_template_path'), "top-left"
    )
    corner_templates['top_right'] = image_helper.load_template_safely(
        config.get('top_right_template_path'), "top-right"
    )
    corner_templates['bottom_right'] = image_helper.load_template_safely(
        config.get('bottom_right_template_path'), "bottom-right"
    )
    
    return corner_templates


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration dictionary for required fields and valid values.
    
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
    
    # Validate log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if config.get('log_level') not in valid_log_levels:
        print(f"Invalid log level: {config.get('log_level')}. Using INFO.")
        config['log_level'] = 'INFO'
    
    # Validate max_retries
    if not isinstance(config.get('max_retries'), int) or config.get('max_retries') < 1:
        print(f"Invalid max_retries: {config.get('max_retries')}. Using 5.")
        config['max_retries'] = 5
    
    return True


def parse_template_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and resolve template paths in the configuration.
    
    Args:
        config: Configuration dictionary with template paths
    
    Returns:
        Updated configuration dictionary with resolved paths
    """
    main_dir = Path(__file__).parent
    
    for key in ['top_left_template_path', 'top_right_template_path', 'bottom_right_template_path', 'icon_template_path']:
        if key in config and config[key]:
            config_path = Path(config[key])
            # If path is relative, make it relative to main directory
            if not config_path.is_absolute():
                absolute_path = main_dir / config_path
                config[key] = str(absolute_path)
                print(f"Resolved {key}: {config[key]}")
    
    return config


def create_default_config_file(file_path: str = "config.json") -> bool:
    """
    Create a default configuration file.
    
    Args:
        file_path: Path where to create the config file
    
    Returns:
        True if successfully created, False otherwise
    """
    try:
        default_config = load_config()
        
        # Ensure directory exists
        config_dir = Path(file_path).parent
        os.makedirs(config_dir, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        
        print(f"Default configuration saved to {file_path}")
        return True
    except Exception as e:
        print(f"Could not save default config: {e}")
        return False


def load_and_validate_config(config_json: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Load configuration and validate it.
    
    Args:
        config_json: Optional configuration dictionary to override defaults
    
    Returns:
        Valid configuration dictionary, or None if validation failed
    """
    try:
        config = load_config(config_json)
        
        if not validate_config(config):
            print("Configuration validation failed")
            return None
        
        config = parse_template_paths(config)
        
        return config
    except Exception as e:
        print(f"Error loading and validating config: {e}")
        return None
