#!/usr/bin/env python3
"""
Worker API Routes

Endpoints called by remote workers to:
- Fetch and lock the next available task
- Send heartbeats to keep the lease alive
- Update instruction status
- Write step execution logs
- Complete/fail a task

These are separate from the task management endpoints in app.py
to keep the code organized. Mount these in app.py.

All endpoints require a worker_id for identification.
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.db_module.db_client import get_db

router = APIRouter(prefix="/workers", tags=["Workers"])


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class FetchTaskRequest(BaseModel):
    worker_id: str = Field(..., description="Unique worker identifier (e.g., 'worker-machine-A')")
    lease_duration_seconds: int = Field(120, description="Lease duration in seconds")


class FetchTaskResponse(BaseModel):
    task_available: bool
    json_id: Optional[str] = None
    file_name: Optional[str] = None
    revision_number: Optional[str] = None
    instruction_count: Optional[int] = None
    raw_json: Optional[dict] = None
    instructions: Optional[list] = None
    message: str


class HeartbeatRequest(BaseModel):
    worker_id: str
    json_id: str
    lease_duration_seconds: int = Field(120, description="Lease extension duration")


class HeartbeatResponse(BaseModel):
    success: bool
    lease_extended: bool
    message: str


class UpdateInstructionRequest(BaseModel):
    worker_id: str
    status: str = Field(..., description="New status: executing, completed, failed")
    current_step: Optional[str] = None
    failure_reason: Optional[str] = None


class StepLogRequest(BaseModel):
    worker_id: str
    json_id: str
    step_id: str
    attempt_number: int = 1
    phase: Optional[str] = None
    precheck_result: Optional[dict] = None
    action_result: Optional[dict] = None
    postcheck_result: Optional[dict] = None
    screenshot_path: Optional[str] = None
    ocr_output: Optional[dict] = None
    cv_confidence: Optional[float] = None
    error_message: Optional[str] = None
    recovery_attempted: bool = False
    recovery_detail: Optional[dict] = None
    duration_ms: Optional[int] = None


class CompleteTaskRequest(BaseModel):
    worker_id: str
    json_id: str
    status: str = Field(..., description="Final status: completed or failed")
    failure_reason: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/fetch-next", response_model=FetchTaskResponse)
async def fetch_next_task(request: FetchTaskRequest):
    """
    Atomically fetch and lock the next available task for a worker.

    Uses FOR UPDATE SKIP LOCKED to prevent race conditions.
    Returns the full task with raw_json and all instruction records
    so the worker has everything it needs to start executing.
    
    If no tasks are available, returns task_available=False.
    """
    db = get_db()

    # Atomic lock via SKIP LOCKED
    task = db.fetch_and_lock_task(
        worker_id=request.worker_id,
        lease_duration_seconds=request.lease_duration_seconds,
    )

    if task is None:
        return FetchTaskResponse(
            task_available=False,
            message="No tasks available in queue",
        )

    json_id = str(task["json_id"])

    # Load all instructions for this task (worker needs the full list)
    instructions = db.get_instructions_by_task(json_id)

    # Convert instruction UUIDs to strings for JSON serialization
    for inst in instructions:
        inst["instruction_id"] = str(inst["instruction_id"])
        inst["json_id"] = str(inst["json_id"])

    # Also load full instruction_data for each instruction
    full_instructions = []
    for inst in instructions:
        full_inst = db.get_instruction(inst["instruction_id"])
        if full_inst:
            full_inst["instruction_id"] = str(full_inst["instruction_id"])
            full_inst["json_id"] = str(full_inst["json_id"])
            full_instructions.append(full_inst)

    # Update task status to executing
    db.update_task_status(json_id, "executing", worker_id=request.worker_id)

    return FetchTaskResponse(
        task_available=True,
        json_id=json_id,
        file_name=task.get("file_name"),
        revision_number=task.get("revision_number"),
        instruction_count=task.get("instruction_count", 0),
        raw_json=task.get("raw_json"),
        instructions=full_instructions,
        message=f"Task locked for worker '{request.worker_id}'",
    )


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def worker_heartbeat(request: HeartbeatRequest):
    """
    Worker heartbeat — extends the lease on the assigned task.

    Workers must call this every 30 seconds (lease is 120s).
    If a worker fails to heartbeat before lease expiry,
    the task becomes available for other workers.
    """
    db = get_db()

    success = db.extend_lease(
        json_id=request.json_id,
        worker_id=request.worker_id,
        lease_duration_seconds=request.lease_duration_seconds,
    )

    if success:
        return HeartbeatResponse(
            success=True,
            lease_extended=True,
            message="Lease extended",
        )
    else:
        return HeartbeatResponse(
            success=False,
            lease_extended=False,
            message="Failed to extend lease — task may have been reassigned",
        )


@router.put("/instructions/{instruction_id}/status")
async def update_instruction_status(instruction_id: str, request: UpdateInstructionRequest):
    """
    Update the status of an instruction being executed by a worker.
    """
    db = get_db()

    db.update_instruction_status(
        instruction_id=instruction_id,
        status=request.status,
        current_step=request.current_step,
        failure_reason=request.failure_reason,
    )

    return {"success": True, "instruction_id": instruction_id, "status": request.status}


@router.post("/instructions/{instruction_id}/steps/log")
async def write_step_log(instruction_id: str, request: StepLogRequest):
    """
    Write a step execution log entry for an instruction.
    
    Called after each step phase (precheck, action, postcheck).
    This is append-only — logs are never updated.
    """
    db = get_db()

    log_data = {
        "instruction_id": instruction_id,
        "json_id": request.json_id,
        "step_id": request.step_id,
        "worker_id": request.worker_id,
        "attempt_number": request.attempt_number,
        "phase": request.phase,
        "precheck_result": request.precheck_result,
        "action_result": request.action_result,
        "postcheck_result": request.postcheck_result,
        "screenshot_path": request.screenshot_path,
        "ocr_output": request.ocr_output,
        "cv_confidence": request.cv_confidence,
        "error_message": request.error_message,
        "recovery_attempted": request.recovery_attempted,
        "recovery_detail": request.recovery_detail,
        "duration_ms": request.duration_ms,
    }

    result = db.write_step_log(log_data)

    return {"success": True, "log_id": str(result["log_id"])}


@router.get("/instructions/{instruction_id}/steps/logs")
async def get_step_logs(instruction_id: str):
    """
    Get all step execution logs for an instruction (chronological order).
    
    Used by workers to determine resume point after crash recovery.
    Returns completed step count so the worker knows where to resume.
    """
    db = get_db()
    logs = db.get_step_logs(instruction_id)

    # Convert UUIDs to strings
    for log in logs:
        log["log_id"] = str(log["log_id"])

    # Count successfully completed steps (action_result.success == true)
    completed_steps = 0
    completed_step_ids = []
    for log in logs:
        action_result = log.get("action_result")
        if isinstance(action_result, dict) and action_result.get("success"):
            completed_steps += 1
            completed_step_ids.append(log.get("step_id"))

    return {
        "instruction_id": instruction_id,
        "total_logs": len(logs),
        "completed_steps": completed_steps,
        "completed_step_ids": completed_step_ids,
        "logs": logs,
    }


@router.get("/instructions/{instruction_id}/status")
async def get_instruction_status(instruction_id: str):
    """
    Get current status of a single instruction.
    
    Used by workers to check if an instruction was already completed
    (e.g., during crash recovery — skip completed instructions).
    """
    db = get_db()
    instruction = db.get_instruction(instruction_id)

    if instruction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instruction not found: {instruction_id}",
        )

    instruction["instruction_id"] = str(instruction["instruction_id"])
    instruction["json_id"] = str(instruction["json_id"])

    return instruction


@router.post("/complete-task")
async def complete_task(request: CompleteTaskRequest):
    """
    Mark a task as completed or failed after all instructions are processed.
    
    This releases the worker from the task so it can poll for the next one.
    """
    db = get_db()

    if request.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'completed' or 'failed'",
        )

    db.update_task_status(
        json_id=request.json_id,
        status=request.status,
        worker_id=None,  # Release the worker assignment
    )

    return {
        "success": True,
        "json_id": request.json_id,
        "status": request.status,
        "message": f"Task marked as {request.status}. Worker released.",
    }


# ============================================================================
# LEASE EXPIRY (called by background job or API endpoint)
# ============================================================================

@router.post("/expire-leases")
async def expire_stale_leases():
    """
    Check for and reset tasks with expired leases.
    
    Call this periodically (e.g., every 60 seconds via cron or scheduler).
    Tasks whose workers stopped sending heartbeats will be reset to 'queued'
    so other workers can pick them up.
    """
    db = get_db()
    count = db.expire_stale_leases()

    return {
        "expired_count": count,
        "message": f"Reset {count} task(s) with expired leases",
    }
