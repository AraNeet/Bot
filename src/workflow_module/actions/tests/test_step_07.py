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

class TestStep07SelectRowByValues(unittest.TestCase):
    
    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_field = MagicMock()
        self.mock_pyautogui = MagicMock()
        self.mock_cv2 = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
            'src.workflow_module.actions.helpers.field_utils': self.mock_field,
            'pyautogui': self.mock_pyautogui,
            'cv2': self.mock_cv2,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("07_select_row_by_values", "07_select_row_by_values_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.step.helpers.search_current_view = MagicMock(return_value=(True, "Found", {"row_y": 100}))
        self.step.helpers.click_and_position_row = MagicMock(return_value=(True, "Clicked"))
        self.step.ensure_table_at_top = MagicMock()
        self.mock_field.get_results_count.return_value = 10
        self.mock_cv.load_image.return_value = MagicMock()
        
        success, msg = self.step.action(estimate_number="123", advertiser_name="Adv", begin_date="Date", end_date="Date")
        self.assertTrue(success)

    def test_action_failure_row_not_found_after_scroll(self):
        # Mock initial search failure
        self.step.helpers.search_current_view.return_value = (False, "Not found", None)
        self.step.ensure_table_at_top = MagicMock()
        self.mock_field.get_results_count.return_value = 100 # > 30 so it scrolls
        self.mock_cv.load_image.return_value = MagicMock()
        
        # Action loops scrolling. We need to make sure it doesn't run forever in test.
        # The loop runs 50 times. That's a lot for a test if we don't break it.
        # But we mock time.sleep implicitly if we cared, but actually it will just run the loop logic fast on mocks.
        
        # However, to avoid spamming the log or waiting, we can set max_scroll_attempts in the module if possible, 
        # or just let it run 50 iterations on mocks.
        
        success, msg = self.step.action(estimate_number="123", advertiser_name="Adv", begin_date="Date", end_date="Date")
        
        self.assertFalse(success)
        self.assertIn("Target not found after scrolling", msg)
        # Verify scroll was called
        self.assertTrue(self.mock_pyautogui.scroll.called)

    def test_action_failure_no_scroll_needed_and_not_found(self):
        self.step.helpers.search_current_view.return_value = (False, "Not found", None)
        self.step.ensure_table_at_top = MagicMock()
        self.mock_field.get_results_count.return_value = 10 # <= 30 so no scroll
        self.mock_cv.load_image.return_value = MagicMock()
        
        success, msg = self.step.action(estimate_number="123", advertiser_name="Adv", begin_date="Date", end_date="Date")
        
        self.assertFalse(success)
        self.assertIn("results <= 30", msg)
        self.assertFalse(self.mock_pyautogui.scroll.called)

if __name__ == '__main__':
    unittest.main()
