#!/usr/bin/env python3
"""
Date Utilities Module

This module provides utilities for date processing:
- Date normalization for flexible matching
"""

import re

def normalize_date(date_str: str) -> str:
    """
    Remove leading zeros from date components for flexible date matching.
    
    Example: 09/16/2025 → 9/16/2025
    
    Args:
        date_str: Date string to normalize
        
    Returns:
        Normalized date string with leading zeros removed
    """
    # Remove leading zeros from each numeric component
    normalized = re.sub(r'\b0+(\d)', r'\1', date_str)
    return normalized.lower()

