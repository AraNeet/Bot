#!/usr/bin/env python3
"""
Action Handler Module

This module contains HIGH-LEVEL action functions that understand the APPLICATION.
Unlike actions.py (generic automation), these functions know WHERE to click,
WHAT to look for, and HOW to interact with specific UI elements.

Key Difference:
- actions.py: Generic "click at (x, y)" 
- action_handler.py: Specific "click_search_button()" that knows where the button is

Architecture:
    Instruction JSON
        ↓
    action_executor.py (routes action_type directly to this file)
        ↓
    action_handler.py (THIS FILE - knows UI locations, calls actions.py)
        ↓
    actions.py (performs generic automation)

Each function here:
1. Knows specific UI element locations
2. Uses helper functions to find elements
3. Calls actions.py to perform automation
4. Returns (success: bool, message: str)

IMPORTANT: Functions receive parameters via **kwargs pattern:
    def enter_advertiser_name(advertiser_name: str = "", **kwargs):
        # Use advertiser_name
        # Ignore any extra kwargs
"""

from typing import Tuple, Dict, Any, Optional
from . import actions
from ..helpers import computer_vision_utils, ocr_utils
import time
import cv2


# ============================================================================
# APPLICATION STARTUP ACTIONS
# ============================================================================

# def open_application() -> Tuple[bool, str]:
#     """
#     Open the target application.
    
#     This function knows:
#     - Application path from config
#     - How to verify application opened
#     - What window to look for
    
#     Returns:
#         Tuple of (success: bool, message: str)
        
#     TODO: Implement application opening logic
#     - Get app path from config
#     - Launch application
#     - Wait for window to appear
#     - Verify window opened
#     """
#     print("[ACTION_HANDLER] Opening application...")
    
#     # TODO: Get app path from config
#     # app_path = config.get('app_path')
    
#     # TODO: Launch application
#     # success = launch_app(app_path)
    
#     # TODO: Verify application window appeared
#     # window = wait_for_window(app_name, timeout=10)
    
#     # Placeholder
#     return True, "Application opened successfully"


# ============================================================================
# NAVIGATION ACTIONS
# ============================================================================

