-- ====================================================================
-- Migration: 013_add_sender_fields.sql
-- Date: 2026-08-21
-- Description: 添加发送者信息字段到message_process_log表
--              支持在通知中显示发送者信息
-- Prerequisites: 011_add_wxchat_article_message_type.sql
-- Order: 13
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更: 添加发送者信息字段
-- ====================================================================

-- 添加发送者ID字段
ALTER TABLE message_process_log
ADD COLUMN sender_id VARCHAR(100) COMMENT '发送者ID' AFTER raw_message;

-- 添加发送者昵称字段
ALTER TABLE message_process_log
ADD COLUMN sender_nick VARCHAR(200) COMMENT '发送者昵称' AFTER sender_id;

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

-- 验证字段添加成功
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME IN ('sender_id', 'sender_nick');

-- 测试插入带发送者信息的记录
-- INSERT INTO message_process_log (
--     message_hash,
--     original_message,
--     share_link,
--     folder_name,
--     source,
--     message_type,
--     sender_id,
--     sender_nick,
--     process_status
-- ) VALUES (
--     'test_sender_info_hash',
--     'Test message with sender info',
--     'https://test.com/link',
--     'test_folder',
--     'dingtalk',
--     'pdf_link',
--     'user123',
--     '测试用户',
--     'pending'
-- );

-- 验证测试数据插入成功
-- SELECT message_hash, sender_id, sender_nick, message_type
-- FROM message_process_log
-- WHERE message_hash = 'test_sender_info_hash';

-- 清理测试数据（如果测试成功）
-- DELETE FROM message_process_log WHERE message_hash = 'test_sender_info_hash';

-- 预期结果:
-- sender_id 和 sender_nick 字段应该成功添加
-- 可以成功插入和查询带发送者信息的记录
-- ====================================================================