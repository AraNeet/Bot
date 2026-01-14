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

class TestStep05SetEndDate(unittest.TestCase):
    
    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_field = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_verification = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_cv2 = MagicMock()
        self.mock_pyautogui = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.field_utils': self.mock_field,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
            'src.workflow_module.actions.helpers.verification_utils': self.mock_verification,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'cv2': self.mock_cv2,
            'pyautogui': self.mock_pyautogui,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("05_set_end_date", "05_set_end_date_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.mock_field.type_text_in_field.return_value = (True, "Typed")
        success, msg = self.step.action(end_date="01/31/2026")
        self.assertTrue(success)

    def test_action_failure(self):
        self.mock_field.type_text_in_field.return_value = (False, "Failed")
        success, msg = self.step.action(end_date="01/31/2026")
        self.assertFalse(success)

    def test_verifier_success(self):
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.extract_text = MagicMock(return_value=(True, "01/31/2026"))
        self.mock_verification.extract_date_from_text.return_value = "01/31/2026"
        self.mock_verification.calculate_text_similarity.return_value = 1.0
        
        success, msg, data = self.step.verifier(end_date="01/31/2026")
        self.assertTrue(success)

    def test_verifier_failure_date_mismatch(self):
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.extract_text = MagicMock(return_value=(True, "01/01/2026"))
        self.mock_verification.extract_date_from_text.return_value = "01/01/2026"
        self.mock_verification.calculate_text_similarity.return_value = 0.5
        
        success, msg, data = self.step.verifier(end_date="01/31/2026")
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
