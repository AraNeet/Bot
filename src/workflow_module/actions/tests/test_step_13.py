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


class TestStep13EditAssignmentPercentage(unittest.TestCase):

    def setUp(self):
        self.mock_cv = MagicMock()
        self.mock_debugger_instance = MagicMock()
        self.mock_debugger_class = MagicMock(return_value=self.mock_debugger_instance)
        self.mock_debug_utils = MagicMock()
        self.mock_debug_utils.Debugger = self.mock_debugger_class

        self.mock_screenshot = MagicMock()
        self.mock_cv.take_screenshot.return_value = self.mock_screenshot

        # Mock helpers (step 13 loads helpers from 13_helper.py at import time)
        self.mock_helpers = MagicMock()
        self.mock_helpers.WORK_AREA = (200, 425, 1450, 570)

        # Default: ensure_assignment_aliases_in_view returns success with two aliases
        self.mock_aliases = [
            {"alias": "A", "alias_x": 250, "row_y": 500},
            {"alias": "B", "alias_x": 250, "row_y": 530},
        ]
        self.mock_helpers.ensure_assignment_aliases_in_view.return_value = (
            True,
            {"x": 200, "y": 450, "width": 1450, "height": 400},
            self.mock_aliases,
        )

        self.mock_pyautogui = MagicMock()
        self.mock_ocr_utils = MagicMock()

        self.modules_patcher = patch.dict(sys.modules, {
            "src.workflow_module.actions.helpers.computer_vision_utils": self.mock_cv,
            "src.workflow_module.actions.helpers.debug_utils": self.mock_debug_utils,
            "src.workflow_module.actions.helpers.ocr_utils": self.mock_ocr_utils,
            "pyautogui": self.mock_pyautogui,
        })
        self.modules_patcher.start()

        self.step = load_step_module("13_edit_assignment_percentage", "13_edit_assignment_percentage_handler")
        self.step.helpers = self.mock_helpers
        self.step.Debugger = self.mock_debugger_class

    def tearDown(self):
        self.modules_patcher.stop()

    # ========================================================================
    # ACTION FUNCTION TESTS
    # ========================================================================

    def test_action_success_with_assignment_data(self):
        """Test Action: Success with assignment_data dict."""
        assignment_data = {"A": "50", "B": "50"}
        success, msg = self.step.action(assignment_data=assignment_data)

        self.assertTrue(success)
        self.assertIn("aliases in view", msg)
        self.mock_helpers.ensure_assignment_aliases_in_view.assert_called_once()
        self.mock_helpers.select_all_in_alias_input_fields.assert_called()
        self.mock_helpers.right_click_delete_field.assert_called()
        self.mock_helpers.input_value_in_field.assert_called()

    def test_action_success_empty_assignment_data(self):
        """Test Action: Success with empty assignment_data (skip processing)."""
        success, msg = self.step.action(assignment_data={})

        self.assertTrue(success)
        self.assertIn("No assignment data", msg)
        self.mock_helpers.ensure_assignment_aliases_in_view.assert_not_called()

    def test_action_success_none_assignment_data(self):
        """Test Action: Success with None assignment_data (treated as empty)."""
        success, msg = self.step.action(assignment_data=None)

        self.assertTrue(success)
        self.assertIn("No assignment data", msg)
        self.mock_helpers.ensure_assignment_aliases_in_view.assert_not_called()

    def test_action_calls_input_value_for_each_alias(self):
        """Test Action: input_value_in_field called per alias with correct value."""
        assignment_data = {"A": "60", "B": "40"}
        self.step.action(assignment_data=assignment_data)

        calls = self.mock_helpers.input_value_in_field.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0]["alias"], "A")
        self.assertEqual(calls[0][0][1], "60")
        self.assertEqual(calls[1][0][0]["alias"], "B")
        self.assertEqual(calls[1][0][1], "40")

    def test_action_screenshot_failure(self):
        """Test Action: Failure when take_screenshot returns None."""
        self.mock_cv.take_screenshot.return_value = None

        success, msg = self.step.action(assignment_data={"A": "100"})

        self.assertFalse(success)
        self.assertIn("screenshot", msg.lower())
        self.mock_helpers.ensure_assignment_aliases_in_view.assert_not_called()

    def test_action_ensure_aliases_failure(self):
        """Test Action: Failure when ensure_assignment_aliases_in_view returns success=False."""
        self.mock_helpers.ensure_assignment_aliases_in_view.return_value = (False, None, [])

        success, msg = self.step.action(assignment_data={"A": "100"})

        self.assertFalse(success)
        self.assertIn("Total or 10+ aliases", msg)
        self.mock_helpers.select_all_in_alias_input_fields.assert_not_called()

    # ========================================================================
    # VERIFIER FUNCTION TESTS
    # ========================================================================

    def test_verifier_success(self):
        """Test Verifier: Success when total is 100% and all fields have numbers."""
        self.mock_helpers.get_total_percentage.return_value = 100
        self.mock_helpers.verify_all_fields_have_numbers.return_value = (True, [])

        success, msg, details = self.step.verifier(assignment_data={"A": "50", "B": "50"})

        self.assertTrue(success)
        self.assertIn("100%", msg)
        self.assertEqual(details.get("total"), 100)
        self.assertEqual(details.get("invalid_fields"), [])

    def test_verifier_failure_ensure_aliases(self):
        """Test Verifier: Failure when ensure_assignment_aliases_in_view fails."""
        self.mock_helpers.ensure_assignment_aliases_in_view.return_value = (False, None, [])

        success, msg, details = self.step.verifier(assignment_data={})

        self.assertFalse(success)
        self.assertIn("could not get Assignment area", msg)
        self.assertEqual(details, {})

    def test_verifier_failure_screenshot(self):
        """Test Verifier: Failure when take_screenshot returns None."""
        self.mock_cv.take_screenshot.return_value = None

        success, msg, details = self.step.verifier(assignment_data={})

        self.assertFalse(success)
        self.assertIn("screenshot", msg.lower())
        self.assertEqual(details, {})

    def test_verifier_failure_total_not_100(self):
        """Test Verifier: Failure when Total percentage is not 100."""
        self.mock_helpers.get_total_percentage.return_value = 90
        self.mock_helpers.verify_all_fields_have_numbers.return_value = (True, [])

        success, msg, details = self.step.verifier(assignment_data={})

        self.assertFalse(success)
        self.assertIn("90%", msg)
        self.assertIn("100%", msg)
        self.assertEqual(details.get("total"), 90)

    def test_verifier_failure_total_none(self):
        """Test Verifier: Failure when get_total_percentage returns None."""
        self.mock_helpers.get_total_percentage.return_value = None

        success, msg, details = self.step.verifier(assignment_data={})

        self.assertFalse(success)
        self.assertIn("could not read Total", msg)
        self.assertIsNone(details.get("total"))

    def test_verifier_failure_invalid_fields(self):
        """Test Verifier: Failure when some fields have no number."""
        self.mock_helpers.get_total_percentage.return_value = 100
        self.mock_helpers.verify_all_fields_have_numbers.return_value = (False, ["B"])

        success, msg, details = self.step.verifier(assignment_data={})

        self.assertFalse(success)
        self.assertIn("no number", msg)
        self.assertEqual(details.get("invalid_fields"), ["B"])

    # ========================================================================
    # ERROR HANDLER FUNCTION TESTS
    # ========================================================================

    def test_error_handler_returns_false(self):
        """Test Error Handler: Returns (False, error_msg)."""
        success, msg = self.step.error_handler(
            error_msg="Could not get Assignment area",
            attempt=1,
            max_attempts=3,
        )

        self.assertFalse(success)
        self.assertEqual(msg, "Could not get Assignment area")


if __name__ == "__main__":
    unittest.main()
