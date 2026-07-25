-- 钉钉消息接收功能数据库迁移脚本
-- 添加 source 字段到 message_process_log 表

USE test;

-- 检查字段是否已存在
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM
    INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'test'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'source';

-- 如果字段不存在，则添加
-- 注意：如果上面的查询返回了结果，说明字段已存在，不要再执行下面的ALTER TABLE

ALTER TABLE message_process_log
ADD COLUMN source ENUM('feishu', 'dingtalk')
DEFAULT 'feishu'
COMMENT '消息来源（飞书/钉钉）';

-- 创建索引以提高查询性能
CREATE INDEX idx_source ON message_process_log(source);

-- 验证迁移结果
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM
    INFORMATION_SCHEMA.COLUMNS
WHERE
    TABLE_SCHEMA = 'test'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'source';

-- 检查现有数据兼容性（应该自动填充为 'feishu'）
SELECT
    COUNT(*) as total_messages,
    source,
    process_status
FROM message_process_log
GROUP BY source, process_status
ORDER BY source, process_status;