#!/usr/bin/env python3
"""
Unified Executor Module

Executes step handlers using the Precheck -> Action -> Postcheck lifecycle.

Execution flow for each step:
1. PRECHECK: Verify the UI is in the expected state (correct page, element visible)
2. ACTION: Perform the UI interaction (click, type, select, scroll)
3. POSTCHECK (verifier): Verify the expected outcome occurred

Multi-level retry:
- Precheck retries: 3 attempts (UI may still be loading)
- Action retries: 2 attempts (click may have missed)
- Postcheck retries: 3 attempts (UI update may be delayed)
- Step retries: 2 attempts (full precheck+action+postcheck cycle)

Every failure captures a screenshot for debugging.
"""

from typing import Dict, Any, Tuple, Optional
import json
import time
import importlib
from pathlib import Path
from src.notification_module.error_notifier import notify_error
from src.workflow_module.actions.helpers.computer_vision_utils import capture_failure_screenshot

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_action_list(config_path: str = "src/workflow_module/actions/action_list.json") -> Dict[str, Any]:
    """Load action list from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"[UNIFIED_EXECUTOR] Loaded action list from {config_path}")
        return config
    except FileNotFoundError:
        print(f"[UNIFIED_EXECUTOR ERROR] Action list file not found: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[UNIFIED_EXECUTOR ERROR] Failed to parse action list: {e}")
        return {}

# Load action list at module import
ACTION_LIST = load_action_list()

# ============================================================================
# DEFAULT RETRY CONFIGURATION
# ============================================================================

DEFAULT_RETRY_POLICY = {
    "precheck_retries": 3,
    "precheck_interval": 2.0,
    "action_retries": 2,
    "action_interval": 1.0,
    "postcheck_retries": 3,
    "postcheck_interval": 2.0,
    "step_retries": 2,
    "step_interval": 3.0,
}

# ============================================================================
# HANDLER LOADING
# ============================================================================

def get_handler_module(action_type: str):
    """Dynamically import and return the handler module for an action type."""
    if action_type not in ACTION_LIST:
        return None
    
    handler_info = ACTION_LIST[action_type]
    module_path = handler_info.get('module')
    
    if not module_path:
        print(f"[UNIFIED_EXECUTOR ERROR] No module path for action type: {action_type}")
        return None
    
    try:
        module = importlib.import_module(module_path)
        return module
    except ImportError as e:
        print(f"[UNIFIED_EXECUTOR ERROR] Failed to import handler module {module_path}: {e}")
        return None

# ============================================================================
# PHASE EXECUTORS
# ============================================================================

def _run_precheck(handler_module, action_type: str, parameters: Dict[str, Any],
                  retry_policy: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Run the precheck phase with retries.
    
    If the handler has no precheck(), this phase is skipped (returns success).
    """
    if not hasattr(handler_module, 'precheck'):
        return True, "No precheck defined (skipped)"
    
    max_retries = retry_policy.get("precheck_retries", 3)
    interval = retry_policy.get("precheck_interval", 2.0)
    
    msg = ""
    for attempt in range(1, max_retries + 1):
        try:
            success, msg = handler_module.precheck(**parameters)
        except Exception as e:
            success = False
            msg = f"Precheck exception: {e}"
        
        if success:
            print(f"[PRECHECK] Passed: {msg}")
            return True, msg
        
        print(f"[PRECHECK] Failed (attempt {attempt}/{max_retries}): {msg}")
        capture_failure_screenshot(action_type, attempt=attempt, context="precheck")
        
        if attempt < max_retries:
            time.sleep(interval)
    
    return False, f"Precheck failed after {max_retries} attempts: {msg}"


