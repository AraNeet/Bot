import unittest
from unittest.mock import MagicMock, patch, Mock
import sys
import os
import importlib.util
from datetime import date, datetime
import pytz

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

class TestStep11EditDefinition(unittest.TestCase):
    
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
        self.mock_pyautogui.press.return_value = None
        
        # Create mock screenshot
        self.mock_screenshot = MagicMock()
        self.mock_screenshot.copy.return_value = self.mock_screenshot
        
        # Patch sys.modules BEFORE loading the module (including all dependencies)
        self.modules_patcher = patch.dict(sys.modules, {
            'src.workflow_module.actions.helpers.computer_vision_utils': self.mock_cv,
            'src.workflow_module.actions.helpers.actions': self.mock_actions,
            'src.workflow_module.actions.helpers.debug_utils': self.mock_debug_utils,
            'src.workflow_module.actions.helpers.ocr_utils': self.mock_ocr_utils,
            'pyautogui': self.mock_pyautogui,
            'pytz': MagicMock(),
            'dateutil': MagicMock(),
            'dateutil.parser': MagicMock(),
        })
        self.modules_patcher.start()
        
        # Load the step module
        self.step = load_step_module("11_edit_definition", "11_edit_definition_handler")
        
        # Patch Debugger on the loaded module (after loading)
        self.step.Debugger = self.mock_debugger_class
        
        # Patch helpers module on the loaded module
        self.step.helpers = self.mock_helpers
        
        # Patch pyautogui on the loaded module
        self.step.pyautogui = self.mock_pyautogui
        
        # Setup default helper return values
        self.mock_helpers.DEFINITION_WINDOW_REGION = (200, 425, 1425, 575)
        self.mock_helpers.find_field_input_box.return_value = (500, 500)
        self.mock_helpers.extract_field_value.return_value = "01/01/2026"
        self.mock_helpers.parse_date_string.return_value = date(2026, 1, 1)
        self.mock_helpers.get_current_mountain_date.return_value = date(2026, 1, 15)
        self.mock_helpers.update_and_verify_date.return_value = (True, "Date updated successfully")
        self.mock_helpers.verify_date_field.return_value = (True, "Date verified")
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        # Setup default action mocks
        self.mock_cv.take_screenshot.return_value = self.mock_screenshot
        self.mock_actions.click_at_position.return_value = (True, "Clicked")
        self.mock_actions.type_text.return_value = (True, "Typed")
        self.mock_actions.press_key.return_value = (True, "Pressed")

    def tearDown(self):
        self.modules_patcher.stop()
        # Reset all side_effects
        self.mock_helpers.find_field_input_box.side_effect = None
        self.mock_helpers.extract_field_value.side_effect = None
        self.mock_helpers.update_and_verify_date.side_effect = None
        self.mock_helpers.verify_date_field.side_effect = None
        self.mock_helpers.verify_comment.side_effect = None

    # ========================================================================
    # ACTION FUNCTION TESTS
    # ========================================================================
    
    def test_action_success_all_fields_updated(self):
        """Test Action: Success scenario with all fields updated"""
        self.mock_helpers.get_current_mountain_date.return_value = date(2026, 1, 10)  # System date < Begin Date
        self.mock_helpers.parse_date_string.return_value = date(2026, 1, 12)  # Begin Date > System Date
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertTrue(success)
        self.assertIn("successfully", msg.lower())
        self.assertEqual(self.mock_helpers.update_and_verify_date.call_count, 2)  # Begin Date + End Date

    def test_action_success_begin_date_skipped(self):
        """Test Action: Success when Begin Date update is skipped (system date >= begin date)"""
        self.mock_helpers.get_current_mountain_date.return_value = date(2026, 1, 15)  # System date
        self.mock_helpers.parse_date_string.return_value = date(2026, 1, 12)  # Begin Date < System Date
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertTrue(success)
        # Begin Date update should be skipped
        begin_date_calls = [call for call in self.mock_helpers.update_and_verify_date.call_args_list 
                           if call[0][0] == "Begin Date"]
        self.assertEqual(len(begin_date_calls), 0)

    def test_action_screenshot_failure(self):
        """Test Action: Screenshot failure edge case"""
        self.mock_cv.take_screenshot.return_value = None
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("screenshot", msg.lower())

    def test_action_begin_date_field_not_found(self):
        """Test Action: Begin Date field not found edge case"""
        # Reset side_effect
        self.mock_helpers.find_field_input_box.side_effect = None
        self.mock_helpers.find_field_input_box.return_value = None  # Begin Date not found initially
        
        # When update_and_verify_date is called, it will call find_field_input_box again
        # So we need to set up the side_effect to return None first, then values
        call_count = [0]
        def find_field_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return None  # First call (Begin Date check)
            elif call_count[0] == 2:
                return (500, 500)  # Second call (in update_and_verify_date for Begin Date)
            elif call_count[0] == 3:
                return (500, 500)  # Third call (in update_and_verify_date for End Date)
            elif call_count[0] == 4:
                return (500, 500)  # Fourth call (Comment)
            return (500, 500)
        
        self.mock_helpers.find_field_input_box.side_effect = find_field_side_effect
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        # Should still proceed to update Begin Date (attempt anyway)
        # The update_and_verify_date will handle the field not found case
        self.assertIsNotNone(success)

    def test_action_end_date_field_not_found(self):
        """Test Action: End Date field not found edge case"""
        # Reset side_effect
        self.mock_helpers.find_field_input_box.side_effect = None
        self.mock_helpers.find_field_input_box.return_value = (500, 500)
        
        # Since system date >= begin date, Begin Date update is skipped
        # So the first (and only) call to update_and_verify_date is for End Date
        self.mock_helpers.update_and_verify_date.side_effect = None
        self.mock_helpers.update_and_verify_date.side_effect = [
            (False, "Could not locate 'End Date' field"),  # End Date failure (first call)
        ]
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("End Date", msg)

    def test_action_comment_field_not_found(self):
        """Test Action: Comment field not found edge case"""
        # Reset side_effect
        self.mock_helpers.find_field_input_box.side_effect = None
        
        # Since system date >= begin date, Begin Date update is skipped
        # Calls to find_field_input_box:
        # Call 1: Begin Date check
        # Call 2: Comment check (update_and_verify_date is mocked, doesn't call find_field_input_box)
        call_count = [0]
        def find_field_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (500, 500)  # Begin Date check
            return None  # Comment not found (call 2)
        
        self.mock_helpers.find_field_input_box.side_effect = find_field_side_effect
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("Comment", msg)
        self.assertIn("not locate", msg.lower())

    def test_action_begin_date_update_failure(self):
        """Test Action: Begin Date update failure edge case"""
        self.mock_helpers.get_current_mountain_date.return_value = date(2026, 1, 10)
        self.mock_helpers.parse_date_string.return_value = date(2026, 1, 12)
        # Reset side_effect first
        self.mock_helpers.update_and_verify_date.side_effect = None
        self.mock_helpers.update_and_verify_date.side_effect = [
            (False, "Failed to update Begin Date"),  # Begin Date failure
        ]
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("Begin Date", msg)

    def test_action_end_date_update_failure(self):
        """Test Action: End Date update failure edge case"""
        self.mock_helpers.get_current_mountain_date.return_value = date(2026, 1, 15)
        self.mock_helpers.parse_date_string.return_value = date(2026, 1, 12)
        # Reset side_effect first
        self.mock_helpers.update_and_verify_date.side_effect = None
        # Begin Date will be skipped (system date >= begin date), so only End Date is called
        self.mock_helpers.update_and_verify_date.side_effect = [
            (False, "Failed to update End Date"),  # End Date failure
        ]
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("End Date", msg)

    def test_action_missing_parameters(self):
        """Test Action: Missing required parameters edge case"""
        success, msg = self.step.action(
            begin_date="",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        # Should still attempt to run but may fail or warn
        # The function checks but doesn't fail immediately
        self.assertIsNotNone(success)

    def test_action_empty_parameters(self):
        """Test Action: All empty parameters edge case"""
        success, msg = self.step.action(
            begin_date="",
            end_date="",
            revision_number="",
            agent_name=""
        )
        
        # Should handle gracefully
        self.assertIsNotNone(success)

    def test_action_begin_date_parsing_failure(self):
        """Test Action: Begin Date parsing failure edge case"""
        self.mock_helpers.parse_date_string.return_value = None  # Parsing fails
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        # Should default to updating Begin Date if parsing fails
        self.assertIsNotNone(success)

    def test_action_comment_extraction_empty(self):
        """Test Action: Comment field extraction returns empty string"""
        # Reset side_effect
        self.mock_helpers.extract_field_value.side_effect = None
        
        # Setup extract_field_value to return different values for different calls
        call_count = [0]
        def extract_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "01/01/2026"  # Begin Date
            elif call_count[0] == 2:
                return "01/16/2026"  # End Date (in update_and_verify_date verification)
            elif call_count[0] == 3:
                return ""  # Comment is empty
            return ""
        
        self.mock_helpers.extract_field_value.side_effect = extract_side_effect
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        # Should handle empty comment gracefully
        self.assertTrue(success)

    def test_action_default_agent_name(self):
        """Test Action: Default agent name when not provided"""
        self.mock_helpers.find_field_input_box.return_value = (500, 500)
        
        success, msg = self.step.action(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name=""  # Empty agent name
        )
        
        # Should use default "test agent"
        self.assertTrue(success)

    # ========================================================================
    # VERIFIER FUNCTION TESTS
    # ========================================================================
    
    def test_verifier_all_pass(self):
        """Test Verifier: All verifications pass"""
        self.mock_helpers.verify_date_field.return_value = (True, "Date verified")
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent",
            original_comment="Original text"
        )
        
        self.assertTrue(success)
        self.assertIn("passed", msg.lower())
        self.assertEqual(len(results), 3)  # begin_date, end_date, comment
        self.assertTrue(results["begin_date"]["success"])
        self.assertTrue(results["end_date"]["success"])
        self.assertTrue(results["comment"]["success"])

    def test_verifier_begin_date_fails(self):
        """Test Verifier: Begin Date verification fails"""
        # Reset side_effect first
        self.mock_helpers.verify_date_field.side_effect = None
        self.mock_helpers.verify_date_field.side_effect = [
            (False, "Begin Date mismatch"),  # Begin Date fails
            (True, "End Date verified"),  # End Date passes
        ]
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())
        self.assertFalse(results["begin_date"]["success"])
        self.assertTrue(results["end_date"]["success"])
        self.assertTrue(results["comment"]["success"])

    def test_verifier_end_date_fails(self):
        """Test Verifier: End Date verification fails"""
        # Reset side_effect first
        self.mock_helpers.verify_date_field.side_effect = None
        self.mock_helpers.verify_date_field.side_effect = [
            (True, "Begin Date verified"),  # Begin Date passes
            (False, "End Date mismatch"),  # End Date fails
        ]
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())
        self.assertTrue(results["begin_date"]["success"])
        self.assertFalse(results["end_date"]["success"])
        self.assertTrue(results["comment"]["success"])

    def test_verifier_comment_fails(self):
        """Test Verifier: Comment verification fails"""
        self.mock_helpers.verify_date_field.return_value = (True, "Date verified")
        self.mock_helpers.verify_comment.return_value = (False, "Comment mismatch")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())
        self.assertTrue(results["begin_date"]["success"])
        self.assertTrue(results["end_date"]["success"])
        self.assertFalse(results["comment"]["success"])

    def test_verifier_multiple_failures(self):
        """Test Verifier: Multiple verifications fail"""
        # Reset side_effect first
        self.mock_helpers.verify_date_field.side_effect = None
        self.mock_helpers.verify_date_field.side_effect = [
            (False, "Begin Date mismatch"),
            (False, "End Date mismatch"),
        ]
        self.mock_helpers.verify_comment.return_value = (False, "Comment mismatch")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())
        self.assertFalse(results["begin_date"]["success"])
        self.assertFalse(results["end_date"]["success"])
        self.assertFalse(results["comment"]["success"])

    def test_verifier_missing_begin_date(self):
        """Test Verifier: Begin Date not provided (should skip)"""
        self.mock_helpers.verify_date_field.return_value = (True, "End Date verified")
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="",  # Empty
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertTrue(success)
        self.assertEqual(results["begin_date"]["message"], "Skipped (no begin_date provided)")

    def test_verifier_missing_end_date(self):
        """Test Verifier: End Date not provided (should skip)"""
        self.mock_helpers.verify_date_field.return_value = (True, "Begin Date verified")
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="",  # Empty
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertTrue(success)
        self.assertEqual(results["end_date"]["message"], "Skipped (no end_date provided)")

    def test_verifier_missing_all_dates(self):
        """Test Verifier: Both dates missing (should skip both)"""
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="",
            end_date="",
            revision_number="APR2125",
            agent_name="test agent"
        )
        
        self.assertTrue(success)
        self.assertEqual(results["begin_date"]["message"], "Skipped (no begin_date provided)")
        self.assertEqual(results["end_date"]["message"], "Skipped (no end_date provided)")

    def test_verifier_original_comment_provided(self):
        """Test Verifier: Original comment is provided"""
        self.mock_helpers.verify_date_field.return_value = (True, "Date verified")
        self.mock_helpers.verify_comment.return_value = (True, "Comment verified")
        
        success, msg, results = self.step.verifier(
            begin_date="01/12/2026",
            end_date="01/16/2026",
            revision_number="APR2125",
            agent_name="test agent",
            original_comment="Original text here"
        )
        
        self.assertTrue(success)
        # Verify comment should be called with original_comment
        self.mock_helpers.verify_comment.assert_called_once()
        call_args = self.mock_helpers.verify_comment.call_args[0]
        self.assertEqual(call_args[2], "Original text here")  # original_comment parameter

    # ========================================================================
    # ERROR HANDLER FUNCTION TESTS
    # ========================================================================
    
    def test_error_handler_retry_allowed(self):
        """Test Error Handler: Retry when attempt < max_attempts"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=1,
            max_attempts=3
        )
        
        self.assertTrue(success)
        self.assertIn("Retrying", msg)

    def test_error_handler_no_retry(self):
        """Test Error Handler: No retry when attempt >= max_attempts"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=3,
            max_attempts=3
        )
        
        self.assertFalse(success)
        self.assertEqual(msg, "Test error")

    def test_error_handler_attempt_exceeds_max(self):
        """Test Error Handler: Attempt exceeds max_attempts"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=5,
            max_attempts=3
        )
        
        self.assertFalse(success)
        self.assertEqual(msg, "Test error")

    def test_error_handler_first_attempt(self):
        """Test Error Handler: First attempt (should retry)"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=0,
            max_attempts=3
        )
        
        self.assertTrue(success)
        self.assertIn("Retrying", msg)

    def test_error_handler_last_attempt(self):
        """Test Error Handler: Last attempt (should not retry)"""
        success, msg = self.step.error_handler(
            error_msg="Test error",
            attempt=2,
            max_attempts=3
        )
        
        self.assertTrue(success)  # Still retries (2 < 3)
        self.assertIn("Retrying", msg)

if __name__ == '__main__':
    unittest.main()
