-- ====================================================================
-- Migration: 011_add_wxchat_article_message_type.sql
-- Date: 2026-08-21
-- Description: 添加wxchat-article消息类型支持
--              支持微信公众号文章链接的处理
-- Prerequisites: 004_add_message_type_support.sql
-- Order: 11
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更: 更新消息类型约束以支持 wxchat-article
-- ====================================================================

-- 删除旧的约束（如果存在）
ALTER TABLE message_process_log
DROP CONSTRAINT IF EXISTS chk_message_type;

-- 创建新的约束，包含 wxchat-article 类型
ALTER TABLE message_process_log
ADD CONSTRAINT chk_message_type
CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip', 'wxchat-article'));

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

-- 验证约束更新成功
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
WHERE
    CONSTRAINT_SCHEMA = 'baidu_download'
    AND CONSTRAINT_NAME = 'chk_message_type';

-- 验证字段信息
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_COMMENT,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'message_type';

-- 测试插入 wxchat-article 类型消息
-- INSERT INTO message_process_log (
--     message_hash,
--     original_message,
--     share_link,
--     folder_name,
--     extraction_code,
--     source,
--     message_type,
--     process_status
-- ) VALUES (
--     'test_wxchat_article_hash',
--     '{"wxchat_article_url": "https://mp.weixin.qq.com/s/test123", "wxchat_article_id": "test123"}',
--     'https://mp.weixin.qq.com/s/test123',
--     NULL,
--     NULL,
--     'feishu',
--     'wxchat-article',
--     'pending'
-- );

-- 验证测试数据插入成功
-- SELECT message_hash, message_type, process_status
-- FROM message_process_log
-- WHERE message_type = 'wxchat-article';

-- 清理测试数据（如果测试成功）
-- DELETE FROM message_process_log WHERE message_hash = 'test_wxchat_article_hash';

-- 预期结果:
-- chk_message_type 约束应该包含 'wxchat-article'
-- message_type 字段支持 wxchat-article 类型
-- 可以成功插入和查询 wxchat-article 类型的记录
-- ====================================================================
