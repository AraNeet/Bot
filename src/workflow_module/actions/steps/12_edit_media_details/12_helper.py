#!/usr/bin/env python3
"""
Helper functions for Step 12: Edit Media Details
Handles delete and input of ISCI values row by row.
"""

from typing import Tuple, Optional, List, Dict
import time
import pyautogui
import cv2

from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Initialize TextScanner
scanner = TextScanner()

# Constants
# Work area - subwindow containing Definition, Media Details, and Assignment sections
WORK_AREA = (200, 425, 1450, 570)  # x, y, width, height

# Scroll area - only area that allows scrolling in the subwindow
SCROLL_AREA = (1625, 460, 20, 540)  # x, y, width, height

# Generate alphabet dynamically (A-Z)
def get_alphabet():
    """Return list of uppercase letters A-Z."""
    return [chr(i) for i in range(ord('A'), ord('Z') + 1)]

def get_expected_letter(position: int) -> str:
    """Get the expected letter at a given position (0=A, 1=B, etc.)."""
    if 0 <= position < 26:
        return chr(ord('A') + position)
    return None

def get_letter_position(letter: str) -> int:
    """Get the position of a letter (A=0, B=1, etc.). Returns -1 if not a letter."""
    if letter and len(letter) == 1 and letter.isalpha():
        return ord(letter.upper()) - ord('A')
    return -1

def scroll_down_once() -> bool:
    """Scroll down once in the subwindow."""
    scroll_x = SCROLL_AREA[0] + SCROLL_AREA[2] // 2
    scroll_y = SCROLL_AREA[1] + SCROLL_AREA[3] // 2
    
    pyautogui.moveTo(scroll_x, scroll_y, duration=0.2)
    time.sleep(0.1)
    pyautogui.scroll(-8)
    time.sleep(0.4)
    return True

def scroll_up_once() -> bool:
    """Scroll up once in the subwindow."""
    scroll_x = SCROLL_AREA[0] + SCROLL_AREA[2] // 2
    scroll_y = SCROLL_AREA[1] + SCROLL_AREA[3] // 2
    
    pyautogui.moveTo(scroll_x, scroll_y, duration=0.2)
    time.sleep(0.1)
    pyautogui.scroll(8)
    time.sleep(0.4)
    return True

