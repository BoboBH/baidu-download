-- ====================================================================
-- crawler-wxchat 管道相关数据表 DDL 汇总
-- 生成: 2026-09-06（从线上库 SHOW CREATE TABLE 导出，与实际结构一致）
-- 库: test（主库）
--
-- 内容:
--   [1] wechat_crawler_article_status        —— 本系统新增（migration 014），处理状态表
--   [2] wechat_crawler_articles   —— 外部爬虫系统表（参考用，本系统只读！）
--   [3] wechat_crawler_accounts   —— 外部爬虫系统表（参考用，本系统只读！）
--
-- 说明:
--   - AUTO_INCREMENT=xxx 起始值已剥离（对新建环境无意义）
--   - [2][3] 属外部爬虫系统所有，本管道仅 SELECT，禁止写入；
--     此处 DDL 仅用于环境重建参考，勿在库间复制后当作可写表
--   - 排序规则差异：本系统表 utf8mb4_unicode_ci，外部表 utf8mb4_0900_ai_ci，
--     因此代码中 JOIN 必须显式 COLLATE utf8mb4_0900_ai_ci（processor.py 已处理）
-- ====================================================================

USE test;

-- ====================================================================
-- [1] wechat_crawler_article_status —— 爬虫源微信文章处理状态表（本系统新增）
--     来源: database/migrations/014_create_wechat_crawler_article_status.sql（与线上一致）
--     关键语义:
--       article_key   = wechat_crawler_articles.dedup_key（唯一去重键）
--       processed_at  NULL=未成功待重试 / 非NULL=已成功（断点续跑依据）
--       retry_count   失败次数；退避 = updated_at + retry_count×20分钟；
--                     1000000 ≈ 永久搁置
-- ====================================================================

CREATE TABLE IF NOT EXISTS `wechat_crawler_article_status` (
  `id` int NOT NULL AUTO_INCREMENT,
  `article_key` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '去重键=wechat_crawler_articles.dedup_key',
  `crawler_article_id` int NOT NULL COMMENT 'wechat_crawler_articles.id（溯源用，不外键）',
  `account_id` int NOT NULL COMMENT 'wechat_crawler_accounts.id',
  `account_name` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '公众号名称快照（JOIN所得）',
  `title` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章标题',
  `publish_date` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发布日期，源表为VARCHAR YYYY-MM-DD',
  `pdf_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'PDF的SFTP相对路径',
  `processed_at` datetime DEFAULT NULL COMMENT '处理完成时间（NULL=未成功，待重试）',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '最近一次失败原因',
  `retry_count` int DEFAULT '0' COMMENT '重试次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_article_key` (`article_key`),
  KEY `idx_crawler_processed_at` (`processed_at`),
  KEY `idx_crawler_account` (`account_id`),
  KEY `idx_crawler_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬虫源微信文章处理状态表（--crawler-wxchat）';

-- ====================================================================
-- [2] wechat_crawler_articles —— 外部爬虫系统：文章表（只读参考）
-- ====================================================================

CREATE TABLE IF NOT EXISTS `wechat_crawler_articles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_id` int NOT NULL,
  `dedup_key` varchar(191) NOT NULL,
  `fallback_key` varchar(191) NOT NULL,
  `url` text,
  `title` varchar(512) NOT NULL,
  `date_text` varchar(64) DEFAULT NULL,
  `publish_date` varchar(32) DEFAULT NULL,
  `url_status` varchar(16) NOT NULL DEFAULT 'pending',
  `created_at` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dedup_key` (`dedup_key`),
  KEY `idx_articles_account` (`account_id`),
  KEY `idx_articles_fallback` (`account_id`,`fallback_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ====================================================================
-- [3] wechat_crawler_accounts —— 外部爬虫系统：公众号表（只读参考）
-- ====================================================================

CREATE TABLE IF NOT EXISTS `wechat_crawler_accounts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(191) NOT NULL,
  `last_crawled_at` varchar(32) DEFAULT NULL,
  `max_publish_date` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
