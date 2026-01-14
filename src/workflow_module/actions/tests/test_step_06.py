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

class TestStep06ClickSearchButton(unittest.TestCase):
    
    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_verification = MagicMock()
        self.mock_field = MagicMock()
        self.mock_cv2 = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
            'src.workflow_module.actions.helpers.verification_utils': self.mock_verification,
            'src.workflow_module.actions.helpers.field_utils': self.mock_field,
            'cv2': self.mock_cv2,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("06_click_search_button", "06_click_search_button_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.find_text_with_position = MagicMock(return_value=(True, True, (10, 10, 50, 20)))
        self.mock_actions.click_at_position.return_value = (True, "Clicked")
        
        success, msg = self.step.action()
        self.assertTrue(success)
        self.mock_actions.click_at_position.assert_called()

    def test_action_failure_button_not_found(self):
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.find_text_with_position = MagicMock(return_value=(False, False, None))
        
        success, msg = self.step.action()
        self.assertFalse(success)
        self.assertIn("Could not determine", msg)

    def test_verifier_success(self):
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Results: 10"))
        self.mock_verification.extract_string_from_text.return_value = "Results"
        self.mock_verification.calculate_text_similarity.return_value = 1.0
        self.mock_field.get_results_count.return_value = 10
        
        success, msg, data = self.step.verifier()
        self.assertTrue(success)
        self.assertEqual(data['results_count'], 10)

    def test_verifier_failure_no_results(self):
        self.step.scanner.extract_text = MagicMock(return_value=(True, "No matches"))
        self.mock_verification.extract_string_from_text.return_value = "Results" # Mock finding text but count is 0
        self.mock_field.get_results_count.return_value = 0
        self.mock_verification.calculate_text_similarity.return_value = 1.0
        
        success, msg, data = self.step.verifier()
        self.assertFalse(success)
        self.assertIn("Search returned 0 results", msg)

if __name__ == '__main__':
    unittest.main()
