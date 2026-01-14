import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib.util

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

def load_step_module(step_name, module_name):
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../steps'))
    step_path = os.path.join(base_path, step_name, f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, step_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

class TestStep09MultinetworkPopup(unittest.TestCase):
    
    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_pyautogui = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
            'cv2': self.mock_cv2,
            'pyautogui': self.mock_pyautogui,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("09_multinetwork_popup", "09_multinetwork_popup_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.mock_cv.load_image.return_value = MagicMock(shape=(50, 50, 3))
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock(shape=(500, 500, 3))
        self.mock_cv.match_template_in_region.return_value = (True, 0.9, (100, 100))
        self.mock_cv.crop_image.return_value = MagicMock()
        
        mock_scanner_instance = self.mock_ocr.TextScanner.return_value
        mock_scanner_instance.get_text_data.return_value = (True, {
            'text': ['Open as Multi-Network Instruction'],
            'bbox': [(0,0,50,20)]
        })
        
        self.mock_actions.click_at_position.return_value = (True, "Clicked")
        self.mock_pyautogui.size.return_value = (1920, 1080)
        
        success, msg = self.step.action()
        self.assertTrue(success)

    def test_action_failure_popup_not_found(self):
        self.mock_cv.load_image.return_value = MagicMock(shape=(50, 50, 3))
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock(shape=(500, 500, 3))
        # Ensure take_screenshot returns an object with a shape attribute
        mock_screenshot = MagicMock()
        mock_screenshot.shape = (1080, 1920, 3)
        self.mock_cv.take_screenshot.return_value = mock_screenshot
        
        self.mock_cv.match_template_in_region.return_value = (False, 0.5, None)
        self.mock_cv.find_template_in_region.return_value = (False, 0.0, None)
        self.mock_pyautogui.size.return_value = (1920, 1080)
        self.mock_cv.detect_loading_circle.return_value = (False, None)
        
        success, msg = self.step.action()
        self.assertTrue(success)
        self.assertIn("assuming flow can proceed", msg)

if __name__ == '__main__':
    unittest.main()
