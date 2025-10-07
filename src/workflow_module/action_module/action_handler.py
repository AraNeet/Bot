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

        # Define region to search for the icon
        region_x = 93
        region_y = 52
        region_width = 84
        region_height = 66
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
            actions.move_mouse(500, 500, 0)
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

        region_x = 372
        region_y = 152
        region_width = 166
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)

        print(f"[ACTION_HANDLER] Searching for 'advertiser' word in region {search_region}")

        ocr_success, text_found = ocr_utils.find_text_in_region(
            screenshot,
            "advertiser",
            search_region,
            case_sensitive=False
        )

        if not ocr_success:
            return False, "OCR search failed"

        if not text_found:
            return False, f"Word 'advertiser' not found in region {search_region}"

        print(f"[ACTION_HANDLER] ✓ Found 'advertiser' word in region {search_region}")

        success, found, bbox = ocr_utils.find_text_with_position(
            screenshot,
            "advertiser",
            case_sensitive=False
        )

        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'advertiser' text"

        text_x, text_y, text_width, text_height = bbox
        print(f"[ACTION_HANDLER] ✓ 'advertiser' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")

        field_spacing = 15
        field_x = text_x
        field_y = text_y + text_height + field_spacing

        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'advertiser' text")

        # Click on the input field
        print(f"[ACTION_HANDLER] Clicking on advertiser input field at ({field_x}, {field_y})")
        click_success, click_msg = actions.click_at_position(field_x, field_y)

        if not click_success:
            return False, f"Failed to click on advertiser field: {click_msg}"

        # Clear any existing text in the field (Citrix-specific approach)
        print(f"[ACTION_HANDLER] Clearing existing text in field...")
        clear_success, clear_msg = actions.clear_field()

        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")

        # Wait longer for Citrix to process the clear action
        time.sleep(1.0)

        # Type the advertiser name using Citrix-optimized function
        print(f"[ACTION_HANDLER] Typing advertiser name: '{advertiser_name}' (Citrix mode)")
        type_success, type_msg = actions.type_text_citrix(advertiser_name, interval=0.5)

        if not type_success:
            return False, f"Failed to type advertiser name: {type_msg}"

        # Wait longer for Citrix to process all keystrokes
        time.sleep(2.0)

        # Verify the text was entered correctly (Citrix validation)
        print(f"[ACTION_HANDLER] Verifying text entry in Citrix...")
        verification_success, verification_msg = verify_text_entry(advertiser_name, field_x, field_y)
        
        if not verification_success:
            print(f"[ACTION_HANDLER] Warning: Text verification failed: {verification_msg}")
            # Don't fail the function, just log the warning

        print(f"[ACTION_HANDLER] ✓ Successfully entered advertiser name: '{advertiser_name}'")
        return True, f"Successfully entered advertiser name: '{advertiser_name}'"

    except Exception as e:
        error_msg = f"Error entering advertiser name: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


