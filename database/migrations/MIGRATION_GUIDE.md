# Database Schema Migration Guide

## 迁移脚本组织结构

本项目使用版本化的数据库迁移脚本系统，确保数据库结构变更的可追溯性和可回滚性。

### 文件结构

```
database/migrations/
├── 000_init_schema.sql                    # 初始数据库架构
├── 001_add_source_field.sql               # 添加消息来源字段
├── 002_allow_null_folder_name.sql         # 允许文件夹名为空
├── 003_add_retry_count.sql                 # 添加重试计数字段
├── rollback/
│   ├── 001_rollback_add_source_field.sql
│   ├── 002_rollback_allow_null_folder_name.sql
│   └── 003_rollback_add_retry_count.sql
└── MIGRATION_GUIDE.md                     # 本文档
```

## 迁移执行顺序

迁移脚本必须按照以下顺序执行：

1. **000_init_schema.sql** - 初始数据库架构（全新安装时执行）
2. **001_add_source_field.sql** - 添加 source 字段支持钉钉/飞书
3. **002_allow_null_folder_name.sql** - 允许 folder_name 为 NULL
4. **003_add_retry_count.sql** - 添加重试计数功能

## 执行方法

### 方法一：全新安装

如果是全新的数据库实例，直接执行初始架构脚本：

```bash
# 创建初始数据库结构
mysql -u root -p < database/migrations/000_init_schema.sql
```

### 方法二：增量迁移

对于现有数据库，按顺序执行需要的迁移：

```bash
# 执行单个迁移
mysql -u root -p baidu_download < database/migrations/001_add_source_field.sql

# 执行下一个迁移
mysql -u root -p baidu_download < database/migrations/002_allow_null_folder_name.sql

# 执行最新迁移
mysql -u root -p baidu_download < database/migrations/003_add_retry_count.sql
```

### 方法三：批量执行

从当前状态到最新版本：

```bash
# 如果数据库是初始状态，执行所有迁移
mysql -u root -p baidu_download < database/migrations/001_add_source_field.sql
mysql -u root -p baidu_download < database/migrations/002_allow_null_folder_name.sql
mysql -u root -p baidu_download < database/migrations/003_add_retry_count.sql
```

## 验证迁移结果

每个迁移脚本都包含验证查询，执行后应该运行相应的验证检查：

### 验证 001_add_source_field.sql

```sql
-- 检查 source 字段是否存在
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND COLUMN_NAME = 'source';

-- 检查现有数据的 source 分布
SELECT source, process_status, COUNT(*) as count
FROM message_process_log
GROUP BY source, process_status;
```

### 验证 002_allow_null_folder_name.sql

```sql
-- 检查 folder_name 是否允许 NULL
SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND COLUMN_NAME = 'folder_name';

-- 预期：IS_NULLABLE = 'YES'
```

### 验证 003_add_retry_count.sql

```sql
-- 检查 retry_count 字段
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND COLUMN_NAME = 'retry_count';

-- 检查索引是否存在
SELECT INDEX_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND INDEX_NAME = 'idx_retry_count';

-- 检查现有数据的 retry_count 分布
SELECT retry_count, process_status, COUNT(*) as count
FROM message_process_log
GROUP BY retry_count, process_status;
```

## 回滚操作

如果迁移后发现问题需要回滚，可以使用对应的回滚脚本：

```bash
# 回滚最近的迁移
mysql -u root -p baidu_download < database/migrations/rollback/003_rollback_add_retry_count.sql

# 回滚更多迁移（按逆序）
mysql -u root -p baidu_download < database/migrations/rollback/002_rollback_allow_null_folder_name.sql
mysql -u root -p baidu_download < database/migrations/rollback/001_rollback_add_source_field.sql
```

## 迁移前准备

### 1. 备份数据库

```bash
# 创建数据库备份
mysqldump -u root -p baidu_download > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# 或仅备份结构
mysqldump -u root -p --no-data baidu_download > schema_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. 检查当前状态

```sql
-- 检查当前数据库结构
SELECT TABLE_NAME, TABLE_COMMENT 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'baidu_download'
ORDER BY TABLE_NAME;

-- 检查 message_process_log 表结构
DESCRIBE message_process_log;

-- 检查现有索引
SHOW INDEX FROM message_process_log;
```

### 3. 评估影响

```sql
-- 检查现有记录数量
SELECT 
    (SELECT COUNT(*) FROM message_process_log) as total_messages,
    (SELECT COUNT(*) FROM file_transfer_log) as total_transfers,
    (SELECT COUNT(*) FROM execution_summary) as total_summaries;

-- 检查数据质量
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN folder_name IS NULL THEN 1 ELSE 0 END) as null_folder_names,
    SUM(CASE WHEN share_link IS NULL THEN 1 ELSE 0 END) as null_share_links,
    SUM(CASE WHEN extraction_code IS NULL THEN 1 ELSE 0 END) as null_extraction_codes
FROM message_process_log;
```

## 常见问题排查

### 问题1：迁移执行失败

**症状**：执行迁移脚本时报错

**解决方案**：
1. 检查数据库连接是否正常
2. 确认数据库用户权限
3. 检查前置依赖的迁移是否已执行
4. 查看具体错误信息进行针对性处理

### 问题2：字段已存在

**症状**：错误提示字段已存在

**解决方案**：
```sql
-- 检查字段是否真的存在
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND COLUMN_NAME = 'source';  -- 替换为相应字段名
```

### 问题3：索引创建失败

**症状**：索引创建时报错

**解决方案**：
```sql
-- 检查索引是否已存在
SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'baidu_download' 
  AND TABLE_NAME = 'message_process_log' 
  AND INDEX_NAME = 'idx_retry_count';  -- 替换为相应索引名

-- 如果已存在，先删除
DROP INDEX idx_retry_count ON message_process_log;
```

### 问题4：数据兼容性问题

**症状**：迁移后查询结果异常

**解决方案**：
- 检查现有数据是否符合新的字段约束
- 必要时进行数据清理或更新
- 验证应用程序是否正确处理新字段

## 生产环境部署建议

### 1. 预发布环境测试

- 先在测试环境执行完整迁移流程
- 验证应用程序功能正常
- 检查性能影响

### 2. 维护窗口

- 选择低峰期执行迁移
- 通知用户可能的维护时间
- 准备回滚方案

### 3. 监控

- 迁移后监控系统性能
- 关注应用程序日志
- 检查数据库错误日志

### 4. 文档更新

- 更新数据库设计文档
- 更新操作手册
- 记录迁移时间和结果

## 迁移历史

| 日期 | 版本 | 描述 | 影响 |
|------|------|------|------|
| 2026-08-19 | 003 | 添加 retry_count 字段 | 支持消息重试限制功能 |
| 2026-08-19 | 002 | 允许 folder_name 为 NULL | 适配简化消息解析逻辑 |
| 2026-08-19 | 001 | 添加 source 字段 | 支持钉钉和飞书双消息源 |
| 2026-08-19 | 000 | 初始数据库架构 | 基础表结构 |

## 联系支持

如遇到迁移相关问题，请联系数据库管理员或查看项目文档。