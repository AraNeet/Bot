#!/usr/bin/env python3
"""
Page Object Loader Module

Loads page configuration files that define all UI regions, template paths,
confidence thresholds, and element locations for each Citrix page.

This centralizes all hardcoded coordinates so they can be updated in one place
when the Citrix UI layout changes.

Usage:
    from src.workflow_module.pages.page_loader import get_page, get_element, get_region

    # Load a page config
    page = get_page("search_page")

    # Get a specific element's config
    element = get_element("search_page", "advertiser_field")
    region = element["verification_region"]

    # Quick access to just a region tuple
    region = get_region("search_page", "advertiser_field", "verification_region")

    # Get a resolved template path
    template_path = get_template_path("search_page", "multi_network_icon")
"""

import json
import os
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

# ============================================================================
# MODULE STATE
# ============================================================================

_page_cache: Dict[str, Dict[str, Any]] = {}
_pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
_steps_base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "actions")


# ============================================================================
# CORE LOADING
# ============================================================================

def load_page(page_name: str, force_reload: bool = False) -> Dict[str, Any]:
    """
    Load a page configuration from JSON file.
    
    Args:
        page_name: Name of the page (e.g., "search_page", "multinetwork_page")
        force_reload: If True, reload from disk even if cached
        
    Returns:
        Page configuration dictionary
        
    Raises:
        FileNotFoundError: If page config file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if page_name in _page_cache and not force_reload:
        return _page_cache[page_name]
    
    config_path = os.path.join(_pages_dir, f"{page_name}.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Page config not found: {config_path}. "
            f"Available pages: {list_available_pages()}"
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validate basic structure
    if "elements" not in config:
        raise ValueError(f"Page config '{page_name}' missing 'elements' key")
    
    _page_cache[page_name] = config
    print(f"[PAGE_LOADER] Loaded page config: {page_name} ({len(config['elements'])} elements)")
    
    return config


def list_available_pages() -> List[str]:
    """List all available page config files."""
    pages = []
    for f in os.listdir(_pages_dir):
        if f.endswith('.json'):
            pages.append(f.replace('.json', ''))
    return pages


# ============================================================================
# ELEMENT ACCESS
# ============================================================================

def get_page(page_name: str) -> Dict[str, Any]:
    """
    Get the full page configuration.
    
    Args:
        page_name: Name of the page
        
    Returns:
        Full page config dictionary
    """
    return load_page(page_name)


def get_element(page_name: str, element_name: str) -> Dict[str, Any]:
    """
    Get a specific element's configuration from a page.
    
    Args:
        page_name: Name of the page (e.g., "search_page")
        element_name: Name of the element (e.g., "advertiser_field")
        
    Returns:
        Element configuration dictionary
        
    Raises:
        KeyError: If element doesn't exist on the page
    """
    page = load_page(page_name)
    elements = page.get("elements", {})
    
    if element_name not in elements:
        available = list(elements.keys())
        raise KeyError(
            f"Element '{element_name}' not found on page '{page_name}'. "
            f"Available elements: {available}"
        )
    
    return elements[element_name]


def get_region(page_name: str, element_name: str, region_key: str = "region") -> Tuple[int, int, int, int]:
    """
    Get a region tuple (x, y, width, height) for an element.
    
    Args:
        page_name: Name of the page
        element_name: Name of the element
        region_key: Key within the element config that holds the region
                    (e.g., "region", "verification_region", "search_region")
        
    Returns:
        Tuple of (x, y, width, height)
        
    Raises:
        KeyError: If element or region_key doesn't exist
    """
    element = get_element(page_name, element_name)
    
    if region_key not in element:
        available_keys = [k for k, v in element.items() if isinstance(v, list) and len(v) == 4]
        raise KeyError(
            f"Region key '{region_key}' not found in element '{element_name}'. "
            f"Available region keys: {available_keys}"
        )
    
    region = element[region_key]
    return tuple(region)


def get_page_markers(page_name: str) -> Dict[str, Any]:
    """
    Get the page markers used to verify the correct page is displayed.
    
    Args:
        page_name: Name of the page
        
    Returns:
        Dictionary with 'header_texts' and 'header_region'
    """
    page = load_page(page_name)
    markers = page.get("page_markers", {})
    
    if not markers:
        raise ValueError(f"Page '{page_name}' has no page_markers defined")
    
    return markers


def get_defaults(page_name: str) -> Dict[str, Any]:
    """
    Get the default values for a page (confidence thresholds, spacing, etc).
    
    Args:
        page_name: Name of the page
        
    Returns:
        Defaults dictionary
    """
    page = load_page(page_name)
    return page.get("defaults", {})


# ============================================================================
# TEMPLATE PATH RESOLUTION
# ============================================================================

def get_template_path(page_name: str, element_name: str, 
                      template_key: str = "template") -> str:
    """
    Get the fully resolved filesystem path for a template image.
    
    Template paths in the config are relative to the handler's step directory.
    This function resolves them to absolute paths.
    
    Args:
        page_name: Name of the page
        element_name: Name of the element
        template_key: Key in element config for the template filename
                      (e.g., "template", "close_template", "loading_template")
        
    Returns:
        Absolute path to the template image file
        
    Raises:
        KeyError: If template or template_dir not found in element config
        FileNotFoundError: If the resolved template file doesn't exist
    """
    element = get_element(page_name, element_name)
    
    # Get template filename
    template_filename = element.get(template_key)
    if not template_filename:
        raise KeyError(
            f"Template key '{template_key}' not found in element '{element_name}' "
            f"on page '{page_name}'"
        )
    
    # Get the directory key (convention: template_key + "_dir", or "template_dir")
    dir_key = template_key + "_dir"
    if dir_key not in element:
        dir_key = "template_dir"
    
    template_dir = element.get(dir_key, "")
    
    # Resolve the full path
    full_path = os.path.normpath(
        os.path.join(_steps_base_dir, template_dir, template_filename)
    )
    
    if not os.path.exists(full_path):
        print(f"[PAGE_LOADER WARNING] Template file not found: {full_path}")
    
    return full_path


def get_confidence(page_name: str, element_name: str, 
                   confidence_key: str = "confidence") -> float:
    """
    Get the confidence threshold for an element's template matching.
    
    Falls back to the page's default confidence if not set on the element.
    
    Args:
        page_name: Name of the page
        element_name: Name of the element
        confidence_key: Key in element config for confidence value
        
    Returns:
        Confidence threshold (0.0 to 1.0)
    """
    element = get_element(page_name, element_name)
    
    # Try element-level confidence first
    if confidence_key in element:
        return element[confidence_key]
    
    # Fall back to page defaults
    defaults = get_defaults(page_name)
    return defaults.get("confidence_threshold", 0.8)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_field_config(page_name: str, element_name: str) -> Dict[str, Any]:
    """
    Get all config needed for a text field interaction.
    
    Returns a dict with:
        - field_label: str or list of str
        - search_region: tuple
        - verification_region: tuple
        - field_spacing: int
        
    Args:
        page_name: Name of the page
        element_name: Name of the field element
        
    Returns:
        Field configuration dictionary
    """
    element = get_element(page_name, element_name)
    defaults = get_defaults(page_name)
    
    return {
        "field_label": element.get("field_label", element_name),
        "search_region": tuple(element.get("search_region", defaults.get("search_region", [0, 0, 1920, 1080]))),
        "verification_region": tuple(element.get("verification_region", [0, 0, 100, 50])),
        "field_spacing": element.get("field_spacing", defaults.get("field_spacing", 15)),
    }


def reload_all() -> None:
    """Clear the page cache, forcing reload from disk on next access."""
    _page_cache.clear()
    print("[PAGE_LOADER] Cache cleared - pages will reload on next access")