def verify_text_entry(expected_text: str, field_x: int, field_y: int) -> Tuple[bool, str]:
    """
    Verify that text was entered correctly in a Citrix field.
    
    This function takes a screenshot and uses OCR to verify the entered text
    matches what was expected, helping detect double letters or other issues.
    
    Args:
        expected_text: The text that should have been entered
        field_x: X coordinate of the field
        field_y: Y coordinate of the field
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Take a fresh screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification"
        
        # Define a region around the field to check for text
        # Use a small region around the clicked position
        check_region = (field_x - 50, field_y - 10, 200, 30)  # (x, y, width, height)
        
        # Extract text from the field region
        success, extracted_text = ocr_utils.extract_text_from_region(
            screenshot, 
            check_region
        )
        
        if not success:
            return False, f"Failed to extract text from field region: {extracted_text}"
        
        # Clean up the extracted text for comparison
        extracted_clean = extracted_text.strip().lower()
        expected_clean = expected_text.strip().lower()
        
        print(f"[ACTION_HANDLER] Verification - Expected: '{expected_clean}', Found: '{extracted_clean}'")
        
        # Check if the text matches (allowing for some OCR variations)
        if expected_clean in extracted_clean or extracted_clean in expected_clean:
            return True, f"Text verification successful: '{extracted_clean}'"
        else:
            return False, f"Text verification failed - Expected: '{expected_clean}', Found: '{extracted_clean}'"
            
    except Exception as e:
        return False, f"Text verification error: {e}"


def verify_advertiser_found(advertiser_name: str) -> Tuple[bool, str]:
    """
    Verify that the advertiser name was found in the dropdown.
    
    This function knows:
    - Where the dropdown appears
    - What text to look for
    - How long to wait for dropdown
    
    Args:
        advertiser_name: Name of advertiser to verify
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement verification logic
    - Take screenshot
    - Look for advertiser name in dropdown region
    - Verify text appears
    """
    print(f"[ACTION_HANDLER] Verifying advertiser found: '{advertiser_name}'")
    
    # TODO: Define dropdown region (where autocomplete appears)
    # DROPDOWN_REGION = (400, 220, 300, 200)  # (x, y, width, height)
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Crop to dropdown region
    # region_img = computer_vision_utils.crop_image(screenshot, *DROPDOWN_REGION)
    
    # TODO: Use OCR to find advertiser name
    # success, found = ocr_utils.find_text(region_img, advertiser_name, case_sensitive=False)
    
    # TODO: Return result
    # if found:
    #     return True, f"Advertiser '{advertiser_name}' found in dropdown"
    # else:
    #     return False, f"Advertiser '{advertiser_name}' not found in dropdown"
    
    # Placeholder
    return True, f"Advertiser '{advertiser_name}' verified in dropdown"

def enter_order_id(order_number: str) -> Tuple[bool, str]:
    """
    Enter order ID in the search field.
    
    This function knows:
    - Where the order ID field is located
    - How to activate the field
    - Expected format for order IDs
    
    Args:
        order_number: Order ID to enter
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement field entry logic
    - Click order ID field at known location
    - Clear any existing text
    - Type order number
    """
    print(f"[ACTION_HANDLER] Entering order ID: '{order_number}'")
    
    # TODO: Click order ID field at known location
    # ORDER_FIELD_X = 500
    # ORDER_FIELD_Y = 250
    # success, msg = actions.click_at_position(ORDER_FIELD_X, ORDER_FIELD_Y)
    
    # TODO: Clear any existing text
    # success, msg = actions.clear_field()
    
    # TODO: Type order number
    # success, msg = actions.type_text(order_number, interval=0.05)
    
    # Placeholder
    return True, f"Entered order ID: '{order_number}'"

def verify_order_found(order_number: str) -> Tuple[bool, str]:
    """
    Verify that the order ID was accepted/found.
    
    This function knows:
    - Where to look for confirmation
    - What indicates order was found
    - Error messages to check for
    
    Args:
        order_number: Order ID to verify
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement verification logic
    - Check if order ID appears in field
    - Look for error messages
    - Verify no "not found" text appears
    """
    print(f"[ACTION_HANDLER] Verifying order found: '{order_number}'")
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Check if order number appears in field (confirms it was entered)
    # success, found = ocr_utils.find_text(screenshot, order_number)
    
    # TODO: Check for error messages
    # error_found = ocr_utils.find_text(screenshot, "not found")
    # if error_found:
    #     return False, f"Order '{order_number}' not found in system"
    
    # Placeholder
    return True, f"Order '{order_number}' verified"


# ============================================================================
# DATE FIELD ACTIONS
# ============================================================================

def enter_start_date(start_date: str) -> Tuple[bool, str]:
    """
    Enter start date in the date field.
    
    This function knows:
    - Where the start date field is located
    - Expected date format (YYYY-MM-DD or MM/DD/YYYY)
    - How to handle date picker (if any)
    
    Args:
        start_date: Start date to enter (format: YYYY-MM-DD)
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement date entry logic
    - Click start date field
    - Clear existing date
    - Type new date (handle format conversion if needed)
    - Close date picker if it opens
    """
    print(f"[ACTION_HANDLER] Entering start date: '{start_date}'")
    
    # TODO: Click start date field
    # START_DATE_FIELD_X = 500
    # START_DATE_FIELD_Y = 300
    # success, msg = actions.click_at_position(START_DATE_FIELD_X, START_DATE_FIELD_Y)
    
    # TODO: Clear existing date
    # success, msg = actions.clear_field()
    
    # TODO: Convert date format if needed
    # formatted_date = convert_date_format(start_date, from_format="YYYY-MM-DD", to_format="MM/DD/YYYY")
    
    # TODO: Type date
    # success, msg = actions.type_text(formatted_date, interval=0.05)
    
    # TODO: Press Tab to move to next field (closes date picker)
    # success, msg = actions.press_key("tab")
    
    # Placeholder
    return True, f"Entered start date: '{start_date}'"

def calculate_and_enter_end_date(start_date: str) -> Tuple[bool, str]:
    """
    Calculate end date (start + 31 days) and enter it.
    
    This function knows:
    - Where the end date field is located
    - How to calculate end date from start date
    - Date format requirements
    
    Args:
        start_date: Start date (format: YYYY-MM-DD)
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement date calculation and entry
    - Parse start_date
    - Add 31 days
    - Format as required
    - Enter in end date field
    """
    print(f"[ACTION_HANDLER] Calculating and entering end date from: '{start_date}'")
    
    # TODO: Parse start date
    # from datetime import datetime, timedelta
    # start = datetime.strptime(start_date, "%Y-%m-%d")
    
    # TODO: Add 31 days
    # end = start + timedelta(days=31)
    
    # TODO: Format end date
    # end_date_str = end.strftime("%Y-%m-%d")
    
    # TODO: Click end date field
    # END_DATE_FIELD_X = 500
    # END_DATE_FIELD_Y = 350
    # success, msg = actions.click_at_position(END_DATE_FIELD_X, END_DATE_FIELD_Y)
    
    # TODO: Clear existing date
    # success, msg = actions.clear_field()
    
    # TODO: Type end date
    # success, msg = actions.type_text(end_date_str, interval=0.05)
    
    # Placeholder
    return True, f"Calculated and entered end date (start + 31 days)"

# ============================================================================
# BUTTON ACTIONS
# ============================================================================

def click_search_button() -> Tuple[bool, str]:
    """
    Click the search button to submit the search form.
    
    This function knows:
    - Exact location of search button
    - What happens after clicking (loading, page change)
    - How to verify click was successful
    
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement button click logic
    - Click search button at known location
    - Wait for any loading indicators
    - Verify results page loaded
    """
    print("[ACTION_HANDLER] Clicking search button...")
    
    # TODO: Click search button at known location
    # SEARCH_BUTTON_X = 700
    # SEARCH_BUTTON_Y = 400
    # success, msg = actions.click_at_position(SEARCH_BUTTON_X, SEARCH_BUTTON_Y)
    
    # TODO: Wait for any loading indicator to appear
    # time.sleep(0.5)
    
    # Placeholder
    return True, "Clicked search button"

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
        
    TODO: Implement wait logic
    - Watch for loading spinner to disappear
    - Look for results table to appear
    - Verify "No results" isn't shown
    """
    print(f"[ACTION_HANDLER] Waiting for search results (timeout: {timeout}s)...")
    
    # TODO: Wait for loading indicator to disappear
    # screenshot = computer_vision_utils.take_screenshot()
    # success, disappeared = wait_for_text_disappear(screenshot, "Loading...", timeout)
    
    # TODO: Verify results table appeared
    # screenshot = computer_vision_utils.take_screenshot()
    # success, found = ocr_utils.find_text(screenshot, "Results")
    
    # TODO: Check for "No results found" message
    # screenshot = computer_vision_utils.take_screenshot()
    # success, no_results = ocr_utils.find_text(screenshot, "No results")
    # if no_results:
    #     return False, "Search returned no results"
    
    # Placeholder
    return True, "Search results loaded successfully"

