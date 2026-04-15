#!/usr/bin/env python3
"""
Worker Runner — Standalone Process (Production Version)

Main entry point for a worker machine. Runs as a long-lived process that:
1. Checks for crash recovery checkpoint on startup
2. Polls the central API for available tasks
3. Locks a task, loads all instructions
4. For each instruction: executes steps via unified_executor
5. After each step: updates current_step in Supabase + saves local checkpoint
6. Sends heartbeats to keep the lease alive
7. On completion/failure: updates Supabase, clears checkpoint, polls next

Run:
    python -m src.worker_module.worker_runner

Config via worker_config.env:
    WORKER_ID=worker-machine-A
    API_URL=http://localhost:8000
    POLL_INTERVAL=10
    LEASE_DURATION=120
    HEARTBEAT_INTERVAL=30
"""

import os
import sys
import time
import signal
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from dotenv import load_dotenv

# Load worker config
load_dotenv("worker_config.env")
load_dotenv("bot.env")
load_dotenv(".env")

from src.worker_module.worker_api_client import WorkerAPIClient
from src.worker_module.local_checkpoint import LocalCheckpoint


# ============================================================================
# CONFIGURATION
# ============================================================================

WORKER_ID = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
API_URL = os.getenv("API_URL", "http://localhost:8000")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))
LEASE_DURATION = int(os.getenv("LEASE_DURATION", "120"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))


# ============================================================================
# HEARTBEAT THREAD
# ============================================================================

class HeartbeatThread:
    """Background thread that sends periodic heartbeats to keep the task lease alive."""

    def __init__(self, client: WorkerAPIClient, json_id: str, interval: int = 30):
        self.client = client
        self.json_id = json_id
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[HEARTBEAT] Started for task {self.json_id} (every {self.interval}s)")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print(f"[HEARTBEAT] Stopped for task {self.json_id}")

    def _run(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval)
            if not self._stop_event.is_set():
                success = self.client.send_heartbeat(self.json_id)
                if not success:
                    print(f"[HEARTBEAT WARNING] Failed to extend lease")


# ============================================================================
# STEP EXECUTION WITH TRACKING
# ============================================================================

