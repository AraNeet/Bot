"""
Verifier handlers for workflow actions.

This module contains high-level verifier functions for each workflow action.
Each function handles the verification logic for a specific action type.
"""

from typing import Dict, Any, Tuple, Optional
from . import verifier


def verify_advertiser_name_entered(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the advertiser name was entered correctly using OCR similarity check.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the advertiser field region (206, 152, 1439, 79)
    3. Uses OCR to extract text from the field
    4. Performs similarity check (80% threshold) to verify the advertiser name
    
    Args:
        advertiser_name: Expected advertiser name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    try:
        # Take screenshot
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the advertiser field region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the advertiser field region
        cropped_image = verifier.crop_image_for_verification(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to advertiser field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = verifier.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from advertiser field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract advertiser name from the OCR text using similarity matching
        extracted_advertiser_name = _extract_advertiser_name_from_text(extracted_text, advertiser_name)
        
        if not extracted_advertiser_name:
            error_msg = f"✗ Advertiser name verification failed. Expected: '{advertiser_name}', Could not extract advertiser name from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": advertiser_name,
                "extracted_text": extracted_text,
                "extracted_advertiser_name": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted advertiser name: '{extracted_advertiser_name}'")
        
        # Perform similarity check (80% threshold) on the extracted advertiser name
        similarity = verifier.calculate_text_similarity(advertiser_name, extracted_advertiser_name)
        
        verification_data = {
            "expected_text": advertiser_name,
            "extracted_text": extracted_text,
            "extracted_advertiser_name": extracted_advertiser_name,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Advertiser name verified with {similarity:.2%} similarity (extracted: '{extracted_advertiser_name}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Advertiser name verification failed. Expected: '{advertiser_name}', Extracted: '{extracted_advertiser_name}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying advertiser name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_order_id_entered(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the order ID was entered correctly using OCR similarity check.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the order field region (206, 152, 1439, 79)
    3. Uses OCR to extract text from the field
    4. Performs similarity check (80% threshold) to verify the order ID
    
    Args:
        order_number: Expected order ID to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{order_number}'")
    
    if not order_number:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the order field region
        cropped_image = verifier.crop_image_for_verification(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = verifier.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_order_id = _extract_order_id_from_text(extracted_text, order_number)
        
        if not extracted_order_id:
            error_msg = f"✗ Order ID verification failed. Expected: '{order_number}', Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": order_number,
                "extracted_text": extracted_text,
                "extracted_order_id": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_order_id}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity(order_number, extracted_order_id)
        
        verification_data = {
            "expected_text": order_number,
            "extracted_text": extracted_text,
            "extracted_order_id": extracted_order_id,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_order_id}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: '{order_number}', Extracted: '{extracted_order_id}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_agency_name_entered(agency_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the agency name was entered correctly using OCR similarity check.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the agency field region (206, 152, 1439, 79)
    3. Uses OCR to extract text from the field
    4. Performs similarity check (80% threshold) to verify the agency name
    
    Args:
        agency_name: Expected agency name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

def verify_begin_date_entered(begin_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the begin date was entered correctly using OCR similarity check.
    
    Args:
        begin_date: Expected begin date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass


def verify_end_date_entered(end_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the end date was entered correctly using OCR similarity check.
    
    Args:
        end_date: Expected end date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

def verify_search_button_clicked(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the search button was clicked successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying search button clicked...")
    
    try:
        # Use verifier.py to verify button click
        success, message, verification_data = verifier.verify_button_clicked(
            expected_indicators=[
                "loading", "searching", "results", "found", "no results", 
                "search results", "loading...", "please wait"
            ],
            timeout=2.0
        )
        
        return success, message, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying search button click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_multinetwork_page_opened(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the multi-network instructions page was opened successfully.
    
    This function checks if the search fields are visible at the expected region (206, 152, 1439, 79)
    or if the words "order" or "agency" are present in that region.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying multi-network page opened...")
    
    try:
        # Take screenshot
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the search fields region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the search fields region
        cropped_image = verifier.crop_image_for_verification(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to search fields region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = verifier.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from search fields region: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from search fields region: '{extracted_text}'")
        
        # Check if the words "order" or "agency" are present in the extracted text
        extracted_text_lower = extracted_text.lower()
        has_order = "order" in extracted_text_lower
        has_agency = "agency" in extracted_text_lower
        
        verification_data = {
            "extracted_text": extracted_text,
            "field_region": field_region,
            "has_order": has_order,
            "has_agency": has_agency
        }
        
        if has_order or has_agency:
            success_msg = f"✓ Multi-network page opened successfully. Found search fields with {'order' if has_order else ''}{' and ' if has_order and has_agency else ''}{'agency' if has_agency else ''}"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Multi-network page verification failed. Expected 'order' or 'agency' in search fields region, but found: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying multi-network page opening: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_row_found(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row was found in the table.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying row found...")
    
    try:
        # Use verifier.py to verify row presence
        success, message = verifier.verify_element_present(
            element_type="table_row",
            timeout=2.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row found: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_row_right_clicked(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row was right-clicked successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying row right-clicked...")
    
    try:
        # Use verifier.py to verify context menu appeared
        success, message = verifier.verify_ui_state_change(
            expected_texts=["Edit", "Copy", "Delete"],
            timeout=2.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row right-click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_edit_menu_selected(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the edit menu was selected successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying edit menu selected...")
    
    try:
        # Use verifier.py to verify UI state change
        success, message = verifier.verify_ui_state_change(
            expected_texts=["Edit", "Multi-network", "Instructions"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying edit menu selection: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_1_entered(isci_1: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 1 was entered correctly.
    
    Args:
        isci_1: Expected ISCI 1 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 1 entered: '{isci_1}'")
    
    if not isci_1:
        return True, "No ISCI 1 to verify", None
    
    try:
        # Take screenshot and verify text entry
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        success, extracted_text = verifier.extract_text_from_cropped_image(screenshot)
        
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        similarity = verifier.calculate_text_similarity(isci_1, extracted_text)
        
        if similarity >= 0.80:
            success_msg = f"✓ ISCI 1 verified with {similarity:.2%} similarity"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, {"similarity_score": similarity}
        else:
            error_msg = f"✗ ISCI 1 verification failed. Expected: '{isci_1}', Extracted: '{extracted_text}', Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, {"similarity_score": similarity}
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 1 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_2_entered(isci_2: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 2 was entered correctly.
    
    Args:
        isci_2: Expected ISCI 2 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 2 entered: '{isci_2}'")
    
    if not isci_2:
        return True, "No ISCI 2 to verify", None
    
    try:
        # Take screenshot and verify text entry
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        success, extracted_text = verifier.extract_text_from_cropped_image(screenshot)
        
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        similarity = verifier.calculate_text_similarity(isci_2, extracted_text)
        
        if similarity >= 0.80:
            success_msg = f"✓ ISCI 2 verified with {similarity:.2%} similarity"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, {"similarity_score": similarity}
        else:
            error_msg = f"✗ ISCI 2 verification failed. Expected: '{isci_2}', Extracted: '{extracted_text}', Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, {"similarity_score": similarity}
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 2 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_3_entered(isci_3: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 3 was entered correctly.
    
    Args:
        isci_3: Expected ISCI 3 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 3 entered: '{isci_3}'")
    
    if not isci_3:
        return True, "No ISCI 3 to verify", None
    
    try:
        # Take screenshot and verify text entry
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        success, extracted_text = verifier.extract_text_from_cropped_image(screenshot)
        
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        similarity = verifier.calculate_text_similarity(isci_3, extracted_text)
        
        if similarity >= 0.80:
            success_msg = f"✓ ISCI 3 verified with {similarity:.2%} similarity"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, {"similarity_score": similarity}
        else:
            error_msg = f"✗ ISCI 3 verification failed. Expected: '{isci_3}', Extracted: '{extracted_text}', Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, {"similarity_score": similarity}
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 3 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_instruction_saved(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the instruction was saved successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying instruction saved...")
    
    try:
        # Use verifier.py to verify save confirmation
        success, message = verifier.verify_ui_state_change(
            expected_texts=["saved", "success", "completed"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying instruction save: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_text_typed(text: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that text was typed correctly.
    
    Args:
        text: Expected text to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying text typed: '{text}'")
    
    if not text:
        return True, "No text to verify", None
    
    try:
        # Take screenshot and verify text entry
        screenshot = verifier.take_screenshot_for_verification()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        success, extracted_text = verifier.extract_text_from_cropped_image(screenshot)
        
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        similarity = verifier.calculate_text_similarity(text, extracted_text)
        
        if similarity >= 0.80:
            success_msg = f"✓ Text verified with {similarity:.2%} similarity"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, {"similarity_score": similarity}
        else:
            error_msg = f"✗ Text verification failed. Expected: '{text}', Extracted: '{extracted_text}', Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, {"similarity_score": similarity}
        
    except Exception as e:
        error_msg = f"Error verifying text entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_position_clicked(x: int = 0, y: int = 0, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a position was clicked successfully.
    
    Args:
        x: X coordinate that was clicked
        y: Y coordinate that was clicked
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying position clicked: ({x}, {y})")
    
    try:
        # Use verifier.py to verify click action
        success, message = verifier.verify_click_action(x, y, timeout=2.0)
        
        return success, message, {"click_position": (x, y)}
        
    except Exception as e:
        error_msg = f"Error verifying position click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_key_pressed(key: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a key was pressed successfully.
    
    Args:
        key: Key that was pressed
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying key pressed: '{key}'")
    
    if not key:
        return True, "No key to verify", None
    
    try:
        # Use verifier.py to verify key press action
        success, message = verifier.verify_key_action(key, timeout=2.0)
        
        return success, message, {"key_pressed": key}
        
    except Exception as e:
        error_msg = f"Error verifying key press: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# Helper Functions
# ============================================================================

def _extract_order_id_from_text(ocr_text: str, expected_order_id: str) -> Optional[str]:
    """
    Extract order ID from OCR text using similarity matching.
    
    This function looks for the order ID in the OCR text by:
    1. Extracting all numeric patterns from the OCR text
    2. Finding the pattern with the highest similarity to the expected order ID
    
    Args:
        ocr_text: Full OCR text from the field
        expected_order_id: Expected order ID to match against
        
    Returns:
        Extracted order ID string or None if not found
    """
    import re
    
    # Clean the OCR text
    ocr_text_clean = ocr_text.strip()
    
    # Extract all numeric patterns from the OCR text
    numeric_patterns = re.findall(r'\d+', ocr_text_clean)
    
    if not numeric_patterns:
        print(f"[VERIFIER_HANDLER] No numeric patterns found in OCR text")
        return None
    
    # Find the pattern with the highest similarity to the expected order ID
    best_match = None
    best_similarity = 0.0
    
    for pattern in numeric_patterns:
        similarity = verifier.calculate_text_similarity(expected_order_id, pattern)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pattern
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFIER_HANDLER] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFIER_HANDLER] No suitable order ID pattern found (best similarity: {best_similarity:.2%})")
    return None


def _extract_advertiser_name_from_text(ocr_text: str, expected_advertiser_name: str) -> Optional[str]:
    """
    Extract advertiser name from OCR text using similarity matching.
    
    This function looks for the advertiser name in the OCR text by:
    1. Extracting all text patterns from the OCR text
    2. Finding the pattern with the highest similarity to the expected advertiser name
    
    Args:
        ocr_text: Full OCR text from the field
        expected_advertiser_name: Expected advertiser name to match against
        
    Returns:
        Extracted advertiser name string or None if not found
    """
    import re
    
    # Clean the OCR text
    ocr_text_clean = ocr_text.strip()
    
    # Extract all text patterns (words/phrases) from the OCR text
    # Split by common delimiters and get meaningful text segments
    text_patterns = re.findall(r'[A-Za-z][A-Za-z\s]+[A-Za-z]', ocr_text_clean)
    
    if not text_patterns:
        print(f"[VERIFIER_HANDLER] No text patterns found in OCR text")
        return None
    
    # Find the pattern with the highest similarity to the expected advertiser name
    best_match = None
    best_similarity = 0.0
    
    for pattern in text_patterns:
        pattern_clean = pattern.strip()
        if len(pattern_clean) < 3:  # Skip very short patterns
            continue
            
        similarity = verifier.calculate_text_similarity(expected_advertiser_name, pattern_clean)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pattern_clean
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFIER_HANDLER] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFIER_HANDLER] No suitable advertiser name pattern found (best similarity: {best_similarity:.2%})")
    return None