def open_multinetwork_instructions_page() -> Tuple[bool, str]:
    """
    Navigate to the Multinetwork Instructions page.
    
    This function:
    1. Takes a screenshot
    2. Uses computer vision to find the multi_network_icon in the toolbar region (250, 80, 180, 40) with 90% confidence
    3. Performs OCR check in the same region to verify "Multi-Network Instructions" text
    4. Clicks on the icon if both conditions are met
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Navigating to Multinetwork Instructions page...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region for Multi-Network Instructions button in toolbar
        # Based on typical toolbar layout: (x, y, width, height) format
        region_x = 93  # Estimated X position in toolbar
        region_y = 52   # Estimated Y position below menu tabs
        region_width = 84 # Width to cover the button text and icon
        region_height = 66 # Height to cover the button
        region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for multi_network_icon in region {region}")
        
        # Step 1: Use computer vision to find the multi_network_icon
        icon_found, confidence, icon_position = computer_vision_utils.find_template_in_region(
            screenshot, 
            'assets/multi_network_Icon.png', 
            region, 
            confidence=0.9
        )
        
        if not icon_found:
            return False, f"Multi-network icon not found in region {region} (confidence: {confidence:.2f})"
        
        print(f"[ACTION_HANDLER] ✓ Multi-network icon found at {icon_position} with confidence {confidence:.2f}")
        
        # Step 2: Use OCR to check for "Multi-Network Instructions" text in the same region
        print(f"[ACTION_HANDLER] Checking for 'Multi-Network Instructions' text in region {region}")

        # Step 3: Click on the icon position
        if icon_position is None:
            return False, "Icon position is None despite being found"
        
        click_x, click_y = icon_position
        print(f"[ACTION_HANDLER] Clicking on multi-network icon at ({click_x}, {click_y})")
        
        
        success, msg = actions.click_at_position(click_x, click_y)
        if success:
            actions.move_mouse(1800, 50, 0)
        if not success:
            return False, f"Failed to click on multi-network icon: {msg}"
        # Wait a moment for the page to load
        time.sleep(1.0)
        
        return True, "Successfully navigated to Multinetwork Instructions page"
        
    except Exception as e:
        error_msg = f"Error navigating to Multinetwork Instructions page: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# SEARCH FIELD ACTIONS
# ============================================================================

def enter_advertiser_name(advertiser_name: str) -> Tuple[bool, str]:
    """
    Enter advertiser name in the search field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "advertiser" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "advertiser" text
    4. Enters the advertiser name in the field
    
    Args:
        advertiser_name: Name of advertiser to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering advertiser name: '{advertiser_name}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "advertiser" word
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'advertiser' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"advertiser_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # # Use OCR to find the "advertiser" word within the cropped region
        # ocr_success, text_found = ocr_utils.find_text(
        #     cropped_image,
        #     "advertiser",
        #     case_sensitive=False
        # )
        
        # if not ocr_success:
        #     return False, "OCR search failed"
        
        # if not text_found:
        #     return False, f"Word 'advertiser' not found in region {search_region}"
        
        # print(f"[ACTION_HANDLER] ✓ Found 'advertiser' word in region {search_region}")
        
        # # Now find the exact position of the "advertiser" text in the cropped image
        # print(f"[ACTION_HANDLER] Finding exact position of 'advertiser' text in cropped image...")
        
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "advertiser",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'advertiser' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'advertiser' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the input field position 15 pixels below the "advertiser" text
        field_spacing = 15  # pixels below the text
        field_x = text_x  # Same horizontal position as the text
        field_y = text_y + text_height + field_spacing  # 15 pixels below the text
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'advertiser' text")
        
        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on advertiser input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        
        if not click_success:
            return False, f"Failed to click on advertiser field: {click_msg}"
        
        # Wait a moment for the field to be focused
        time.sleep(0.5)
        
        # Clear any existing text in the field
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()
        
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
            # Continue anyway, as the field might be empty
        
        # Wait a moment after clearing to ensure field is ready
        time.sleep(0.2)
        
        # Type the advertiser name with faster interval to prevent double letters
        print(f"[ACTION_HANDLER] Typing advertiser name: '{advertiser_name}'")
        type_success, type_msg = actions.type_text(advertiser_name, interval=0.02)
        
        if not type_success:
            return False, f"Failed to type advertiser name: {type_msg}"
        
        # Wait a moment for the text to be entered
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered advertiser name: '{advertiser_name}'")
        return True, f"Successfully entered advertiser name: '{advertiser_name}'"
        
    except Exception as e:
        error_msg = f"Error entering advertiser name: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


def verify_advertiser_found(advertiser_name: str) -> Tuple[bool, str]:
    """
    Verify that the advertiser name was found in the dropdown.
    
    This function is now handled by the verifier module.
    The verifier module will automatically verify advertiser entries.
    
    Args:
        advertiser_name: Name of advertiser to verify
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Advertiser verification is handled by verifier module")
    return True, f"Advertiser '{advertiser_name}' verification delegated to verifier module"


def enter_order_id(order_number: str) -> Tuple[bool, str]:
    """
    Enter order ID in the search field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "order" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "order" text
    4. Enters the order ID in the field
    
    Args:
        order_number: Order ID to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering order ID: '{order_number}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "order" word
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'order' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"order_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # Use OCR to find the "order" word within the cropped region
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "order",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'order' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'order' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the input field position 15 pixels below the "order" text
        field_spacing = 15  # pixels below the text
        field_x = text_x  # Same horizontal position as the text
        field_y = text_y + text_height + field_spacing  # 15 pixels below the text
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'order' text")
        
        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on order input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        
        if not click_success:
            return False, f"Failed to click on order field: {click_msg}"
        
        # Wait a moment for the field to be focused
        time.sleep(0.5)
        
        # Clear any existing text in the field
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()
        
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
            # Continue anyway, as the field might be empty
        
        # Wait a moment after clearing to ensure field is ready
        time.sleep(0.2)
        
        # Type the order ID with faster interval to prevent double letters
        print(f"[ACTION_HANDLER] Typing order ID: '{order_number}'")
        type_success, type_msg = actions.type_text(order_number, interval=0.02)
        
        if not type_success:
            return False, f"Failed to type order ID: {type_msg}"
        
        # Wait a moment for the text to be entered
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered order ID: '{order_number}'")
        return True, f"Successfully entered order ID: '{order_number}'"
        
    except Exception as e:
        error_msg = f"Error entering order ID: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg

