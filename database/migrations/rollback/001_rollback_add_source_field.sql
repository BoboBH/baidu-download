-- ====================================================================
-- Rollback: 001_rollback_add_source_field.sql
-- Date: 2026-08-19
-- Description: 回滚 source 字段变更
-- Warning: 此操作将删除 source 字段和相关索引
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 回滚前检查
-- ====================================================================

-- 检查 source 字段数据分布
SELECT
    source,
    process_status,
    COUNT(*) as count
FROM message_process_log
GROUP BY source, process_status
ORDER BY source, process_status;

-- 检查是否有钉钉消息
SELECT COUNT(*) as dingtalk_message_count
FROM message_process_log
WHERE source = 'dingtalk';

-- ====================================================================
-- 回滚操作
-- ====================================================================

-- Step 1: 删除 source 索引
DROP INDEX IF EXISTS idx_source ON message_process_log;

-- Step 2: 删除 source 字段
ALTER TABLE message_process_log
DROP COLUMN IF EXISTS source;

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
    AND COLUMN_NAME = 'source';

-- 验证索引已删除（应该返回空结果）
SELECT
    INDEX_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND INDEX_NAME = 'idx_source';

-- 预期结果:
-- source 字段应该不存在
-- idx_source 索引应该不存在