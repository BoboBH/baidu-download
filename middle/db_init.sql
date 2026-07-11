-- 百度网盘PDF文件自动传输系统数据库初始化脚本
-- 使用方法：mysql -u root -p < db_init.sql

-- 创建数据库
CREATE DATABASE IF NOT EXISTS baidu_download
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE baidu_download;

-- 创建文件传输记录表
CREATE TABLE IF NOT EXISTS file_transfer_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_link VARCHAR(500) NOT NULL COMMENT '分享链接',
    extraction_code VARCHAR(20) NOT NULL COMMENT '提取码',
    folder_name VARCHAR(255) NOT NULL COMMENT '目录名称',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    transfer_status ENUM('pending', 'downloading', 'uploading', 'success', 'failed', 'skipped')
        DEFAULT 'pending' COMMENT '传输状态',
    error_message TEXT COMMENT '错误信息',
    start_time DATETIME COMMENT '开始时间',
    download_time DATETIME COMMENT '下载完成时间',
    upload_time DATETIME COMMENT '上传完成时间',
    file_size BIGINT COMMENT '文件大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    INDEX idx_share_link (share_link(255)),
    INDEX idx_folder_name (folder_name),
    INDEX idx_status (transfer_status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='文件传输记录表';

-- 创建执行摘要表
CREATE TABLE IF NOT EXISTS execution_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_link VARCHAR(500) NOT NULL,
    folder_name VARCHAR(255) NOT NULL,
    total_files INT DEFAULT 0 COMMENT '总文件数',
    success_count INT DEFAULT 0 COMMENT '成功数量',
    failed_count INT DEFAULT 0 COMMENT '失败数量',
    skipped_count INT DEFAULT 0 COMMENT '跳过数量',
    start_time DATETIME COMMENT '执行开始时间',
    end_time DATETIME COMMENT '执行结束时间',
    total_size BIGINT COMMENT '总文件大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='执行摘要表';

-- 显示创建的表
SHOW TABLES;
