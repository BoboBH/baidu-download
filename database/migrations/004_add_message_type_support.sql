-- ====================================================================
-- Migration: 004_add_message_type_support.sql
-- Date: 2026-08-20
-- Description: 添加多消息类型支持功能
--              支持 Baidu Pan、PDF 链接、DingTalk 文件三种消息类型
-- Prerequisites: 003_add_retry_count.sql
-- Order: 5
-- ====================================================================

USE test;

-- ====================================================================
-- 变更: 添加消息类型支持字段
-- ====================================================================

-- Phase 1: 添加 message_type 字段，默认值为 'baidupan'
ALTER TABLE message_process_log
ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT '消息类型：baidupan/pdf_link/dingtalk_pdf/dingtalk_zip'
AFTER source;

-- Phase 2: 添加 raw_message 字段用于存储原始消息 JSON
ALTER TABLE message_process_log
ADD COLUMN raw_message JSON COMMENT '原始消息内容（JSON格式）'
AFTER message_type;

-- Phase 3: 添加 file_info 字段用于存储文件元数据
ALTER TABLE message_process_log
ADD COLUMN file_info JSON COMMENT '文件元数据信息（JSON格式）'
AFTER raw_message;

-- Phase 4: 创建索引以支持高效的消息类型查询
CREATE INDEX idx_message_type ON message_process_log(message_type);
CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type);

-- Phase 5: 添加消息类型约束
ALTER TABLE message_process_log
ADD CONSTRAINT chk_message_type
CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'));

-- Phase 6: 更新现有记录，设置 message_type 为 'baidupan'
UPDATE message_process_log
SET message_type = 'baidupan'
WHERE message_type IS NULL OR message_type = '';

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
    AND COLUMN_NAME IN ('message_type', 'raw_message', 'file_info')
ORDER BY COLUMN_NAME;

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
    AND INDEX_NAME IN ('idx_message_type', 'idx_process_status_type')
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- 验证约束创建成功
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
WHERE
    CONSTRAINT_SCHEMA = 'baidu_download'
    AND CONSTRAINT_NAME = 'chk_message_type';

-- 检查现有数据兼容性（所有现有记录应该有 message_type = 'baidupan'）
SELECT
    message_type,
    process_status,
    COUNT(*) as count
FROM message_process_log
GROUP BY message_type, process_status
ORDER BY message_type, process_status;

-- 预期结果:
-- message_type 字段应该存在，类型为 VARCHAR(20)，默认值为 'baidupan'
-- raw_message 字段应该存在，类型为 JSON
-- file_info 字段应该存在，类型为 JSON
-- idx_message_type 和 idx_process_status_type 索引应该存在
-- chk_message_type 约束应该存在
-- 所有现有记录的 message_type 应该为 'baidupan'

-- ====================================================================
-- 功能验证查询（用于后续功能测试）
-- ====================================================================

-- 按消息类型统计消息数量
-- SELECT message_type, process_status, COUNT(*) as count
-- FROM message_process_log
-- GROUP BY message_type, process_status
-- ORDER BY message_type, process_status;

-- 查询特定类型的消息
-- SELECT message_hash, message_type, process_status, created_at
-- FROM message_process_log
-- WHERE message_type = 'pdf_link'
--   AND process_status = 'pending'
-- ORDER BY created_at ASC;
