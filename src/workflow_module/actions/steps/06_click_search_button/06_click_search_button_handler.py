#!/usr/bin/env python3
"""
Handler for: Click Search Button

- Precheck: Verify search page is displayed
- Action: Click the search button to submit the search form
- Verifier: Wait for loading spinner to clear, then verify results loaded
- Error Handler: Handle errors
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
from src.workflow_module.actions.helpers.field_utils import get_results_count
from src.workflow_module.actions.helpers.precheck_utils import verify_page, verify_no_loading_spinner
from src.workflow_module.pages.page_loader import get_element
import time
import cv2

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify search page is displayed before clicking search."""
    return verify_page("search_page")

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """Click the search button to submit the search form."""
    print("[ACTION_HANDLER] Clicking search button...")
    
    # Get action region from page config
    btn_config = get_element("search_page", "search_button")
    action_region = tuple(btn_config["action_region"])
    region_x, region_y, region_width, region_height = action_region
    
    cropped_image = take_screenshot_and_crop(action_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region"
    
    success, found, bbox = scanner.find_text_with_position(cropped_image, "search", case_sensitive=False)
    if not success or not found or bbox is None:
        return False, "Could not determine exact position of 'search' text"
    
    cropped_text_x, cropped_text_y, text_width, text_height = bbox
    text_x = region_x + cropped_text_x
    text_y = region_y + cropped_text_y
    
    button_x = text_x + (text_width // 2)
    button_y = text_y + (text_height // 2)
    
    click_success, click_msg = actions.click_at_position(button_x, button_y)
    if not click_success:
        return False, f"Failed to click on search button: {click_msg}"

    time.sleep(0.5)
    return True, "Successfully clicked search button"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Wait for loading to clear, then verify search results are present."""
    print("[VERIFIER_HANDLER] Verifying search button clicked and checking results...")
    
    # Wait for any loading spinner to disappear
    spinner_ok, spinner_msg = verify_no_loading_spinner(max_wait=30.0, poll_interval=2.0)
    if not spinner_ok:
        return False, f"Loading spinner did not clear: {spinner_msg}", None
    
    # Wait for search results to load
    time.sleep(2.0)
    
    # Check results count region from page config
    btn_config = get_element("search_page", "search_button")
    field_region = tuple(btn_config["results_count_region"])
    cropped_image = take_screenshot_and_crop(field_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to order field region", None
    
    success, extracted_text = scanner.extract_text(cropped_image)
    if not success:
        return False, f"Failed to extract text from order field: {extracted_text}", None
    
    extracted_results = extract_string_from_text(extracted_text, "Results")
    if not extracted_results:
        return False, f"Expected 'Results', could not extract from: '{extracted_text}'", None
    
    similarity = calculate_text_similarity("Results", extracted_results)
    
    results_count = get_results_count()
    if results_count is None:
        return False, "Failed to extract results count from the page", None
    
    verification_data = {
        "expected_text": "Results",
        "extracted_text": extracted_text,
        "similarity_score": similarity,
        "results_count": results_count
    }
    
    if results_count == 0:
        return False, f"Search returned 0 results. No data found matching the search criteria.", verification_data
    
    if similarity >= 0.80:
        return True, f"Search results verified ({similarity:.0%} similarity). Found {results_count} result(s).", verification_data
    else:
        return False, f"Search button verification failed. Similarity: {similarity:.0%}", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to clicking search button."""
    print(f"[ERROR_HANDLER] Handling error for click_search_button (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    
    return False, f"Failed to click search button after {max_attempts} attempts"
