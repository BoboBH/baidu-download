-- ====================================================================
-- 修复现有数据：根据 share_link 和 folder_name 更新 message_type
-- ====================================================================

USE test;

-- 修复钉钉文件消息：根据 share_link 前缀识别
-- dingtalk:file_id:space_id:download_code 格式的是钉钉文件
UPDATE message_process_log
SET message_type = CASE
    -- 根据文件扩展名判断
    WHEN share_link LIKE 'dingtalk:%' AND folder_name LIKE '%.pdf' THEN 'dingtalk_pdf'
    WHEN share_link LIKE 'dingtalk:%' AND folder_name LIKE '%.zip' THEN 'dingtalk_zip'
    -- 根据share_link内容判断（如果是PDF URL）
    WHEN share_link LIKE 'https://%.pdf' OR share_link LIKE 'http://%.pdf' THEN 'pdf_link'
    -- 保持百度网盘类型
    ELSE 'baidupan'
END
WHERE message_type = 'baidupan' OR message_type IS NULL;

-- 验证修复结果
SELECT
    message_type,
    COUNT(*) as count,
    COUNT(DISTINCT source) as sources
FROM message_process_log
GROUP BY message_type
ORDER BY message_type;

-- 查看每种类型的示例
SELECT
    message_type,
    source,
    LEFT(share_link, 50) as share_link_preview,
    folder_name,
    LEFT(original_message, 30) as message_preview
FROM message_process_log
ORDER BY message_type, created_at DESC
LIMIT 20;

SELECT '✅ Message type values fixed!' as status;
