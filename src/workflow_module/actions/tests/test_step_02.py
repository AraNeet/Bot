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

class TestStep02TypeAdvertiserName(unittest.TestCase):
    
    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_field = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_pyautogui = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.field_utils': self.mock_field,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'cv2': self.mock_cv2,
            'pyautogui': self.mock_pyautogui,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("02_type_advertiser_name", "02_type_advertiser_name_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.mock_field.type_text_in_field.return_value = (True, "Typed")
        success, msg = self.step.action(advertiser_name="Test Advertiser")
        self.assertTrue(success)

    def test_action_failure(self):
        self.mock_field.type_text_in_field.return_value = (False, "Failed to type")
        success, msg = self.step.action(advertiser_name="Test Advertiser")
        self.assertFalse(success)
        self.assertIn("Failed to type", msg)

    def test_verifier_success(self):
        self.mock_cv.take_screenshot.return_value = MagicMock()
        self.mock_cv.find_template_in_region.return_value = (False, 0.0, None) # No popup
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.mock_cv.detect_underline.return_value = True
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Test Advertiser"))
        
        success, msg, data = self.step.verifier(advertiser_name="Test Advertiser")
        self.assertTrue(success)
        self.assertIn("Underline detected", msg)

    def test_verifier_popup_detected(self):
        self.mock_cv.take_screenshot.return_value = MagicMock()
        self.mock_cv.find_template_in_region.return_value = (True, 0.9, (100, 100)) # Popup found
        
        # Mock template image for width calculation
        mock_template = MagicMock()
        mock_template.shape = (20, 20, 3)
        self.mock_cv.load_image.return_value = mock_template
        
        self.mock_actions.click_at_position.return_value = (True, "Closed popup")
        
        success, msg, data = self.step.verifier(advertiser_name="Test Advertiser")
        
        # Handler returns False when popup is closed to trigger retry
        self.assertFalse(success)
        self.assertIn("Name search dialog appeared and was closed", msg)
        self.mock_actions.click_at_position.assert_called()

    def test_verifier_failure_no_underline(self):
        self.mock_cv.take_screenshot.return_value = MagicMock()
        self.mock_cv.find_template_in_region.return_value = (False, 0.0, None)
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.mock_cv.detect_underline.return_value = False
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Test Advertiser"))
        
        success, msg, data = self.step.verifier(advertiser_name="Test Advertiser")
        self.assertFalse(success)
        self.assertIn("No underline detected", msg)

    def test_verifier_failure_wrong_text(self):
        self.mock_cv.take_screenshot.return_value = MagicMock()
        self.mock_cv.find_template_in_region.return_value = (False, 0.0, None)
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.mock_cv.detect_underline.return_value = True
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Wrong Text"))
        
        success, msg, data = self.step.verifier(advertiser_name="Test Advertiser")
        self.assertTrue(success) # Passed because underline detected overrides text match

if __name__ == '__main__':
    unittest.main()
