-- ====================================================================
-- Migration: 002_allow_null_folder_name.sql
-- Date: 2026-08-19
-- Description: 允许 message_process_log 表的 folder_name 字段为 NULL
--              适配新的简化消息解析逻辑，其中文件夹名称由 BaiduPCS-Go 获取
-- Prerequisites: 001_add_source_field.sql
-- Order: 3
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 变更: 修改 folder_name 字段允许 NULL
-- ====================================================================

-- 检查当前字段状态
SELECT
    COLUMN_NAME,
    IS_NULLABLE,
    COLUMN_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'folder_name';

-- 修改字段为允许 NULL
ALTER TABLE message_process_log
MODIFY COLUMN folder_name VARCHAR(255) NULL COMMENT '提取的目录名（可为NULL，由BaiduPCS-Go获取）';

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

-- 验证字段修改成功
SELECT
    COLUMN_NAME,
    IS_NULLABLE,
    COLUMN_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'baidu_download'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'folder_name';

-- 检查现有数据（如果有 NULL 值是正常的）
SELECT
    folder_name,
    process_status,
    COUNT(*) as count
FROM message_process_log
GROUP BY folder_name, process_status
ORDER BY process_status, folder_name;

-- 预期结果:
-- folder_name 字段的 IS_NULLABLE 应该为 'YES'