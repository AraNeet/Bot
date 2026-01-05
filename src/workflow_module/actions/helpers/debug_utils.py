#!/usr/bin/env python3
"""
Debug Utilities Module

This module provides helpers for visual debugging of computer vision operations.
It handles creating, annotating, and saving debug images.
"""

import cv2
import numpy as np
import os
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Common colors (BGR format)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_BLUE = (255, 0, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_CYAN = (255, 255, 0)
COLOR_MAGENTA = (255, 0, 255)
COLOR_ORANGE = (0, 165, 255)

class Debugger:
    def __init__(self, action_name: str):
        self.action_name = action_name
        self.output_dir = os.path.join("debug_images", action_name)
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[DEBUGGER] Initialized for '{action_name}'. Output dir: {self.output_dir}")

    def save_image(self, image: np.ndarray, filename: str) -> Optional[str]:
        """Save an image to the action's debug directory."""
        if image is None:
            return None
        
        try:
            filepath = os.path.join(self.output_dir, filename)
            cv2.imwrite(filepath, image)
            abs_path = os.path.abspath(filepath)
            print(f"[DEBUGGER] Saved: {abs_path}")
            return abs_path
        except Exception as e:
            print(f"[DEBUGGER] Failed to save {filename}: {e}")
            return None

    def draw_rect(self, image: np.ndarray, rect: Tuple[int, int, int, int], color=COLOR_GREEN, thickness=2, label: str = None):
        """Draws a rectangle on the image (in-place). Rect is (x, y, w, h)."""
        x, y, w, h = rect
        cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
        if label:
            cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def draw_point(self, image: np.ndarray, point: Tuple[int, int], color=COLOR_RED, radius=5, label: str = None):
        """Draws a point/circle on the image (in-place)."""
        cv2.circle(image, point, radius, color, -1)
        if label:
            x, y = point
            cv2.putText(image, label, (x + radius + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def visualize_search_region(self, screenshot: np.ndarray, region: Tuple[int, int, int, int], step_name: str):
        """Saves a screenshot with the search region highlighted."""
        debug_img = screenshot.copy()
        self.draw_rect(debug_img, region, color=COLOR_ORANGE, label="Search Region")
        self.save_image(debug_img, f"{step_name}_search_region.png")

    def visualize_template_match(self, screenshot: np.ndarray, found: bool, position: Optional[Tuple[int, int]], 
                               template_size: Tuple[int, int], step_name: str, confidence: float = 0.0):
        """Saves a screenshot with the template match highlighted."""
        debug_img = screenshot.copy()
        if found and position:
            cx, cy = position
            w, h = template_size
            top_left = (cx - w // 2, cy - h // 2)
            self.draw_rect(debug_img, (top_left[0], top_left[1], w, h), color=COLOR_GREEN, label=f"Match ({confidence:.2f})")
            self.draw_point(debug_img, position, color=COLOR_BLUE)
        else:
             cv2.putText(debug_img, "Template Not Found", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLOR_RED, 2)
             
        self.save_image(debug_img, f"{step_name}_match_result.png")

    def visualize_ocr(self, image: np.ndarray, ocr_data: Dict, step_name: str, highlight_text: str = None):
        """Saves an image with OCR bounding boxes drawn."""
        if image is None or not ocr_data or 'text' not in ocr_data:
            return

        debug_img = image.copy()
        
        for i, text in enumerate(ocr_data['text']):
            if not text: continue
            
            x1, y1, x2, y2 = map(int, ocr_data['bbox'][i])
            w = x2 - x1
            h = y2 - y1
            
            color = COLOR_CYAN
            thickness = 1
            
            # Highlight specific text if requested
            if highlight_text and highlight_text.lower() in text.lower():
                color = COLOR_MAGENTA
                thickness = 2
                
            self.draw_rect(debug_img, (x1, y1, w, h), color=color, thickness=thickness)
            
        self.save_image(debug_img, f"{step_name}_ocr_result.png")

