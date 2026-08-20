-- ====================================================================
-- Migration: 010_create_wechat_tables.sql
-- Date: 2026-08-19
-- Description: 创建微信公众号文章处理相关的表结构
--              用于微信公众号文章PDF转换和上传功能
-- Prerequisites: 003_add_retry_count.sql
-- Order: 5 (可选功能模块)
-- ====================================================================

USE baidu_download;

-- ====================================================================
-- 微信公众号账号表
-- ====================================================================
CREATE TABLE IF NOT EXISTS wx_account (
    account_id VARCHAR(100) PRIMARY KEY COMMENT '账号ID',
    account_name VARCHAR(255) NOT NULL COMMENT '账号名称',
    app_id VARCHAR(100) COMMENT '所属应用ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号账号表';

-- ====================================================================
-- 微信公众号文章表
-- ====================================================================
CREATE TABLE IF NOT EXISTS wx_article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id VARCHAR(100) NOT NULL UNIQUE COMMENT '文章ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    title VARCHAR(500) COMMENT '文章标题',
    publish_date DATETIME COMMENT '发布时间',
    pdf_url VARCHAR(500) COMMENT 'PDF的SFTP路径',
    processed_at DATETIME COMMENT '处理完成时间',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_account_id (account_id),
    INDEX idx_publish_date (publish_date),
    INDEX idx_processed_at (processed_at),
    INDEX idx_pdf_url (pdf_url),
    INDEX idx_retry_count (retry_count),
    FOREIGN KEY (account_id) REFERENCES wx_account(account_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号文章表';

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

-- 验证表创建成功
SELECT
    TABLE_NAME,
    TABLE_COMMENT,
    CREATE_TIME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'baidu_download'
AND TABLE_NAME IN ('wx_account', 'wx_article')
ORDER BY TABLE_NAME;

-- 验证表结构
DESCRIBE wx_account;
DESCRIBE wx_article;

-- 验证外键约束
SELECT
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'baidu_download'
AND TABLE_NAME = 'wx_article'
AND REFERENCED_TABLE_NAME = 'wx_account';

-- 预期结果:
-- wx_account 表应该存在
-- wx_article 表应该存在
-- wx_article 表应该有指向 wx_account 的外键约束