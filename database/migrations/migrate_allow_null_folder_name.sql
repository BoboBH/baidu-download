-- 允许 message_process_log 表的 folder_name 字段为 NULL
-- 适配新的简化消息解析逻辑，其中文件夹名称由BaiduPCS-Go获取

ALTER TABLE message_process_log
MODIFY COLUMN folder_name VARCHAR(255) NULL COMMENT '提取的目录名（可为NULL，由BaiduPCS-Go获取）';

-- 验证修改
SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'message_process_log'
AND COLUMN_NAME = 'folder_name';