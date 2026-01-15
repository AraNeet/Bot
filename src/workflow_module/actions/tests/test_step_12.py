import unittest
from unittest.mock import MagicMock, patch, Mock
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


class TestStep12EditMediaDetails(unittest.TestCase):
    
    def setUp(self):
        # Create mocks
        self.mock_cv = MagicMock()
        self.mock_actions = MagicMock()
        self.mock_debugger_instance = MagicMock()
        self.mock_debugger_class = MagicMock(return_value=self.mock_debugger_instance)
        self.mock_helpers = MagicMock()
        self.mock_pyautogui = MagicMock()
        self.mock_ocr_utils = MagicMock()
        self.mock_debug_utils = MagicMock()
        
        # Setup Debugger mock class on debug_utils
        self.mock_debug_utils.Debugger = self.mock_debugger_class
        
        # Setup pyautogui mock context manager
        self.mock_pyautogui.hold.return_value.__enter__ = MagicMock()
        self.mock_pyautogui.hold.return_value.__exit__ = MagicMock()
        
        # Create mock screenshot
        self.mock_screenshot = MagicMock()
        self.mock_screenshot.copy.return_value = self.mock_screenshot
        
        # Patch sys.modules BEFORE loading the module
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.debug_utils': self.mock_debug_utils,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr_utils,
            'pyautogui': self.mock_pyautogui,
            'pytz': MagicMock(),
        })
        self.modules_patcher.start()
        
        # Load the step module
        self.step = load_step_module("12_edit_media_details", "12_edit_media_details_handler")
        
        # Patch Debugger on the loaded module
        self.step.Debugger = self.mock_debugger_class
        
        # Patch helpers module on the loaded module
        self.step.helpers = self.mock_helpers
        
        # Setup default helper return values
        self.mock_helpers.scroll_to_media_details.return_value = (True, "Scrolled")
        self.mock_helpers.delete_all_existing_media.return_value = (True, "Deleted", 2)
        self.mock_helpers.enter_all_isci_values.return_value = (True, "Entered", 3)
        self.mock_helpers.verify_isci_entries.return_value = (True, "Verified", {"A": {"success": True}})
        self.mock_helpers.scroll_media_details_to_top.return_value = (True, "Scrolled to top")
        
        # Setup default action mocks
        self.mock_cv.take_screenshot.return_value = self.mock_screenshot

    def tearDown(self):
        self.modules_patcher.stop()
        # Reset all side_effects
        self.mock_helpers.delete_all_existing_media.side_effect = None
        self.mock_helpers.enter_all_isci_values.side_effect = None
        self.mock_helpers.verify_isci_entries.side_effect = None

    # ========================================================================
    # ACTION FUNCTION TESTS
    # ========================================================================
    
    def test_action_success_with_isci_list(self):
        """Test Action: Success with ISCI list"""
        isci_list = ["BADTAA30ENH", "BADTSA30ENH", "BADTBA30ENH"]
        
        success, msg = self.step.action(isci_list=isci_list)
        
        self.assertTrue(success)
        self.assertIn("updated", msg.lower())
        self.mock_helpers.delete_all_existing_media.assert_called_once()
        self.mock_helpers.enter_all_isci_values.assert_called_once()

    def test_action_success_empty_isci_list(self):
        """Test Action: Success with empty ISCI list (just delete existing)"""
        success, msg = self.step.action(isci_list=[])
        
        self.assertTrue(success)
        self.mock_helpers.delete_all_existing_media.assert_called_once()
        # enter_all_isci_values should NOT be called with empty list
        self.mock_helpers.enter_all_isci_values.assert_not_called()

    def test_action_success_none_isci_list(self):
        """Test Action: Success with None ISCI list"""
        success, msg = self.step.action(isci_list=None)
        
        self.assertTrue(success)
        self.mock_helpers.delete_all_existing_media.assert_called_once()

    def test_action_success_string_isci(self):
        """Test Action: Success with single ISCI as string (converted to list)"""
        success, msg = self.step.action(isci_list="BADTAA30ENH")
        
        self.assertTrue(success)
        self.mock_helpers.enter_all_isci_values.assert_called_once()
        # Verify it was called with a list containing the string
        call_args = self.mock_helpers.enter_all_isci_values.call_args[0]
        self.assertEqual(call_args[0], ["BADTAA30ENH"])

    def test_action_screenshot_failure(self):
        """Test Action: Screenshot failure"""
        self.mock_cv.take_screenshot.return_value = None
        
        success, msg = self.step.action(isci_list=["BADTAA30ENH"])
        
        self.assertFalse(success)
        self.assertIn("screenshot", msg.lower())

    def test_action_delete_failure(self):
        """Test Action: Delete existing media failure"""
        self.mock_helpers.delete_all_existing_media.return_value = (False, "Delete failed", 0)
        
        success, msg = self.step.action(isci_list=["BADTAA30ENH"])
        
        self.assertFalse(success)
        self.assertIn("delete", msg.lower())

    def test_action_enter_isci_failure(self):
        """Test Action: Enter ISCI failure"""
        self.mock_helpers.enter_all_isci_values.return_value = (False, "Enter failed", 1)
        
        success, msg = self.step.action(isci_list=["BADTAA30ENH", "BADTSA30ENH"])
        
        self.assertFalse(success)
        self.assertIn("enter", msg.lower())

    # ========================================================================
    # VERIFIER FUNCTION TESTS
    # ========================================================================
    
    def test_verifier_success(self):
        """Test Verifier: All ISCI values verified"""
        isci_list = ["BADTAA30ENH", "BADTSA30ENH"]
        self.mock_helpers.verify_isci_entries.return_value = (True, "All verified", {
            "A": {"success": True, "message": "Verified"},
            "B": {"success": True, "message": "Verified"}
        })
        
        success, msg, results = self.step.verifier(isci_list=isci_list)
        
        self.assertTrue(success)
        self.assertTrue(results["verified"])
        self.assertEqual(results["expected_count"], 2)

    def test_verifier_empty_list(self):
        """Test Verifier: Empty ISCI list (nothing to verify)"""
        success, msg, results = self.step.verifier(isci_list=[])
        
        self.assertTrue(success)
        self.assertEqual(results["count"], 0)

    def test_verifier_failure(self):
        """Test Verifier: ISCI verification fails"""
        isci_list = ["BADTAA30ENH", "BADTSA30ENH"]
        self.mock_helpers.verify_isci_entries.return_value = (False, "Verification failed for aliases: B", {
            "A": {"success": True, "message": "Verified"},
            "B": {"success": False, "message": "Mismatch"}
        })
        
        success, msg, results = self.step.verifier(isci_list=isci_list)
        
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())

    # ========================================================================
    # ERROR HANDLER FUNCTION TESTS
    # ========================================================================
    
    def test_error_handler_retry(self):
        """Test Error Handler: Retry when attempt < max_attempts"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=1,
            max_attempts=3
        )
        
        self.assertTrue(success)
        self.assertIn("Retry", msg)
        self.mock_helpers.scroll_media_details_to_top.assert_called_once()

    def test_error_handler_no_retry(self):
        """Test Error Handler: No retry when attempt >= max_attempts"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=3,
            max_attempts=3
        )
        
        self.assertFalse(success)
        self.assertEqual(msg, "Test error")


if __name__ == '__main__':
    unittest.main()
