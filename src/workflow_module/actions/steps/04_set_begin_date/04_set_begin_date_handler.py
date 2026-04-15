#!/usr/bin/env python3
"""
Handler for: Set Begin Date

- Precheck: Verify search page is displayed
- Action: Enter begin date into the field
- Verifier: Verify the begin date was entered correctly
- Error Handler: Handle errors
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_date_from_text
from src.workflow_module.actions.helpers.field_utils import type_text_in_field
from src.workflow_module.actions.helpers.precheck_utils import verify_page
from src.workflow_module.pages.page_loader import get_element
import time

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify search page is displayed before setting begin date."""
    return verify_page("search_page")

# ============================================================================
# ACTION
# ============================================================================

def action(begin_date: str, **kwargs) -> Tuple[bool, str]:
    """Enter begin date into the field."""
    print(f"[ACTION_HANDLER] Entering begin date: '{begin_date}'")
    
    # Debug: Print what OCR sees in the search region
    field_config = get_element("search_page", "begin_date_field")
    search_region = tuple(field_config["search_region"])
    cropped_image = take_screenshot_and_crop(search_region)
    if cropped_image is not None:
        success, extracted_text = scanner.extract_text(cropped_image)
        if success:
            print(f"[ACTION_HANDLER] DEBUG - OCR Content in region {search_region}: '{extracted_text}'")
        else:
            print(f"[ACTION_HANDLER] DEBUG - OCR failed to extract text in region {search_region}")
    
    return type_text_in_field(
        field_label=["begin", "begin date"],
        text_to_type=begin_date,
        press_enter=False,
        typing_interval=0.02
    )

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(begin_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the begin date was entered correctly."""
    print(f"[VERIFIER_HANDLER] Verifying begin date entered: '{begin_date}'")
    
    if not begin_date:
        return True, "No begin date to verify", None
    
    # Get verification region from page config
    field_config = get_element("search_page", "begin_date_field")
    field_region = tuple(field_config["verification_region"])
    cropped_image = take_screenshot_and_crop(field_region)
    
    if cropped_image is None:
        return False, "Failed to crop image to begin date field region", None
    
    success, extracted_text = scanner.extract_text(cropped_image)
    if not success:
        return False, f"Failed to extract text: {extracted_text}", None
    
    extracted_date = extract_date_from_text(extracted_text, begin_date)
    
    print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
    print(f"[VERIFIER_HANDLER] Extracted date: '{extracted_date}'")
    
    if extracted_date:
        similarity = calculate_text_similarity(begin_date, extracted_date)
        verification_data = {
            "expected_date": begin_date,
            "extracted_text": extracted_text,
            "extracted_date": extracted_date,
            "similarity": similarity,
            "field_region": field_region,
        }
        
        if similarity >= 0.80:
            return True, f"Begin date verified ({similarity:.0%} match)", verification_data
        else:
            return False, f"Begin date mismatch (similarity: {similarity:.0%})", verification_data
    else:
        verification_data = {
            "expected_date": begin_date,
            "extracted_text": extracted_text,
            "extracted_date": None,
            "field_region": field_region,
        }
        return False, f"Could not extract date from: '{extracted_text}'", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to setting begin date."""
    print(f"[ERROR_HANDLER] Handling error for set_begin_date (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    
    return False, f"Failed to set begin date after {max_attempts} attempts"
