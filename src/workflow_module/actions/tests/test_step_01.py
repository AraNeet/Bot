import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib.util

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

def load_step_module(step_name, module_name):
    """Helper to load step modules dynamically."""
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../steps'))
    step_path = os.path.join(base_path, step_name, f"{module_name}.py")
    
    spec = importlib.util.spec_from_file_location(module_name, step_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

class TestStep01OpenInstructionsPage(unittest.TestCase):
    
    def setUp(self):
        # Create mocks
        self.mock_cv = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_ocr = MagicMock()
        
        # Patch sys.modules
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr,
        })
        self.modules_patcher.start()
        
        self.step = load_step_module("01_open_instructions_page", "01_open_instructions_page_handler")

    def tearDown(self):
        self.modules_patcher.stop()

    def test_action_success(self):
        """Test Step 01 Action: Success scenario"""
        self.mock_cv.take_screenshot.return_value = MagicMock() 
        self.mock_cv.find_template_in_region.return_value = (True, 0.95, (100, 100))
        self.mock_actions.click_at_position.return_value = (True, "Clicked")
        
        success, msg = self.step.action()
        self.assertTrue(success)
        self.assertIn("Successfully navigated", msg)

    def test_action_template_not_found(self):
        """Test Step 01 Action: Template not found edge case"""
        self.mock_cv.take_screenshot.return_value = MagicMock() 
        self.mock_cv.find_template_in_region.return_value = (False, 0.5, None)
        
        success, msg = self.step.action()
        self.assertFalse(success)
        self.assertIn("not found", msg)

    def test_action_click_failure(self):
        """Test Step 01 Action: Click failure edge case"""
        self.mock_cv.take_screenshot.return_value = MagicMock() 
        self.mock_cv.find_template_in_region.return_value = (True, 0.95, (100, 100))
        self.mock_actions.click_at_position.return_value = (False, "Click failed")
        
        success, msg = self.step.action()
        self.assertFalse(success)
        self.assertIn("Failed to click", msg)

    def test_verifier_success(self):
        """Test Step 01 Verifier: Success scenario"""
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Search Global Comm"))
        
        success, msg, data = self.step.verifier()
        self.assertTrue(success)
        self.assertIn("Found 'Search Global Comm'", msg)

    def test_verifier_failure_text_not_found(self):
        """Test Step 01 Verifier: Text not found edge case"""
        self.mock_cv.take_screenshot_and_crop.return_value = MagicMock()
        self.step.scanner.extract_text = MagicMock(return_value=(True, "Some other text"))
        
        success, msg, data = self.step.verifier()
        self.assertFalse(success)
        self.assertIn("verification failed", msg)

if __name__ == '__main__':
    unittest.main()