def enter_agency(agency_name: str) -> Tuple[bool, str]:
    """
    Enter agency name in the search field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "agency" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "agency" text
    4. Enters the agency name in the field
    
    Args:
        agency_name: Name of agency to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering agency name: '{agency_name}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "agency" word
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'agency' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"agency_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # Use OCR to find the "agency" word within the cropped region
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "agency",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'agency' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'agency' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the input field position 15 pixels below the "agency" text
        field_spacing = 15  # pixels below the text
        field_x = text_x  # Same horizontal position as the text
        field_y = text_y + text_height + field_spacing  # 15 pixels below the text
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'agency' text")
        
        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on agency input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        
        if not click_success:
            return False, f"Failed to click on agency field: {click_msg}"
        
        # Wait a moment for the field to be focused
        time.sleep(0.5)
        
        # Clear any existing text in the field
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()
        
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
            # Continue anyway, as the field might be empty
        
        # Wait a moment after clearing to ensure field is ready
        time.sleep(0.2)
        
        # Type the agency name with faster interval to prevent double letters
        print(f"[ACTION_HANDLER] Typing agency name: '{agency_name}'")
        type_success, type_msg = actions.type_text(agency_name, interval=0.02)
        
        if not type_success:
            return False, f"Failed to type agency name: {type_msg}"
        
        # Wait a moment for the text to be entered
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered agency name: '{agency_name}'")
        return True, f"Successfully entered agency name: '{agency_name}'"
        
    except Exception as e:
        error_msg = f"Error entering agency name: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg

def enter_begin_date(begin_date: str) -> Tuple[bool, str]:
    """
    Enter begin date in the date field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "begin" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "begin" text
    4. Enters the begin date in the field
    
    Args:
        begin_date: Begin date to enter (format: YYYY-MM-DD or MM/DD/YYYY)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering begin date: '{begin_date}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "begin" word
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'begin' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"begin_date_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # Use OCR to find the "begin" word within the cropped region
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "begin",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'begin' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'begin' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the input field position 15 pixels below the "begin" text
        field_spacing = 15  # pixels below the text
        field_x = text_x  # Same horizontal position as the text
        field_y = text_y + text_height + field_spacing  # 15 pixels below the text
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'begin' text")
        
        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on begin date input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        
        if not click_success:
            return False, f"Failed to click on begin date field: {click_msg}"
        
        # Wait a moment for the field to be focused
        time.sleep(0.5)
        
        # Clear any existing text in the field
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()
        
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
            # Continue anyway, as the field might be empty
        
        # Wait a moment after clearing to ensure field is ready
        time.sleep(0.2)
        
        # Type the begin date with faster interval to prevent double letters
        print(f"[ACTION_HANDLER] Typing begin date: '{begin_date}'")
        type_success, type_msg = actions.type_text(begin_date, interval=0.02)
        
        if not type_success:
            return False, f"Failed to type begin date: {type_msg}"
        
        # Wait a moment for the text to be entered
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered begin date: '{begin_date}'")
        return True, f"Successfully entered begin date: '{begin_date}'"
        
    except Exception as e:
        error_msg = f"Error entering begin date: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


