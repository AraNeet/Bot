-- ============================================================================
-- Citrix XRD Automation Engine — Supabase Schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ============================================================================

-- ============================================================================
-- TABLE 1: tasks
-- Stores the incoming JSON payloads. One row per submitted JSON file.
-- Workers lock an entire task (JSON) and process all its instructions.
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    json_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_hash    VARCHAR(64) NOT NULL,               -- SHA-256 of raw JSON for dedup
    raw_json        JSONB NOT NULL,                      -- Full original JSON payload
    file_name       VARCHAR(512),                        -- e.g. "MAY6525_DISH NCC_TrafficAlerts.pdf"
    revision_number VARCHAR(100),                        -- e.g. "MAY6525"
    status          VARCHAR(20) NOT NULL DEFAULT 'unread',
        -- unread:    just received, waiting in queue
        -- queued:    instructions extracted, ready for workers
        -- assigned:  locked by a worker
        -- executing: worker is processing instructions
        -- completed: all instructions done
        -- failed:    one or more instructions failed
    assigned_worker_id  VARCHAR(100),                    -- which worker holds the lock
    lease_expires_at    TIMESTAMPTZ,                     -- heartbeat lease expiry
    instruction_count   INT DEFAULT 0,                   -- total instructions extracted
    source              VARCHAR(255),                    -- upstream system identifier
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,

    -- Dedup constraint: same payload_hash = same file
    CONSTRAINT uq_tasks_payload_hash UNIQUE (payload_hash)
);

-- Index for worker polling query (SKIP LOCKED needs this to be fast)
CREATE INDEX IF NOT EXISTS idx_tasks_status_created 
    ON tasks (status, created_at ASC) 
    WHERE status IN ('queued', 'unread');

-- Index for lease expiry checker
CREATE INDEX IF NOT EXISTS idx_tasks_lease_expiry 
    ON tasks (lease_expires_at) 
    WHERE status = 'assigned' AND lease_expires_at IS NOT NULL;


-- ============================================================================
-- TABLE 2: instructions
-- Each instruction is one unit of work within a task.
-- For Cadent: each alert's instruction_set entry becomes one instruction.
-- All instructions in a task execute in strict sequence on the same worker.
-- ============================================================================

CREATE TABLE IF NOT EXISTS instructions (
    instruction_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    json_id         UUID NOT NULL REFERENCES tasks(json_id) ON DELETE CASCADE,
    alert_id        INT,                                 -- alert number from JSON (1-based)
    instruction_index INT NOT NULL,                      -- order within the task (1-based)
    action_type     VARCHAR(50),                         -- E=edit, D=duplicate, etc.
    instruction_data JSONB NOT NULL,                     -- full instruction payload (copy_instructions, dates, etc.)
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending:    waiting for execution
        -- executing:  currently being processed
        -- completed:  all steps passed
        -- failed:     step failure after all retries + recovery
        -- skipped:    skipped due to prior instruction failure
    current_step    VARCHAR(100),                        -- step_id currently executing
    retry_count     INT NOT NULL DEFAULT 0,
    max_retries     INT NOT NULL DEFAULT 2,
    failure_reason  TEXT,                                -- structured failure description
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fetching instructions by task in order
CREATE INDEX IF NOT EXISTS idx_instructions_json_id_order 
    ON instructions (json_id, instruction_index ASC);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_instructions_status 
    ON instructions (status);


-- ============================================================================
-- TABLE 3: step_logs
-- Every precheck/action/postcheck execution for every step is logged here.
-- This is the audit trail — append-only, never updated.
-- ============================================================================

CREATE TABLE IF NOT EXISTS step_logs (
    log_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instruction_id      UUID NOT NULL REFERENCES instructions(instruction_id) ON DELETE CASCADE,
    json_id             UUID NOT NULL REFERENCES tasks(json_id) ON DELETE CASCADE,
    step_id             VARCHAR(100) NOT NULL,            -- e.g. "type_advertiser_name"
    worker_id           VARCHAR(100),
    attempt_number      INT NOT NULL DEFAULT 1,           -- which retry attempt
    phase               VARCHAR(20),                      -- precheck, action, postcheck, recovery
    
    -- Results for each phase
    precheck_result     JSONB,                            -- {success: bool, message: str}
    action_result       JSONB,                            -- {success: bool, message: str}
    postcheck_result    JSONB,                            -- {success: bool, message: str, data: {}}
    
    -- Diagnostics
    screenshot_path     VARCHAR(512),                     -- local path to failure screenshot
    ocr_output          JSONB,                            -- OCR text captured during this step
    cv_confidence       REAL,                             -- template match confidence score
    error_message       TEXT,                             -- failure reason if any phase failed
    
    -- Recovery info
    recovery_attempted  BOOLEAN DEFAULT FALSE,
    recovery_detail     JSONB,                            -- backtrack steps, validations, restorations
    
    -- Timing
    duration_ms         INT,                              -- total step execution time
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying logs by instruction (most common query)
CREATE INDEX IF NOT EXISTS idx_step_logs_instruction 
    ON step_logs (instruction_id, created_at ASC);

-- Index for querying logs by task
CREATE INDEX IF NOT EXISTS idx_step_logs_json_id 
    ON step_logs (json_id, created_at ASC);

-- Index for querying by worker (debugging)
CREATE INDEX IF NOT EXISTS idx_step_logs_worker 
    ON step_logs (worker_id, created_at DESC) 
    WHERE worker_id IS NOT NULL;


-- ============================================================================
-- AUTO-UPDATE updated_at TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to tasks
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
CREATE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply to instructions
DROP TRIGGER IF EXISTS update_instructions_updated_at ON instructions;
CREATE TRIGGER update_instructions_updated_at 
    BEFORE UPDATE ON instructions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- VERIFY
-- ============================================================================
SELECT 'Schema created successfully' AS result;
