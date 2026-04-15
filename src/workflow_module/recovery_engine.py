#!/usr/bin/env python3
"""
Recovery Engine

When a step fails after all retries are exhausted, the recovery engine
backtracks through the step dependency chain to find and restore the
most recent valid state, then retries the failed step.

Recovery Algorithm:
    Step N fails
    → Check step N-1 postcheck (verifier)
    → If N-1 postcheck passes → prior state is intact → retry step N
    → If N-1 postcheck fails:
        → Check N-1 precheck
        → If N-1 precheck passes → rerun N-1 action → verify N-1 postcheck
        → If restored → retry step N
        → If N-1 cannot be restored → walk back to N-2, repeat
    → Continue all the way to step 1 if needed
    → If step 1 precheck also fails → recovery failed → instruction fails

Usage:
    from src.workflow_module.recovery_engine import attempt_recovery

    success, message = attempt_recovery(
        steps=all_steps,
        failed_step_index=4,       # 0-based index of the step that failed
        failed_step_message="Postcheck failed: field not found",
    )
"""

import time
from typing import Dict, Any, List, Tuple, Optional


def attempt_recovery(
    steps: List[Dict[str, Any]],
    failed_step_index: int,
    failed_step_message: str,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Attempt to recover from a step failure by backtracking.
    
    Walks backward through the step chain, validating and restoring
    prior step states until a valid state is found, then retries
    the original failed step.
    
    Args:
        steps: Full list of step dicts (each has action_type, parameters)
        failed_step_index: 0-based index of the step that failed
        failed_step_message: Error message from the failed step
        
    Returns:
        Tuple of:
            success: bool — whether recovery succeeded and the failed step now passes
            message: str — description of what happened
            recovery_trace: list of dicts documenting each backtrack attempt
    """
    from src.workflow_module.actions.unified_executor import (
        get_handler_module, _run_precheck, _run_action, _run_postcheck,
        DEFAULT_RETRY_POLICY,
    )

    total_steps = len(steps)
    failed_step = steps[failed_step_index]
    failed_action_type = failed_step.get("action_type", "unknown")
    failed_params = failed_step.get("parameters", {})

    print(f"\n{'!'*60}")
    print(f"[RECOVERY] === RECOVERY ENGINE ACTIVATED ===")
    print(f"[RECOVERY] Failed step: {failed_step_index + 1}/{total_steps} ({failed_action_type})")
    print(f"[RECOVERY] Failure: {failed_step_message}")
    print(f"[RECOVERY] Will backtrack to find restorable state...")
    print(f"{'!'*60}")

    recovery_trace = []
    policy = {**DEFAULT_RETRY_POLICY}

    # Walk backward from the step BEFORE the failed one
    backtrack_start = failed_step_index - 1

    if backtrack_start < 0:
        msg = "Cannot backtrack — failed step is the first step (step 1)"
        print(f"[RECOVERY] {msg}")
        recovery_trace.append({
            "action": "no_backtrack_possible",
            "reason": msg,
        })
        return False, msg, recovery_trace

    restored_to_index = -1  # Track which step we successfully restored to

    for check_index in range(backtrack_start, -1, -1):
        check_step = steps[check_index]
        check_action_type = check_step.get("action_type", "unknown")
        check_params = check_step.get("parameters", {})
        step_num = check_index + 1  # 1-based for display

        print(f"\n[RECOVERY] --- Checking step {step_num}/{total_steps}: {check_action_type} ---")

        # Load the handler module for this step
        handler_module = get_handler_module(check_action_type)
        if handler_module is None:
            print(f"[RECOVERY] Cannot load handler for '{check_action_type}' — skipping")
            recovery_trace.append({
                "step_index": check_index,
                "step_id": check_action_type,
                "action": "skip",
                "reason": "handler not loadable",
            })
            continue

        # ── PHASE 1: Validate prior step's postcheck ──
        if hasattr(handler_module, 'verifier'):
            print(f"[RECOVERY] Validating postcheck of step {step_num} ({check_action_type})...")
            postcheck_ok, postcheck_msg, _ = _run_postcheck(
                handler_module, check_action_type, check_params, policy
            )

            if postcheck_ok:
                print(f"[RECOVERY] Step {step_num} postcheck VALID — prior state is intact")
                restored_to_index = check_index
                recovery_trace.append({
                    "step_index": check_index,
                    "step_id": check_action_type,
                    "action": "postcheck_valid",
                    "result": "prior state intact",
                })
                break  # Found valid state — stop backtracking
            else:
                print(f"[RECOVERY] Step {step_num} postcheck INVALID: {postcheck_msg}")
                recovery_trace.append({
                    "step_index": check_index,
                    "step_id": check_action_type,
                    "action": "postcheck_invalid",
                    "message": postcheck_msg,
                })
        else:
            print(f"[RECOVERY] Step {step_num} has no verifier — cannot validate postcheck")
            recovery_trace.append({
                "step_index": check_index,
                "step_id": check_action_type,
                "action": "no_verifier",
                "reason": "handler has no verifier function",
            })

        # ── PHASE 2: Try to restore this step (precheck → action → postcheck) ──
        print(f"[RECOVERY] Attempting to RESTORE step {step_num} ({check_action_type})...")

        # Check precheck first
        precheck_ok = True
        if hasattr(handler_module, 'precheck'):
            precheck_ok, precheck_msg = _run_precheck(
                handler_module, check_action_type, check_params, policy
            )
            if not precheck_ok:
                print(f"[RECOVERY] Step {step_num} precheck FAILED: {precheck_msg}")
                print(f"[RECOVERY] Cannot restore step {step_num} — walking further back...")
                recovery_trace.append({
                    "step_index": check_index,
                    "step_id": check_action_type,
                    "action": "precheck_failed",
                    "message": precheck_msg,
                })
                continue  # Walk back further
        
        # Precheck passed — run the action
        print(f"[RECOVERY] Step {step_num} precheck passed — re-running action...")
        action_ok, action_msg = _run_action(
            handler_module, check_action_type, check_params, policy
        )

        if not action_ok:
            print(f"[RECOVERY] Step {step_num} action FAILED during restore: {action_msg}")
            recovery_trace.append({
                "step_index": check_index,
                "step_id": check_action_type,
                "action": "restore_action_failed",
                "message": action_msg,
            })
            continue  # Walk back further

        # Action succeeded — verify postcheck
        if hasattr(handler_module, 'verifier'):
            postcheck_ok2, postcheck_msg2, _ = _run_postcheck(
                handler_module, check_action_type, check_params, policy
            )

            if postcheck_ok2:
                print(f"[RECOVERY] Step {step_num} RESTORED successfully")
                restored_to_index = check_index
                recovery_trace.append({
                    "step_index": check_index,
                    "step_id": check_action_type,
                    "action": "restored",
                    "result": "step re-executed and verified",
                })
                break  # Restored — stop backtracking
            else:
                print(f"[RECOVERY] Step {step_num} postcheck FAILED after restore: {postcheck_msg2}")
                recovery_trace.append({
                    "step_index": check_index,
                    "step_id": check_action_type,
                    "action": "restore_postcheck_failed",
                    "message": postcheck_msg2,
                })
                continue  # Walk back further
        else:
            # No verifier — assume action success means restored
            print(f"[RECOVERY] Step {step_num} restored (no verifier to confirm)")
            restored_to_index = check_index
            recovery_trace.append({
                "step_index": check_index,
                "step_id": check_action_type,
                "action": "restored_no_verifier",
                "result": "action re-executed, no verifier to confirm",
            })
            break

    # ── PHASE 3: Check if we found a restorable state ──
    if restored_to_index < 0:
        msg = f"Recovery FAILED — could not restore any prior step (walked back to step 1)"
        print(f"\n[RECOVERY] {msg}")
        recovery_trace.append({
            "action": "recovery_failed",
            "reason": "no restorable state found after full backtrack",
        })
        return False, msg, recovery_trace

    # ── PHASE 4: Re-execute steps from restored point to failed step ──
    print(f"\n[RECOVERY] State restored at step {restored_to_index + 1}")
    print(f"[RECOVERY] Now re-executing steps {restored_to_index + 2} through {failed_step_index + 1}...")

    # Re-run intermediate steps (between restored step and failed step)
    for rerun_index in range(restored_to_index + 1, failed_step_index + 1):
        rerun_step = steps[rerun_index]
        rerun_action_type = rerun_step.get("action_type", "unknown")
        rerun_params = rerun_step.get("parameters", {})
        rerun_num = rerun_index + 1

        print(f"\n[RECOVERY] Re-executing step {rerun_num}/{total_steps}: {rerun_action_type}")

        handler = get_handler_module(rerun_action_type)
        if handler is None:
            msg = f"Recovery FAILED — cannot load handler for step {rerun_num} ({rerun_action_type})"
            recovery_trace.append({"action": "rerun_handler_missing", "step_id": rerun_action_type})
            return False, msg, recovery_trace

        # Run full precheck → action → postcheck
        from src.workflow_module.actions.unified_executor import execute_action_with_verification

        rerun_ok, rerun_msg, _ = execute_action_with_verification(
            action_type=rerun_action_type,
            parameters=rerun_params,
            max_retries=3,
            verify=True,
        )

        if rerun_ok:
            print(f"[RECOVERY] Step {rerun_num} re-executed successfully")
            recovery_trace.append({
                "step_index": rerun_index,
                "step_id": rerun_action_type,
                "action": "rerun_success",
            })
        else:
            msg = f"Recovery FAILED — step {rerun_num} ({rerun_action_type}) failed during re-execution: {rerun_msg}"
            print(f"[RECOVERY] {msg}")
            recovery_trace.append({
                "step_index": rerun_index,
                "step_id": rerun_action_type,
                "action": "rerun_failed",
                "message": rerun_msg,
            })
            return False, msg, recovery_trace

    # ── PHASE 5: All re-executions passed (including the originally failed step) ──
    msg = (
        f"Recovery SUCCEEDED — backtracked to step {restored_to_index + 1}, "
        f"re-executed steps {restored_to_index + 2} through {failed_step_index + 1}"
    )
    print(f"\n[RECOVERY] {msg}")
    print(f"[RECOVERY] === RECOVERY ENGINE COMPLETE ===\n")

    return True, msg, recovery_trace
