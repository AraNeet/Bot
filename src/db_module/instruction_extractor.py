#!/usr/bin/env python3
"""
Instruction Extractor Module

Parses a stored JSON task payload and extracts individual instructions
from each alert's instruction_set. Creates instruction records in Supabase.

JSON Structure (Cadent format):
    payload.alerts[] → each alert has:
        alert_id, advertiser, order_id, product
        instruction_set[] → each instruction has:
            instruction_id, flight_start_date, flight_end_date,
            action (E=edit, D=duplicate),
            copy_instructions[] → individual copy entries

This module flattens the hierarchy into a sequential list of instructions
that the worker will execute in order on its Citrix session.

Usage:
    from src.db_module.instruction_extractor import extract_and_store_instructions

    count = extract_and_store_instructions("016311ba-4237-43bf-bdce-dd33a9394bdc")
    print(f"Extracted {count} instructions")
"""

from typing import Dict, Any, List, Tuple, Optional
from src.db_module.db_client import get_db


# ============================================================================
# ACTION TYPE MAPPING
# ============================================================================

ACTION_TYPE_MAP = {
    "E": "edit_copy",
    "D": "duplicate_copy",
    # Add more as needed:
    # "N": "new_copy",
    # "C": "cancel_copy",
}


def _map_action_type(action_code: str) -> str:
    """
    Map the action code from JSON to a workflow type.
    
    Args:
        action_code: Single letter code from JSON (e.g., "E", "D")
        
    Returns:
        Workflow type string (e.g., "edit_copy", "duplicate_copy")
    """
    action_upper = action_code.strip().upper() if action_code else ""
    mapped = ACTION_TYPE_MAP.get(action_upper, f"unknown_{action_upper}")
    
    if mapped.startswith("unknown_"):
        print(f"[EXTRACTOR WARNING] Unknown action code: '{action_code}' — mapped to '{mapped}'")
    
    return mapped


# ============================================================================
# EXTRACTION LOGIC
# ============================================================================

def _extract_instructions_from_payload(raw_json: dict) -> List[Dict[str, Any]]:
    """
    Parse the JSON payload and extract a flat list of instruction records.
    
    Each instruction record contains:
        - alert_id: which alert this belongs to
        - instruction_index: global sequential index (1-based)
        - action_type: mapped workflow type (edit_copy, duplicate_copy, etc.)
        - instruction_data: full context needed for execution (alert info + instruction details)
    
    Args:
        raw_json: The full JSON payload stored in the tasks table
        
    Returns:
        List of instruction dicts ready for DB insertion
    """
    alerts = raw_json.get("alerts", [])
    
    if not alerts:
        print("[EXTRACTOR WARNING] No alerts found in JSON payload")
        return []
    
    # Shared context from the top-level JSON (needed by the worker for search/navigation)
    shared_context = {
        "file_name": raw_json.get("file_name", ""),
        "revision_number": raw_json.get("revision_number", ""),
        "sales_id": raw_json.get("sales_id", ""),
        "agency": raw_json.get("agency", ""),
        "document_date": raw_json.get("document_date", ""),
    }
    
    instructions = []
    global_index = 0  # Sequential index across all alerts
    
    for alert in alerts:
        alert_id = alert.get("alert_id", 0)
        
        # Alert-level context (needed for searching the right order in Citrix)
        alert_context = {
            "advertiser": alert.get("advertiser", ""),
            "order_id": alert.get("order_id", ""),
            "product": alert.get("product", ""),
            "description": alert.get("description_of_traffic_alert", ""),
            "other_instructions": alert.get("other_instructions", ""),
        }
        
        instruction_set = alert.get("instruction_set", [])
        
        if not instruction_set:
            print(f"[EXTRACTOR WARNING] Alert {alert_id} has no instruction_set")
            continue
        
        for inst in instruction_set:
            global_index += 1
            
            action_code = inst.get("action", "")
            action_type = _map_action_type(action_code)
            
            # Build the full instruction data that the worker needs
            instruction_data = {
                # Shared context
                **shared_context,
                
                # Alert context
                "alert_id": alert_id,
                **alert_context,
                
                # Instruction-specific data
                "local_instruction_id": inst.get("instruction_id"),
                "action_code": action_code,
                "flight_start_date": inst.get("flight_start_date", ""),
                "flight_end_date": inst.get("flight_end_date", ""),
                "networks_to_run": inst.get("networks_to_run", ""),
                "copy_instructions": inst.get("copy_instructions", []),
            }
            
            instructions.append({
                "alert_id": alert_id,
                "instruction_index": global_index,
                "action_type": action_type,
                "instruction_data": instruction_data,
            })
            
            # Log what we extracted
            copy_count = len(inst.get("copy_instructions", []))
            print(
                f"[EXTRACTOR] Instruction #{global_index}: "
                f"alert={alert_id}, action={action_type}, "
                f"dates={inst.get('flight_start_date', '?')} to {inst.get('flight_end_date', '?')}, "
                f"copies={copy_count}"
            )
    
    return instructions


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def extract_and_store_instructions(json_id: str) -> Tuple[bool, int]:
    """
    Extract instructions from a stored task and save them to the instructions table.
    
    This is called after a task is created via POST /tasks.
    It reads the raw_json from the tasks table, parses it, creates
    instruction records, updates the task's instruction_count, and
    sets the task status to 'queued' (ready for workers).
    
    Args:
        json_id: The task's json_id (UUID string)
        
    Returns:
        Tuple of (success: bool, instruction_count: int)
    """
    db = get_db()
    
    print(f"\n[EXTRACTOR] === Extracting instructions for task {json_id} ===")
    
    # Step 1: Load the task and its raw JSON
    task = db.get_task(json_id)
    if task is None:
        print(f"[EXTRACTOR ERROR] Task not found: {json_id}")
        return False, 0
    
    if task["status"] not in ("unread",):
        print(f"[EXTRACTOR WARNING] Task {json_id} status is '{task['status']}', expected 'unread'. Proceeding anyway.")
    
    # Step 2: Get the raw JSON payload
    # get_task doesn't return raw_json (by design), so we need to fetch it directly
    from src.db_module.db_client import get_connection
    with get_connection() as conn:
        result = conn.execute(
            "SELECT raw_json FROM tasks WHERE json_id = %s",
            (json_id,)
        ).fetchone()
    
    if result is None or result["raw_json"] is None:
        print(f"[EXTRACTOR ERROR] No raw_json found for task {json_id}")
        return False, 0
    
    raw_json = result["raw_json"]
    
    # Step 3: Extract instructions from the payload
    instruction_records = _extract_instructions_from_payload(raw_json)
    
    if not instruction_records:
        print(f"[EXTRACTOR WARNING] No instructions extracted from task {json_id}")
        # Still mark as queued (empty task, worker will complete it immediately)
        db.update_task_status(json_id, "queued")
        db.update_task_instruction_count(json_id, 0)
        return True, 0
    
    # Step 4: Store instructions in the database (single transaction)
    try:
        created = db.create_instructions_batch(json_id, instruction_records)
        count = len(created)
        print(f"[EXTRACTOR] Stored {count} instructions in database")
    except Exception as e:
        print(f"[EXTRACTOR ERROR] Failed to store instructions: {e}")
        return False, 0
    
    # Step 5: Update task metadata
    db.update_task_instruction_count(json_id, count)
    db.update_task_status(json_id, "queued")
    
    print(f"[EXTRACTOR] Task {json_id} → status='queued', instruction_count={count}")
    print(f"[EXTRACTOR] === Extraction complete ===\n")
    
    return True, count