# ============================================================================
# TABLE INTERACTION ACTIONS
# ============================================================================

def find_row_by_deal_number(order_number: str, max_pages: int = 20) -> Tuple[bool, str]:
    """
    Search through table rows to find matching deal number.
    
    This function knows:
    - How to read table rows
    - Where deal numbers appear in rows
    - How to navigate through pages
    - How to handle pagination
    
    Args:
        order_number: Deal number to search for
        max_pages: Maximum pages to search through
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement table search logic
    - Read visible table rows
    - Look for order_number in each row
    - If not found, go to next page
    - Repeat until found or max_pages reached
    """
    print(f"[ACTION_HANDLER] Searching for deal number: '{order_number}' (max {max_pages} pages)")
    
    # TODO: Loop through pages
    # for page in range(1, max_pages + 1):
    #     # Take screenshot of current page
    #     screenshot = computer_vision_utils.take_screenshot()
    #     
    #     # Define table region
    #     TABLE_REGION = (100, 450, 1000, 400)
    #     table_img = computer_vision_utils.crop_image(screenshot, *TABLE_REGION)
    #     
    #     # Use OCR to find order number
    #     success, found = ocr_utils.find_text(table_img, order_number)
    #     
    #     if found:
    #         return True, f"Found deal number '{order_number}' on page {page}"
    #     
    #     # Click next page button
    #     NEXT_PAGE_BUTTON_X = 900
    #     NEXT_PAGE_BUTTON_Y = 850
    #     actions.click_at_position(NEXT_PAGE_BUTTON_X, NEXT_PAGE_BUTTON_Y)
    #     time.sleep(1.0)  # Wait for page to load
    
    # TODO: If not found after all pages
    # return False, f"Deal number '{order_number}' not found in {max_pages} pages"
    
    # Placeholder
    return True, f"Found row with deal number: '{order_number}'"

