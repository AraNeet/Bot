import cv2
import numpy as np
import pyautogui
from paddleocr import PaddleOCR
import time

# Initialize once (important for performance)
ocr = PaddleOCR(lang='en', use_doc_unwarping=False, use_doc_orientation_classify=False, use_textline_orientation=False)

def find_keyword_position(image, keyword, region_offset, y_offset=15):
    results = ocr.predict(image)

    for res in results:
        texts = res['rec_texts']
        scores = res['rec_scores']
        boxes = res['dt_polys']

        for text, score, box in zip(texts, scores, boxes):
            if keyword.lower() in text.lower():

                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]

                center_x = int(sum(x_coords) / 4)
                bottom_y = int(max(y_coords))

                click_x = region_offset[0] + center_x
                click_y = region_offset[1] + bottom_y + y_offset

                return (click_x, click_y, text, score)

    return None

def find_word_position(image, keyword, region_offset):
    results = ocr.predict(image)

    for res in results:
        texts = res['rec_texts']
        scores = res['rec_scores']
        boxes = res['dt_polys']

        for text, score, box in zip(texts, scores, boxes):
            if keyword.lower() in text.lower():

                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]

                center_x = int(sum(x_coords) / 4)
                bottom_y = int(max(y_coords))

                click_x = region_offset[0] + center_x
                click_y = region_offset[1] + bottom_y

                return (click_x, click_y, text, score)

    return None

def login_area(template, threshold=0.8):

    h, w = template.shape[:2]

    screenshot = pyautogui.screenshot()
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    return {
        "top_left": top_left,
        "bottom_right": bottom_right,
        "width": w,
        "height": h,
        "confidence": max_val
    }

def text_input(keyword: str, input_text:str, pos_x: int, pos_y: int,
                neutral_x: int, neutral_y: int, image):
    pos = find_keyword_position(image, keyword, (pos_x, pos_y))
    if not pos:
        print(f"{keyword} field not found")
        return False

    click_x, click_y, text, conf = pos
    print(f"[{keyword}] Found '{text}' → clicking at ({click_x}, {click_y})")

    pyautogui.click(click_x, click_y)
    time.sleep(0.3)
    pyautogui.write(input_text, interval=0.05)
    # To clear login assist
    pyautogui.click(neutral_x, neutral_y)
    # Delay inbetween each step
    time.sleep(2)

    return True
