# 微信SFTP目录配置修复说明

## ✅ 问题已修复

用户发现的重要问题已解决：**微信文章PDF上传到SFTP服务器缺少专门的目录配置**。

## 🔧 新增配置

**配置参数**: `WXCHAT_SFTP_REMOTE_PATH`  
**默认值**: `/wxchat`  
**用途**: 指定微信文章PDF文件的SFTP上传根目录

## 📁 目录组织方式

系统会自动按**YYMM格式**组织微信PDF文件：

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

## ⚙️ 配置步骤

### 1. 在.env文件中添加配置
```bash
# 微信文章SFTP上传配置
WXCHAT_SFTP_REMOTE_PATH=/wxchat
```

### 2. 在SFTP服务器上创建目录
```bash
mkdir -p /wxchat
chmod 755 /wxchat
```

### 3. 重启程序使配置生效
```bash
baidu-download.exe --wxchat --wxchat-days 1
```

## 🔍 配置对比

| 功能 | 配置参数 | 默认路径 | 用途 |
|------|----------|----------|------|
| 百度网盘文件 | `SFTP_REMOTE_PATH` | `/sftp01/upload` | 现有功能 |
| 微信文章PDF | `WXCHAT_SFTP_REMOTE_PATH` | `/wxchat` | 微信功能 |

## 📋 完整配置示例

```bash
# ===== 微信公众号配置 =====
WXCHAT_ENABLED=true

# wewe_rss数据库配置
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=123456
WXCHAT_WEWE_DB_NAME=wewe_rss

# 微信文章SFTP上传配置 (新增)
WXCHAT_SFTP_REMOTE_PATH=/wxchat

# PDF生成配置
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20

# 反限流配置
WXCHAT_DOWNLOAD_DELAY=5
WXCHAT_MAX_DAYS=30
```

## 📊 路径生成规则

**完整路径示例**:
- 配置: `WXCHAT_SFTP_REMOTE_PATH=/wxchat`
- 文章发布日期: `2024-07-28`
- 文章ID: `article_12345`
- **最终路径**: `/wxchat/2407/article_12345.pdf`

## ✅ 更新内容

1. **Settings类**: 添加 `wxchat_sftp_remote_path` 配置参数
2. **Processor逻辑**: 使用YYMM格式自动组织子目录
3. **配置文件**: 更新 `.env.example` 添加新配置说明
4. **数据库**: 记录完整的SFTP路径到 `pdf_url` 字段

## 🚀 验证方法

### 查看日志确认上传成功
```bash
tail -f logs/transfer.log | grep "PDF上传成功"
```

### 数据库验证
```sql
SELECT article_id, title, pdf_url, publish_date 
FROM wx_article 
WHERE pdf_url IS NOT NULL;
```

---

**修复日期**: 2026-07-28  
**版本**: v1.2.3+  
**状态**: ✅ 生产就绪