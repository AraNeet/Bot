"""
Verifier handlers for workflow actions.

This module contains high-level verifier functions for each workflow action.
Each function handles the verification logic for a specific action type.
"""

from typing import Dict, Any, Tuple, Optional
import re
from . import verifier
from src.workflow_module.helpers import computer_vision_utils
from src.workflow_module.helpers.ocr_utils import TextScanner

scanner = TextScanner()

# =====================================================================================================
# Field Verifier Logic
# =====================================================================================================

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
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the advertiser field region
        field_region = (370, 175, 160, 48)
        
        # Crop the screenshot to the advertiser field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to advertiser field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from advertiser field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] This is the extracted text: '{extracted_text}'")
        
        # Extract advertiser name from the OCR text using similarity matching
        extracted_advertiser_name = _extract_string_from_text(extracted_text, advertiser_name)
        
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

def verify_order_number_entered(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
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
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (206, 175, 82, 48)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_order_id = _extract_number_from_text(extracted_text, order_number)
        
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

def verify_deal_number_entered(deal_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the order ID was entered correctly using OCR similarity check.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the order field region (206, 152, 1439, 79)
    3. Uses OCR to extract text from the field
    4. Performs similarity check (80% threshold) to verify the order ID
    
    Args:
        deal_number: Expected order ID to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{deal_number}'")
    
    if not deal_number:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (286, 175, 80, 48)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_deal_number = _extract_number_from_text(extracted_text, deal_number)
        
        if not extracted_deal_number:
            error_msg = f"✗ Order ID verification failed. Expected: '{deal_number}', Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": deal_number,
                "extracted_text": extracted_text,
                "extracted_deal_number": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_deal_number}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity(deal_number, extracted_deal_number)
        
        verification_data = {
            "expected_text": deal_number,
            "extracted_text": extracted_text,
            "extracted_deal_number": extracted_deal_number,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_deal_number}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: '{deal_number}', Extracted: '{extracted_deal_number}', Similarity: {similarity:.2%} (threshold: 80%)"
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
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{agency_name}'")
    
    if not agency_name:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (668, 180, 130, 40)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_agency_name = _extract_string_from_text(extracted_text, agency_name)
        
        if not extracted_agency_name:
            error_msg = f"✗ Order ID verification failed. Expected: '{agency_name}', Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": agency_name,
                "extracted_text": extracted_text,
                "extracted_agency_name": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_agency_name}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity(agency_name, extracted_agency_name)
        
        verification_data = {
            "expected_text": agency_name,
            "extracted_text": extracted_text,
            "extracted_agency_name": extracted_agency_name,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_agency_name}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: '{agency_name}', Extracted: '{extracted_agency_name}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

def verify_begin_date_entered(begin_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the begin date was entered correctly using OCR similarity check.
    
    Args:
        begin_date: Expected begin date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{begin_date}'")
    
    if not begin_date:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (992, 175, 114, 50)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_begin_date = _extract_date_from_text(extracted_text, begin_date)
        
        if not extracted_begin_date:
            error_msg = f"✗ Order ID verification failed. Expected: '{begin_date}', Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": begin_date,
                "extracted_text": extracted_text,
                "extracted_begin_date": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_begin_date}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity(begin_date, extracted_begin_date)
        
        verification_data = {
            "expected_text": begin_date,
            "extracted_text": extracted_text,
            "extracted_begin_date": extracted_begin_date,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_begin_date}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: '{begin_date}', Extracted: '{extracted_begin_date}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

def verify_end_date_entered(end_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the end date was entered correctly using OCR similarity check.
    
    Args:
        end_date: Expected end date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{end_date}'")
    
    if not end_date:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (1105, 175, 114, 50)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Extract order ID from the OCR text using similarity matching
        extracted_end_date = _extract_date_from_text(extracted_text, end_date)
        
        if not extracted_end_date:
            error_msg = f"✗ Order ID verification failed. Expected: '{end_date}', Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": end_date,
                "extracted_text": extracted_text,
                "extracted_end_date": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_end_date}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity(end_date, extracted_end_date)
        
        verification_data = {
            "expected_text": end_date,
            "extracted_text": extracted_text,
            "extracted_end_date": extracted_end_date,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_end_date}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: '{end_date}', Extracted: '{extracted_end_date}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

