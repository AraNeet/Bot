#!/usr/bin/env python3
"""
Citrix XRD Automation Engine — API Server

FastAPI application providing endpoints for:
- Task submission (POST /tasks)
- Task status queries (GET /tasks/{json_id})
- Instruction listing (GET /tasks/{json_id}/instructions)
- Health check (GET /health)

Start the server:
    uvicorn src.api_module.app:app --host 0.0.0.0 --port 8000 --reload

Or:
    python -m src.api_module.app
"""

import os
import sys
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Load env vars
from dotenv import load_dotenv
load_dotenv("bot.env")
load_dotenv(".env")

from src.db_module.db_client import get_db, close_pool


# ============================================================================
# LIFESPAN (startup / shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[API] Starting up...")
    # Verify DB connection on startup
    try:
        db = get_db()
        print("[API] Database connection verified")
    except Exception as e:
        print(f"[API ERROR] Database connection failed: {e}")

    # Start background lease expiry checker
    import threading
    lease_checker_stop = threading.Event()

    def _lease_expiry_loop():
        """Background loop that resets tasks with expired leases every 60s."""
        import time
        print("[LEASE_CHECKER] Background lease expiry checker started (every 60s)")
        while not lease_checker_stop.is_set():
            lease_checker_stop.wait(60)
            if not lease_checker_stop.is_set():
                try:
                    count = get_db().expire_stale_leases()
                    if count > 0:
                        print(f"[LEASE_CHECKER] Reset {count} task(s) with expired leases")
                except Exception as e:
                    print(f"[LEASE_CHECKER ERROR] {e}")

    lease_thread = threading.Thread(target=_lease_expiry_loop, daemon=True)
    lease_thread.start()

    yield
    # Shutdown
    print("[API] Shutting down...")
    lease_checker_stop.set()
    close_pool()


# ============================================================================
# APP
# ============================================================================

app = FastAPI(
    title="Citrix XRD Automation Engine",
    description="API for submitting and tracking Citrix automation tasks",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount worker routes
from src.api_module.worker_routes import router as worker_router
app.include_router(worker_router)


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class TaskSubmitRequest(BaseModel):
    """Request body for submitting a new task."""
    payload: dict = Field(..., description="The full JSON payload to process")
    file_name: Optional[str] = Field(None, description="Original filename")
    source: Optional[str] = Field(None, description="Upstream system identifier")


class TaskSubmitResponse(BaseModel):
    """Response after submitting a task."""
    json_id: str
    status: str
    message: str
    is_duplicate: bool = False


class TaskStatusResponse(BaseModel):
    """Response for task status query."""
    json_id: str
    file_name: Optional[str]
    revision_number: Optional[str]
    status: str
    assigned_worker_id: Optional[str]
    instruction_count: int
    completed_instructions: int
    failed_instructions: int
    executing_instructions: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]


class InstructionResponse(BaseModel):
    """Single instruction in the list response."""
    instruction_id: str
    alert_id: Optional[int]
    instruction_index: int
    action_type: Optional[str]
    status: str
    current_step: Optional[str]
    retry_count: int
    failure_reason: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class InstructionsListResponse(BaseModel):
    """Response for listing instructions under a task."""
    json_id: str
    total_instructions: int
    instructions: List[InstructionResponse]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    timestamp: datetime


# ============================================================================
# ENDPOINTS
# ============================================================================