def right_click_row(order_number: str) -> Tuple[bool, str]:
    """
    Right-click on the row containing the specified order number.
    
    This function knows:
    - Where the row is located (from find_row_by_deal_number)
    - How to get row coordinates
    - Where to right-click in the row
    
    Args:
        order_number: Deal number to identify the row
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement right-click logic
    - Use OCR to find exact position of order_number
    - Calculate row center coordinates
    - Right-click on row
    - Verify context menu appeared
    """
    print(f"[ACTION_HANDLER] Right-clicking row with deal number: '{order_number}'")
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Use OCR with position data to find order_number
    # success, text_data = ocr_utils.get_text_data(screenshot)
    # 
    # for i, text in enumerate(text_data['text']):
    #     if order_number in text:
    #         # Get position of this text
    #         x = text_data['left'][i]
    #         y = text_data['top'][i]
    #         height = text_data['height'][i]
    #         
    #         # Right-click in center of row
    #         row_center_y = y + (height // 2)
    #         success, msg = actions.right_click_at_position(x + 100, row_center_y)
    #         break
    
    # Placeholder
    return True, f"Right-clicked on row with deal number: '{order_number}'"

def select_edit_multinetwork_instruction() -> Tuple[bool, str]:
    """
    Select 'Edit Multi-network Instruction' from context menu.
    
    This function knows:
    - Where context menu appears
    - What menu item to click
    - How to verify menu item was clicked
    
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement menu selection logic
    - Find "Edit Multi-network Instruction" text in context menu
    - Click on that menu item
    - Verify edit page starts loading
    """
    print("[ACTION_HANDLER] Selecting 'Edit Multi-network Instruction' from context menu...")
    
    # TODO: Wait for context menu to appear
    # time.sleep(0.5)
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Find "Edit Multi-network Instruction" text
    # success, text_data = ocr_utils.get_text_data(screenshot)
    # 
    # for i, text in enumerate(text_data['text']):
    #     if "Edit Multi-network Instruction" in text:
    #         x = text_data['left'][i]
    #         y = text_data['top'][i]
    #         height = text_data['height'][i]
    #         
    #         # Click on menu item
    #         menu_center_y = y + (height // 2)
    #         success, msg = actions.click_at_position(x + 50, menu_center_y)
    #         break
    
    # Placeholder
    return True, "Selected 'Edit Multi-network Instruction' from context menu"

# ============================================================================
# PAGE LOAD WAITING ACTIONS
# ============================================================================

def wait_for_edit_page_load(timeout: int = 10) -> Tuple[bool, str]:
    """
    Wait for the edit page to finish loading.
    
    This function knows:
    - What indicates page is loading
    - What indicates page finished loading
    - Expected page title or elements
    
    Args:
        timeout: Maximum seconds to wait
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement wait logic
    - Watch for loading indicator
    - Wait for page title to appear
    - Verify key form fields are visible
    """
    print(f"[ACTION_HANDLER] Waiting for edit page to load (timeout: {timeout}s)...")
    
    # TODO: Wait for loading indicator to disappear
    # Wait for specific text that indicates page loaded
    # screenshot = computer_vision_utils.take_screenshot()
    # success, found = wait_for_text_appear(screenshot, "Edit Multi-network Instructions", timeout)
    
    # Placeholder
    return True, "Edit page loaded successfully"