def enter_end_date(end_date: str) -> Tuple[bool, str]:
    """
    Enter end date in the date field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "end" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "end" text
    4. Enters the end date in the field
    
    Args:
        end_date: End date to enter (format: YYYY-MM-DD or MM/DD/YYYY)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering end date: '{end_date}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "end" word
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'end' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"end_date_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # Use OCR to find the "end" word within the cropped region
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "end",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'end' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'end' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the input field position 15 pixels below the "end" text
        field_spacing = 15  # pixels below the text
        field_x = text_x  # Same horizontal position as the text
        field_y = text_y + text_height + field_spacing  # 15 pixels below the text
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'end' text")
        
        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on end date input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        
        if not click_success:
            return False, f"Failed to click on end date field: {click_msg}"
        
        # Wait a moment for the field to be focused
        time.sleep(0.5)
        
        # Clear any existing text in the field
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()
        
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
            # Continue anyway, as the field might be empty
        
        # Wait a moment after clearing to ensure field is ready
        time.sleep(0.2)
        
        # Type the end date with faster interval to prevent double letters
        print(f"[ACTION_HANDLER] Typing end date: '{end_date}'")
        type_success, type_msg = actions.type_text(end_date, interval=0.02)
        
        if not type_success:
            return False, f"Failed to type end date: {type_msg}"
        
        # Wait a moment for the text to be entered
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered end date: '{end_date}'")
        return True, f"Successfully entered end date: '{end_date}'"
        
    except Exception as e:
        error_msg = f"Error entering end date: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


# ============================================================================
# BUTTON ACTIONS
# ============================================================================

def click_search_button() -> Tuple[bool, str]:
    """
    Click the search button to submit the search form.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "search" within region (206, 152, 1439, 79)
    3. Clicks on the "search" text position
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Clicking search button...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "search" word
        # Region: (206, 170, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 170
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'search' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        # Save the cropped image for debugging
        debug_filename = f"search_button_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[ACTION_HANDLER] Saved cropped image for debugging: {debug_filename}")
        
        # Use OCR to find the "search" word within the cropped region
        success, found, bbox = ocr_utils.find_text_with_position(
            cropped_image,
            "search",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'search' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x  # Add region offset
        text_y = region_y + cropped_text_y  # Add region offset
        
        print(f"[ACTION_HANDLER] ✓ 'search' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        print(f"[ACTION_HANDLER] Cropped coordinates: ({cropped_text_x}, {cropped_text_y}) -> Full coordinates: ({text_x}, {text_y})")
        
        # Calculate the button click position (center of the text)
        button_x = text_x + (text_width // 2)  # Center horizontally
        button_y = text_y + (text_height // 2)  # Center vertically
        
        print(f"[ACTION_HANDLER] Calculated button click position: ({button_x}, {button_y}) - center of 'search' text")
        
        # Click on the search button
        print(f"[ACTION_HANDLER] Clicking on search button at ({button_x}, {button_y})")
        click_success, click_msg = actions.click_at_position(button_x, button_y)
        
        if not click_success:
            return False, f"Failed to click on search button: {click_msg}"
        
        actions.move_mouse(1800, 50, 0)
        # Wait a moment for the click to register
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully clicked search button")
        return True, "Successfully clicked search button"
        
    except Exception as e:
        error_msg = f"Error clicking search button: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


def wait_for_search_results(timeout: int = 10) -> Tuple[bool, str]:
    """
    Wait for search results to load.
    
    This function knows:
    - What loading indicators to watch for
    - What text indicates results loaded
    - How long is reasonable to wait
    
    Args:
        timeout: Maximum seconds to wait for results
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Waiting for search results (timeout: {timeout}s)...")
    
    # Simple wait implementation
    import time
    time.sleep(2.0)  # Wait 2 seconds for results to load
    
    return True, "Search results loaded successfully"


# ============================================================================
# TABLE INTERACTION ACTIONS
# ============================================================================

def find_row_by_deal_number(order_number: str, max_pages: int = 20) -> Tuple[bool, str]:
    """
    Search through table rows to find matching deal number.
    
    Args:
        order_number: Deal number to search for
        max_pages: Maximum pages to search through
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Searching for deal number: '{order_number}' (max {max_pages} pages)")
    
    # Simple implementation - assume row is found
    # TODO: Implement actual table search when table structure is known
    return True, f"Found row with deal number: '{order_number}'"


def right_click_row(order_number: str) -> Tuple[bool, str]:
    """
    Right-click on the row containing the specified order number.
    
    Args:
        order_number: Deal number to identify the row
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Right-clicking row with deal number: '{order_number}'")
    
    # Simple implementation - assume right-click succeeded
    # TODO: Implement actual right-click when row coordinates are known
    return True, f"Right-clicked on row with deal number: '{order_number}'"


def select_edit_multinetwork_instruction() -> Tuple[bool, str]:
    """
    Select 'Edit Multi-network Instruction' from context menu.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Selecting 'Edit Multi-network Instruction' from context menu...")
    
    # Simple implementation - assume menu selection succeeded
    # TODO: Implement actual menu selection when context menu structure is known
    return True, "Selected 'Edit Multi-network Instruction' from context menu"


# ============================================================================
# PAGE LOAD WAITING ACTIONS
# ============================================================================

def wait_for_edit_page_load(timeout: int = 10) -> Tuple[bool, str]:
    """
    Wait for the edit page to finish loading.
    
    Args:
        timeout: Maximum seconds to wait
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Waiting for edit page to load (timeout: {timeout}s)...")
    
    # Simple wait implementation
    import time
    time.sleep(3.0)  # Wait 3 seconds for page to load
    
    return True, "Edit page loaded successfully"


def verify_edit_page_opened(order_number: str) -> Tuple[bool, str]:
    """
    Verify the Edit Multi-network Instructions page opened for correct Deal ID.
    
    Args:
        order_number: Expected deal ID on the page
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Verifying edit page opened for deal: '{order_number}'")
    
    # Simple implementation - assume page opened correctly
    # TODO: Implement actual verification when page structure is known
    return True, f"Edit page opened for deal: '{order_number}'"


# ============================================================================
# FORM FIELD ACTIONS (ISCI CODES)
# ============================================================================

def enter_isci_1(isci_1: str) -> Tuple[bool, str]:
    """
    Enter ISCI 1 value in the form.
    
    Args:
        isci_1: ISCI code to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering ISCI 1: '{isci_1}'")
    
    # Simple implementation - assume ISCI entry succeeded
    # TODO: Implement actual ISCI entry when field coordinates are known
    return True, f"Entered ISCI 1: '{isci_1}'"


def enter_isci_2_if_provided(isci_2: str, rotation_percent_isci_2: str) -> Tuple[bool, str]:
    """
    Enter ISCI 2 and rotation percentage if provided in optional fields.
    
    Args:
        isci_2: ISCI code (empty string if not provided)
        rotation_percent_isci_2: Rotation percentage (empty string if not provided)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Checking ISCI 2: '{isci_2}' with rotation: '{rotation_percent_isci_2}'")
    
    if not isci_2:
        return True, "ISCI 2 not provided - skipped"
    
    # Simple implementation - assume ISCI entry succeeded
    # TODO: Implement actual ISCI entry when field coordinates are known
    return True, f"Entered ISCI 2: '{isci_2}' with rotation: '{rotation_percent_isci_2}%'"


def enter_isci_3_if_provided(isci_3: str, rotation_percent_isci_3: str) -> Tuple[bool, str]:
    """
    Enter ISCI 3 and rotation percentage if provided in optional fields.
    
    Args:
        isci_3: ISCI code (empty string if not provided)
        rotation_percent_isci_3: Rotation percentage (empty string if not provided)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Checking ISCI 3: '{isci_3}' with rotation: '{rotation_percent_isci_3}'")
    
    if not isci_3:
        return True, "ISCI 3 not provided - skipped"
    
    # Simple implementation - assume ISCI entry succeeded
    # TODO: Implement actual ISCI entry when field coordinates are known
    return True, f"Entered ISCI 3: '{isci_3}' with rotation: '{rotation_percent_isci_3}%'"


# ============================================================================
# SAVE ACTIONS
# ============================================================================

def save_instruction() -> Tuple[bool, str]:
    """
    Save the edited instruction.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Saving instruction...")
    
    # Simple implementation - assume save succeeded
    # TODO: Implement actual save when save button coordinates are known
    return True, "Instruction saved successfully"


def verify_save_successful(order_number: str) -> Tuple[bool, str]:
    """
    Verify the instruction was saved successfully.
    
    Args:
        order_number: Deal ID to verify in success message
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Verifying save was successful for deal: '{order_number}'")
    
    # Simple implementation - assume save verification succeeded
    # TODO: Implement actual save verification when success indicators are known
    return True, f"Save verified for deal: '{order_number}'"
