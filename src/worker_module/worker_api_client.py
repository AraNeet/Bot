#!/usr/bin/env python3
"""
Worker API Client

Thin HTTP client that workers use to communicate with the central API server.
No database dependency — only needs the `requests` library and the API URL.

This runs on each worker machine. It handles:
- Fetching and locking tasks from the queue
- Sending heartbeats to keep the lease alive
- Updating instruction status
- Writing step execution logs
- Completing/failing tasks

Usage:
    from src.worker_module.worker_api_client import WorkerAPIClient

    client = WorkerAPIClient(api_url="http://192.168.1.100:8000", worker_id="worker-A")

    task = client.fetch_next_task()
    if task:
        # process task...
        client.send_heartbeat(task["json_id"])
        client.update_instruction_status(instruction_id, "executing")
        client.complete_task(task["json_id"], "completed")
"""

import requests
from typing import Dict, Any, Optional, List


class WorkerAPIClient:
    """
    HTTP client for worker ↔ central API communication.
    """

    def __init__(self, api_url: str, worker_id: str, 
                 lease_duration: int = 120, timeout: int = 30):
        """
        Args:
            api_url: Base URL of the central API (e.g., "http://192.168.1.100:8000")
            worker_id: Unique identifier for this worker (e.g., "worker-machine-A")
            lease_duration: Lease duration in seconds for task locking
            timeout: HTTP request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.worker_id = worker_id
        self.lease_duration = lease_duration
        self.timeout = timeout

        print(f"[WORKER_CLIENT] Initialized: worker_id={worker_id}, api={api_url}")

    def _url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.api_url}{path}"

    def _post(self, path: str, data: dict) -> dict:
        """Make a POST request and return JSON response."""
        resp = requests.post(self._url(path), json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        """Make a PUT request and return JSON response."""
        resp = requests.put(self._url(path), json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict:
        """Make a GET request and return JSON response."""
        resp = requests.get(self._url(path), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ── Task Operations ──

    def fetch_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Fetch and lock the next available task from the queue.

        Returns:
            Task dict with json_id, raw_json, instructions, etc.
            None if no tasks available.
        """
        try:
            result = self._post("/workers/fetch-next", {
                "worker_id": self.worker_id,
                "lease_duration_seconds": self.lease_duration,
            })

            if result.get("task_available"):
                print(f"[WORKER_CLIENT] Task received: {result['json_id']}")
                return result
            else:
                return None

        except requests.exceptions.ConnectionError:
            print(f"[WORKER_CLIENT ERROR] Cannot connect to API at {self.api_url}")
            return None
        except requests.exceptions.Timeout:
            print(f"[WORKER_CLIENT ERROR] API request timed out")
            return None
        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to fetch task: {e}")
            return None

    def send_heartbeat(self, json_id: str) -> bool:
        """
        Send a heartbeat to keep the lease alive on the current task.

        Must be called more frequently than the lease duration (every 30s recommended).

        Returns:
            True if lease was extended, False if failed
        """
        try:
            result = self._post("/workers/heartbeat", {
                "worker_id": self.worker_id,
                "json_id": json_id,
                "lease_duration_seconds": self.lease_duration,
            })
            return result.get("lease_extended", False)

        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Heartbeat failed: {e}")
            return False

    def complete_task(self, json_id: str, final_status: str,
                      failure_reason: str = None) -> bool:
        """
        Mark a task as completed or failed. Releases the worker.

        Args:
            json_id: Task ID
            final_status: "completed" or "failed"
            failure_reason: Reason for failure (only if status="failed")
        """
        try:
            result = self._post("/workers/complete-task", {
                "worker_id": self.worker_id,
                "json_id": json_id,
                "status": final_status,
                "failure_reason": failure_reason,
            })
            print(f"[WORKER_CLIENT] Task {json_id} marked as {final_status}")
            return result.get("success", False)

        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to complete task: {e}")
            return False

    # ── Instruction Operations ──

    def update_instruction_status(self, instruction_id: str, status: str,
                                   current_step: str = None,
                                   failure_reason: str = None) -> bool:
        """Update the status of an instruction."""
        try:
            result = self._put(f"/workers/instructions/{instruction_id}/status", {
                "worker_id": self.worker_id,
                "status": status,
                "current_step": current_step,
                "failure_reason": failure_reason,
            })
            return result.get("success", False)

        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to update instruction: {e}")
            return False

    # ── Step Log Operations ──

    def write_step_log(self, instruction_id: str, json_id: str,
                       step_id: str, **kwargs) -> Optional[str]:
        """
        Write a step execution log entry.

        Args:
            instruction_id: Parent instruction
            json_id: Parent task
            step_id: Step that was executed
            **kwargs: Additional log fields (attempt_number, phase,
                      precheck_result, action_result, postcheck_result,
                      screenshot_path, ocr_output, cv_confidence,
                      error_message, recovery_attempted, recovery_detail,
                      duration_ms)

        Returns:
            log_id string, or None on failure
        """
        try:
            data = {
                "worker_id": self.worker_id,
                "json_id": json_id,
                "step_id": step_id,
                **kwargs,
            }
            result = self._post(f"/workers/instructions/{instruction_id}/steps/log", data)
            return result.get("log_id")

        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to write step log: {e}")
            return None

    # ── Health Check ──

    def check_api_health(self) -> bool:
        """Check if the central API is reachable."""
        try:
            result = self._get("/health")
            return result.get("status") in ("healthy",)
        except Exception:
            return False

    # ── Query Operations (for resume logic) ──

    def get_step_logs(self, instruction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get step execution logs for an instruction.
        
        Returns dict with:
            completed_steps: int (count of successfully completed steps)
            completed_step_ids: list of step_id strings
            logs: full log records
            
        Used for crash recovery — determines where to resume.
        """
        try:
            result = self._get(f"/workers/instructions/{instruction_id}/steps/logs")
            return result
        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to get step logs: {e}")
            return None

    def get_instruction_status(self, instruction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an instruction.
        
        Used during crash recovery to check if an instruction was
        already completed (skip it) or needs resuming.
        """
        try:
            result = self._get(f"/workers/instructions/{instruction_id}/status")
            return result
        except Exception as e:
            print(f"[WORKER_CLIENT ERROR] Failed to get instruction status: {e}")
            return None