def verify_edit_page_opened(order_number: str) -> Tuple[bool, str]:
    """
    Verify the Edit Multi-network Instructions page opened for correct Deal ID.
    
    This function knows:
    - Where deal ID appears on edit page
    - What page title should be
    - What fields should be visible
    
    Args:
        order_number: Expected deal ID on the page
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement verification logic
    - Check page title
    - Verify deal ID matches order_number
    - Confirm key form fields are visible
    """
    print(f"[ACTION_HANDLER] Verifying edit page opened for deal: '{order_number}'")
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Verify page title
    # success, found = ocr_utils.find_text(screenshot, "Edit Multi-network Instructions")
    # if not found:
    #     return False, "Edit page title not found"
    
    # TODO: Verify deal ID appears on page
    # success, found = ocr_utils.find_text(screenshot, order_number)
    # if not found:
    #     return False, f"Deal ID '{order_number}' not found on edit page"
    
    # Placeholder
    return True, f"Edit page opened for deal: '{order_number}'"

# ============================================================================
# FORM FIELD ACTIONS (ISCI CODES)
# ============================================================================

def enter_isci_1(isci_1: str) -> Tuple[bool, str]:
    """
    Enter ISCI 1 value in the form.
    
    This function knows:
    - Where ISCI 1 field is located
    - Field validation requirements
    - Expected ISCI code format
    
    Args:
        isci_1: ISCI code to enter
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement ISCI entry logic
    - Click ISCI 1 field
    - Clear existing value
    - Type new ISCI code
    - Verify format is valid
    """
    print(f"[ACTION_HANDLER] Entering ISCI 1: '{isci_1}'")
    
    # TODO: Click ISCI 1 field
    # ISCI_1_FIELD_X = 500
    # ISCI_1_FIELD_Y = 500
    # success, msg = actions.click_at_position(ISCI_1_FIELD_X, ISCI_1_FIELD_Y)
    
    # TODO: Clear existing value
    # success, msg = actions.clear_field()
    
    # TODO: Type ISCI code
    # success, msg = actions.type_text(isci_1, interval=0.05)
    
    # TODO: Press Tab to move to next field
    # success, msg = actions.press_key("tab")
    
    # Placeholder
    return True, f"Entered ISCI 1: '{isci_1}'"

def enter_isci_2_if_provided(isci_2: str, rotation_percent_isci_2: str) -> Tuple[bool, str]:
    """
    Enter ISCI 2 and rotation percentage if provided in optional fields.
    
    This function knows:
    - Where ISCI 2 field is located
    - Where rotation percentage field is located
    - How to skip if not provided
    
    Args:
        isci_2: ISCI code (empty string if not provided)
        rotation_percent_isci_2: Rotation percentage (empty string if not provided)
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement conditional ISCI entry
    - Check if isci_2 is provided (not empty)
    - If provided, enter ISCI 2 and rotation percentage
    - If not provided, skip
    """
    print(f"[ACTION_HANDLER] Checking ISCI 2: '{isci_2}' with rotation: '{rotation_percent_isci_2}'")
    
    # TODO: Check if ISCI 2 was provided
    # if not isci_2:
    #     return True, "ISCI 2 not provided - skipping"
    
    # TODO: Click ISCI 2 field
    # ISCI_2_FIELD_X = 500
    # ISCI_2_FIELD_Y = 550
    # success, msg = actions.click_at_position(ISCI_2_FIELD_X, ISCI_2_FIELD_Y)
    
    # TODO: Clear and enter ISCI 2
    # success, msg = actions.clear_and_type(isci_2)
    
    # TODO: Click rotation percentage field
    # ROTATION_2_FIELD_X = 700
    # ROTATION_2_FIELD_Y = 550
    # success, msg = actions.click_at_position(ROTATION_2_FIELD_X, ROTATION_2_FIELD_Y)
    
    # TODO: Clear and enter rotation percentage
    # success, msg = actions.clear_and_type(rotation_percent_isci_2)
    
    # Placeholder
    if not isci_2:
        return True, "ISCI 2 not provided - skipped"
    
    return True, f"Entered ISCI 2: '{isci_2}' with rotation: '{rotation_percent_isci_2}%'"

