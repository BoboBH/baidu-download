-- ================================================================================
-- 微信公众号表重命名迁移脚本
-- ================================================================================
-- 用途: 将 wx_account 和 wx_article 表重命名为 new_wx_account 和 new_wx_article
-- 执行条件: 旧的 wx_account 和 wx_article 表已存在
-- 执行方法: mysql -u root -p test < database/migrations/migrate_rename_wxchat_tables.sql
-- 安全性: 重命名表，数据不会丢失，便于系统迁移
-- ================================================================================

USE test;

-- ================================================================================
-- 步骤1: 检查旧表是否存在
-- ================================================================================
SET @wx_account_exists = (SELECT COUNT(*) FROM information_schema.tables
                          WHERE table_schema = 'test' AND table_name = 'wx_account');

SET @wx_article_exists = (SELECT COUNT(*) FROM information_schema.tables
                          WHERE table_schema = 'test' AND table_name = 'wx_article');

-- 显示检查结果
SELECT
    CASE WHEN @wx_account_exists > 0 THEN '旧表 wx_account 存在' ELSE '旧表 wx_account 不存在' END AS wx_account_status,
    CASE WHEN @wx_article_exists > 0 THEN '旧表 wx_article 存在' ELSE '旧表 wx_article 不存在' END AS wx_article_status;

-- ================================================================================
-- 步骤2: 重命名表（如果旧表存在）
-- ================================================================================

-- 重命名 wx_account 表
SET @rename_account_sql = IF(@wx_account_exists > 0,
    'RENAME TABLE wx_account TO new_wx_account',
    'SELECT ''跳过 wx_account 重命名（表不存在）'' AS message');

PREPARE stmt FROM @rename_account_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 重命名 wx_article 表
SET @rename_article_sql = IF(@wx_article_exists > 0,
    'RENAME TABLE wx_article TO new_wx_article',
    'SELECT ''跳过 wx_article 重命名（表不存在）'' AS message');

PREPARE stmt FROM @rename_article_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ================================================================================
-- 步骤3: 更新外键约束（如果需要）
-- ================================================================================

-- 检查新表的外键约束并更新
SET @fk_exists = (SELECT COUNT(*) FROM information_schema.key_column_usage
                  WHERE table_schema = 'test'
                  AND table_name = 'new_wx_article'
                  AND constraint_name = 'new_wx_article_ibfk_1');

-- 如果外键约束使用的是旧表名，则更新
SET @update_fk_sql = IF(@fk_exists > 0 AND @wx_account_exists > 0,
    'ALTER TABLE new_wx_article DROP FOREIGN KEY new_wx_article_ibfk_1',
    'SELECT ''外键约束更新跳过（不需要或不存在）'' AS message');

PREPARE stmt FROM @update_fk_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加正确的外键约束
SET @add_fk_sql = IF(@fk_exists > 0 AND @wx_account_exists > 0,
    'ALTER TABLE new_wx_article ADD CONSTRAINT new_wx_article_ibfk_1 FOREIGN KEY (account_id) REFERENCES new_wx_account(account_id) ON DELETE CASCADE',
    'SELECT ''外键约束添加跳过（不需要或已存在）'' AS message');

PREPARE stmt FROM @add_fk_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ================================================================================
-- 步骤4: 验证迁移结果
-- ================================================================================

-- 检查新表是否存在
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'test' AND table_name = 'new_wx_account')
        THEN '✅ new_wx_account 表创建成功'
        ELSE '❌ new_wx_account 表不存在' END AS account_table_status,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'test' AND table_name = 'new_wx_article')
        THEN '✅ new_wx_article 表创建成功'
        ELSE '❌ new_wx_article 表不存在' END AS article_table_status;

-- 显示新表的记录数量
SELECT
    (SELECT COUNT(*) FROM new_wx_account) AS new_wx_account_records,
    (SELECT COUNT(*) FROM new_wx_article) AS new_wx_article_records;

-- 显示新表结构
DESCRIBE new_wx_account;
DESCRIBE new_wx_article;

-- ================================================================================
-- 步骤5: 数据完整性检查
-- ================================================================================

-- 检查孤立记录（没有对应账号的文章）
SELECT
    COUNT(*) AS orphaned_articles_count,
    CASE WHEN COUNT(*) = 0 THEN '✅ 无孤立记录' ELSE '⚠️ 存在孤立记录，需要清理' END AS integrity_status
FROM new_wx_article wa
LEFT JOIN new_wx_account wa_acc ON wa.account_id = wa_acc.account_id
WHERE wa_acc.account_id IS NULL;

-- ================================================================================
-- 完成提示
-- ================================================================================
SELECT '🎉 表重命名迁移完成！' AS status,
       '新表名: new_wx_account, new_wx_article' AS new_table_names,
       '数据已保留，可以安全使用新表名' AS data_safety,
       '旧表名已不存在，系统将使用新表名' AS migration_result;