def execute_steps_for_instruction(
    client: WorkerAPIClient,
    checkpoint: LocalCheckpoint,
    json_id: str,
    instruction: Dict[str, Any],
    steps: List[Dict[str, Any]],
    resume_from_step: int = 0,
) -> Tuple[bool, str]:
    """
    Execute all steps for a single instruction with per-step tracking.
    
    For each step:
        1. Update current_step in Supabase
        2. Run precheck → action → postcheck via unified_executor
        3. Log results to Supabase
        4. Save local checkpoint
        5. On failure: stop and return
    
    Args:
        client: API client for Supabase updates
        checkpoint: Local checkpoint manager
        json_id: Parent task ID
        instruction: Instruction record from API
        steps: List of step dicts from the objective definition
        resume_from_step: Step index to resume from (0-based, for crash recovery)
        
    Returns:
        Tuple of (success, failure_reason or success message)
    """
    instruction_id = instruction["instruction_id"]
    instruction_index = instruction.get("instruction_index", 0)
    total_steps = len(steps)

    from src.workflow_module.actions.unified_executor import execute_action_with_verification

    for step_index, step in enumerate(steps):
        step_num = step_index + 1  # 1-based for display
        action_type = step.get("action_type", "unknown")
        parameters = step.get("parameters", {})

        # Skip steps that were already completed (crash recovery)
        if step_index < resume_from_step:
            print(f"[WORKER] Step {step_num}/{total_steps}: {action_type} — SKIPPED (already completed)")
            continue

        print(f"\n{'─'*60}")
        print(f"[WORKER] Step {step_num}/{total_steps}: {action_type}")
        print(f"[WORKER] Parameters: {parameters}")
        print(f"{'─'*60}")

        # Update current_step in Supabase
        client.update_instruction_status(
            instruction_id, "executing", current_step=action_type
        )

        # Execute step via unified executor (precheck → action → postcheck)
        step_start = time.time()
        success, message, verification_data = execute_action_with_verification(
            action_type=action_type,
            parameters=parameters,
            max_retries=3,
            verify=True,
        )
        duration_ms = int((time.time() - step_start) * 1000)

        # Log step result to Supabase
        log_data = {
            "phase": "complete",
            "attempt_number": 1,
            "duration_ms": duration_ms,
        }
        if success:
            log_data["action_result"] = {"success": True, "message": message}
        else:
            log_data["error_message"] = message
            log_data["action_result"] = {"success": False, "message": message}

        client.write_step_log(
            instruction_id=instruction_id,
            json_id=json_id,
            step_id=action_type,
            **log_data,
        )

        if success:
            print(f"[WORKER] Step {step_num}/{total_steps}: {action_type} — PASSED ({duration_ms}ms)")

            # Save checkpoint after each successful step
            checkpoint.save(
                json_id=json_id,
                instruction_id=instruction_id,
                instruction_index=instruction_index,
                step_index=step_num,  # 1-based: "step 3 of 13 completed"
                step_id=action_type,
                total_steps=total_steps,
                status="in_progress",
            )
        else:
            print(f"[WORKER] Step {step_num}/{total_steps}: {action_type} — FAILED ({duration_ms}ms)")
            print(f"[WORKER] Failure: {message}")

            # ── ATTEMPT RECOVERY ──
            # Instead of immediately failing, try to backtrack and restore
            from src.workflow_module.recovery_engine import attempt_recovery

            print(f"[WORKER] Invoking recovery engine for step {step_num}...")
            recovery_ok, recovery_msg, recovery_trace = attempt_recovery(
                steps=steps,
                failed_step_index=step_index,
                failed_step_message=message,
            )

            # Log recovery attempt to Supabase
            recovery_log = {
                "phase": "recovery",
                "attempt_number": 1,
                "duration_ms": int((time.time() - step_start) * 1000),
                "error_message": message,
                "recovery_attempted": True,
                "recovery_detail": {
                    "success": recovery_ok,
                    "message": recovery_msg,
                    "trace": recovery_trace,
                },
            }
            client.write_step_log(
                instruction_id=instruction_id,
                json_id=json_id,
                step_id=action_type,
                **recovery_log,
            )

            if recovery_ok:
                print(f"[WORKER] Recovery SUCCEEDED — step {step_num} passed after backtrack")
                print(f"[WORKER] {recovery_msg}")

                # Save checkpoint — recovery restored us through the failed step
                checkpoint.save(
                    json_id=json_id,
                    instruction_id=instruction_id,
                    instruction_index=instruction_index,
                    step_index=step_num,  # This step is now completed via recovery
                    step_id=action_type,
                    total_steps=total_steps,
                    status="in_progress",
                )
                # Continue to next step (don't return failure)
                continue
            else:
                print(f"[WORKER] Recovery FAILED — {recovery_msg}")

                # Save checkpoint with failure state
                checkpoint.save(
                    json_id=json_id,
                    instruction_id=instruction_id,
                    instruction_index=instruction_index,
                    step_index=step_num - 1,  # Last SUCCESSFUL step
                    step_id=action_type,
                    total_steps=total_steps,
                    status="step_failed",
                )

                return False, f"Step {step_num} ({action_type}) failed. Recovery failed: {recovery_msg}"

    return True, f"All {total_steps} steps completed successfully"


# ============================================================================
# INSTRUCTION EXECUTION
# ============================================================================