def _run_action(handler_module, action_type: str, parameters: Dict[str, Any],
                retry_policy: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Run the action phase with retries.
    
    On failure, calls the handler's error_handler() if available.
    """
    max_retries = retry_policy.get("action_retries", 2)
    interval = retry_policy.get("action_interval", 1.0)
    
    msg = ""
    for attempt in range(1, max_retries + 1):
        try:
            success, msg = handler_module.action(**parameters)
        except Exception as e:
            success = False
            msg = f"Action exception: {e}"
        
        if success:
            print(f"[ACTION] Succeeded: {msg}")
            return True, msg
        
        print(f"[ACTION] Failed (attempt {attempt}/{max_retries}): {msg}")
        capture_failure_screenshot(action_type, attempt=attempt, context="action")
        
        # Call error handler if available
        if hasattr(handler_module, 'error_handler'):
            try:
                should_retry, recovery_msg = handler_module.error_handler(
                    error_msg=msg, attempt=attempt, max_attempts=max_retries, **parameters
                )
                print(f"[ACTION] Error handler: {recovery_msg}")
                if not should_retry:
                    return False, f"Error handler says don't retry: {recovery_msg}"
            except Exception as e:
                print(f"[ACTION] Error handler failed: {e}")
        
        if attempt < max_retries:
            time.sleep(interval)
    
    return False, f"Action failed after {max_retries} attempts: {msg}"


def _run_postcheck(handler_module, action_type: str, parameters: Dict[str, Any],
                   retry_policy: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict]]:
    """
    Run the postcheck (verifier) phase with retries.
    
    If the handler has no verifier(), this phase is skipped (returns success).
    """
    if not hasattr(handler_module, 'verifier'):
        return True, "No verifier defined (skipped)", None
    
    max_retries = retry_policy.get("postcheck_retries", 3)
    interval = retry_policy.get("postcheck_interval", 2.0)
    
    verification_data = None
    msg = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            result = handler_module.verifier(**parameters)
            
            # Handle different return types
            if isinstance(result, tuple):
                if len(result) == 2:
                    success, msg = result
                    verification_data = None
                elif len(result) == 3:
                    success, msg, verification_data = result
                else:
                    success, msg, verification_data = False, "Invalid verifier return format", None
            else:
                success, msg, verification_data = True, str(result), None
                
        except Exception as e:
            success = False
            msg = f"Postcheck exception: {e}"
            verification_data = None
        
        if success:
            print(f"[POSTCHECK] Passed: {msg}")
            return True, msg, verification_data
        
        print(f"[POSTCHECK] Failed (attempt {attempt}/{max_retries}): {msg}")
        capture_failure_screenshot(action_type, attempt=attempt, context="postcheck")
        
        if attempt < max_retries:
            time.sleep(interval)
    
    return False, f"Postcheck failed after {max_retries} attempts: {msg}", verification_data


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def execute_action_with_verification(
    action_type: str,
    parameters: Dict[str, Any],
    max_retries: int = 3,
    verify: bool = True,
    retry_policy: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute a step using the Precheck -> Action -> Postcheck lifecycle.
    
    Step-level retries: if the full cycle fails, the entire
    precheck -> action -> postcheck sequence is retried up to step_retries times.
    
    Args:
        action_type: Type of action to execute (e.g., "enter_advertiser_name")
        parameters: Parameters dict for the action
        max_retries: Legacy parameter (kept for backward compatibility, 
                     use retry_policy for fine-grained control)
        verify: Whether to run postcheck after action
        retry_policy: Optional retry configuration overriding defaults
        
    Returns:
        Tuple of (success: bool, message: str, verification_data: Optional[Dict])
    """
    # Merge retry policy with defaults
    policy = {**DEFAULT_RETRY_POLICY}
    if retry_policy:
        policy.update(retry_policy)
    # Honor legacy max_retries for step-level if no explicit policy
    if retry_policy is None and max_retries != 3:
        policy["step_retries"] = max_retries
    
    print(f"\n[UNIFIED_EXECUTOR] === Executing: {action_type} ===")
    print(f"[UNIFIED_EXECUTOR] Parameters: {parameters}")
    
    # Validate action type is supported
    if action_type not in ACTION_LIST:
        error_msg = f"Unsupported action type: '{action_type}'"
        print(f"[UNIFIED_EXECUTOR ERROR] {error_msg}")
        notify_error(error_msg, "unified_executor", {"action_type": action_type})
        return False, error_msg, None
    
    # Load handler module
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        error_msg = f"Failed to load handler module for: '{action_type}'"
        return False, error_msg, None
    
    if not hasattr(handler_module, 'action'):
        error_msg = f"Handler for '{action_type}' missing 'action' function"
        return False, error_msg, None
    
    # Step-level retry loop
    step_retries = policy.get("step_retries", 2)
    step_interval = policy.get("step_interval", 3.0)
    
    for step_attempt in range(1, step_retries + 1):
        if step_attempt > 1:
            print(f"\n[UNIFIED_EXECUTOR] --- Step retry {step_attempt}/{step_retries} for '{action_type}' ---")
        
        # -- PHASE 1: PRECHECK --
        precheck_ok, precheck_msg = _run_precheck(
            handler_module, action_type, parameters, policy
        )
        
        if not precheck_ok:
            print(f"[UNIFIED_EXECUTOR] Precheck failed: {precheck_msg}")
            if step_attempt < step_retries:
                time.sleep(step_interval)
                continue
            else:
                final_msg = f"Step '{action_type}' failed at precheck after {step_retries} step attempts: {precheck_msg}"
                notify_error(final_msg, "unified_executor", {
                    "action_type": action_type, "phase": "precheck",
                    "step_attempts": step_retries
                })
                return False, final_msg, None
        
        # -- PHASE 2: ACTION --
        action_ok, action_msg = _run_action(
            handler_module, action_type, parameters, policy
        )
        
        if not action_ok:
            print(f"[UNIFIED_EXECUTOR] Action failed: {action_msg}")
            if step_attempt < step_retries:
                time.sleep(step_interval)
                continue
            else:
                final_msg = f"Step '{action_type}' failed at action after {step_retries} step attempts: {action_msg}"
                notify_error(final_msg, "unified_executor", {
                    "action_type": action_type, "phase": "action",
                    "step_attempts": step_retries
                })
                return False, final_msg, None
        
        # -- PHASE 3: POSTCHECK (VERIFIER) --
        if verify:
            postcheck_ok, postcheck_msg, verification_data = _run_postcheck(
                handler_module, action_type, parameters, policy
            )
            
            if not postcheck_ok:
                print(f"[UNIFIED_EXECUTOR] Postcheck failed: {postcheck_msg}")
                if step_attempt < step_retries:
                    time.sleep(step_interval)
                    continue
                else:
                    final_msg = f"Step '{action_type}' failed at postcheck after {step_retries} step attempts: {postcheck_msg}"
                    notify_error(final_msg, "unified_executor", {
                        "action_type": action_type, "phase": "postcheck",
                        "step_attempts": step_retries
                    })
                    return False, final_msg, verification_data
        else:
            verification_data = None
        
        # -- ALL PHASES PASSED --
        success_msg = f"Step '{action_type}' completed successfully"
        print(f"[UNIFIED_EXECUTOR] {success_msg}")
        return True, success_msg, verification_data
    
    # Should not reach here
    return False, f"Unexpected end of step retry loop for '{action_type}'", None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_supported_actions() -> list:
    """Get list of supported action types."""
    return list(ACTION_LIST.keys())

def has_verifier(action_type: str) -> bool:
    """Check if an action type has a verifier."""
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        return False
    return hasattr(handler_module, 'verifier')

def has_error_handler(action_type: str) -> bool:
    """Check if an action type has an error handler."""
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        return False
    return hasattr(handler_module, 'error_handler')

def has_precheck(action_type: str) -> bool:
    """Check if an action type has a precheck."""
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        return False
    return hasattr(handler_module, 'precheck')
