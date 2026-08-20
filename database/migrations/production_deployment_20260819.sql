-- ====================================================================
-- 生产环境Schema变更部署脚本
-- Date: 2026-08-19
-- Description: 最近两天的数据库schema变更合并脚本
--              包含消息来源字段、文件夹名可空、重试计数功能
-- Database: baidu_download
-- ====================================================================
-- 使用说明：
-- 1. 执行前请确保已备份数据库
-- 2. 执行：mysql -u root -p baidu_download < production_deployment_20260819.sql
-- 3. 执行后请验证应用程序功能正常
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更 1: 添加 source 字段支持钉钉和飞书消息来源
-- ====================================================================

-- 添加 source 字段（如果不存在）
ALTER TABLE message_process_log
ADD COLUMN source ENUM('feishu', 'dingtalk')
DEFAULT 'feishu'
COMMENT '消息来源（飞书/钉钉）'
AFTER extraction_code;

-- 创建索引以提高查询性能
CREATE INDEX idx_source ON message_process_log(source);

-- ====================================================================
-- 变更 2: 允许 folder_name 字段为 NULL
-- ====================================================================

-- 修改字段为允许 NULL，适配新的简化消息解析逻辑
ALTER TABLE message_process_log
MODIFY COLUMN folder_name VARCHAR(255) NULL COMMENT '提取的目录名（可为NULL，由BaiduPCS-Go获取）';

-- ====================================================================
-- 变更 3: 添加 retry_count 字段支持消息重试次数限制
-- ====================================================================

-- 添加 retry_count 字段，默认值为 0
ALTER TABLE message_process_log
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数'
AFTER error_message;

-- 创建索引以支持高效的 retry 过滤查询
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- ====================================================================
-- 验证变更结果（可选，用于确认部署成功）
-- ====================================================================

-- 检查新增的字段
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_DEFAULT,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'baidu_download'
  AND TABLE_NAME = 'message_process_log'
  AND COLUMN_NAME IN ('source', 'folder_name', 'retry_count')
ORDER BY ORDINAL_POSITION;

-- 检查新增的索引
SELECT
    INDEX_NAME,
    COLUMN_NAME,
    INDEX_TYPE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'baidu_download'
  AND TABLE_NAME = 'message_process_log'
  AND INDEX_NAME IN ('idx_source', 'idx_retry_count')
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- ====================================================================
-- 验证重试逻辑（重要：确保retry_count功能正常）
-- ====================================================================

-- 测试查询：获取需要重试的消息（retry_count < 10）
-- 这个查询确保 failed 状态且 retry_count < 阈值的消息会被重新处理
SELECT
    message_hash,
    process_status,
    retry_count,
    created_at,
    error_message
FROM message_process_log
WHERE process_status = 'failed'
  AND retry_count < 10
  AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY created_at ASC;

-- 测试查询：确保超过重试阈值的消息不会被重新处理
SELECT
    '⚠️ 以下消息超过重试阈值，不会被重新处理' as info,
    message_hash,
    process_status,
    retry_count,
    created_at
FROM message_process_log
WHERE process_status = 'failed'
  AND retry_count >= 10
ORDER BY retry_count DESC, created_at DESC;

-- 测试查询：确保 critical_error 状态的消息不会被重新处理
SELECT
    'ℹ️ 以下消息为部分错误，不需要重试' as info,
    message_hash,
    process_status,
    retry_count,
    created_at
FROM message_process_log
WHERE process_status = 'critical_error'
ORDER BY created_at DESC;

-- ====================================================================
-- 部署完成
-- ====================================================================
-- 预期结果：
-- 1. source 字段存在，类型为 ENUM('feishu', 'dingtalk')，默认 'feishu'
-- 2. folder_name 字段允许 NULL
-- 3. retry_count 字段存在，类型为 INT，默认 0
-- 4. idx_source 和 idx_retry_count 索引已创建
-- 5. 代码逻辑修复：
--    - 'failed' 状态消息会被重新处理（当 retry_count < 阈值）
--    - 'critical_error' 状态消息不会被重新处理
--    - retry_count 在 failed/critical_error 时自动递增
--    - retry_count 在 success 时重置为 0
-- ====================================================================