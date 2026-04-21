import pyautogui
from src.startup_module.helpers.login_utils import *
import numpy as np
import cv2
import time
import pyotp

def login_system(username, password, secret, login_templates):
    login_area_template = login_templates.get("login_screen")

    area = None
    neutral_x, neutral_y = 500, 200

    # 🔁 Retry login area detection
    for attempt in range(3):
        print(f"Attempt {attempt + 1} to detect login screen...")
        area = login_area(login_area_template)
        if area is not None:
            break
        time.sleep(3)

    if area is None:
        print("Login screen not found after 3 attempts")
        return False    

    # Work region
    x, y = area["top_left"]
    w, h = area["width"], area["height"]
    work_region = (x, y, w, h)

    print("Login area detected:", work_region)

    screenshot = pyautogui.screenshot(region=work_region)
    image = np.array(screenshot)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # 🔹 USERNAME
    if not text_input("username", username, x, y, neutral_x, neutral_y, image):
        return False

    # 🔹 PASSWORD
    if not text_input("password", password, x, y, neutral_x, neutral_y, image):
        return False

    # 🔹 TOKEN (special case)
    totp = pyotp.TOTP(secret)
    token = totp.now()
    print("[TOKEN] Generated:", token)

    if not text_input("token", token, x, y, neutral_x, neutral_y, image):
        return False

    # 🔹 SIGN IN
    pos = find_word_position(image, "Sign In", (x, y))
    if not pos:
        print("Sign-in button not found")
        return False
    
    click_x, click_y, text, conf = pos
    print(f"[Sign-in button] Found '{text}' → clicking at ({click_x}, {click_y})")

    pyautogui.click(click_x, click_y)

    return True

def open_network_app(workspace_template, wait_time=120):
    print("="*30)
    print("Opening Network App...")
    workspace_template_screen = workspace_template.get("network_app_selection_screen")

    area = None

    # 🔁 Retry workspace detection
    for attempt in range(3):
        print(f"Attempt {attempt + 1} to detect workspace...")
        area = login_area(workspace_template_screen)   # reuse your template matcher
        if area is not None:
            break
        time.sleep(3)

    if area is None:
        print("Workspace not found after 3 attempts")
        return False

    # Define region
    x, y = area["top_left"]
    w, h = area["width"], area["height"]
    work_region = (x, y, w, h)

    print("Workspace detected:", work_region)

    # Screenshot only workspace
    screenshot = pyautogui.screenshot(region=work_region)
    image = np.array(screenshot)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # 🔹 Find and click "Disg Staging XRD"
    pos = find_word_position(image, "Dish Staging XRD", (x, y))

    if not pos:
        print("'Disg Staging XRD' not found")
        return False

    click_x, click_y, text, conf = pos
    print(f"[APP] Found '{text}' → clicking at ({click_x}, {click_y})")

    pyautogui.click(click_x, click_y)

    # ⏳ Wait for app to load
    print(f"Waiting {wait_time} seconds for app to load...")
    time.sleep(wait_time)

    return True