# ── Task 1: Health check ──

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    System health check.
    
    Verifies API is running and database is reachable.
    """
    db_status = "unknown"
    try:
        from src.db_module.db_client import get_connection
        with get_connection() as conn:
            conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        timestamp=datetime.utcnow(),
    )


# ── Task 2 + 7: Submit task ──

@app.post("/tasks", response_model=TaskSubmitResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def submit_task(request: TaskSubmitRequest):
    """
    Submit a JSON payload for processing.

    The payload is stored in Supabase, instructions are extracted from
    the alerts, and the task is marked as 'queued' (ready for workers).

    If the same payload was already submitted (same SHA-256 hash),
    the existing json_id is returned instead of creating a duplicate.
    """
    db = get_db()

    try:
        result = db.create_task(
            raw_json=request.payload,
            file_name=request.file_name,
            source=request.source,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store task: {str(e)}",
        )

    # Check if this was a duplicate (existing task returned)
    is_duplicate = result.get("status") != "unread" or "completed_at" in result

    json_id = str(result["json_id"])

    if is_duplicate:
        return TaskSubmitResponse(
            json_id=json_id,
            status=result.get("status", "unknown"),
            message=f"Duplicate payload detected. Existing task returned.",
            is_duplicate=True,
        )

    # Extract instructions from the JSON payload
    from src.db_module.instruction_extractor import extract_and_store_instructions
    try:
        extraction_ok, instruction_count = extract_and_store_instructions(json_id)
        if not extraction_ok:
            print(f"[API WARNING] Instruction extraction failed for task {json_id}")
    except Exception as e:
        print(f"[API ERROR] Instruction extraction error: {e}")
        instruction_count = 0

    return TaskSubmitResponse(
        json_id=json_id,
        status="queued",
        message=f"Task received. {instruction_count} instruction(s) extracted and queued.",
        is_duplicate=False,
    )


# ── Task 8: Get task status ──

@app.get("/tasks/{json_id}", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(json_id: str):
    """
    Get the current status of a task.

    Returns task metadata, status, worker assignment, and instruction progress.
    Never returns the raw JSON payload (by design — security boundary).
    """
    db = get_db()

    task = db.get_task(json_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {json_id}",
        )

    return TaskStatusResponse(
        json_id=str(task["json_id"]),
        file_name=task.get("file_name"),
        revision_number=task.get("revision_number"),
        status=task["status"],
        assigned_worker_id=task.get("assigned_worker_id"),
        instruction_count=task.get("instruction_count", 0),
        completed_instructions=task.get("completed_instructions", 0),
        failed_instructions=task.get("failed_instructions", 0),
        executing_instructions=task.get("executing_instructions", 0),
        created_at=task.get("created_at"),
        updated_at=task.get("updated_at"),
        completed_at=task.get("completed_at"),
    )


# ── Task 9: List instructions ──

@app.get("/tasks/{json_id}/instructions", response_model=InstructionsListResponse, tags=["Tasks"])
async def list_instructions(json_id: str):
    """
    List all instructions for a task with their statuses.

    Instructions are returned in execution order (by instruction_index).
    """
    db = get_db()

    # Verify task exists
    task = db.get_task(json_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {json_id}",
        )

    instructions = db.get_instructions_by_task(json_id)

    return InstructionsListResponse(
        json_id=json_id,
        total_instructions=len(instructions),
        instructions=[
            InstructionResponse(
                instruction_id=str(inst["instruction_id"]),
                alert_id=inst.get("alert_id"),
                instruction_index=inst["instruction_index"],
                action_type=inst.get("action_type"),
                status=inst["status"],
                current_step=inst.get("current_step"),
                retry_count=inst.get("retry_count", 0),
                failure_reason=inst.get("failure_reason"),
                started_at=inst.get("started_at"),
                completed_at=inst.get("completed_at"),
            )
            for inst in instructions
        ],
    )


# ── Extract instructions (utility endpoint) ──

@app.post("/tasks/{json_id}/extract", tags=["Tasks"])
async def extract_instructions(json_id: str):
    """
    Manually trigger instruction extraction for a task.
    
    Useful for:
    - Tasks that were created before extraction was wired in
    - Re-extracting after a payload fix
    
    Will skip if instructions already exist for this task.
    """
    db = get_db()
    
    task = db.get_task(json_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {json_id}",
        )
    
    # Check if instructions already exist
    existing = db.get_instructions_by_task(json_id)
    if existing:
        return {
            "json_id": json_id,
            "message": f"Instructions already exist ({len(existing)} found). Use /tasks/{json_id}/re-extract to force re-extraction.",
            "instruction_count": len(existing),
            "skipped": True,
        }
    
    from src.db_module.instruction_extractor import extract_and_store_instructions
    
    try:
        success, count = extract_and_store_instructions(json_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}",
        )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Extraction failed — check server logs for details",
        )
    
    return {
        "json_id": json_id,
        "message": f"Successfully extracted {count} instruction(s)",
        "instruction_count": count,
        "status": "queued",
    }


# ── Instruction execution history ──

@app.get("/instructions/{instruction_id}/history", tags=["Tasks"])
async def get_instruction_history(instruction_id: str):
    """
    Get the full execution history for an instruction.

    Returns the instruction metadata plus all step log entries
    in chronological order — including precheck/action/postcheck results,
    screenshot paths, OCR outputs, recovery traces, and timing.

    Use this for:
    - Debugging why an instruction failed
    - Auditing what the worker did at each step
    - Viewing recovery engine traces
    - Finding failure screenshots
    """
    db = get_db()

    # Get instruction metadata
    instruction = db.get_instruction(instruction_id)
    if instruction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instruction not found: {instruction_id}",
        )

    # Get all step logs
    step_logs = db.get_step_logs(instruction_id)

    # Convert UUIDs to strings
    instruction["instruction_id"] = str(instruction["instruction_id"])
    instruction["json_id"] = str(instruction["json_id"])
    for log in step_logs:
        log["log_id"] = str(log["log_id"])

    # Build summary stats
    total_logs = len(step_logs)
    successful_steps = sum(
        1 for log in step_logs
        if isinstance(log.get("action_result"), dict)
        and log["action_result"].get("success")
    )
    failed_steps = sum(
        1 for log in step_logs
        if log.get("error_message")
    )
    recovery_attempts = sum(
        1 for log in step_logs
        if log.get("recovery_attempted")
    )
    screenshots = [
        log["screenshot_path"] for log in step_logs
        if log.get("screenshot_path")
    ]
    total_duration_ms = sum(
        log.get("duration_ms", 0) for log in step_logs
        if log.get("duration_ms")
    )

    return {
        "instruction": instruction,
        "summary": {
            "total_log_entries": total_logs,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "recovery_attempts": recovery_attempts,
            "screenshots_captured": len(screenshots),
            "screenshot_paths": screenshots,
            "total_duration_ms": total_duration_ms,
        },
        "step_logs": step_logs,
    }


# ============================================================================
# RUN (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api_module.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
