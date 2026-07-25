-- ================================================================================
-- 数据库表结构检查脚本
-- ================================================================================
-- 用途: 检查baidu_download数据库中的所有表和结构
-- 执行方法: mysql -u root -p baidu_download < check_tables.sql
-- ================================================================================

USE baidu_download;

SELECT '====================================================================' AS '';
SELECT '数据库表结构检查报告' AS '';
SELECT '====================================================================' AS '';

-- 显示所有表
SELECT
    '1. 当前所有表' AS step,
    TABLE_NAME AS '表名',
    TABLE_COMMENT AS '说明',
    CREATE_TIME AS '创建时间',
    TABLE_ROWS AS '行数'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'baidu_download'
ORDER BY TABLE_NAME;

-- 显示表结构详情
SELECT '--------------------------------------------------------------------' AS '';
SELECT '2. 表结构详情' AS '';
SELECT '--------------------------------------------------------------------' AS '';

-- file_transfer_log 表结构
SELECT 'file_transfer_log 表结构:' AS '';
DESCRIBE file_transfer_log;

-- execution_summary 表结构
SELECT 'execution_summary 表结构:' AS '';
DESCRIBE execution_summary;

-- message_process_log 表结构 (如果存在)
SELECT 'message_process_log 表结构:' AS '';
DESCRIBE message_process_log;

-- 显示索引信息
SELECT '--------------------------------------------------------------------' AS '';
SELECT '3. 索引信息' AS '';
SELECT '--------------------------------------------------------------------' AS '';

SHOW INDEX FROM file_transfer_log;
SHOW INDEX FROM execution_summary;
SHOW INDEX FROM message_process_log;

SELECT '====================================================================' AS '';
SELECT '检查完成!' AS '';
SELECT '====================================================================' AS '';