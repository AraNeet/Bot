#!/usr/bin/env python3
"""
Real-time workflow watcher (integration test).

Runs the workflow pipeline end-to-end in a subprocess, streams its output in real time,
and fails if the workflow ends in an overall failure state.

This script intentionally does NOT modify any step handler code.
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import time
from typing import List, Optional


def _drain_queue_and_print(q: "queue.Queue[Optional[str]]") -> List[str]:
    lines: List[str] = []
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if item is None:
            continue
        line = item.rstrip("\n")
        print(line)
        lines.append(line)
    return lines


def run_and_watch(
    *,
    python_executable: str,
    repo_root: str,
    objectives_file_path: str,
    timeout_seconds: int,
    log_file_path: str,
) -> int:
    # Readability-only constants for output detection.
    success_markers = [
        "Overall Status: SUCCESS",
        "WORKFLOW ENGINE - WORKFLOW COMPLETE",
    ]
    failure_markers = [
        "Overall Status: FAILED",
        "WORKFLOW ENGINE - WORKFLOW FAILED",
        "Workflow Error:",
    ]

    # Important: use -u for unbuffered output so we can stream logs immediately.
    # We run the pipeline directly (not main.py) so we can pass an arbitrary objectives file path.
    pipeline_code = r"""
import os
import sys
import time
import subprocess

from src.startup_module.system_initializer import initialize_system
from src.parser_module.objectives_processer import process_objectives_file
from src.workflow_module.engine.process_input import process_input_workflow

objectives_file_path = sys.argv[1]

res = subprocess.run(
    [sys.executable, "generate_objectives_config.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=True,
)
if res.stdout:
    print(res.stdout)

success = initialize_system()
if not success:
    print("Failed startup sequence.")
    sys.exit(1)

success, results = process_objectives_file(objectives_file_path)
if not success:
    print(f"Parser Error: {results}")
    sys.exit(1)

print(f"Parser Results: {results}")
time.sleep(1)

success, results = process_input_workflow(results)
if not success:
    print(f"Workflow Error: {results}")
    sys.exit(1)
"""

    env = os.environ.copy()
    # Force UTF-8 output from the subprocess so Windows cp1252 can't crash on ✓/✗.
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [
        python_executable,
        "-u",
        "-X",
        "utf8",
        "-c",
        pipeline_code,
        objectives_file_path,
    ]

    q: "queue.Queue[Optional[str]]" = queue.Queue()
    proc_holder = {"proc": None}  # filled by reader thread

    def reader_thread() -> None:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=repo_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            proc_holder["proc"] = proc
            assert proc.stdout is not None

            for line in iter(proc.stdout.readline, ""):
                q.put(line)

            proc.wait()
            q.put(None)
            # Store exit code on the thread function.
            reader_thread.exit_code = proc.returncode  # type: ignore[attr-defined]
        except Exception as e:
            q.put(f"[WATCHER] Reader thread error: {e}\n")
            reader_thread.exit_code = 1  # type: ignore[attr-defined]
            q.put(None)

    reader_thread.exit_code = 1  # type: ignore[attr-defined]

    # Stream in-process: start reader thread first, then consume queue with timeout.
    t = threading.Thread(target=reader_thread, daemon=True)
    t.start()

    started = time.time()
    collected_lines: List[str] = []
    fatal_failure_seen = False

    # Open log file early so we keep everything even if the run is long.
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, "w", encoding="utf-8") as f:
        while True:
            # Timeout handling
            if time.time() - started > timeout_seconds:
                print(f"[WATCHER] Timeout exceeded ({timeout_seconds}s). Killing subprocess...")
                # The subprocess is owned by the reader thread, so we store the handle.
                if proc_holder["proc"] is not None:
                    try:
                        proc_holder["proc"].kill()
                    except Exception:
                        pass
                    try:
                        proc_holder["proc"].wait(timeout=5)
                    except Exception:
                        pass
                break

            try:
                item = q.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                # Subprocess output ended; drain remaining queued output and stop.
                collected_lines.extend(_drain_queue_and_print(q))
                break

            line = item.rstrip("\n")
            collected_lines.append(line)
            f.write(line + "\n")
            print(line)

            if any(m in line for m in failure_markers):
                fatal_failure_seen = True

    exit_code = int(getattr(reader_thread, "exit_code", 1))

    # Final log-only analysis
    output_text = "\n".join(collected_lines)
    success_seen = any(m in output_text for m in success_markers)
    failure_seen = any(m in output_text for m in failure_markers)

    if exit_code == 0 and success_seen and not failure_seen and not fatal_failure_seen:
        print("[WATCHER] PASS: workflow finished successfully.")
        return 0

    print("[WATCHER] FAIL: workflow did not finish in a successful state.")
    print(f"[WATCHER] exit_code={exit_code}, success_seen={success_seen}, failure_seen={failure_seen}, fatal_failure_seen={fatal_failure_seen}")
    print(f"[WATCHER] log_file={log_file_path}")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--objectives-file",
        default="APR2125_DISH CUA_TrafficAlerts_plan.json",
        help="Objectives plan JSON file (relative to repo root).",
    )
    parser.add_argument(
        "--timeout-minutes",
        type=int,
        default=180,
        help="Hard timeout for the watcher run.",
    )
    parser.add_argument(
        "--log-file",
        default="watch_workflow_real_time.log",
        help="Log file path (relative to repo root).",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    python_executable = sys.executable

    objectives_file_path = os.path.abspath(os.path.join(repo_root, args.objectives_file))
    log_file_path = os.path.abspath(os.path.join(repo_root, args.log_file))

    if not os.path.exists(objectives_file_path):
        print(f"[WATCHER] Objectives file not found: {objectives_file_path}")
        sys.exit(1)

    timeout_seconds = int(args.timeout_minutes) * 60
    exit_code = run_and_watch(
        python_executable=python_executable,
        repo_root=repo_root,
        objectives_file_path=objectives_file_path,
        timeout_seconds=timeout_seconds,
        log_file_path=log_file_path,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