def verify_search_button_clicked(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the search button was clicked successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying search button clicked...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the order field region
        field_region = (205, 225, 50, 30)
        
        # Crop the screenshot to the order field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")

        # Extract order ID from the OCR text using similarity matching
        extracted_end_date = _extract_string_from_text(extracted_text, "Results")
        
        if not extracted_end_date:
            error_msg = f"✗ Order ID verification failed. Expected: Results, Could not extract order ID from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": "Results",
                "extracted_text": extracted_text,
                "extracted_end_date": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted order ID: '{extracted_end_date}'")
        
        # Perform similarity check (80% threshold) on the extracted order ID
        similarity = verifier.calculate_text_similarity("Results", extracted_end_date)
        
        verification_data = {
            "expected_text": "Results",
            "extracted_text": extracted_text,
            "extracted_end_date": extracted_end_date,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Order ID verified with {similarity:.2%} similarity (extracted: '{extracted_end_date}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Order ID verification failed. Expected: Results, Extracted: '{extracted_end_date}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying search button click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

#  =====================================================================================================
#  Verifiers for instructions edits
#  =====================================================================================================

def verify_isci_1_entered(isci_1: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 1 was entered correctly.
    
    Args:
        isci_1: Expected ISCI 1 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

def verify_isci_2_entered(isci_2: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 2 was entered correctly.
    
    Args:
        isci_2: Expected ISCI 2 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

def verify_isci_3_entered(isci_3: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 3 was entered correctly.
    
    Args:
        isci_3: Expected ISCI 3 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

def verify_instruction_saved(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the instruction was saved successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    pass

# =====================================================================================================
#  Checks if page are open
# =====================================================================================================

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
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the search fields region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the search fields region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to search fields region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
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

def is_edit_page_loaded_and_open(timeout: int = 4) -> Tuple[bool, str]:
    """
    Wait for the edit page to finish loading.
    
    Args:
        timeout: Maximum seconds to wait
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Waiting for edit page to load (timeout: {timeout}s)...")
    time.sleep(timeout)
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the search fields region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the search fields region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to search fields region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from search fields region: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from search fields region: '{extracted_text}'")
        
        # Check if the words "order" or "agency" are present in the extracted text
        extracted_text_lower = extracted_text.lower()
        has_deal = "deal" in extracted_text_lower
        verification_data = {
            "extracted_text": extracted_text,
            "field_region": field_region,
            "has_deal": has_deal,
        }
        
        if has_deal:
            success_msg = f"✓ Multi-network edit page opened successfully. Found search fields with {'order' if has_order else ''}{' and ' if has_order and has_agency else ''}{'agency' if has_agency else ''}"
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

# ============================================================================
# Helper Functions
# ============================================================================

def _extract_number_from_text(ocr_text: str, expected_order_id: str) -> Optional[str]:
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

def _extract_string_from_text(ocr_text: str, expected_string: str) -> Optional[str]:
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
            
        similarity = verifier.calculate_text_similarity(expected_string, pattern_clean)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pattern_clean
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFIER_HANDLER] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFIER_HANDLER] No suitable advertiser name pattern found (best similarity: {best_similarity:.2%})")
    return None

def _extract_date_from_text(ocr_text: str, expected_date: str) -> Optional[str]:
    """
    Extract date in MM/DD/YYYY format from OCR text, ignoring letters and allowing single-digit months/days.
    
    This function looks for a date in the OCR text by:
    1. Removing all letters from the OCR text
    2. Using a regex to find M/D/YYYY or MM/DD/YYYY formats
    3. Normalizing to MM/DD/YYYY format
    4. Finding the pattern with the highest similarity to the expected date
    
    Args:
        ocr_text: Full OCR text from the field
        expected_date: Expected date in MM/DD/YYYY format to match against
        
    Returns:
        Extracted date string or None if not found
    """
    # Clean the OCR text and remove all letters
    ocr_text_clean = re.sub(r'[a-zA-Z]', '', ocr_text.strip())
    
    # Regex for M/D/YYYY or MM/DD/YYYY (months 1-12, days 1-31, year 4 digits)
    date_pattern = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    date_matches = re.findall(date_pattern, ocr_text_clean)
    
    if not date_matches:
        print(f"[VERIFIER_HANDLER] No date patterns found in OCR text: '{ocr_text_clean}'")
        return None
    
    # Normalize matches to MM/DD/YYYY format
    date_strings = []
    for month, day, year in date_matches:
        try:
            # Convert to integers to validate ranges
            month_int = int(month)
            day_int = int(day)
            if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                date_str = f"{month_int:02d}/{day_int:02d}/{year}"
                date_strings.append(date_str)
        except ValueError:
            continue
    
    if not date_strings:
        print(f"[VERIFIER_HANDLER] No valid date patterns found in OCR text: '{ocr_text_clean}'")
        return None
    
    # Find the pattern with the highest similarity to the expected date
    best_match = None
    best_similarity = 0.0
    
    for date_str in date_strings:
        similarity = verifier.calculate_text_similarity(expected_date, date_str)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = date_str
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFIER_HANDLER] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFIER_HANDLER] No suitable date pattern found (best similarity: {best_similarity:.2%})")
    return None