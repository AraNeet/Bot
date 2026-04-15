#!/usr/bin/env python3
"""
Database Client Module

Direct PostgreSQL connection to Supabase (not REST API) for:
- Task queue operations (SKIP LOCKED)
- Instruction CRUD
- Step log writes
- Status updates

Uses psycopg (v3) with connection pooling.

Setup:
    Set these env vars (or put in .env):
        SUPABASE_DB_HOST=db.xxxx.supabase.co
        SUPABASE_DB_PORT=5432
        SUPABASE_DB_NAME=postgres
        SUPABASE_DB_USER=postgres
        SUPABASE_DB_PASSWORD=your-password

Usage:
    from src.db_module.db_client import get_db

    db = get_db()
    task = db.create_task(raw_json, file_name="test.json")
    print(task["json_id"])
"""

import os
import json
import hashlib
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except ImportError:
    raise ImportError(
        "psycopg and psycopg_pool are required. Install with:\n"
        "  pip install psycopg[binary] psycopg_pool"
    )


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

_pool: Optional[ConnectionPool] = None


def _get_connection_string() -> str:
    """Build PostgreSQL connection string from env vars."""
    host = os.getenv("SUPABASE_DB_HOST", "")
    port = os.getenv("SUPABASE_DB_PORT", "5432")
    dbname = os.getenv("SUPABASE_DB_NAME", "postgres")
    user = os.getenv("SUPABASE_DB_USER", "postgres")
    password = os.getenv("SUPABASE_DB_PASSWORD", "")

    if not host or not password:
        raise ValueError(
            "Missing database credentials. Set SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD "
            "environment variables (or in .env file)."
        )

    return f"host={host} port={port} dbname={dbname} user={user} password={password} sslmode=require"


def _get_pool() -> ConnectionPool:
    """Get or create the connection pool (singleton)."""
    global _pool
    if _pool is None:
        conninfo = _get_connection_string()
        _pool = ConnectionPool(
            conninfo=conninfo,
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
        )
        print("[DB] Connection pool created")
    return _pool


@contextmanager
def get_connection():
    """Get a database connection from the pool."""
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn


def close_pool():
    """Close the connection pool (call on shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        print("[DB] Connection pool closed")


# ============================================================================
# DATABASE CLIENT CLASS
# ============================================================================

class DBClient:
    """
    Database client with all query operations for the automation engine.
    """

    # ── TASK OPERATIONS ──

    def create_task(self, raw_json: dict, file_name: str = None,
                    source: str = None) -> Dict[str, Any]:
        """
        Store a new JSON task in the database.

        Computes payload_hash for deduplication. If a task with the same
        hash already exists, returns the existing task instead of creating
        a duplicate.

        Args:
            raw_json: The full JSON payload
            file_name: Original filename (optional)
            source: Upstream system identifier (optional)

        Returns:
            Task record dict with json_id
        """
        payload_str = json.dumps(raw_json, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        revision_number = raw_json.get("revision_number", "")

        with get_connection() as conn:
            # Check for duplicate
            existing = conn.execute(
                "SELECT json_id, status FROM tasks WHERE payload_hash = %s",
                (payload_hash,)
            ).fetchone()

            if existing:
                print(f"[DB] Duplicate task detected (hash={payload_hash[:12]}...), returning existing json_id={existing['json_id']}")
                return dict(existing)

            # Insert new task
            result = conn.execute(
                """
                INSERT INTO tasks (payload_hash, raw_json, file_name, revision_number, source, status)
                VALUES (%s, %s, %s, %s, %s, 'unread')
                RETURNING json_id, payload_hash, status, file_name, created_at
                """,
                (payload_hash, psycopg.types.json.Json(raw_json), file_name, revision_number, source)
            ).fetchone()
            conn.commit()

            print(f"[DB] Task created: json_id={result['json_id']}")
            return dict(result)

    def get_task(self, json_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by json_id with instruction progress."""
        with get_connection() as conn:
            task = conn.execute(
                """
                SELECT 
                    t.json_id, t.payload_hash, t.file_name, t.revision_number,
                    t.status, t.assigned_worker_id, t.instruction_count,
                    t.source, t.created_at, t.updated_at, t.completed_at,
                    COUNT(i.instruction_id) FILTER (WHERE i.status = 'completed') AS completed_instructions,
                    COUNT(i.instruction_id) FILTER (WHERE i.status = 'failed') AS failed_instructions,
                    COUNT(i.instruction_id) FILTER (WHERE i.status = 'executing') AS executing_instructions
                FROM tasks t
                LEFT JOIN instructions i ON t.json_id = i.json_id
                WHERE t.json_id = %s
                GROUP BY t.json_id
                """,
                (json_id,)
            ).fetchone()

            if task:
                return dict(task)
            return None

    def update_task_status(self, json_id: str, status: str,
                          worker_id: str = None,
                          lease_duration_seconds: int = 120) -> bool:
        """Update task status and optionally assign worker."""
        with get_connection() as conn:
            params: dict = {"status": status, "json_id": json_id}
            set_parts = ["status = %(status)s"]

            if worker_id is not None:
                set_parts.append("assigned_worker_id = %(worker_id)s")
                params["worker_id"] = worker_id

            if status == "assigned":
                set_parts.append("lease_expires_at = now() + interval '%(lease)s seconds'")
                params["lease"] = lease_duration_seconds

            if status in ("completed", "failed"):
                set_parts.append("completed_at = now()")

            query = f"UPDATE tasks SET {', '.join(set_parts)} WHERE json_id = %(json_id)s"
            conn.execute(query, params)
            conn.commit()
            return True

    def update_task_instruction_count(self, json_id: str, count: int) -> bool:
        """Update the instruction_count field after extraction."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET instruction_count = %s WHERE json_id = %s",
                (count, json_id)
            )
            conn.commit()
            return True

    # ── INSTRUCTION OPERATIONS ──

    def create_instruction(self, json_id: str, alert_id: int,
                           instruction_index: int, action_type: str,
                           instruction_data: dict) -> Dict[str, Any]:
        """Create a single instruction record."""
        with get_connection() as conn:
            result = conn.execute(
                """
                INSERT INTO instructions 
                    (json_id, alert_id, instruction_index, action_type, instruction_data, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                RETURNING instruction_id, json_id, alert_id, instruction_index, action_type, status, created_at
                """,
                (json_id, alert_id, instruction_index, action_type,
                 psycopg.types.json.Json(instruction_data))
            ).fetchone()
            conn.commit()
            return dict(result)

    def create_instructions_batch(self, json_id: str,
                                   instructions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple instruction records in a single transaction.

        Args:
            json_id: Parent task ID
            instructions: List of dicts with keys:
                alert_id, instruction_index, action_type, instruction_data

        Returns:
            List of created instruction records
        """
        created = []
        with get_connection() as conn:
            for inst in instructions:
                result = conn.execute(
                    """
                    INSERT INTO instructions 
                        (json_id, alert_id, instruction_index, action_type, instruction_data, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING instruction_id, json_id, alert_id, instruction_index, action_type, status
                    """,
                    (json_id, inst["alert_id"], inst["instruction_index"],
                     inst["action_type"], psycopg.types.json.Json(inst["instruction_data"]))
                ).fetchone()
                created.append(dict(result))
            conn.commit()

        print(f"[DB] Created {len(created)} instructions for task {json_id}")
        return created

    def get_instructions_by_task(self, json_id: str) -> List[Dict[str, Any]]:
        """Get all instructions for a task, ordered by instruction_index."""
        with get_connection() as conn:
            results = conn.execute(
                """
                SELECT instruction_id, json_id, alert_id, instruction_index,
                       action_type, status, current_step, retry_count,
                       failure_reason, started_at, completed_at, created_at
                FROM instructions
                WHERE json_id = %s
                ORDER BY instruction_index ASC
                """,
                (json_id,)
            ).fetchall()
            return [dict(r) for r in results]

    def get_instruction(self, instruction_id: str) -> Optional[Dict[str, Any]]:
        """Get a single instruction with its full data."""
        with get_connection() as conn:
            result = conn.execute(
                """
                SELECT instruction_id, json_id, alert_id, instruction_index,
                       action_type, instruction_data, status, current_step,
                       retry_count, failure_reason, started_at, completed_at
                FROM instructions
                WHERE instruction_id = %s
                """,
                (instruction_id,)
            ).fetchone()
            if result:
                return dict(result)
            return None

    def update_instruction_status(self, instruction_id: str, status: str,
                                   current_step: str = None,
                                   failure_reason: str = None) -> bool:
        """Update instruction status and optional fields."""
        with get_connection() as conn:
            set_parts = ["status = %s"]
            params = [status]

            if current_step is not None:
                set_parts.append("current_step = %s")
                params.append(current_step)

            if failure_reason is not None:
                set_parts.append("failure_reason = %s")
                params.append(failure_reason)

            if status == "executing":
                set_parts.append("started_at = COALESCE(started_at, now())")

            if status in ("completed", "failed"):
                set_parts.append("completed_at = now()")

            params.append(instruction_id)
            query = f"UPDATE instructions SET {', '.join(set_parts)} WHERE instruction_id = %s"
            conn.execute(query, params)
            conn.commit()
            return True

    # ── STEP LOG OPERATIONS ──

    def write_step_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write a step execution log entry (append-only).

        Args:
            log_data: Dict with keys matching step_logs columns:
                instruction_id, json_id, step_id, worker_id, attempt_number,
                phase, precheck_result, action_result, postcheck_result,
                screenshot_path, ocr_output, cv_confidence, error_message,
                recovery_attempted, recovery_detail, duration_ms

        Returns:
            Created log record with log_id
        """
        with get_connection() as conn:
            result = conn.execute(
                """
                INSERT INTO step_logs (
                    instruction_id, json_id, step_id, worker_id, attempt_number,
                    phase, precheck_result, action_result, postcheck_result,
                    screenshot_path, ocr_output, cv_confidence, error_message,
                    recovery_attempted, recovery_detail, duration_ms
                ) VALUES (
                    %(instruction_id)s, %(json_id)s, %(step_id)s, %(worker_id)s, %(attempt_number)s,
                    %(phase)s, %(precheck_result)s, %(action_result)s, %(postcheck_result)s,
                    %(screenshot_path)s, %(ocr_output)s, %(cv_confidence)s, %(error_message)s,
                    %(recovery_attempted)s, %(recovery_detail)s, %(duration_ms)s
                )
                RETURNING log_id, created_at
                """,
                {
                    "instruction_id": log_data.get("instruction_id"),
                    "json_id": log_data.get("json_id"),
                    "step_id": log_data.get("step_id"),
                    "worker_id": log_data.get("worker_id"),
                    "attempt_number": log_data.get("attempt_number", 1),
                    "phase": log_data.get("phase"),
                    "precheck_result": psycopg.types.json.Json(log_data.get("precheck_result")),
                    "action_result": psycopg.types.json.Json(log_data.get("action_result")),
                    "postcheck_result": psycopg.types.json.Json(log_data.get("postcheck_result")),
                    "screenshot_path": log_data.get("screenshot_path"),
                    "ocr_output": psycopg.types.json.Json(log_data.get("ocr_output")),
                    "cv_confidence": log_data.get("cv_confidence"),
                    "error_message": log_data.get("error_message"),
                    "recovery_attempted": log_data.get("recovery_attempted", False),
                    "recovery_detail": psycopg.types.json.Json(log_data.get("recovery_detail")),
                    "duration_ms": log_data.get("duration_ms"),
                }
            ).fetchone()
            conn.commit()
            return dict(result)

    def get_step_logs(self, instruction_id: str) -> List[Dict[str, Any]]:
        """Get all step logs for an instruction, in chronological order."""
        with get_connection() as conn:
            results = conn.execute(
                """
                SELECT log_id, step_id, worker_id, attempt_number, phase,
                       precheck_result, action_result, postcheck_result,
                       screenshot_path, ocr_output, cv_confidence, error_message,
                       recovery_attempted, recovery_detail, duration_ms,
                       started_at, completed_at, created_at
                FROM step_logs
                WHERE instruction_id = %s
                ORDER BY created_at ASC
                """,
                (instruction_id,)
            ).fetchall()
            return [dict(r) for r in results]

    # ── QUEUE OPERATIONS ──

    def fetch_and_lock_task(self, worker_id: str,
                            lease_duration_seconds: int = 120) -> Optional[Dict[str, Any]]:
        """
        Atomically fetch and lock the next available task for a worker.

        Uses FOR UPDATE SKIP LOCKED to prevent race conditions between
        multiple workers polling simultaneously.

        Args:
            worker_id: Unique identifier for the worker
            lease_duration_seconds: How long the lock lasts before expiry

        Returns:
            Locked task record, or None if no tasks available
        """
        with get_connection() as conn:
            result = conn.execute(
                """
                UPDATE tasks 
                SET status = 'assigned',
                    assigned_worker_id = %(worker_id)s,
                    lease_expires_at = now() + make_interval(secs => %(lease)s)
                WHERE json_id = (
                    SELECT json_id FROM tasks
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING json_id, payload_hash, file_name, revision_number,
                          raw_json, status, assigned_worker_id, instruction_count,
                          created_at
                """,
                {"worker_id": worker_id, "lease": lease_duration_seconds}
            ).fetchone()
            conn.commit()

            if result:
                print(f"[DB] Task {result['json_id']} locked by worker {worker_id}")
                return dict(result)

            return None

    def extend_lease(self, json_id: str, worker_id: str,
                     lease_duration_seconds: int = 120) -> bool:
        """Extend the lease on a task (heartbeat)."""
        with get_connection() as conn:
            result = conn.execute(
                """
                UPDATE tasks 
                SET lease_expires_at = now() + make_interval(secs => %s)
                WHERE json_id = %s AND assigned_worker_id = %s AND status IN ('assigned', 'executing')
                RETURNING json_id
                """,
                (lease_duration_seconds, json_id, worker_id)
            ).fetchone()
            conn.commit()
            return result is not None

    def expire_stale_leases(self) -> int:
        """
        Find tasks with expired leases and reset them to queued.

        Called periodically by the orchestrator / lease checker.

        Returns:
            Number of tasks reset
        """
        with get_connection() as conn:
            results = conn.execute(
                """
                UPDATE tasks
                SET status = 'queued',
                    assigned_worker_id = NULL,
                    lease_expires_at = NULL
                WHERE status IN ('assigned', 'executing')
                  AND lease_expires_at < now()
                RETURNING json_id, assigned_worker_id
                """
            ).fetchall()
            conn.commit()

            count = len(results)
            if count > 0:
                for r in results:
                    print(f"[DB] Expired lease: task {r['json_id']} (was worker {r['assigned_worker_id']})")
            return count


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_db_instance: Optional[DBClient] = None


def get_db() -> DBClient:
    """Get the singleton DBClient instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DBClient()
    return _db_instance
