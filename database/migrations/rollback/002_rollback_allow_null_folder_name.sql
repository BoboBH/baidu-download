-- ====================================================================
-- Rollback: 002_rollback_allow_null_folder_name.sql
-- Date: 2026-08-19
-- Description: 回滚 folder_name 字段的 NULL 允许设置
-- Warning: 此操作将要求 folder_name 必须为 NOT NULL
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 回滚前检查
-- ====================================================================

-- 检查是否有 NULL 值存在
SELECT COUNT(*) as null_folder_name_count
FROM message_process_log
WHERE folder_name IS NULL;

-- 如果上述查询返回 > 0，需要先处理 NULL 值
-- 可以选择：1. 删除这些记录 2. 更新为默认值 3. 取消回滚

-- ====================================================================
-- 回滚操作（仅在确认没有 NULL 值后执行）
-- ====================================================================

-- Step 1: 更新任何 NULL 值为空字符串（可选，根据业务需求调整）
-- UPDATE message_process_log
-- SET folder_name = ''
-- WHERE folder_name IS NULL;

-- Step 2: 修改字段为 NOT NULL
ALTER TABLE message_process_log
MODIFY COLUMN folder_name VARCHAR(255) NOT NULL COMMENT '提取的目录名';

-- ====================================================================
-- 验证回滚结果
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

-- 检查是否还有 NULL 值
SELECT COUNT(*) as null_folder_name_count
FROM message_process_log
WHERE folder_name IS NULL;

-- 预期结果:
-- folder_name 字段的 IS_NULLABLE 应该为 'NO'
-- null_folder_name_count 应该为 0