def find_aliases_in_work_area(screenshot, debugger: Optional[Debugger] = None, save_image: bool = False) -> List[Dict]:
    """
    Find all alias letters (A-Z) and * in the alias column.
    Returns list sorted by Y position (top to bottom).
    
    Handles OCR corrections (I->1, O->0, etc.) and fills gaps using row spacing.
    """
    ALIAS_COLUMN_WIDTH = 60
    
    # OCR corrections: what OCR might read -> what it should be
    OCR_FIXES = {
        '1': 'I', '|': 'I',  # I misread
        '0': 'O',             # O misread  
        '@': 'Q', '9': 'Q',   # Q misread
    }
    
    # Crop to work area, then to alias column
    cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if cropped is None:
        return []
    
    alias_column = cropped[:, 0:ALIAS_COLUMN_WIDTH]
    if debugger and save_image:
        debugger.save_image(alias_column, "alias_column_scan.png")
    
    # Get OCR results
    success, data = scanner.get_text_data(alias_column)
    if not success:
        return []
    
    # Collect single characters with positions, sorted by Y
    raw_results = []
    for i, text in enumerate(data['text']):
        text_clean = text.strip().upper()
        if len(text_clean) == 1:
            bbox = data['bbox'][i]
            raw_results.append({
                'raw_text': text_clean,
                'alias_x': WORK_AREA[0] + (bbox[0] + bbox[2]) // 2,
                'row_y': WORK_AREA[1] + (bbox[1] + bbox[3]) // 2,
                'local_bbox': bbox
            })
    raw_results.sort(key=lambda x: x['row_y'])
    print(f"[MEDIA_DETAILS] Raw results: {raw_results}")
    
    print(f"[MEDIA_DETAILS] Raw OCR (sorted by Y): {[r['raw_text'] for r in raw_results]}")
    
    # Process OCR results with corrections
    aliases = []
    seen = set()
    
    for idx, result in enumerate(raw_results):
        text = result['raw_text']
        prev_text = raw_results[idx - 1]['raw_text'] if idx > 0 else None
        next_text = raw_results[idx + 1]['raw_text'] if idx < len(raw_results) - 1 else None
        
        # Determine the alias letter
        if text.isalpha():
            alias = text
        elif text == '*':
            alias = '*'
        elif text in OCR_FIXES:
            alias = OCR_FIXES[text]
            print(f"[MEDIA_DETAILS] OCR fix: '{text}' -> '{alias}' (prev={prev_text}, next={next_text})")
        else:
            continue
        
        # Add if not duplicate
        if alias not in seen:
            seen.add(alias)
            aliases.append({
                'alias': alias,
                'alias_x': result['alias_x'],
                'row_y': result['row_y'],
                'local_bbox': result['local_bbox']
            })
    
    aliases.sort(key=lambda x: x['row_y'])
    
    # Calculate average row spacing (exclude gaps > 100px)
    letter_aliases = [a for a in aliases if a['alias'] != '*']
    spacings = [
        letter_aliases[i + 1]['row_y'] - letter_aliases[i]['row_y']
        for i in range(len(letter_aliases) - 1)
        if 0 < letter_aliases[i + 1]['row_y'] - letter_aliases[i]['row_y'] < 100
    ]
    avg_spacing = sum(spacings) / len(spacings) if spacings else 30
    typical_x = letter_aliases[0]['alias_x'] if letter_aliases else WORK_AREA[0] + 30
    
    print(f"[MEDIA_DETAILS] Average row spacing: {avg_spacing:.1f}px")
    
    # Fill gaps in sequence (e.g., H -> K means I, J are missing)
    aliases_to_add = []
    for i in range(len(aliases) - 1):
        curr, nxt = aliases[i], aliases[i + 1]
        if curr['alias'] == '*' or nxt['alias'] == '*':
            continue
        
        curr_idx, nxt_idx = get_letter_position(curr['alias']), get_letter_position(nxt['alias'])
        if curr_idx >= 0 and nxt_idx > curr_idx + 1:
            # Gap found - fill missing letters
            missing = [get_expected_letter(j) for j in range(curr_idx + 1, nxt_idx)]
            step = (nxt['row_y'] - curr['row_y']) / (len(missing) + 1)
            
            print(f"[MEDIA_DETAILS] Gap: {curr['alias']} -> {nxt['alias']}, filling: {missing}")
            for j, letter in enumerate(missing):
                if letter not in seen:
                    seen.add(letter)
                    aliases_to_add.append({
                        'alias': letter,
                        'alias_x': typical_x,
                        'row_y': int(curr['row_y'] + step * (j + 1)),
                        'local_bbox': [0, 0, 20, 20]
                    })
    
    # Check for missing letters before '*'
    # Calculate how many rows could fit in the space between last letter and '*'
    asterisk = next((a for a in aliases if a['alias'] == '*'), None)
    last_letter = next((a for a in reversed(aliases) if a['alias'].isalpha()), None)
    
    if asterisk and last_letter and avg_spacing > 0:
        space = asterisk['row_y'] - last_letter['row_y']
        last_idx = get_letter_position(last_letter['alias'])
        
        # Calculate how many rows could fit in this space
        # Use 1.3x threshold to be more sensitive to gaps
        estimated_missing_count = int((space / avg_spacing) - 0.7)  # -0.7 accounts for the normal gap to '*'
        
        print(f"[MEDIA_DETAILS] Space before '*': {space:.1f}px, avg_spacing: {avg_spacing:.1f}px, estimated missing: {estimated_missing_count}")
        
        if estimated_missing_count > 0 and last_idx < 25:
            # Add all missing letters
            for i in range(estimated_missing_count):
                next_letter = get_expected_letter(last_idx + 1 + i)
                if next_letter and next_letter not in seen:
                    interpolated_y = int(last_letter['row_y'] + avg_spacing * (i + 1))
                    print(f"[MEDIA_DETAILS] Adding missing letter before '*': '{next_letter}' at Y={interpolated_y}")
                    seen.add(next_letter)
                    aliases_to_add.append({
                        'alias': next_letter,
                        'alias_x': typical_x,
                        'row_y': interpolated_y,
                        'local_bbox': [0, 0, 20, 20]
                    })
    
    # Combine and sort
    aliases.extend(aliases_to_add)
    aliases.sort(key=lambda x: x['row_y'])
    
    # Log results and any remaining gaps
    alias_letters = [a['alias'] for a in aliases if a['alias'] != '*']
    if alias_letters:
        first_idx, last_idx = get_letter_position(alias_letters[0]), get_letter_position(alias_letters[-1])
        expected = {get_expected_letter(i) for i in range(max(0, first_idx), last_idx + 1)}
        missing = expected - set(alias_letters)
        if missing:
            print(f"[MEDIA_DETAILS] WARNING: Still missing: {sorted(missing)}")
    
    print(f"[MEDIA_DETAILS] Aliases found: {[a['alias'] for a in aliases]}")
    return aliases


