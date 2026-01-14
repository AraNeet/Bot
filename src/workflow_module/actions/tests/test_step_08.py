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

class TestStep08OpenMultinetworkRowByDate(unittest.TestCase):
    
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
        
        self.step = load_step_module("08_open_multinetwork_row_by_date", "08_open_multinetwork_row_by_date_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        self.step.helpers.detect_blue_highlighted_expanded_row = MagicMock(return_value=(True, {'x':0,'y':0,'width':100,'height':100}))
        self.step.helpers.calculate_crop_region_from_expanded_row = MagicMock(return_value=(0,0,100,100))
        self.step.helpers.extract_table_with_column_splits = MagicMock(return_value=(MagicMock(), [10, 20]))
        self.step.helpers.visualize_column_splits_in_table = MagicMock()
        self.step.helpers.search_date_in_cropped_table = MagicMock(return_value=(True, 50, 50, "Found"))
        self.step.helpers.execute_double_click_at_position = MagicMock(return_value=(True, "Clicked"))
        
        self.mock_cv.take_screenshot.return_value = MagicMock(shape=(1080, 1920, 3))
        
        success, msg = self.step.action(begin_date="01/01/2026")
        self.assertTrue(success)

    def test_action_failure_no_blue_row(self):
        self.step.helpers.detect_blue_highlighted_expanded_row = MagicMock(return_value=(False, None))
        self.mock_cv.take_screenshot.return_value = MagicMock(shape=(1080, 1920, 3))
        
        success, msg = self.step.action(begin_date="01/01/2026")
        self.assertFalse(success)
        self.assertIn("not found", msg)

    def test_action_failure_date_not_found(self):
        self.step.helpers.detect_blue_highlighted_expanded_row = MagicMock(return_value=(True, {'x':0,'y':0,'width':100,'height':100}))
        self.step.helpers.calculate_crop_region_from_expanded_row = MagicMock(return_value=(0,0,100,100))
        self.step.helpers.extract_table_with_column_splits = MagicMock(return_value=(MagicMock(), [10, 20]))
        self.step.helpers.search_date_in_cropped_table = MagicMock(return_value=(False, 0, 0, "Not Found"))
        
        self.mock_cv.take_screenshot.return_value = MagicMock(shape=(1080, 1920, 3))
        
        success, msg = self.step.action(begin_date="01/01/2026")
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
