# 微信SFTP目录配置说明

## 问题修复

用户发现微信文章PDF上传到SFTP服务器时缺少专门的目录配置，现已修复。

## 新增配置参数

**配置名称**: `WXCHAT_SFTP_REMOTE_PATH`

**默认值**: `/wxchat`

**说明**: 微信文章PDF文件将上传到此SFTP目录下，并按YYMM格式组织子目录。

**默认值**: `/wxchat`

**配置示例**:
```bash
# 在.env文件中设置
WXCHAT_SFTP_REMOTE_PATH=/wxchat
```

## 目录结构说明

### 文件组织方式
系统会自动按**YYMM格式**组织微信PDF文件：

```
SFTP服务器结构:
/wxchat/                      ← WXCHAT_SFTP_REMOTE_PATH
├── 2407/                    ← 2024年7月
│   ├── article_001.pdf
│   ├── article_002.pdf
│   └── ...
├── 2408/                    ← 2024年8月
│   ├── article_003.pdf
│   └── ...
└── 2409/                    ← 2024年9月
    └── ...
```

### 路径生成规则
1. **主目录**: 使用 `WXCHAT_SFTP_REMOTE_PATH` 配置
2. **子目录**: 按文章发布日期的YYMM格式自动创建
3. **文件名**: 使用 `article_id.pdf` 格式

**完整路径示例**:
- 配置: `WXCHAT_SFTP_REMOTE_PATH=/wxchat`
- 文章发布日期: `2024-07-28`
- 文章ID: `article_12345`
- **最终路径**: `/wxchat/2407/article_12345.pdf`

## 配置优先级

微信功能使用**独立的SFTP目录配置**，不与现有的百度网盘文件传输共用目录：

- **现有功能**: 使用 `SFTP_REMOTE_PATH`（如：`/sftp01/upload`）
- **微信功能**: 使用 `WXCHAT_SFTP_REMOTE_PATH`（如：`/wxchat`）

这样可以避免文件混淆，便于管理和维护。

## 使用建议

### 1. 目录权限
确保SFTP服务器上的目标目录具有写权限：
```bash
# 在SFTP服务器上创建目录
mkdir -p /wxchat
chmod 755 /wxchat
```

### 2. 存储规划
根据预期存储量合理规划：
- **小型部署**: 直接使用 `/wxchat` 目录
- **大型部署**: 考虑按年份进一步细分，如 `/wxchat/2024/2407/`

### 3. 备份策略
微信PDF文件按时间自动组织，便于：
- 按月备份归档
- 定期清理过期文件
- 监控存储使用情况

## 数据库记录

系统会在数据库中记录完整的SFTP路径：

```sql
-- 查看文章的SFTP路径
SELECT article_id, title, pdf_url, publish_date 
FROM wx_article 
WHERE pdf_url IS NOT NULL;
```

**结果示例**:
```
article_id: article_12345
title: "某文章标题"
pdf_url: "/wxchat/2407/article_12345.pdf"
publish_date: "2024-07-28 10:30:00"
```

## 兼容性说明

- **向后兼容**: 新配置有默认值 `/wxchat`，不影响现有部署
- **独立配置**: 与现有SFTP配置分离，避免冲突
- **自动创建**: 子目录会在首次上传时自动创建

## 配置示例

### 开发环境
```bash
WXCHAT_SFTP_REMOTE_PATH=/wxchat_dev
```

### 生产环境
```bash
WXCHAT_SFTP_REMOTE_PATH=/wxchat
```

### 测试环境
```bash
WXCHAT_SFTP_REMOTE_PATH=/wxchat_test
```

---

**修复日期**: 2026-07-28  
**影响范围**: 微信文章PDF处理功能  
**配置文件**: `.env`, `.env.example`  
**代码更新**: `src/config/settings.py`, `src/wxchat/processor.py`