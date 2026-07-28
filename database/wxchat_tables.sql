-- ================================================================================
-- 微信公众号文章处理表创建脚本
-- ================================================================================
-- 用途: 创建wx_account和wx_article表用于微信公众号文章PDF转换和上传功能
-- 执行条件: MySQL 5.7+ , test数据库已创建
-- 执行方法: mysql -u root -p test < database/wxchat_tables.sql
-- 安全性: 创建新表，不影响现有数据
-- ================================================================================

USE test;

-- 微信公众号账号表
CREATE TABLE IF NOT EXISTS wx_account (
    account_id VARCHAR(100) PRIMARY KEY COMMENT '账号ID',
    account_name VARCHAR(255) NOT NULL COMMENT '账号名称',
    app_id VARCHAR(100) COMMENT '所属应用ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号账号表';

-- 微信公众号文章表
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
    FOREIGN KEY (account_id) REFERENCES wx_account(account_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号文章表';

-- 验证表是否创建成功
SELECT CONCAT('表 wx_account 创建成功!') AS status;
SELECT CONCAT('表 wx_article 创建成功!') AS status;

-- 显示新创建的表结构
DESCRIBE wx_account;
DESCRIBE wx_article;
