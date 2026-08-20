-- ====================================================================
-- Migration: 001_add_source_field.sql
-- Date: 2026-08-19
-- Description: 添加 source 字段支持钉钉和飞书消息来源
-- Prerequisites: 000_init_schema.sql
-- Order: 2
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更: 添加 source 字段
-- ====================================================================

-- 检查字段是否已存在
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM
    INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'source';

-- 如果字段不存在，则添加（仅在检查查询返回空结果时执行）
ALTER TABLE message_process_log
ADD COLUMN source ENUM('feishu', 'dingtalk')
DEFAULT 'feishu'
COMMENT '消息来源（飞书/钉钉）'
AFTER extraction_code;

-- 创建索引以提高查询性能
CREATE INDEX idx_source ON message_process_log(source);

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
    AND COLUMN_NAME = 'source';

-- 检查现有数据兼容性（现有记录应自动填充为 'feishu'）
SELECT
    COUNT(*) as total_messages,
    source,
    process_status
FROM message_process_log
GROUP BY source, process_status
ORDER BY source, process_status;

-- 预期结果:
-- source 字段应该存在，类型为 ENUM('feishu', 'dingtalk')
-- 所有现有记录的 source 应该为 'feishu' (默认值)