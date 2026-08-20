# Database Schema 变更脚本 - 快速开始

## 🚀 5分钟快速开始

### 方式一：全新安装（推荐）

```bash
# 1. 创建基础数据库结构
mysql -u root -p < database/migrations/000_init_schema.sql

# 2. 执行所有增量迁移
./database/migrations/migrate_all.sh baidu_download root
# 或 Windows: database\migrations\migrate_all.bat baidu_download root

# 3. 验证迁移状态
./database/migrations/verify_migrations.sh baidu_download root
```

### 方式二：手动分步执行

```bash
# 1. 添加消息来源字段
mysql -u root -p baidu_download < database/migrations/001_add_source_field.sql

# 2. 允许文件夹名为空
mysql -u root -p baidu_download < database/migrations/002_allow_null_folder_name.sql

# 3. 添加重试计数功能
mysql -u root -p baidu_download < database/migrations/003_add_retry_count.sql
```

### 方式三：包含微信功能

```bash
# 1-3. 执行基础迁移
# (同上)

# 4. 创建微信相关表
mysql -u root -p baidu_download < database/migrations/010_create_wechat_tables.sql
```

## 🛠️ 维护操作

### 清理旧迁移文件

```bash
# Linux/Mac
./database/migrations/cleanup_old_migrations.sh

# Windows
database\migrations\cleanup_old_migrations.bat
```

### 回滚操作

```bash
# 回滚最新的迁移
mysql -u root -p baidu_download < database/migrations/rollback/003_rollback_add_retry_count.sql

# 回滚更多迁移（逆序）
mysql -u root -p baidu_download < database/migrations/rollback/002_rollback_allow_null_folder_name.sql
mysql -u root -p baidu_download < database/migrations/rollback/001_rollback_add_source_field.sql
```

### 备份数据库

```bash
# 完整备份
mysqldump -u root -p baidu_download > backup_$(date +%Y%m%d).sql

# 仅备份结构
mysqldump -u root -p --no-data baidu_download > schema_backup.sql
```

## 📋 检查清单

### 部署前 ✅
- [ ] 在测试环境验证迁移脚本
- [ ] 创建生产数据库备份
- [ ] 确认维护时间窗口
- [ ] 通知相关人员

### 部署中 ✅
- [ ] 按顺序执行迁移脚本
- [ ] 检查每个脚本的执行结果
- [ ] 验证表结构变更
- [ ] 确认索引创建成功

### 部署后 ✅
- [ ] 运行验证脚本
- [ ] 测试应用程序功能
- [ ] 检查性能指标
- [ ] 监控错误日志

## 🔧 常用命令

### 查看当前数据库状态
```sql
-- 查看所有表
SHOW TABLES;

-- 查看特定表结构
DESCRIBE message_process_log;

-- 查看索引
SHOW INDEX FROM message_process_log;
```

### 检查迁移状态
```bash
# 使用验证脚本
./database/migrations/verify_migrations.sh baidu_download root
```

### 紧急回滚
```bash
# 从备份恢复
mysql -u root -p baidu_download < backup_YYYYMMDD.sql
```

## 📞 获取帮助

- **详细文档**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **组织说明**: [README.md](README.md)
- **归档文件**: [archive/ARCHIVED_MIGRATIONS.md](archive/ARCHIVED_MIGRATIONS.md)

## ⚠️ 重要提醒

1. **生产环境**: 务必在测试环境先验证所有迁移
2. **数据备份**: 执行迁移前必须创建完整备份
3. **按序执行**: 严格按照版本号顺序执行迁移
4. **停机时间**: 评估迁移对生产环境的影响

---

**准备好了吗？** 从执行验证脚本开始：`./verify_migrations.sh`