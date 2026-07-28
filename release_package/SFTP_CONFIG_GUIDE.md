# 微信SFTP目录配置说明

## 🔧 重要配置修复

已修复微信文章PDF上传到SFTP服务器的目录配置问题。

## 新增配置参数

**配置名称**: `WXCHAT_SFTP_REMOTE_PATH`  
**默认值**: `/wxchat`  
**用途**: 指定微信文章PDF文件的SFTP上传目录

## 📁 目录结构说明

### 自动文件组织
系统按**YYMM格式**自动组织PDF文件：

```
SFTP服务器结构:
/wxchat/                      ← WXCHAT_SFTP_REMOTE_PATH
├── 2407/                    ← 2024年7月
│   ├── article_001.pdf
│   ├── article_002.pdf
│   └── ...
├── 2408/                    ← 2024年8月
│   └── ...
```

### 路径生成规则
- **主目录**: 使用 `WXCHAT_SFTP_REMOTE_PATH` 配置
- **子目录**: 按文章发布日期的YYMM格式自动创建
- **文件名**: 使用 `article_id.pdf` 格式

**完整示例**: `/wxchat/2407/article_12345.pdf`

## ⚙️ 配置方法

### 1. 在.env文件中添加
```bash
# 微信文章SFTP上传配置
WXCHAT_SFTP_REMOTE_PATH=/wxchat
```

### 2. 配置建议
```bash
# 开发环境
WXCHAT_SFTP_REMOTE_PATH=/wxchat_dev

# 生产环境  
WXCHAT_SFTP_REMOTE_PATH=/wxchat

# 测试环境
WXCHAT_SFTP_REMOTE_PATH=/wxchat_test
```

## 🔍 配置对比

| 功能 | 配置参数 | 默认路径 | 说明 |
|------|----------|----------|------|
| 百度网盘文件 | `SFTP_REMOTE_PATH` | `/sftp01/upload` | 现有功能 |
| 微信文章PDF | `WXCHAT_SFTP_REMOTE_PATH` | `/wxchat` | 新增功能 |

## 📋 使用前检查

### 1. SFTP目录权限
确保目标目录有写权限：
```bash
mkdir -p /wxchat
chmod 755 /wxchat
```

### 2. 存储空间规划
- 根据文章数量预留足够空间
- 考虑按月归档策略
- 设置存储监控告警

### 3. 数据库验证
系统会记录完整路径到数据库：
```sql
SELECT article_id, pdf_url, publish_date 
FROM wx_article 
WHERE pdf_url IS NOT NULL;
```

## 🚀 部署步骤

1. **更新配置文件**: 添加 `WXCHAT_SFTP_REMOTE_PATH=/wxchat`
2. **创建SFTP目录**: `mkdir -p /wxchat && chmod 755 /wxchat`
3. **重启服务**: 使新配置生效
4. **测试上传**: 运行 `baidu-download.exe --wxchat --wxchat-days 1`

## 📊 配置验证

### 检查配置是否生效
```bash
# 查看处理日志
tail -f logs/transfer.log | grep "PDF上传成功"

# 应该看到类似的输出：
# PDF上传成功: /wxchat/2407/article_12345.pdf
```

---

**更新日期**: 2026-07-28  
**版本**: v1.2.3+  
**状态**: ✅ 配置问题已修复