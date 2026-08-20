-- ====================================================================
-- Rollback: 003_rollback_add_retry_count.sql
-- Date: 2026-08-19
-- Description: 回滚 retry_count 字段变更
-- Warning: 此操作将删除 retry_count 字段和相关索引
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 回滚操作
-- ====================================================================

-- Warning: 首先检查 retry_count 是否存在
SELECT
    COLUMN_NAME,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'retry_count';

-- 如果上述查询返回结果，说明字段存在，可以安全删除
-- 如果没有返回结果，说明字段已被删除或不存在

-- Step 1: 删除 retry_count 索引
DROP INDEX IF EXISTS idx_retry_count ON message_process_log;

-- Step 2: 删除 retry_count 字段
ALTER TABLE message_process_log
DROP COLUMN IF EXISTS retry_count;

-- ====================================================================
-- 验证回滚结果
-- ====================================================================

-- 验证字段已删除（应该返回空结果）
SELECT
    COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'retry_count';

-- 验证索引已删除（应该返回空结果）
SELECT
    INDEX_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND INDEX_NAME = 'idx_retry_count';

-- 预期结果:
-- retry_count 字段应该不存在
-- idx_retry_count 索引应该不存在