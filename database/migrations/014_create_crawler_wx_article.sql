-- ====================================================================
-- Migration: 014_create_crawler_wx_article.sql
-- Date: 2026-09-04
-- Description: 创建爬虫源微信文章处理状态表 crawler_wx_article
--              服务 --crawler-wxchat 命令的去重与状态记录
--              数据源表 wechat_crawler_articles/wechat_crawler_accounts
--              属外部爬虫系统（只读），本表只记录本系统的处理状态，
--              与源表无外键关联
-- Prerequisites: database/wxchat_tables.sql（test 库）
-- Order: 14
-- 执行方法: mysql -u root -p test < database/migrations/014_create_crawler_wx_article.sql
-- 注意: 本表在主库 test（与 wxchat_tables.sql 同库），
--       而 migrations 目录其他迁移默认 USE baidu_download，勿混淆
-- ====================================================================

USE test;

-- ====================================================================
-- 变更: 创建 crawler_wx_article 表
-- ====================================================================

CREATE TABLE IF NOT EXISTS crawler_wx_article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_key VARCHAR(191) NOT NULL COMMENT '去重键=wechat_crawler_articles.dedup_key',
    crawler_article_id INT NOT NULL COMMENT 'wechat_crawler_articles.id（溯源用，不外键）',
    account_id INT NOT NULL COMMENT 'wechat_crawler_accounts.id',
    account_name VARCHAR(191) COMMENT '公众号名称快照（JOIN所得）',
    title VARCHAR(512) COMMENT '文章标题',
    publish_date VARCHAR(32) COMMENT '发布日期，源表为VARCHAR YYYY-MM-DD',
    pdf_url VARCHAR(500) COMMENT 'PDF的SFTP相对路径',
    processed_at DATETIME COMMENT '处理完成时间（NULL=未成功，待重试）',
    error_message TEXT COMMENT '最近一次失败原因',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY uk_article_key (article_key),
    INDEX idx_crawler_processed_at (processed_at),
    INDEX idx_crawler_account (account_id),
    INDEX idx_crawler_publish_date (publish_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='爬虫源微信文章处理状态表（--crawler-wxchat）';

-- ====================================================================
-- 验证迁移结果
-- ====================================================================

DESCRIBE crawler_wx_article;

-- 预期结果:
-- crawler_wx_article 表创建成功，包含 uk_article_key 唯一键
-- article_key 为去重主键，processed_at IS NOT NULL 表示处理成功
-- ====================================================================