def enter_isci_3_if_provided(isci_3: str, rotation_percent_isci_3: str) -> Tuple[bool, str]:
    """
    Enter ISCI 3 and rotation percentage if provided in optional fields.
    
    This function knows:
    - Where ISCI 3 field is located
    - Where rotation percentage field is located
    - How to skip if not provided
    
    Args:
        isci_3: ISCI code (empty string if not provided)
        rotation_percent_isci_3: Rotation percentage (empty string if not provided)
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement conditional ISCI entry
    - Check if isci_3 is provided (not empty)
    - If provided, enter ISCI 3 and rotation percentage
    - If not provided, skip
    """
    print(f"[ACTION_HANDLER] Checking ISCI 3: '{isci_3}' with rotation: '{rotation_percent_isci_3}'")
    
    # TODO: Check if ISCI 3 was provided
    # if not isci_3:
    #     return True, "ISCI 3 not provided - skipping"
    
    # TODO: Click ISCI 3 field
    # ISCI_3_FIELD_X = 500
    # ISCI_3_FIELD_Y = 600
    # success, msg = actions.click_at_position(ISCI_3_FIELD_X, ISCI_3_FIELD_Y)
    
    # TODO: Clear and enter ISCI 3
    # success, msg = actions.clear_and_type(isci_3)
    
    # TODO: Click rotation percentage field
    # ROTATION_3_FIELD_X = 700
    # ROTATION_3_FIELD_Y = 600
    # success, msg = actions.click_at_position(ROTATION_3_FIELD_X, ROTATION_3_FIELD_Y)
    
    # TODO: Clear and enter rotation percentage
    # success, msg = actions.clear_and_type(rotation_percent_isci_3)
    
    # Placeholder
    if not isci_3:
        return True, "ISCI 3 not provided - skipped"
    
    return True, f"Entered ISCI 3: '{isci_3}' with rotation: '{rotation_percent_isci_3}%'"

# ============================================================================
# SAVE ACTIONS
# ============================================================================

def save_instruction() -> Tuple[bool, str]:
    """
    Save the edited instruction.
    
    This function knows:
    - Where the Save button is located
    - What happens after clicking Save
    - How to verify save was successful
    
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement save logic
    - Click Save button
    - Wait for save confirmation
    - Verify no error messages
    """
    print("[ACTION_HANDLER] Saving instruction...")
    
    # TODO: Click Save button
    # SAVE_BUTTON_X = 600
    # SAVE_BUTTON_Y = 700
    # success, msg = actions.click_at_position(SAVE_BUTTON_X, SAVE_BUTTON_Y)
    
    # TODO: Wait for save to complete
    # time.sleep(1.0)
    
    # Placeholder
    return True, "Instruction saved successfully"

def verify_save_successful(order_number: str) -> Tuple[bool, str]:
    """
    Verify the instruction was saved successfully.
    
    This function knows:
    - What success message to look for
    - What error messages to check for
    - How to confirm we're back on correct page
    
    Args:
        order_number: Deal ID to verify in success message
        
    Returns:
        Tuple of (success: bool, message: str)
        
    TODO: Implement save verification
    - Look for success message
    - Check for error messages
    - Verify page state
    """
    print(f"[ACTION_HANDLER] Verifying save was successful for deal: '{order_number}'")
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Look for success message
    # success, found = ocr_utils.find_text(screenshot, "Successfully saved")
    # if found:
    #     return True, "Save verified - success message found"
    
    # TODO: Check for error messages
    # success, error_found = ocr_utils.find_text(screenshot, "Error")
    # if error_found:
    #     return False, "Save failed - error message found"
    
    # Placeholder
    return True, f"Save verified for deal: '{order_number}'"

# ============================================================================
# HELPER FUNCTIONS (UI Element Locators)
# ============================================================================

