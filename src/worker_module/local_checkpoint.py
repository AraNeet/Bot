#!/usr/bin/env python3
"""
Local Checkpoint Module

Provides crash recovery for workers by persisting execution state to a local
JSON file after every successful step. If the worker process crashes and
restarts, it reads the checkpoint to resume from the last completed step.

Checkpoint lifecycle:
    1. Worker locks a task → create checkpoint
    2. Each step completes → update checkpoint
    3. Instruction completes/fails → update checkpoint
    4. All instructions done / task released → clear checkpoint

The checkpoint file is per-worker (one file per WORKER_ID).

Usage:
    from src.worker_module.local_checkpoint import LocalCheckpoint

    cp = LocalCheckpoint(worker_id="worker-A")

    # Save after each step
    cp.save(json_id, instruction_id, step_index=3, step_id="set_begin_date", total_steps=13)

    # On startup, check for existing checkpoint
    state = cp.load()
    if state:
        print(f"Resuming from step {state['last_completed_step_index'] + 1}")

    # Clear when task is done
    cp.clear()
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime


class LocalCheckpoint:
    """
    Manages a local checkpoint file for crash recovery.
    
    One checkpoint file per worker. Stored in the checkpoints/ directory
    at the project root.
    """

    def __init__(self, worker_id: str, checkpoint_dir: str = "checkpoints"):
        """
        Args:
            worker_id: Unique worker identifier
            checkpoint_dir: Directory to store checkpoint files
        """
        self.worker_id = worker_id
        self.checkpoint_dir = checkpoint_dir
        self.filepath = os.path.join(checkpoint_dir, f"{worker_id}.json")

        # Ensure directory exists
        os.makedirs(checkpoint_dir, exist_ok=True)

    def save(self, json_id: str, instruction_id: str,
             instruction_index: int,
             step_index: int, step_id: str,
             total_steps: int,
             retry_count: int = 0,
             status: str = "in_progress") -> bool:
        """
        Save current execution state to checkpoint file.
        
        Called after every successful step.
        
        Args:
            json_id: Current task ID
            instruction_id: Current instruction ID
            instruction_index: Instruction position (1-based)
            step_index: Completed step index (1-based). 
                        0 means instruction started but no steps completed yet.
            step_id: Completed step action_type (e.g., "type_advertiser_name")
            total_steps: Total steps in this instruction
            retry_count: Current retry count for this step
            status: "in_progress", "instruction_completed", "instruction_failed"
        """
        checkpoint = {
            "worker_id": self.worker_id,
            "json_id": json_id,
            "instruction_id": instruction_id,
            "instruction_index": instruction_index,
            "last_completed_step_index": step_index,
            "last_completed_step_id": step_id,
            "total_steps": total_steps,
            "retry_count": retry_count,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            with open(self.filepath, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            return True
        except Exception as e:
            print(f"[CHECKPOINT ERROR] Failed to save checkpoint: {e}")
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint from file.
        
        Returns:
            Checkpoint dict if exists, None if no checkpoint or file is invalid.
        """
        if not os.path.exists(self.filepath):
            return None

        try:
            with open(self.filepath, 'r') as f:
                checkpoint = json.load(f)

            # Validate it has required fields
            required = ["json_id", "instruction_id", "last_completed_step_index"]
            if not all(k in checkpoint for k in required):
                print(f"[CHECKPOINT WARNING] Invalid checkpoint file — missing fields. Ignoring.")
                return None

            print(f"[CHECKPOINT] Loaded: task={checkpoint['json_id']}, "
                  f"instruction={checkpoint['instruction_index']}, "
                  f"step={checkpoint['last_completed_step_index']}/{checkpoint['total_steps']}")
            return checkpoint

        except (json.JSONDecodeError, Exception) as e:
            print(f"[CHECKPOINT WARNING] Failed to read checkpoint: {e}")
            return None

    def clear(self) -> bool:
        """
        Delete the checkpoint file (task completed or fully failed).
        """
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
                print(f"[CHECKPOINT] Cleared checkpoint for {self.worker_id}")
            return True
        except Exception as e:
            print(f"[CHECKPOINT ERROR] Failed to clear checkpoint: {e}")
            return False

    def exists(self) -> bool:
        """Check if a checkpoint file exists."""
        return os.path.exists(self.filepath)
