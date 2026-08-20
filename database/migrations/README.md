# Database Schema 变更脚本 - 组织说明

## 📋 概览

本项目数据库迁移脚本已重新组织为版本化的增量迁移系统，确保数据库变更的可追溯性、可执行性和可回滚性。

## 🗂️ 文件结构

```
database/migrations/
├── README.md                              # 本文档
├── MIGRATION_GUIDE.md                     # 详细迁移指南
├── 000_init_schema.sql                    # 初始数据库架构
├── 001_add_source_field.sql               # 添加消息来源字段
├── 002_allow_null_folder_name.sql         # 允许文件夹名为空
├── 003_add_retry_count.sql                 # 添加重试计数字段
├── rollback/                               # 回滚脚本目录
│   ├── 001_rollback_add_source_field.sql
│   ├── 002_rollback_allow_null_folder_name.sql
│   └── 003_rollback_add_retry_count.sql
├── migrate_all.sh                          # Linux/Mac 自动迁移脚本
├── migrate_all.bat                         # Windows 自动迁移脚本
└── verify_migrations.sh                   # 迁移验证脚本
```

## 🔄 迁移版本历史

| 版本 | 文件 | 日期 | 描述 | 影响范围 |
|------|------|------|------|----------|
| 000 | `000_init_schema.sql` | 2026-08-19 | 初始数据库架构 | 创建所有基础表 |
| 001 | `001_add_source_field.sql` | 2026-08-19 | 添加消息来源字段 | 支持飞书/钉钉双消息源 |
| 002 | `002_allow_null_folder_name.sql` | 2026-08-19 | 允许文件夹名为NULL | 适配简化消息解析逻辑 |
| 003 | `003_add_retry_count.sql` | 2026-08-19 | 添加重试计数字段 | 防止消息无限重试 |

## 🚀 快速开始

### 全新安装
```bash
# 创建初始数据库结构
mysql -u root -p < database/migrations/000_init_schema.sql
```

### 自动执行所有迁移
```bash
# Linux/Mac
./database/migrations/migrate_all.sh baidu_download root

# Windows
database\migrations\migrate_all.bat baidu_download root
```

### 验证迁移状态
```bash
./database/migrations/verify_migrations.sh baidu_download root
```

## 📊 数据库表结构

### 核心表

#### message_process_log (消息处理记录表)
主要的消息处理状态跟踪表，经过多次迁移扩展：

- **基础字段** (v000): message_hash, original_message, share_link, folder_name, extraction_code, process_status, error_message, etc.
- **v001 扩展**: `source` 字段支持飞书/钉钉消息来源
- **v002 扩展**: `folder_name` 允许 NULL，支持新的消息解析逻辑  
- **v003 扩展**: `retry_count` 字段支持重试次数限制

#### file_transfer_log (文件传输记录表)
记录文件传输过程中的详细信息。

#### execution_summary (执行摘要表)
记录批量处理任务的执行摘要信息。

## 🛠️ 维护指南

### 执行新迁移
1. 按版本号顺序创建新的迁移文件 (如 004_xxx.sql)
2. 在 rollback/ 目录创建对应的回滚脚本
3. 更新本文档的版本历史表
4. 测试迁移和回滚脚本
5. 更新 MIGRATION_GUIDE.md

### 迁移命名规范
- 格式: `VVV_description.sql` (VVV = 3位版本号)
- 使用描述性的英文名称
- 只能使用小写字母、数字、下划线
- 严禁修改已发布的迁移文件

### 回滚策略
每个迁移都应包含回滚脚本，回滚脚本命名: `VVV_rollback_description.sql`

## 🔍 验证检查清单

### 迁移前检查
- [ ] 创建数据库备份
- [ ] 验证当前数据库状态
- [ ] 检查应用程序兼容性
- [ ] 评估执行时间影响

### 迁移后验证
- [ ] 检查表结构变更
- [ ] 验证索引创建
- [ ] 测试应用程序功能
- [ ] 检查数据完整性
- [ ] 验证性能影响

## 📝 迁移脚本规范

### 标准结构
```sql
-- ====================================================================
-- Migration: VVV_name.sql
-- Date: YYYY-MM-DD
-- Description: 详细描述迁移的目的和影响
-- Prerequisites: 前置依赖的迁移版本
-- Order: N (执行顺序)
-- ====================================================================

USE database_name;

-- 变更操作
-- 具体的 SQL 语句

-- 验证查询
-- 用于验证迁移成功的查询语句
```

### 回滚脚本结构
```sql
-- ====================================================================
-- Rollback: VVV_rollback_name.sql
-- Date: YYYY-MM-DD
-- Description: 回滚操作说明
-- Warning: 潜在风险和注意事项
-- ====================================================================

-- 回滚操作
-- 具体的回滚 SQL 语句

-- 验证回滚结果
-- 用于验证回滚成功的查询语句
```

## 🔧 故障排除

### 常见问题

**问题**: 迁移执行失败
- **检查**: 数据库连接、用户权限、SQL语法
- **解决**: 查看错误日志，修复后重新执行

**问题**: 字段已存在错误
- **检查**: 迁移是否已执行
- **解决**: 使用 verify_migrations.sh 检查状态，跳过已执行的迁移

**问题**: 数据兼容性问题
- **检查**: 现有数据是否符合新约束
- **解决**: 数据清理或更新后重新执行迁移

## 📞 支持和文档

- **详细指南**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **项目文档**: [项目主文档](../../../README.md)
- **技术支持**: 数据库管理员或项目负责人

---

**注意**: 数据库迁移是关键操作，请在生产环境执行前充分测试！