def find_header_positions(screenshot, debugger: Optional[Debugger] = None) -> Dict[str, int]:
    """
    Find the column header positions within the WORK_AREA.
    Returns dict with column name -> X position (center of the column data field).
    
    Table structure (approximate):
    - Alias: x ~127-145
    - Feeds: x ~150-195 (dropdown)
    - ISCI/Ad-ID: x ~200-280 (this is the field we need to click)
    - CID: x ~280-340
    - Length: x ~340-400
    """
    # Crop to work area
    cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if cropped is None:
        return {}
    
    headers = {}
    
    # Find "ISCI" or "Ad-ID" header text
    success, found, bbox = scanner.find_text_with_position(cropped, "ISCI", case_sensitive=False)
    if success and found:
        # The header text position - use center of the text
        # bbox = [x, y, width, height]
        header_x = WORK_AREA[0] + bbox[0] + bbox[2] // 2
        print(f"[MEDIA_DETAILS] Found 'ISCI' header text at X={header_x}")
        # The data field below is roughly at the same X position
        headers['ISCI'] = header_x
    else:
        # Try "Ad-ID"
        success, found, bbox = scanner.find_text_with_position(cropped, "Ad-ID", case_sensitive=False)
        if success and found:
            header_x = WORK_AREA[0] + bbox[0] + bbox[2] // 2
            print(f"[MEDIA_DETAILS] Found 'Ad-ID' header text at X={header_x}")
            headers['ISCI'] = header_x
    
    # Also find "Feeds" header to verify we're not clicking there
    success, found, bbox = scanner.find_text_with_position(cropped, "Feeds", case_sensitive=False)
    if success and found:
        feeds_x = WORK_AREA[0] + bbox[0] + bbox[2] // 2
        headers['Feeds'] = feeds_x
        print(f"[MEDIA_DETAILS] Found 'Feeds' header at X={feeds_x}")
        
        # Ensure ISCI is to the right of Feeds
        if 'ISCI' in headers and headers['ISCI'] <= feeds_x + 30:
            # ISCI position is too close to Feeds, adjust it
            print(f"[MEDIA_DETAILS] WARNING: ISCI too close to Feeds, adjusting...")
            headers['ISCI'] = feeds_x + 80  # ISCI field is about 80px right of Feeds
    
    if debugger and headers:
        annotated = cropped.copy()
        for name, x_pos in headers.items():
            local_x = x_pos - WORK_AREA[0]
            color = (0, 255, 0) if name == 'ISCI' else (0, 0, 255)
            cv2.line(annotated, (local_x, 0), (local_x, cropped.shape[0]), color, 2)
            cv2.putText(annotated, name, (local_x + 5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        debugger.save_image(annotated, "header_positions.png")
    
    return headers


def click_on_alias_A(debugger: Optional[Debugger] = None) -> Tuple[bool, Dict[str, int]]:
    """
    First step: Find and click on the 'A' alias to focus Media Details.
    Also returns header positions.
    
    If 'A' is not visible, scrolls up to find it.
    """
    print("[MEDIA_DETAILS] Step 1: Finding and clicking on alias 'A'...")
    
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, {}
    
    # Find aliases
    aliases = find_aliases_in_work_area(screenshot, debugger, save_image=True)
    headers = find_header_positions(screenshot, debugger)
    
    # Look for 'A'
    alias_A = None
    for a in aliases:
        if a['alias'] == 'A':
            alias_A = a
            break
    
    # If 'A' not found, try scrolling up to find it
    if alias_A is None:
        print("[MEDIA_DETAILS] Alias 'A' not visible, scrolling up to find it...")
        
        for scroll_attempt in range(15):
            scroll_up_once()
            screenshot = computer_vision_utils.take_screenshot()
            if screenshot is None:
                continue
            
            aliases = find_aliases_in_work_area(screenshot)
            headers = find_header_positions(screenshot, debugger)
            
            for a in aliases:
                if a['alias'] == 'A':
                    alias_A = a
                    print(f"[MEDIA_DETAILS] Found 'A' after {scroll_attempt + 1} scroll ups")
                    break
            
            if alias_A:
                break
    
    if alias_A is None:
        print("[MEDIA_DETAILS] Could not find alias 'A' even after scrolling up")
        # Last resort: try clicking on the first visible alias
        if aliases:
            first_alias = aliases[0]
            print(f"[MEDIA_DETAILS] Clicking on first visible alias instead: {first_alias['alias']}")
            pyautogui.click(first_alias['alias_x'], first_alias['row_y'])
            time.sleep(0.5)
            return True, headers
        return False, headers
    
    # Click on the 'A' alias
    click_x = alias_A['alias_x']
    click_y = alias_A['row_y']
    
    print(f"[MEDIA_DETAILS] Clicking on alias 'A' at ({click_x}, {click_y})")
    
    if debugger:
        annotated = screenshot.copy()
        cv2.circle(annotated, (click_x, click_y), 10, (0, 255, 0), 2)
        cv2.putText(annotated, "CLICK A", (click_x + 15, click_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        debugger.save_image(annotated, "click_alias_A.png")
    
    pyautogui.click(click_x, click_y)
    time.sleep(0.5)
    
    return True, headers


def collect_all_aliases(debugger: Optional[Debugger] = None) -> set:
    """
    Scroll down and collect ALL alias letters until we find the * row.
    Returns a SET of unique alias letters found (excluding *).
    Includes gap-filling logic to add any letters that OCR consistently missed.
    """
    print("[MEDIA_DETAILS] Collecting all aliases (scrolling until * found)...")
    
    # Use a SET to store unique aliases
    all_aliases = set()
    found_asterisk = False
    max_scrolls = 20
    
    for scroll_num in range(max_scrolls):
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            continue
        
        # Find visible aliases
        visible = find_aliases_in_work_area(screenshot, debugger if scroll_num == 0 else None)
        visible_letters = [a['alias'] for a in visible]
        
        print(f"[MEDIA_DETAILS] Scroll {scroll_num}: Visible = {visible_letters}")
        
        # Add letter aliases to SET (not *)
        for a in visible:
            if a['alias'] != '*':
                all_aliases.add(a['alias'])
        
        # Check if we found *
        if '*' in visible_letters:
            print(f"[MEDIA_DETAILS] Found '*' - end of aliases")
            found_asterisk = True
            if debugger:
                debugger.save_image(screenshot, "found_asterisk.png")
            break
        
        # Scroll down
        scroll_down_once()
    
    print(f"[MEDIA_DETAILS] Total unique aliases in SET before gap-fill: {sorted(all_aliases)}")
    
    # =========================================================================
    # FINAL GAP-FILLING: Fill any missing letters in the collected set
    # If we found A, B, C, D, E, F, G, H, I, K (missing J), fill it in
    # =========================================================================
    if all_aliases:
        letter_aliases = sorted([a for a in all_aliases if a.isalpha()])
        if len(letter_aliases) >= 2:
            first_idx = get_letter_position(letter_aliases[0])
            last_idx = get_letter_position(letter_aliases[-1])
            
            # Find all letters that should exist between first and last
            expected_letters = {get_expected_letter(i) for i in range(first_idx, last_idx + 1)}
            missing_letters = expected_letters - all_aliases
            
            if missing_letters:
                print(f"[MEDIA_DETAILS] GAP-FILL: Adding missing letters: {sorted(missing_letters)}")
                all_aliases.update(missing_letters)
            else:
                print(f"[MEDIA_DETAILS] No gaps detected in alias sequence")
    
    print(f"[MEDIA_DETAILS] Total unique aliases in SET after gap-fill: {sorted(all_aliases)}")
    
    return all_aliases


def scroll_back_to_headers(debugger: Optional[Debugger] = None) -> bool:
    """
    Scroll back up until the column headers are visible.
    This ensures alias A isn't cut off at the top.
    Looks for "Alias" header text to confirm we're at the top.
    """
    print("[MEDIA_DETAILS] Scrolling back up to headers (so alias A isn't cut off)...")
    
    max_scrolls = 25
    
    for scroll_num in range(max_scrolls):
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            scroll_up_once()
            continue
        
        # Check if "Alias" header is visible (indicates we're at the top)
        headers = find_header_positions(screenshot)
        aliases = find_aliases_in_work_area(screenshot)
        visible_letters = [a['alias'] for a in aliases]
        
        print(f"[MEDIA_DETAILS] Scroll up {scroll_num}: Headers found = {list(headers.keys())}, Aliases = {visible_letters}")
        
        # Check if we can see the "Alias" header AND alias 'A'
        # The header text "Alias" should be visible when we're at the very top
        cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
        if cropped is not None:
            success, found, _ = scanner.find_text_with_position(cropped, "Alias", case_sensitive=False)
            
            if success and found and 'A' in visible_letters:
                print(f"[MEDIA_DETAILS] Found headers and alias 'A' - at the top, ready to process")
                if debugger:
                    debugger.save_image(screenshot, "back_at_headers.png")
                return True
        
        # Scroll up
        scroll_up_once()
    
    # Even if we didn't find the header, check if A is visible
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is not None:
        aliases = find_aliases_in_work_area(screenshot)
        visible_letters = [a['alias'] for a in aliases]
        if 'A' in visible_letters:
            print(f"[MEDIA_DETAILS] Alias 'A' is visible - proceeding")
            if debugger:
                debugger.save_image(screenshot, "back_at_headers.png")
            return True
    
    print(f"[MEDIA_DETAILS] Warning: Could not scroll back to headers after {max_scrolls} scrolls")
    return False


def find_alias_row(alias_letter: str, debugger: Optional[Debugger] = None) -> Optional[Dict]:
    """Find a specific alias row in the current view."""
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return None
    
    aliases = find_aliases_in_work_area(screenshot)
    
    for a in aliases:
        if a['alias'] == alias_letter:
            return a
    
    return None


def delete_media_for_row(isci_x: int, row_y: int, alias_letter: str, debugger: Optional[Debugger] = None) -> bool:
    """
    Right-click on the ISCI/Ad-ID field and select 'Delete Media' from context menu.
    
    NOTE: When hovering over a row, a second empty input field appears below the populated one.
    We need to click on the FIRST (top) ISCI field which contains the actual value.
    The row_y from alias detection should point to the first field.
    
    Args:
        isci_x: X position of ISCI column (from header detection)
        row_y: Y position of the row (should be the first/top ISCI field)
        alias_letter: The alias letter (for logging)
    """
    # Use the row_y directly - this should be aligned with the alias letter
    # which is on the same line as the FIRST (populated) ISCI field
    click_pos = (isci_x, row_y)
    print(f"[MEDIA_DETAILS] Right-clicking FIRST ISCI field for row {alias_letter} at ({isci_x}, {row_y})...")
    
    # Save debug image showing where we're about to click
    if debugger:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is not None:
            annotated = screenshot.copy()
            # Draw crosshair at click position
            cv2.line(annotated, (isci_x - 20, row_y), (isci_x + 20, row_y), (0, 0, 255), 2)
            cv2.line(annotated, (isci_x, row_y - 20), (isci_x, row_y + 20), (0, 0, 255), 2)
            cv2.circle(annotated, (isci_x, row_y), 10, (0, 255, 255), 2)
            cv2.putText(annotated, f"RIGHT-CLICK {alias_letter} (1st field)", (isci_x + 15, row_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            debugger.save_image(annotated, f"before_rightclick_{alias_letter}.png")
    
    # Move to ISCI field (first/top field aligned with alias letter)
    pyautogui.moveTo(click_pos[0], click_pos[1], duration=0.3)
    time.sleep(0.3)
    
    # First right-click to SELECT the field
    print(f"[MEDIA_DETAILS] First right-click to select field...")
    pyautogui.click(button='right')
    time.sleep(0.5)
    
    # Second right-click to OPEN the context menu
    print(f"[MEDIA_DETAILS] Second right-click to open context menu...")
    pyautogui.click(button='right')
    time.sleep(1.5)
    
    # Take screenshot to find "Delete Media"
    screenshot = computer_vision_utils.take_screenshot()
    if debugger:
        debugger.save_image(screenshot, f"context_menu_{alias_letter}.png")
    
    # Search for "Delete Media"
    success, found, bbox = scanner.find_text_with_position(screenshot, "Delete Media", case_sensitive=False)
    
    if success and found:
        click_x = bbox[0] + bbox[2] // 2
        click_y = bbox[1] + bbox[3] // 2
        print(f"[MEDIA_DETAILS] Found 'Delete Media' at ({click_x}, {click_y})")
        
        if debugger:
            annotated = screenshot.copy()
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[0]+bbox[2], bbox[1]+bbox[3]), (0, 255, 0), 2)
            cv2.circle(annotated, (click_x, click_y), 5, (0, 0, 255), -1)
            debugger.save_image(annotated, f"delete_media_click_{alias_letter}.png")
        
        pyautogui.click(click_x, click_y)
        time.sleep(0.5)
        print(f"[MEDIA_DETAILS] Clicked 'Delete Media' for row {alias_letter}")
        
        # Wait for delete to complete and second field to disappear
        time.sleep(0.3)
        return True
    else:
        print(f"[MEDIA_DETAILS] 'Delete Media' not found for row {alias_letter}")
        if debugger:
            debugger.save_image(screenshot, f"menu_not_found_{alias_letter}.png")
        pyautogui.press('escape')
        time.sleep(0.3)
        return False


def enter_isci_for_row(isci_x: int, row_y: int, isci: str, alias_letter: str, debugger: Optional[Debugger] = None) -> bool:
    """
    Click on the empty ISCI field and enter the ISCI value.
    
    Args:
        isci_x: X position of ISCI column
        row_y: Y position of the row
        isci: ISCI value to enter
        alias_letter: The alias letter (for logging)
    """
    click_pos = (isci_x, row_y)
    print(f"[MEDIA_DETAILS] Clicking empty ISCI field for row {alias_letter} at ({isci_x}, {row_y})...")
    
    # Save debug image showing where we're about to click
    if debugger:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is not None:
            annotated = screenshot.copy()
            # Draw crosshair at click position
            cv2.line(annotated, (isci_x - 20, row_y), (isci_x + 20, row_y), (0, 255, 0), 2)
            cv2.line(annotated, (isci_x, row_y - 20), (isci_x, row_y + 20), (0, 255, 0), 2)
            cv2.circle(annotated, (isci_x, row_y), 10, (0, 255, 0), 2)
            cv2.putText(annotated, f"INPUT {alias_letter}: {isci}", (isci_x + 15, row_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            debugger.save_image(annotated, f"before_input_{alias_letter}.png")
    
    # Click on the empty ISCI field to focus it
    # Field should already be empty after Delete Media was clicked
    pyautogui.click(click_pos[0], click_pos[1])
    time.sleep(0.3)
    
    # Type the new ISCI value directly (no shortcuts needed - field is empty)
    print(f"[MEDIA_DETAILS] Typing ISCI: {isci}")
    pyautogui.typewrite(isci, interval=0.03)
    time.sleep(0.2)
    
    # Press Tab to confirm and trigger auto-populate
    pyautogui.press('tab')
    time.sleep(1.0)
    
    # Check for "No Matches" popup
    screenshot = computer_vision_utils.take_screenshot()
    if debugger:
        debugger.save_image(screenshot, f"after_input_{alias_letter}.png")
    
    success, found, _ = scanner.find_text_with_position(screenshot, "No Matches", case_sensitive=False)
    
    if success and found:
        print(f"[MEDIA_DETAILS] WARNING: 'No Matches' popup for {isci}")
        pyautogui.press('enter')
        time.sleep(0.3)
        return False
    
    print(f"[MEDIA_DETAILS] Successfully entered ISCI for row {alias_letter}")
    return True


def process_media_rows(isci_list: List[str], debugger: Optional[Debugger] = None) -> Tuple[bool, str, List[str]]:
    """
    Main function to process Media Details rows.
    
    NOTE: When hovering over a row, a second empty input field appears below the ISCI field.
    This pushes all rows below it down. When the mouse moves away, the extra field disappears
    and rows shift back up. We must account for this dynamic row positioning.
    
    Tracking: Uses a 'completed_aliases' SET and 'pending_aliases' LIST to track progress.
    After each row is processed, it's moved from pending to completed.
    
    Steps:
    1. Click on alias 'A' first to focus Media Details and get header positions
    2. Scroll down to collect ALL aliases (as a SET) until * is found
    3. Scroll back up to headers so alias A isn't cut off
    4. Build list of aliases to process + create completed/pending tracking
    5. For each alias row in order:
       5a. Take fresh screenshot and find row position
       5b. If not visible, scroll down to find it
       5c. Right-click ISCI field twice and click "Delete Media"
       5d. Click away to neutral position (removes hover state/extra field)
       5e. Re-scan to find row position FRESH (positions may have shifted)
       5f. Click empty ISCI field and enter new ISCI value
       5g. Click away again before processing next row
       5h. Add alias to completed SET, remove from pending LIST
    6. Final summary - log completed, pending, and errors
    """
    print(f"[MEDIA_DETAILS] Processing {len(isci_list)} ISCI values...")
    
    # =========================================================================
    # STEP 1: Click on alias 'A' first and get header positions
    # =========================================================================
    print("\n[MEDIA_DETAILS] === STEP 1: Click on alias 'A' and get headers ===")
    success, headers = click_on_alias_A(debugger)
    if not success:
        return False, "Could not find or click alias 'A'", ["Alias A not found"]
    
    if 'ISCI' not in headers:
        return False, "Could not find ISCI/Ad-ID header", ["Header not found"]
    
    isci_x = headers['ISCI']
    print(f"[MEDIA_DETAILS] ISCI column X position: {isci_x}")
    
    time.sleep(0.5)
    
    # =========================================================================
    # STEP 2: Scroll down and collect ALL aliases (as a SET) until * is found
    # =========================================================================
    print("\n[MEDIA_DETAILS] === STEP 2: Collect all aliases until * is found ===")
    all_aliases = collect_all_aliases(debugger)  # Returns a SET
    
    if not all_aliases:
        return False, "Could not find any alias rows", ["No aliases found"]
    
    print(f"[MEDIA_DETAILS] Found {len(all_aliases)} unique aliases: {sorted(all_aliases)}")
    
    # =========================================================================
    # STEP 3: Scroll back up to headers (so alias A isn't cut off)
    # =========================================================================
    print("\n[MEDIA_DETAILS] === STEP 3: Scroll back up to headers ===")
    scroll_back_to_headers(debugger)
    time.sleep(0.5)
    
    errors = []
    
    # =========================================================================
    # STEP 4: Build list of aliases to process (in order: A, B, C, ...)
    # =========================================================================
    print("\n[MEDIA_DETAILS] === STEP 4: Build processing list ===")
    aliases_to_process = []
    for i, isci in enumerate(isci_list):
        alias_letter = get_expected_letter(i)  # 0=A, 1=B, etc.
        if alias_letter and alias_letter in all_aliases:
            aliases_to_process.append((alias_letter, isci))
    
    # Create tracking sets/lists
    pending_aliases = [a[0] for a in aliases_to_process]  # List of aliases still to process
    completed_aliases = set()  # Set of aliases that have been successfully processed
    
    print(f"[MEDIA_DETAILS] Will process {len(aliases_to_process)} rows in order: {pending_aliases}")
    print(f"[MEDIA_DETAILS] Pending: {pending_aliases}, Completed: {sorted(completed_aliases)}")
    
    # =========================================================================
    # STEP 5: Process each row one by one (delete then input)
    # =========================================================================
    print(f"\n[MEDIA_DETAILS] === STEP 5: Process each row ===")
    
    for idx, (alias_letter, isci) in enumerate(aliases_to_process):
        print(f"\n[MEDIA_DETAILS] --- Row {idx+1}/{len(aliases_to_process)}: {alias_letter} -> {isci} ---")
        
        # ---------------------------------------------------------------------
        # STEP 5a: Take fresh screenshot and find current row position
        # ---------------------------------------------------------------------
        screenshot = computer_vision_utils.take_screenshot()
        aliases_visible = find_aliases_in_work_area(screenshot)
        
        row_data = None
        for a in aliases_visible:
            if a['alias'] == alias_letter:
                row_data = a
                break
        
        # ---------------------------------------------------------------------
        # STEP 5b: If not visible, scroll down to find it
        # NOTE: If we find '*' row, stop scrolling - no more aliases after it
        # ---------------------------------------------------------------------
        if row_data is None:
            print(f"[MEDIA_DETAILS] Step 5b: Alias {alias_letter} not visible, scrolling...")
            found_asterisk = False
            
            for scroll_attempt in range(10):
                scroll_down_once()
                screenshot = computer_vision_utils.take_screenshot()
                aliases_visible = find_aliases_in_work_area(screenshot)
                visible_letters = [a['alias'] for a in aliases_visible]
                
                # Check if we found the target alias
                for a in aliases_visible:
                    if a['alias'] == alias_letter:
                        row_data = a
                        break
                
                if row_data:
                    print(f"[MEDIA_DETAILS] Found {alias_letter} after {scroll_attempt + 1} scrolls")
                    break
                
                # Check if we found '*' - means no more aliases exist after this
                if '*' in visible_letters:
                    print(f"[MEDIA_DETAILS] Found '*' row - no more aliases after this point")
                    print(f"[MEDIA_DETAILS] Alias {alias_letter} does not exist (reached end of aliases)")
                    found_asterisk = True
                    break
                
                # -----------------------------------------------------------------
                # If OCR can't find target alias but neighbors are visible,
                # estimate position from neighbors (handles OCR miss for known alias)
                # -----------------------------------------------------------------
                target_idx = get_letter_position(alias_letter)
                prev_letter = get_expected_letter(target_idx - 1) if target_idx > 0 else None
                next_letter = get_expected_letter(target_idx + 1) if target_idx < 25 else None
                
                prev_data = next((a for a in aliases_visible if a['alias'] == prev_letter), None)
                next_data = next((a for a in aliases_visible if a['alias'] == next_letter), None)
                
                if prev_data and next_data:
                    # Both neighbors visible - interpolate position
                    estimated_y = (prev_data['row_y'] + next_data['row_y']) // 2
                    print(f"[MEDIA_DETAILS] OCR missed {alias_letter}, estimating Y from {prev_letter}({prev_data['row_y']}) and {next_letter}({next_data['row_y']}) -> Y={estimated_y}")
                    row_data = {
                        'alias': alias_letter,
                        'alias_x': prev_data['alias_x'],
                        'row_y': estimated_y,
                        'local_bbox': [0, 0, 20, 20],
                        'estimated': True
                    }
                    break
                elif prev_data:
                    # Only previous neighbor visible - extrapolate down
                    # Calculate spacing from visible aliases
                    letter_aliases = [a for a in aliases_visible if a['alias'].isalpha()]
                    letter_aliases.sort(key=lambda x: x['row_y'])
                    spacings = [letter_aliases[i+1]['row_y'] - letter_aliases[i]['row_y'] 
                                for i in range(len(letter_aliases) - 1)
                                if 0 < letter_aliases[i+1]['row_y'] - letter_aliases[i]['row_y'] < 100]
                    avg_spacing = sum(spacings) / len(spacings) if spacings else 30
                    
                    estimated_y = int(prev_data['row_y'] + avg_spacing)
                    print(f"[MEDIA_DETAILS] OCR missed {alias_letter}, estimating Y from {prev_letter}({prev_data['row_y']}) + {avg_spacing:.0f}px -> Y={estimated_y}")
                    row_data = {
                        'alias': alias_letter,
                        'alias_x': prev_data['alias_x'],
                        'row_y': estimated_y,
                        'local_bbox': [0, 0, 20, 20],
                        'estimated': True
                    }
                    break
            
            # If we found asterisk but not the target alias, skip this row
            if found_asterisk and row_data is None:
                errors.append(f"Alias {alias_letter} does not exist (found '*' row)")
                print(f"[MEDIA_DETAILS] Skipping {alias_letter} - alias not found before '*'")
                continue
        
        if row_data is None:
            errors.append(f"Could not find row {alias_letter}")
            print(f"[MEDIA_DETAILS] ERROR: Could not find row {alias_letter}")
            continue
        
        row_y = row_data['row_y']
        print(f"[MEDIA_DETAILS] Row {alias_letter} found at Y={row_y}")
        
        # ---------------------------------------------------------------------
        # STEP 5c: Right-click ISCI field twice and click "Delete Media"
        # NOTE: When hovering on this row, it adds a second empty input field
        #       This pushes rows below down. When we move away, rows shift back.
        # ---------------------------------------------------------------------
        print(f"[MEDIA_DETAILS] Step 5c: Deleting existing media for {alias_letter}...")
        delete_media_for_row(isci_x, row_y, alias_letter, debugger)
        time.sleep(0.5)
        
        # ---------------------------------------------------------------------
        # STEP 5d: Click away to neutral position, then re-scan
        # This removes the hover state and extra field, letting rows settle
        # ---------------------------------------------------------------------
        print(f"[MEDIA_DETAILS] Step 5d: Clicking away to remove hover state...")
        # Click on the Alias column header area (neutral position)
        neutral_x = WORK_AREA[0] + 30  # Left side of work area
        neutral_y = WORK_AREA[1] + 10  # Top of work area (header area)
        pyautogui.click(neutral_x, neutral_y)
        time.sleep(0.5)
        
        # ---------------------------------------------------------------------
        # STEP 5e: Re-scan to find row position FRESH
        # Row positions shift when hover extra field disappears
        # ---------------------------------------------------------------------
        print(f"[MEDIA_DETAILS] Step 5e: Re-scanning for row {alias_letter} (positions may have shifted)...")
        screenshot = computer_vision_utils.take_screenshot()
        aliases_visible = find_aliases_in_work_area(screenshot)
        
        row_data = None
        for a in aliases_visible:
            if a['alias'] == alias_letter:
                row_data = a
                break
        
        if row_data:
            row_y = row_data['row_y']
            print(f"[MEDIA_DETAILS] Row {alias_letter} current position: Y={row_y}")
        else:
            print(f"[MEDIA_DETAILS] WARNING: Could not find row {alias_letter} after re-scan, using previous Y={row_y}")
        
        # ---------------------------------------------------------------------
        # STEP 5f: Click empty ISCI field and enter new ISCI value
        # ---------------------------------------------------------------------
        print(f"[MEDIA_DETAILS] Step 5f: Entering ISCI '{isci}' for {alias_letter}...")
        if not enter_isci_for_row(isci_x, row_y, isci, alias_letter, debugger):
            errors.append(f"Failed to enter ISCI for row {alias_letter}")
        
        time.sleep(0.3)
        
        # ---------------------------------------------------------------------
        # STEP 5g: Click away again to remove hover state before next row
        # This ensures the next row's position is accurate
        # ---------------------------------------------------------------------
        pyautogui.click(neutral_x, neutral_y)
        time.sleep(0.3)
        
        # ---------------------------------------------------------------------
        # STEP 5h: Mark alias as completed and remove from pending
        # ---------------------------------------------------------------------
        completed_aliases.add(alias_letter)
        if alias_letter in pending_aliases:
            pending_aliases.remove(alias_letter)
        
        print(f"[MEDIA_DETAILS] Completed row {alias_letter}")
        print(f"[MEDIA_DETAILS] Progress - Completed: {sorted(completed_aliases)}, Pending: {pending_aliases}")
    
    # =========================================================================
    # STEP 6: Final summary
    # =========================================================================
    print(f"\n[MEDIA_DETAILS] === STEP 6: Final Summary ===")
    print(f"[MEDIA_DETAILS] Completed aliases: {sorted(completed_aliases)}")
    print(f"[MEDIA_DETAILS] Pending aliases: {pending_aliases}")
    print(f"[MEDIA_DETAILS] Errors: {errors}")
    
    if errors:
        return False, f"Completed {len(completed_aliases)} rows with {len(errors)} errors. Pending: {pending_aliases}", errors
    
    return True, f"Successfully processed {len(completed_aliases)} rows: {sorted(completed_aliases)}", []


def scroll_to_media_details(debugger: Optional[Debugger] = None) -> bool:
    """
    Used for error recovery - just clicks on whatever alias is currently visible.
    Does NOT require 'A' - 'A' is only needed at the very beginning.
    """
    print("[MEDIA_DETAILS] Error recovery - finding any visible alias...")
    
    # Take screenshot and find any visible alias
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False
    
    aliases = find_aliases_in_work_area(screenshot)
    if not aliases:
        print("[MEDIA_DETAILS] No aliases found - trying to scroll")
        # Try scrolling a bit to find aliases
        scroll_down_once()
        screenshot = computer_vision_utils.take_screenshot()
        aliases = find_aliases_in_work_area(screenshot)
        
        if not aliases:
            print("[MEDIA_DETAILS] Still no aliases found")
            return False
    
    # Click on the first visible alias (whatever it is)
    first_alias = aliases[0]
    print(f"[MEDIA_DETAILS] Clicking on visible alias: {first_alias['alias']} (A only needed at start)")
    pyautogui.click(first_alias['alias_x'], first_alias['row_y'])
    time.sleep(0.3)
    
    return True


def verify_isci_entries(expected_isci_list: List[str], debugger: Optional[Debugger] = None) -> Tuple[bool, str, dict]:
    """Verify that all ISCI values were entered correctly."""
    print("[MEDIA_DETAILS] Verifying ISCI entries...")
    
    click_on_alias_A(debugger)
    all_aliases = collect_all_aliases(debugger)
    
    results = {}
    all_verified = True
    
    for i, expected_isci in enumerate(expected_isci_list):
        alias_letter = get_expected_letter(i)  # 0=A, 1=B, etc.
        
        if alias_letter and alias_letter in all_aliases:
            results[alias_letter] = {"success": True, "message": f"Row found for {expected_isci}"}
        else:
            results[alias_letter] = {"success": False, "message": "Row not found"}
            all_verified = False
    
    if all_verified:
        return True, f"Verified {len(expected_isci_list)} entries", results
    
    return False, "Some entries failed verification", results