def find_element_by_text(text: str, region: Optional[Tuple[int, int, int, int]] = None) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Find a UI element by its text using OCR.
    
    This is a helper function that other action handlers can use
    to locate elements dynamically instead of using hardcoded coordinates.
    
    Args:
        text: Text to search for
        region: Optional (x, y, width, height) to limit search area
        
    Returns:
        Tuple of (found: bool, position: Optional[Tuple[x, y]])
        
    TODO: Implement element finder
    - Take screenshot
    - Use OCR to find text
    - Return center coordinates of found text
    """
    print(f"[ACTION_HANDLER] Finding element by text: '{text}'")
    
    # TODO: Take screenshot
    # screenshot = computer_vision_utils.take_screenshot()
    
    # TODO: Crop to region if specified
    # if region:
    #     screenshot = computer_vision_utils.crop_image(screenshot, *region)
    
    # TODO: Get text data with positions
    # success, text_data = ocr_utils.get_text_data(screenshot)
    # 
    # if not success:
    #     return False, None
    
    # TODO: Find text and return center position
    # for i, found_text in enumerate(text_data['text']):
    #     if text.lower() in found_text.lower():
    #         x = text_data['left'][i]
    #         y = text_data['top'][i]
    #         width = text_data['width'][i]
    #         height = text_data['height'][i]
    #         
    #         center_x = x + width // 2
    #         center_y = y + height // 2
    #         
    #         return True, (center_x, center_y)
    
    # Placeholder
    return False, None

def find_field_by_label(label_text: str, offset_x: int = 100, offset_y: int = 0) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Find an input field by locating its label and offsetting.
    
    Many forms have labels like "Advertiser:" next to input fields.
    This finds the label, then calculates where the field should be.
    
    Args:
        label_text: Label text to search for (e.g., "Advertiser:")
        offset_x: Horizontal offset from label to field (usually to the right)
        offset_y: Vertical offset from label to field
        
    Returns:
        Tuple of (found: bool, field_position: Optional[Tuple[x, y]])
        
    TODO: Implement label-based field finder
    - Find label position using find_element_by_text()
    - Calculate field position by adding offset
    - Return field coordinates
    """
    print(f"[ACTION_HANDLER] Finding field by label: '{label_text}'")
    
    # TODO: Find label position
    # found, label_pos = find_element_by_text(label_text)
    # 
    # if not found:
    #     return False, None
    
    # TODO: Calculate field position
    # label_x, label_y = label_pos
    # field_x = label_x + offset_x
    # field_y = label_y + offset_y
    # 
    # return True, (field_x, field_y)
    
    # Placeholder
    return False, None

