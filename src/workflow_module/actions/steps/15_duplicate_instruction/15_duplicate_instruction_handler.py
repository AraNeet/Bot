#!/usr/bin/env python3
"""
Handler for: Duplicate Instruction (context menu)

This module contains:
- Action: OCR search for "duplicate instruction" in a fixed screen region, then click it
- Verifier: Pass-through after action so the workflow continues without verification retries
- Error Handler: No retries (single attempt; fail fast)
"""

from typing import Tuple, Dict, Any, Optional

from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import (
    TextScanner,
    screen_center_from_crop_bbox,
    find_click_bbox_for_phrase_in_crop,
)
import time

scanner = TextScanner()

# (x, y, width, height) — screen region to search for "duplicate instruction"
DUPLICATE_INSTRUCTION_REGION = (110, 45, 135, 80)

SEARCH_PHRASE = "duplicate instruction"


# ============================================================================
# ACTION
# ============================================================================


def action(**kwargs) -> Tuple[bool, str]:
    """
    Search for "duplicate instruction" in DUPLICATE_INSTRUCTION_REGION via OCR, then click it.
    """
    print("[ACTION_HANDLER] Duplicate instruction: OCR search in region", DUPLICATE_INSTRUCTION_REGION)

    cropped = take_screenshot_and_crop(DUPLICATE_INSTRUCTION_REGION)
    if cropped is None:
        return False, "Failed to take screenshot and crop duplicate-instruction region"

    ok, bbox = find_click_bbox_for_phrase_in_crop(
        scanner, cropped, SEARCH_PHRASE, DUPLICATE_INSTRUCTION_REGION
    )
    if not ok or bbox is None:
        success, extracted = scanner.extract_text(cropped)
        detail = extracted if success else str(extracted)
        return False, (
            f"'{SEARCH_PHRASE}' not found in region {DUPLICATE_INSTRUCTION_REGION}. OCR: '{detail}'"
        )

    click_x, click_y = screen_center_from_crop_bbox(bbox, DUPLICATE_INSTRUCTION_REGION)
    print(f"[ACTION_HANDLER] Clicking '{SEARCH_PHRASE}' at screen ({click_x}, {click_y})")

    success, msg = actions.click_at_position(click_x, click_y)
    if success:
        actions.move_mouse(1800, 50, 0)
    if not success:
        return False, f"Failed to click duplicate instruction: {msg}"

    time.sleep(0.5)
    return True, "Successfully clicked Duplicate Instruction"


# ============================================================================
# VERIFIER
# ============================================================================


def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    After a successful action, continue without re-OCR or executor retries.
    """
    msg = "Duplicate instruction: continuing after click (no post-click verification)"
    print(f"[VERIFIER_HANDLER] {msg}")
    return True, msg, {"search_region": DUPLICATE_INSTRUCTION_REGION}


# ============================================================================
# ERROR HANDLER
# ============================================================================


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Never request a retry; unified_executor runs this step once then stops on failure."""
    print(f"[ERROR_HANDLER] duplicate_instruction (no retry): {error_msg}")
    return False, "duplicate_instruction does not retry"
