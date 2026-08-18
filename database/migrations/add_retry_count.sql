-- Migration: Add retry_count column to message_process_log table
-- Date: 2026-08-18
-- Description: Add retry tracking for failed message processing attempts

-- Phase 1: Add retry_count column with default value
ALTER TABLE message_process_log
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数'
AFTER error_message;

-- Phase 2: Create index for efficient retry filtering
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- Verification query (run separately to check migration success)
-- Expected: 0 (all existing records should have retry_count = 0)
-- SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;
