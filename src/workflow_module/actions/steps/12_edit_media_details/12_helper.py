#!/usr/bin/env python3
"""
Helper functions for Step 12: Edit Media Details
"""

from typing import Tuple, Optional, List
import time
import pyautogui

from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers import debug_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Initialize TextScanner
scanner = TextScanner()

# Constants
MEDIA_DETAILS_REGION = (200, 425, 1450, 570)  # x, y, width, height
ALIAS_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']


def scroll_to_media_details(debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """
    Scroll the main window so Media Details is at the top of the working region.
    Uses mouse wheel to scroll down until 'Media Details' text is visible at the target position.
    """
    # Step 1: Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    if debugger:
        debugger.save_image(screenshot, "00_before_scroll.png")
    
    # Step 2: Define the scroll target area where we want "Media Details" to appear
    target_y = 425  # Top of working region
    search_region = (0, 400, 400, 200)  # Left side of screen where "Media Details" label would be
    
    # Step 3: Check if Media Details is already visible in target position
    cropped = computer_vision_utils.crop_image(screenshot, *search_region)
    if cropped is not None:
        success, found, bbox = scanner.find_text_with_position(cropped, "Media Details", case_sensitive=False)
        if success and found:
            print("[MEDIA_DETAILS] 'Media Details' already visible in target area")
            return True, "Media Details already in position"
    
    # Step 4: Position mouse for scrolling
    scroll_x, scroll_y = 800, 600
    pyautogui.moveTo(scroll_x, scroll_y)
    time.sleep(0.2)
    
    # Step 5: Scroll loop to find Media Details
    max_scroll_attempts = 10
    for i in range(max_scroll_attempts):
        # Step 5a: Scroll down
        pyautogui.scroll(-3)  # Negative = scroll down
        time.sleep(0.5)
        
        # Step 5b: Take screenshot and check for Media Details
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            continue
            
        # Step 5c: Search for Media Details text
        cropped = computer_vision_utils.crop_image(screenshot, *search_region)
        if cropped is not None:
            success, found, bbox = scanner.find_text_with_position(cropped, "Media Details", case_sensitive=False)
            if success and found:
                # Step 5d: Check if it's near the top of our region
                if bbox[1] < 50:  # Within 50 pixels of top
                    print(f"[MEDIA_DETAILS] Found 'Media Details' at target position after {i+1} scrolls")
                    if debugger:
                        debugger.save_image(screenshot, "01_after_scroll.png")
                    return True, "Scrolled to Media Details"
    
    # Step 6: Return failure if not found
    return False, "Could not scroll to Media Details position"


def find_alias_row(screenshot, alias_letter: str, debugger: Optional[Debugger] = None, 
                   step_name: str = "") -> Optional[Tuple[int, int]]:
    """
    Find an Alias row (A, B, C, etc.) in the Media Details table.
    Returns the position of the ISCI/Ad-ID cell for that alias.
    """
    # Step 1: Crop to Media Details region
    cropped = computer_vision_utils.crop_image(screenshot, *MEDIA_DETAILS_REGION)
    if cropped is None:
        return None
    
    # Step 2: Save debug image
    if debugger:
        debugger.save_image(cropped, f"{step_name}_cropped.png")
    
    # Step 3: Search for the alias letter in the first column
    success, found, bbox = scanner.find_text_with_position(cropped, alias_letter, case_sensitive=True)
    
    if success and found:
        # Step 4: Extract bounding box coordinates
        lx, ly, lw, lh = bbox
        
        # Step 5: Calculate the ISCI/Ad-ID column position
        # Based on the image: Alias column, then Feeds column, then ISCI/Ad-ID column
        isci_x = MEDIA_DETAILS_REGION[0] + lx + 180  # Offset to ISCI column
        isci_y = MEDIA_DETAILS_REGION[1] + ly + (lh // 2)
        
        print(f"[MEDIA_DETAILS] Found Alias '{alias_letter}' - ISCI position: ({isci_x}, {isci_y})")
        
        # Step 6: Save debug visualization
        if debugger:
            debug_img = screenshot.copy()
            alias_rect = (MEDIA_DETAILS_REGION[0] + lx, MEDIA_DETAILS_REGION[1] + ly, lw, lh)
            debugger.draw_rect(debug_img, alias_rect, color=debug_utils.COLOR_GREEN, label=f"Alias {alias_letter}")
            debugger.draw_point(debug_img, (isci_x, isci_y), color=debug_utils.COLOR_RED, label="ISCI Click")
            debugger.save_image(debug_img, f"{step_name}_found.png")
        
        return (isci_x, isci_y)
    
    # Step 7: Return None if alias not found
    print(f"[MEDIA_DETAILS] Alias '{alias_letter}' not found")
    return None


def find_asterisk_row(screenshot, debugger: Optional[Debugger] = None) -> bool:
    """
    Check if the asterisk (*) row is visible, indicating the end of existing aliases.
    """
    # 1. Crop to Media Details region
    cropped = computer_vision_utils.crop_image(screenshot, *MEDIA_DETAILS_REGION)
    if cropped is None:
        return False
    
    # 2. Search for asterisk in the Alias column area
    success, text = scanner.extract_text(cropped)
    if success and '*' in text:
        print("[MEDIA_DETAILS] Found asterisk (*) row - end of aliases")
        return True
    
    return False


def delete_media_at_position(position: Tuple[int, int], debugger: Optional[Debugger] = None,
                             step_name: str = "") -> Tuple[bool, str]:
    """
    Delete media by right-clicking on the ISCI field and selecting 'Delete Media'.
    """
    # Step 1: Right-click on the position to open context menu
    pyautogui.click(position[0], position[1], button='right')
    time.sleep(0.5)
    
    # Step 2: Take screenshot to find "Delete Media" option
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot after right-click"
    
    # Step 3: Save debug screenshot
    if debugger:
        debugger.save_image(screenshot, f"{step_name}_context_menu.png")
    
    # Step 4: Define search region for context menu
    menu_region = (position[0] - 50, position[1] - 20, 200, 200)
    cropped = computer_vision_utils.crop_image(screenshot, *menu_region)
    
    if cropped is not None:
        # Step 5: Search for "Delete Media" text
        success, found, bbox = scanner.find_text_with_position(cropped, "Delete Media", case_sensitive=False)
        
        if success and found:
            # Step 6: Calculate click position for Delete Media
            lx, ly, lw, lh = bbox
            click_x = menu_region[0] + lx + (lw // 2)
            click_y = menu_region[1] + ly + (lh // 2)
            
            # Step 7: Click Delete Media option
            print(f"[MEDIA_DETAILS] Clicking 'Delete Media' at ({click_x}, {click_y})")
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            
            # Step 8: Save debug visualization
            if debugger:
                debug_img = screenshot.copy()
                debugger.draw_point(debug_img, (click_x, click_y), color=debug_utils.COLOR_RED, label="Delete Media")
                debugger.save_image(debug_img, f"{step_name}_delete_click.png")
            
            return True, "Delete Media clicked"
    
    # Step 9: Fallback - close menu if Delete Media not found
    pyautogui.press('escape')
    time.sleep(0.2)
    
    return False, "Could not find 'Delete Media' option"


def scroll_media_details_down(debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """
    Scroll down within the Media Details sub-window using the scrollbar.
    Right-clicks on scrollbar and selects 'Page Down'.
    """
    # 1. Find the scrollbar on the right side of Media Details
    # Scrollbar is typically at the right edge of the region
    scrollbar_x = MEDIA_DETAILS_REGION[0] + MEDIA_DETAILS_REGION[2] - 15  # Right edge
    scrollbar_y = MEDIA_DETAILS_REGION[1] + (MEDIA_DETAILS_REGION[3] // 2)  # Middle vertically
    
    print(f"[MEDIA_DETAILS] Scrollbar position: ({scrollbar_x}, {scrollbar_y})")
    
    # 2. Right-click on scrollbar
    pyautogui.click(scrollbar_x, scrollbar_y, button='right')
    time.sleep(0.5)
    
    # 3. Take screenshot and find "Page Down" option
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    if debugger:
        debugger.save_image(screenshot, "scroll_context_menu.png")
    
    # 4. Search for "Page Down" in context menu
    menu_region = (scrollbar_x - 100, scrollbar_y - 50, 200, 200)
    cropped = computer_vision_utils.crop_image(screenshot, *menu_region)
    
    if cropped is not None:
        success, found, bbox = scanner.find_text_with_position(cropped, "Page Down", case_sensitive=False)
        
        if success and found:
            lx, ly, lw, lh = bbox
            click_x = menu_region[0] + lx + (lw // 2)
            click_y = menu_region[1] + ly + (lh // 2)
            
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            return True, "Scrolled down one page"
    
    # 5. Fallback: Press Escape and use keyboard
    pyautogui.press('escape')
    time.sleep(0.2)
    pyautogui.press('pagedown')
    time.sleep(0.3)
    
    return True, "Scrolled down using keyboard"


def scroll_media_details_to_top(debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """
    Scroll to the top of Media Details sub-window.
    Right-clicks on scrollbar and selects 'Top'.
    """
    # 1. Find the scrollbar
    scrollbar_x = MEDIA_DETAILS_REGION[0] + MEDIA_DETAILS_REGION[2] - 15
    scrollbar_y = MEDIA_DETAILS_REGION[1] + (MEDIA_DETAILS_REGION[3] // 2)
    
    # 2. Right-click on scrollbar
    pyautogui.click(scrollbar_x, scrollbar_y, button='right')
    time.sleep(0.5)
    
    # 3. Take screenshot and find "Top" option
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    # 4. Search for "Top" in context menu
    menu_region = (scrollbar_x - 100, scrollbar_y - 50, 200, 200)
    cropped = computer_vision_utils.crop_image(screenshot, *menu_region)
    
    if cropped is not None:
        success, found, bbox = scanner.find_text_with_position(cropped, "Top", case_sensitive=False)
        
        if success and found:
            lx, ly, lw, lh = bbox
            click_x = menu_region[0] + lx + (lw // 2)
            click_y = menu_region[1] + ly + (lh // 2)
            
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            return True, "Scrolled to top"
    
    # 5. Fallback: Press Escape and use keyboard
    pyautogui.press('escape')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'home')
    time.sleep(0.3)
    
    return True, "Scrolled to top using keyboard"


def type_isci_and_tab(position: Tuple[int, int], isci_value: str, 
                      debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """
    Click on ISCI field, type the value, and press TAB to perform lookup.
    """
    # 1. Click on the ISCI field
    pyautogui.click(position[0], position[1])
    time.sleep(0.3)
    
    # 2. Clear any existing value
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)
    
    # 3. Type the ISCI value
    print(f"[MEDIA_DETAILS] Typing ISCI: {isci_value}")
    pyautogui.typewrite(isci_value, interval=0.05)
    time.sleep(0.3)
    
    # 4. Press TAB to trigger lookup
    pyautogui.press('tab')
    time.sleep(1.0)  # Wait for lookup to complete
    
    if debugger:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot:
            debugger.save_image(screenshot, f"isci_{isci_value}_entered.png")
    
    return True, f"Entered ISCI: {isci_value}"


def delete_all_existing_media(debugger: Optional[Debugger] = None) -> Tuple[bool, str, int]:
    """
    Delete all existing media entries by iterating through aliases A, B, C, etc.
    Returns (success, message, deleted_count).
    """
    deleted_count = 0
    aliases_processed = 0
    
    # Step 1: Scroll to top first
    scroll_media_details_to_top(debugger)
    time.sleep(0.5)
    
    # Step 2: Iterate through alias letters
    for alias in ALIAS_LETTERS:
        # Step 3: Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            continue
        
        # Step 4: Check if asterisk is visible (end marker)
        if find_asterisk_row(screenshot, debugger):
            print(f"[MEDIA_DETAILS] Found asterisk - stopping deletion at Alias {alias}")
            break
        
        # Step 5: Find alias row
        alias_pos = find_alias_row(screenshot, alias, debugger, f"delete_{alias}")
        
        if alias_pos:
            # Step 6: Delete media at this position
            success, msg = delete_media_at_position(alias_pos, debugger, f"delete_{alias}")
            if success:
                deleted_count += 1
                print(f"[MEDIA_DETAILS] Deleted media for Alias {alias}")
            else:
                print(f"[MEDIA_DETAILS] Failed to delete Alias {alias}: {msg}")
            
            aliases_processed += 1
            
            # Step 7: Scroll after every 2 aliases
            if aliases_processed % 2 == 0:
                scroll_media_details_down(debugger)
                time.sleep(0.5)
        else:
            # Step 8: Handle alias not found
            if alias == 'A':
                # Step 8a: If Alias A not found, there might be no media
                print("[MEDIA_DETAILS] Alias A not found - no existing media")
                break
            else:
                # Step 8b: Try scrolling to find more
                scroll_media_details_down(debugger)
                time.sleep(0.5)
                
                # Step 8c: Check again after scroll
                screenshot = computer_vision_utils.take_screenshot()
                if screenshot and find_asterisk_row(screenshot, debugger):
                    print(f"[MEDIA_DETAILS] Found asterisk after scroll")
                    break
    
    # Step 9: Return result
    return True, f"Deleted {deleted_count} existing media entries", deleted_count


def enter_all_isci_values(isci_list: List[str], debugger: Optional[Debugger] = None) -> Tuple[bool, str, int]:
    """
    Enter all ISCI values from the instruction.
    Returns (success, message, entered_count).
    """
    # Step 1: Handle empty ISCI list
    if not isci_list:
        return True, "No ISCI values to enter", 0
    
    entered_count = 0
    
    # Step 2: Scroll to top first
    scroll_media_details_to_top(debugger)
    time.sleep(0.5)
    
    # Step 3: Iterate through ISCI values
    for i, isci_value in enumerate(isci_list):
        # Step 4: Determine alias letter for this entry
        alias_letter = ALIAS_LETTERS[i] if i < len(ALIAS_LETTERS) else '*'
        
        # Step 5: Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, f"Failed to take screenshot for ISCI {i+1}", entered_count
        
        # Step 6: Find the alias row (or asterisk for new entries)
        target_alias = alias_letter if i < len(ALIAS_LETTERS) else '*'
        alias_pos = find_alias_row(screenshot, target_alias, debugger, f"enter_{target_alias}")
        
        # Step 7: Fallback to asterisk row if alias not found
        if alias_pos is None:
            alias_pos = find_alias_row(screenshot, '*', debugger, f"enter_asterisk_{i}")
        
        if alias_pos:
            # Step 8: Type ISCI and tab
            success, msg = type_isci_and_tab(alias_pos, isci_value, debugger)
            if success:
                entered_count += 1
                print(f"[MEDIA_DETAILS] Entered ISCI {entered_count}: {isci_value}")
            else:
                print(f"[MEDIA_DETAILS] Failed to enter ISCI: {msg}")
                return False, msg, entered_count
            
            # Step 9: Scroll after every 2nd alias (B, D, F, H, etc.)
            if (i + 1) % 2 == 0:
                scroll_media_details_down(debugger)
                time.sleep(0.5)
        else:
            # Step 10: Return failure if position not found
            return False, f"Could not find position for ISCI {i+1}", entered_count
    
    # Step 11: Return success
    return True, f"Successfully entered {entered_count} ISCI values", entered_count


def verify_isci_entries(expected_isci_list: List[str], debugger: Optional[Debugger] = None) -> Tuple[bool, str, dict]:
    """
    Verify that all ISCI values were entered correctly.
    """
    verification_results = {}
    all_verified = True
    
    # Step 1: Scroll to top
    scroll_media_details_to_top(debugger)
    time.sleep(0.5)
    
    # Step 2: Iterate through expected ISCI values
    for i, expected_isci in enumerate(expected_isci_list):
        # Step 3: Determine alias letter
        alias_letter = ALIAS_LETTERS[i] if i < len(ALIAS_LETTERS) else '?'
        
        # Step 4: Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            verification_results[alias_letter] = {"success": False, "message": "Screenshot failed"}
            all_verified = False
            continue
        
        # Step 5: Find the alias row
        alias_pos = find_alias_row(screenshot, alias_letter, debugger, f"verify_{alias_letter}")
        
        if alias_pos:
            # Step 6: Define and crop ISCI cell region
            isci_region = (alias_pos[0] - 50, alias_pos[1] - 10, 120, 25)
            cropped = computer_vision_utils.crop_image(screenshot, *isci_region)
            
            if cropped is not None:
                # Step 7: Extract text using OCR
                success, extracted_text = scanner.extract_text(cropped)
                if success:
                    extracted_text = extracted_text.strip()
                    # Step 8: Compare expected vs extracted
                    if expected_isci.upper() in extracted_text.upper():
                        verification_results[alias_letter] = {
                            "success": True, 
                            "message": f"Verified: {extracted_text}"
                        }
                    else:
                        verification_results[alias_letter] = {
                            "success": False, 
                            "message": f"Mismatch: expected '{expected_isci}', got '{extracted_text}'"
                        }
                        all_verified = False
                else:
                    verification_results[alias_letter] = {"success": False, "message": "OCR extraction failed"}
                    all_verified = False
        else:
            verification_results[alias_letter] = {"success": False, "message": "Alias row not found"}
            all_verified = False
        
        # Step 9: Scroll after every 2 aliases
        if (i + 1) % 2 == 0:
            scroll_media_details_down(debugger)
            time.sleep(0.5)
    
    # Step 10: Return verification summary
    if all_verified:
        return True, f"All {len(expected_isci_list)} ISCI values verified", verification_results
    else:
        failed = [k for k, v in verification_results.items() if not v["success"]]
        return False, f"Verification failed for aliases: {', '.join(failed)}", verification_results
