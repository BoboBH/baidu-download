-- ====================================================================
-- Migration: 003_add_retry_count.sql
-- Date: 2026-08-19
-- Description: 添加 retry_count 字段支持消息重试次数限制功能
--              防止消息无限重试，提升系统效率
-- Prerequisites: 002_allow_null_folder_name.sql
-- Order: 4
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更: 添加 retry_count 字段和索引
-- ====================================================================

-- Phase 1: 添加 retry_count 字段，默认值为 0
ALTER TABLE message_process_log
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数'
AFTER error_message;

-- Phase 2: 创建索引以支持高效的 retry 过滤查询
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

-- 验证字段添加成功
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'retry_count';

-- 验证索引创建成功
SELECT
    INDEX_NAME,
    COLUMN_NAME,
    SEQ_IN_INDEX,
    INDEX_TYPE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND INDEX_NAME = 'idx_retry_count'
ORDER BY SEQ_IN_INDEX;

-- 检查现有数据兼容性（所有现有记录应该有 retry_count = 0）
SELECT
    retry_count,
    process_status,
    COUNT(*) as count
FROM message_process_log
GROUP BY retry_count, process_status
ORDER BY retry_count, process_status;

-- 预期结果:
-- retry_count 字段应该存在，类型为 INT，默认值为 0
-- 所有现有记录的 retry_count 应该为 0
-- idx_retry_count 索引应该存在于 retry_count 字段上

-- ====================================================================
-- 功能验证查询（用于后续功能测试）
-- ====================================================================

-- 模拟查询可重试的消息（假设 MESSAGE_MAX_RETRIES = 10）
-- SELECT message_hash, retry_count, process_status
-- FROM message_process_log
-- WHERE process_status = 'critical_error'
--   AND retry_count < 10
--   AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
-- ORDER BY created_at ASC;