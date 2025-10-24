#!/usr/bin/env python3
"""
Objectives Parser Module

This module handles parsing of JSON objectives files and validates them against
supported objective types. It separates supported from unsupported objectives.

TERMINOLOGY:
- Objective Type: What you want to accomplish (e.g., "make_file", "send_email")
- Values: User-provided data for an objective (e.g., {"file_name": "test.txt"})
- Instructions: Action steps the bot performs (e.g., "open_menu", "type_text")
"""

import json
import os
from enum import Enum
from typing import Dict, Any, Tuple
from src.parser_module.objectives_parser import parse_objectives

def process_objectives_file(objectives_file_path: str) -> Tuple[bool, Any]:
    """
    Complete processing pipeline for an objectives file.
    
    This function uses the simplified parser that:
    1. Loads configuration
    2. Reads objectives file
    3. Checks requirements
    4. Returns supported objectives
    
    Args:
        objectives_file_path: Path to the JSON objectives file
        
    Returns:
        Tuple of (success: bool, supported_objectives or error_message)
    """
    # Parse objectives using simplified parser
    success, supported_objectives = parse_objectives(objectives_file_path)
    
    if not success:
        return False, supported_objectives
    
    # Return results for workflow module
    results = {
        "supported_objectives": supported_objectives,
        "unsupported_objectives": []  # Simplified parser doesn't track unsupported
    }
    
    return True, results