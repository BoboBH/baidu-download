-- ========================================================================
-- Production Rollback Script: Message Retry Limit Feature
-- ========================================================================
-- Feature Version: 1.0
-- Rollback Date: 2026-08-19
-- Risk Level: LOW (Removes features only)
-- Estimated Runtime: 1-2 minutes
-- Prerequisite: Database backup available
-- ========================================================================
-- IMPORTANT:
-- 1. This script REMOVES the retry limit feature from the database
-- 2. Application will revert to pre-retry-limit behavior
-- 3. Application code rollback also required
-- 4. All retry count data will be PERMANENTLY LOST
-- 5. Use ONLY if critical issues detected after migration
-- ========================================================================

-- Set execution parameters
SET @start_time = NOW();
SET @rollback_name = 'Message Retry Limit Feature Rollback';
SET @rollback_version = '1.0';

-- ========================================================================
-- PRE-ROLLBACK VALIDATION
-- ========================================================================
SELECT 'Starting pre-rollback validation...' AS status;

-- Validate 1: Check if feature is actually installed
SELECT COUNT(*) INTO @retry_count_exists
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';

IF @retry_count_exists = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ERROR: retry_limit feature not installed - nothing to rollback';
END IF;

SELECT '✓ Retry limit feature detected (ready for rollback)' AS validation_step;

-- Validate 2: Check application status (manual check required)
SELECT '⚠ WARNING: Ensure application is STOPPED before proceeding with rollback!' AS warning;

-- Count existing retry data before rollback (this will be lost)
SELECT
    COUNT(*) as total_messages_affected,
    SUM(CASE WHEN retry_count > 0 THEN 1 ELSE 0 END) as messages_with_retries,
    MAX(retry_count) as max_retry_count
FROM message_process_log;

SELECT '⚠ WARNING: All retry count data shown above will be PERMANENTLY LOST!' AS data_loss_warning;

-- ========================================================================
-- PHASE 1: REMOVE PERFORMANCE INDEX
-- ========================================================================
SELECT 'Phase 1: Removing performance index...' AS status;

-- Check if index exists
SELECT COUNT(*) INTO @index_exists
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_retry_count';

IF @index_exists > 0 THEN
    -- Drop index safely
    SET @sql = 'DROP INDEX idx_retry_count ON message_process_log';
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    SELECT '✓ Performance index idx_retry_count removed' AS phase_1_status;
ELSE
    SELECT '⚠ Index idx_retry_count not found (may have been manually removed)' AS phase_1_status;
END IF;

-- Verify index removal
SELECT COUNT(*) INTO @index_removed
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_retry_count';

IF @index_removed > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ERROR: Failed to remove idx_retry_count index';
END IF;

SELECT '✓ Index removal verified' AS verification_step;

-- ========================================================================
-- PHASE 2: REMOVE retry_count COLUMN
-- ========================================================================
SELECT 'Phase 2: Removing retry_count column...' AS status;

-- Drop column safely
SET @sql = 'ALTER TABLE message_process_log DROP COLUMN retry_count';
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT '✓ retry_count column removed' AS phase_2_status;

-- Verify column removal
SELECT COUNT(*) INTO @column_removed
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';

IF @column_removed > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ERROR: Failed to remove retry_count column';
END IF;

SELECT '✓ Column removal verified' AS verification_step;

-- ========================================================================
-- PHASE 3: VERIFY TABLE INTEGRITY
-- ========================================================================
SELECT 'Phase 3: Verifying table integrity after rollback...' AS status;

-- Check table is accessible and data intact
SELECT COUNT(*) as total_messages FROM message_process_log;

-- Verify expected columns still exist
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log'
ORDER BY ORDINAL_POSITION;

-- Verify critical functionality columns still present
SELECT COUNT(*) INTO @critical_columns
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log'
AND COLUMN_NAME IN ('id', 'message_hash', 'process_status', 'created_at', 'updated_at');

IF @critical_columns < 5 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ERROR: Critical columns missing after rollback';
END IF;

SELECT '✓ Table integrity verified' AS phase_3_status;

-- ========================================================================
-- POST-ROLLBACK VERIFICATION
-- ========================================================================
SELECT 'Starting post-rollback verification...' AS status;

-- Verify 1: Confirm retry_count is completely removed
SELECT COUNT(*) INTO @retry_count_after
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';

IF @retry_count_after > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ERROR: Rollback incomplete - retry_count still exists';
END IF;

SELECT '✓ Retry count feature completely removed' AS rollback_verification;

-- Verify 2: Confirm table functionality
SELECT 'Table structure after rollback:' AS info;
DESCRIBE message_process_log;

-- ========================================================================
-- ROLLBACK COMPLETION SUMMARY
-- ========================================================================
SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT
    '========================================================================' AS separator,
    'ROLLBACK COMPLETED SUCCESSFULLY' AS status,
    CONCAT('Rollback: ', @rollback_name, ' v', @rollback_version) AS rollback_info,
    CONCAT('Started: ', @start_time) AS start_time,
    CONCAT('Completed: ', @end_time) AS end_time,
    CONCAT('Duration: ', @duration, ' seconds') AS duration,
    '========================================================================' AS separator;

-- ========================================================================
-- POST-ROLLBACK ACTIONS REQUIRED
-- ========================================================================
SELECT
    'POST-ROLLBACK ACTIONS REQUIRED:' AS actions_header,
    '1. Remove MESSAGE_MAX_RETRIES from application configuration' AS action_1,
    '2. Revert application code to pre-retry-limit version' AS action_2,
    '3. Restart application with previous version' AS action_3,
    '4. Verify application functions normally without retry limits' AS action_4,
    '5. Monitor system behavior for 24 hours' AS action_5;

-- ========================================================================
-- RE-DEPLOYMENT INSTRUCTIONS (IF FIXING ISSUES)
-- ========================================================================
SELECT
    'IF RE-DEPLOYING AFTER FIXING ISSUES:' AS redeploy_header,
    '1. Resolve the issue that caused this rollback' AS step_1,
    '2. Test fix thoroughly in staging environment' AS step_2,
    '3. Re-run the migration script: migrate_retry_limit_production.sql' AS step_3,
    '4. Follow full deployment checklist procedures' AS step_4,
    '5. Monitor closely for recurrence of the issue' AS step_5;

-- ========================================================================
-- END OF ROLLBACK SCRIPT
-- ========================================================================
SELECT '✓ Rollback completed. Database is now in pre-retry-limit state.' AS final_status;
SELECT '⚠ Application code rollback also required!' AS application_warning;