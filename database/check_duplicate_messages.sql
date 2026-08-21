-- ====================================================================
-- 消息重复检查完整脚本
-- ====================================================================

USE test;

-- 1. 首先修复 share_link 字段允许 NULL
ALTER TABLE message_process_log
MODIFY COLUMN share_link VARCHAR(500) NULL COMMENT '分享链接（百度网盘/PDF链接），钉钉文件为NULL';

-- 2. 添加 message_type 字段（如果还没有）
ALTER TABLE message_process_log
ADD COLUMN IF NOT EXISTS message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT '消息类型：baidupan/pdf_link/dingtalk_pdf/dingtalk_zip'
AFTER source;

-- ====================================================================
-- 消息重复检查机制说明
-- ====================================================================

-- 系统使用 message_hash 字段来检查消息重复
-- message_hash 计算公式：MD5(message_type + ":" + unique_identifier)

-- 不同消息类型的 unique_identifier：
-- 1. 百度网盘: share_link (去除pwd参数)
-- 2. PDF链接: pdf_url
-- 3. 钉钉PDF: file_id:space_id
-- 4. 钉钉ZIP: file_id:space_id

-- ====================================================================
-- 检查重复消息的SQL查询
-- ====================================================================

-- 查看所有消息的 message_hash 和类型
SELECT
    id,
    message_hash,
    message_type,
    process_status,
    created_at,
    LEFT(original_message, 50) as message_preview
FROM message_process_log
ORDER BY created_at DESC
LIMIT 20;

-- 检查是否有重复的 message_hash
SELECT
    message_hash,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY created_at) as record_ids,
    GROUP_CONCAT(message_type) as message_types,
    GROUP_CONCAT(process_status) as statuses
FROM message_process_log
GROUP BY message_hash
HAVING COUNT(*) > 1;

-- 查看特定类型的消息分布
SELECT
    message_type,
    process_status,
    COUNT(*) as count
FROM message_process_log
GROUP BY message_type, process_status
ORDER BY message_type, process_status;

-- 手动检查钉钉PDF消息的重复情况
SELECT
    id,
    message_hash,
    message_type,
    process_status,
    created_at,
    original_message
FROM message_process_log
WHERE message_type = 'dingtalk_pdf'
ORDER BY created_at DESC
LIMIT 10;

-- ====================================================================
-- 清理重复消息（谨慎使用！）
-- ====================================================================

-- 如果需要清理重复消息，保留最早的记录
-- DELETE t1 FROM message_process_log t1
-- INNER JOIN message_process_log t2
-- WHERE t1.id > t2.id
-- AND t1.message_hash = t2.message_hash;

SELECT 'Duplicate message check completed!' as status;