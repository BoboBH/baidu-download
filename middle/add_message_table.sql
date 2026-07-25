-- ================================================================================
-- 飞书消息处理表增量DDL脚本
-- ================================================================================
-- 用途: 为现有baidu_download数据库添加飞书自动模式所需的消息处理表
-- 执行条件: 适用于已有file_transfer_log和execution_summary表的数据库
-- 执行方法: mysql -u root -p baidu_download < add_message_table.sql
-- 安全性: 只添加新表，不修改现有表结构
-- ================================================================================

USE baidu_download;

-- 创建飞书消息处理记录表（自动模式专用）
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(32) NOT NULL UNIQUE COMMENT '消息内容MD5哈希值',
    folder_name VARCHAR(255) NOT NULL COMMENT '解析出的文件夹名(YYMMDD格式)',
    share_link VARCHAR(500) NOT NULL COMMENT '百度网盘分享链接',
    extraction_code VARCHAR(20) NOT NULL COMMENT '提取码',
    message_content TEXT COMMENT '原始飞书消息内容',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
        DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    processed_file_count INT DEFAULT 0 COMMENT '成功处理的文件数量',
    processing_time_ms INT COMMENT '处理耗时(毫秒)',
    feishu_message_time DATETIME COMMENT '飞书消息发送时间',
    start_time DATETIME COMMENT '开始处理时间',
    end_time DATETIME COMMENT '处理完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    INDEX idx_message_hash (message_hash),
    INDEX idx_folder_name (folder_name),
    INDEX idx_process_status (process_status),
    INDEX idx_created_at (created_at),
    INDEX idx_feishu_message_time (feishu_message_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='飞书消息处理记录表';

-- 验证表是否创建成功
SELECT
    CONCAT('表 message_process_log 创建成功! 表名: ', TABLE_NAME) AS status
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'baidu_download'
AND TABLE_NAME = 'message_process_log';

-- 显示新创建的表结构
DESCRIBE message_process_log;

-- 显示当前所有表
SELECT TABLE_NAME, TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'baidu_download'
ORDER BY TABLE_NAME;