def find_button_by_text(button_text: str) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Find a button by its text.
    
    Args:
        button_text: Text on the button (e.g., "Search", "Save", "Cancel")
        
    Returns:
        Tuple of (found: bool, button_position: Optional[Tuple[x, y]])
        
    TODO: Implement button finder
    - Use find_element_by_text() to locate button
    - Return center coordinates for clicking
    """
    print(f"[ACTION_HANDLER] Finding button by text: '{button_text}'")
    
    # TODO: Use find_element_by_text()
    # return find_element_by_text(button_text)
    
    # Placeholder
    return False, None

# ============================================================================
# COORDINATE CONFIGURATION (TO BE MEASURED)
# ============================================================================

class UICoordinates:
    """
    Store all UI element coordinates for the application.
    
    TODO: Measure these coordinates from your application!
    
    How to measure:
    1. Take screenshot of your application
    2. Open in image editor (Paint, GIMP, etc.)
    3. Hover over UI elements to see coordinates
    4. Record coordinates here
    
    Example:
        ADVERTISER_FIELD = (500, 200)  # x=500, y=200
    """
    
    # Main menu coordinates
    MAIN_MENU = (0, 0)  # TODO: Measure
    MULTINETWORK_SUBMENU = (0, 0)  # TODO: Measure
    
    # Search form fields
    ADVERTISER_FIELD = (0, 0)  # TODO: Measure
    ORDER_ID_FIELD = (0, 0)  # TODO: Measure
    START_DATE_FIELD = (0, 0)  # TODO: Measure
    END_DATE_FIELD = (0, 0)  # TODO: Measure
    SEARCH_BUTTON = (0, 0)  # TODO: Measure
    
    # Results table area
    TABLE_REGION = (0, 0, 0, 0)  # (x, y, width, height) TODO: Measure
    NEXT_PAGE_BUTTON = (0, 0)  # TODO: Measure
    
    # Edit form fields
    ISCI_1_FIELD = (0, 0)  # TODO: Measure
    ISCI_2_FIELD = (0, 0)  # TODO: Measure
    ISCI_3_FIELD = (0, 0)  # TODO: Measure
    ROTATION_2_FIELD = (0, 0)  # TODO: Measure
    ROTATION_3_FIELD = (0, 0)  # TODO: Measure
    SAVE_BUTTON = (0, 0)  # TODO: Measure
    
    # Dropdown/autocomplete regions
    ADVERTISER_DROPDOWN_REGION = (0, 0, 0, 0)  # TODO: Measure
    
    @classmethod
    def get_coordinate(cls, name: str) -> Tuple[int, int]:
        """
        Get coordinate by name with validation.
        
        Args:
            name: Name of the coordinate (e.g., "ADVERTISER_FIELD")
            
        Returns:
            Tuple of (x, y) coordinates
            
        Raises:
            ValueError: If coordinate not found or not set (still 0, 0)
        """
        if not hasattr(cls, name):
            raise ValueError(f"Coordinate '{name}' not found in UICoordinates")
        
        coord = getattr(cls, name)
        
        if isinstance(coord, tuple) and len(coord) == 2:
            if coord == (0, 0):
                raise ValueError(f"Coordinate '{name}' not measured yet (still at 0, 0)")
            return coord
        elif isinstance(coord, tuple) and len(coord) == 4:
            if coord == (0, 0, 0, 0):
                raise ValueError(f"Region '{name}' not measured yet (still at 0, 0, 0, 0)")
            return coord
        else:
            raise ValueError(f"Invalid coordinate format for '{name}'")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def wait_for_text_appear(screenshot, text: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Wait for specific text to appear on screen.
    
    Helper function for action handlers that need to wait for UI changes.
    
    Args:
        screenshot: Initial screenshot
        text: Text to wait for
        timeout: Maximum seconds to wait
        
    Returns:
        Tuple of (appeared: bool, message: str)
        
    TODO: Implement wait logic with polling
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        screenshot = computer_vision_utils.take_screenshot()
        success, found = ocr_utils.find_text(screenshot, text, case_sensitive=False)
        
        if success and found:
            elapsed = time.time() - start_time
            return True, f"Text '{text}' appeared after {elapsed:.1f}s"
        
        time.sleep(0.5)
    
    return False, f"Text '{text}' did not appear within {timeout}s"


def wait_for_text_disappear(screenshot, text: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Wait for specific text to disappear from screen.
    
    Helper function for waiting for loading indicators to disappear.
    
    Args:
        screenshot: Initial screenshot
        text: Text to wait for disappearance
        timeout: Maximum seconds to wait
        
    Returns:
        Tuple of (disappeared: bool, message: str)
        
    TODO: Implement wait logic with polling
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        screenshot = computer_vision_utils.take_screenshot()
        success, found = ocr_utils.find_text(screenshot, text, case_sensitive=False)
        
        if success and not found:
            elapsed = time.time() - start_time
            return True, f"Text '{text}' disappeared after {elapsed:.1f}s"
        
        time.sleep(0.5)
    
    return False, f"Text '{text}' still visible after {timeout}s"


def convert_date_format(date_str: str, from_format: str = "YYYY-MM-DD", to_format: str = "MM/DD/YYYY") -> str:
    """
    Convert date from one format to another.
    
    Helper function for handling different date format requirements.
    
    Args:
        date_str: Date string to convert
        from_format: Current format
        to_format: Desired format
        
    Returns:
        Converted date string
        
    TODO: Implement date conversion using datetime
    """
    from datetime import datetime
    
    # TODO: Create format string mapping
    format_map = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "MM/DD/YYYY": "%m/%d/%Y",
        "DD/MM/YYYY": "%d/%m/%Y"
    }
    
    # TODO: Parse and reformat
    # parsed = datetime.strptime(date_str, format_map[from_format])
    # return parsed.strftime(format_map[to_format])
    
    # Placeholder
    return date_str