def execute_instruction(
    client: WorkerAPIClient,
    checkpoint: LocalCheckpoint,
    json_id: str,
    instruction: Dict[str, Any],
    resume_from_step: int = 0,
) -> bool:
    """
    Execute a single instruction end-to-end.
    
    1. Prepare the instruction (load step definitions, merge values)
    2. Execute all steps with tracking
    3. Update status in Supabase
    """
    instruction_id = instruction["instruction_id"]
    action_type = instruction.get("action_type", "unknown")
    instruction_data = instruction.get("instruction_data", {})
    instruction_index = instruction.get("instruction_index", 0)

    print(f"\n{'='*60}")
    print(f"[WORKER] Instruction {instruction_index}: {action_type}")
    print(f"[WORKER] ID: {instruction_id}")
    if resume_from_step > 0:
        print(f"[WORKER] RESUMING from step {resume_from_step + 1}")
    print(f"{'='*60}")

    # Mark instruction as executing
    client.update_instruction_status(instruction_id, "executing")

    # Save initial checkpoint
    checkpoint.save(
        json_id=json_id,
        instruction_id=instruction_id,
        instruction_index=instruction_index,
        step_index=resume_from_step,
        step_id="starting",
        total_steps=0,
        status="in_progress",
    )

    start_time = time.time()

    try:
        # Prepare the instruction — load step definitions and merge values
        from src.workflow_module.engine.workflow_planner import _prepare_single_objective

        objective_type = _map_to_objective_type(action_type)
        objective_values = _build_objective_values(instruction_data)

        prep_success, prepared_data = _prepare_single_objective(
            objective_type=objective_type,
            objective_values=objective_values,
        )

        if not prep_success:
            error_msg = f"Failed to prepare instruction: {prepared_data}"
            print(f"[WORKER ERROR] {error_msg}")
            client.update_instruction_status(instruction_id, "failed", failure_reason=error_msg)
            checkpoint.save(
                json_id=json_id, instruction_id=instruction_id,
                instruction_index=instruction_index, step_index=0,
                step_id="preparation", total_steps=0, status="instruction_failed",
            )
            return False

        steps = prepared_data.get("instructions", [])
        print(f"[WORKER] Loaded {len(steps)} steps for {objective_type}")

        # Execute all steps with tracking
        success, result_message = execute_steps_for_instruction(
            client=client,
            checkpoint=checkpoint,
            json_id=json_id,
            instruction=instruction,
            steps=steps,
            resume_from_step=resume_from_step,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if success:
            print(f"[WORKER] Instruction {instruction_index} COMPLETED ({duration_ms}ms)")
            client.update_instruction_status(instruction_id, "completed")
            checkpoint.save(
                json_id=json_id, instruction_id=instruction_id,
                instruction_index=instruction_index,
                step_index=len(steps), step_id="all_done",
                total_steps=len(steps), status="instruction_completed",
            )
            return True
        else:
            print(f"[WORKER] Instruction {instruction_index} FAILED ({duration_ms}ms): {result_message}")
            client.update_instruction_status(
                instruction_id, "failed", failure_reason=result_message
            )
            return False

    except Exception as e:
        error_msg = f"Exception executing instruction: {str(e)}"
        print(f"[WORKER ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        client.update_instruction_status(instruction_id, "failed", failure_reason=error_msg)
        return False


# ============================================================================
# VALUE MAPPING (instruction_data → handler parameters)
# ============================================================================

def _map_to_objective_type(action_type: str) -> str:
    """Map the extracted action_type to the objective definition filename."""
    mapping = {
        "edit_copy": "edit_copy_definition",
        "duplicate_copy": "duplicate_copy_definition",
    }
    return mapping.get(action_type, action_type)


def _build_objective_values(instruction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the values dict that the existing workflow planner expects.
    Maps instruction_data fields to handler parameter names.
    """
    copy_instructions = instruction_data.get("copy_instructions", [])

    values = {
        "advertiser_name": instruction_data.get("advertiser", ""),
        "agency_name": instruction_data.get("agency", ""),
        "estimate_number": instruction_data.get("order_id", ""),
        "begin_date": instruction_data.get("flight_start_date", ""),
        "end_date": instruction_data.get("flight_end_date", ""),
    }

    # Map copy instructions to ISCI fields
    for i, copy in enumerate(copy_instructions):
        idx = i + 1
        values[f"isci_{idx}"] = copy.get("copy_id", "")
        values[f"rotation_percent_isci_{idx}"] = copy.get("rotation_percent", "").replace("%", "")

    return values


# ============================================================================
# CRASH RECOVERY
# ============================================================================

def attempt_crash_recovery(client: WorkerAPIClient, checkpoint: LocalCheckpoint) -> bool:
    """
    Check for an existing checkpoint and attempt to resume execution.
    
    Called on worker startup before entering the main poll loop.
    
    Returns:
        True if a recovery was attempted (regardless of success),
        False if no checkpoint found.
    """
    state = checkpoint.load()
    if state is None:
        print("[WORKER] No checkpoint found — starting fresh")
        return False

    json_id = state["json_id"]
    instruction_id = state["instruction_id"]
    last_step = state["last_completed_step_index"]
    status = state.get("status", "unknown")

    print(f"\n{'!'*60}")
    print(f"[RECOVERY] Checkpoint found!")
    print(f"[RECOVERY] Task: {json_id}")
    print(f"[RECOVERY] Instruction: {instruction_id} (index {state.get('instruction_index', '?')})")
    print(f"[RECOVERY] Last completed step: {last_step}/{state.get('total_steps', '?')}")
    print(f"[RECOVERY] Status: {status}")
    print(f"{'!'*60}\n")

    # If the instruction was already completed or failed, just clear and continue
    if status in ("instruction_completed", "instruction_failed"):
        print(f"[RECOVERY] Instruction already {status} — clearing checkpoint")
        checkpoint.clear()
        return False

    # Try to re-fetch the task from the API to verify it's still ours
    # The task might have been reassigned after lease expiry
    print(f"[RECOVERY] Attempting to resume task {json_id}...")

    # We can't re-lock a task via the API easily, so we'll just clear
    # the checkpoint and let the normal poll loop pick up whatever is next.
    # The key value of the checkpoint is knowing WHERE we left off —
    # when the task gets re-queued (via lease expiry) and we pick it up again,
    # we can check the step_logs in Supabase to determine the resume point.
    print(f"[RECOVERY] Clearing stale checkpoint. Task will be re-queued via lease expiry.")
    print(f"[RECOVERY] When re-picked, execution will resume from step {last_step + 1}")
    checkpoint.clear()
    return True


# ============================================================================
# MAIN WORKER LOOP
# ============================================================================

def run_worker():
    """
    Main worker loop — polls for tasks, executes them, repeats.
    """
    print(f"\n{'='*60}")
    print(f"CITRIX XRD WORKER STARTING")
    print(f"{'='*60}")
    print(f"  Worker ID:          {WORKER_ID}")
    print(f"  API URL:            {API_URL}")
    print(f"  Poll interval:      {POLL_INTERVAL}s")
    print(f"  Lease duration:     {LEASE_DURATION}s")
    print(f"  Heartbeat interval: {HEARTBEAT_INTERVAL}s")
    print(f"{'='*60}\n")

    client = WorkerAPIClient(
        api_url=API_URL,
        worker_id=WORKER_ID,
        lease_duration=LEASE_DURATION,
    )

    chkpt = LocalCheckpoint(worker_id=WORKER_ID)

    # ── Crash recovery check ──
    attempt_crash_recovery(client, chkpt)

    # ── Check API health ──
    if not client.check_api_health():
        print(f"[WORKER ERROR] Cannot reach API at {API_URL}")
        print(f"[WORKER] Will retry on next poll cycle...")

    # ── Graceful shutdown ──
    shutdown_requested = threading.Event()

    def handle_signal(signum, frame):
        print(f"\n[WORKER] Shutdown signal received. Finishing current task...")
        shutdown_requested.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # ── Main loop ──
    while not shutdown_requested.is_set():
        print(f"\n[WORKER] Polling for tasks...")
        task = client.fetch_next_task()

        if task is None:
            print(f"[WORKER] No tasks available. Waiting {POLL_INTERVAL}s...")
            shutdown_requested.wait(POLL_INTERVAL)
            continue

        json_id = task["json_id"]
        instructions = task.get("instructions", [])

        print(f"\n[WORKER] === TASK RECEIVED: {json_id} ===")
        print(f"[WORKER] File: {task.get('file_name', 'N/A')}")
        print(f"[WORKER] Instructions: {len(instructions)}")

        # Start heartbeat
        heartbeat = HeartbeatThread(client, json_id, HEARTBEAT_INTERVAL)
        heartbeat.start()

        # Execute instructions in sequence
        all_succeeded = True
        for instruction in instructions:
            if shutdown_requested.is_set():
                print(f"[WORKER] Shutdown requested — stopping")
                all_succeeded = False
                break

            instruction_id = instruction["instruction_id"]
            instruction_index = instruction.get("instruction_index", 0)

            # Check if this instruction was already completed (crash recovery)
            inst_status = client.get_instruction_status(instruction_id)
            if inst_status and inst_status.get("status") == "completed":
                print(f"[WORKER] Instruction {instruction_index} already completed — skipping")
                continue

            # Determine resume point within this instruction
            resume_step = _get_resume_step_for_instruction(
                client, instruction_id, json_id
            )

            success = execute_instruction(
                client=client,
                checkpoint=chkpt,
                json_id=json_id,
                instruction=instruction,
                resume_from_step=resume_step,
            )

            if not success:
                all_succeeded = False
                # Mark remaining instructions as skipped
                remaining = [i for i in instructions
                             if i["instruction_index"] > instruction["instruction_index"]]
                for r in remaining:
                    client.update_instruction_status(
                        r["instruction_id"], "skipped",
                        failure_reason="Skipped due to prior instruction failure"
                    )
                break

        # Stop heartbeat
        heartbeat.stop()

        # Complete the task
        if all_succeeded and not shutdown_requested.is_set():
            client.complete_task(json_id, "completed")
            print(f"\n[WORKER] === TASK COMPLETED: {json_id} ===")
        else:
            reason = "Worker shutdown" if shutdown_requested.is_set() else "Instruction failure"
            client.complete_task(json_id, "failed", failure_reason=reason)
            print(f"\n[WORKER] === TASK FAILED: {json_id} ===")

        # Clear checkpoint — task is done (success or fail)
        chkpt.clear()

        if not shutdown_requested.is_set():
            time.sleep(2)

    print(f"\n[WORKER] Worker {WORKER_ID} shut down gracefully.")


def _get_resume_step_for_instruction(client: WorkerAPIClient,
                                      instruction_id: str,
                                      json_id: str) -> int:
    """
    Check if an instruction was partially executed (from a previous crashed run).
    
    Queries the step_logs via the API to count how many steps completed
    successfully. The worker can then skip those steps and resume from
    the next one.
    
    Returns:
        Step index to resume from (0-based). 0 = start from beginning.
    """
    try:
        # Check instruction status first
        inst_status = client.get_instruction_status(instruction_id)
        if inst_status is None:
            return 0

        status = inst_status.get("status", "pending")

        # If already completed, the main loop should skip it entirely
        # but return a high number just in case
        if status == "completed":
            print(f"[RESUME] Instruction {instruction_id} already completed — will skip")
            return 9999

        # If it was never started, start from beginning
        if status == "pending":
            return 0

        # If it was executing (crashed mid-way), check step logs
        if status in ("executing", "failed"):
            logs_result = client.get_step_logs(instruction_id)
            if logs_result and logs_result.get("completed_steps", 0) > 0:
                completed = logs_result["completed_steps"]
                step_ids = logs_result.get("completed_step_ids", [])
                print(f"[RESUME] Instruction {instruction_id}: {completed} steps already completed: {step_ids}")
                print(f"[RESUME] Will resume from step {completed + 1}")
                return completed  # 0-based index = skip this many steps
            else:
                print(f"[RESUME] Instruction {instruction_id} was {status} but no completed steps found — starting from beginning")
                return 0

    except Exception as e:
        print(f"[RESUME WARNING] Error checking resume point: {e} — starting from beginning")

    return 0


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_worker()
