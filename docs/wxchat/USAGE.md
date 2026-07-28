# 微信公众号文章处理功能使用指南

## 功能概述

本功能用于处理微信公众号文章，自动将文章转换为PDF格式并上传到SFTP服务器进行归档存储。

## 环境要求

- Python 3.8+
- MySQL数据库（包含wewe_rss和test两个数据库）
- SFTP服务器
- Python依赖包（见requirements.txt）

## 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 如果需要使用Playwright进行PDF生成（可选）
pip install playwright
playwright install chromium
```

## 配置说明

在`.env`文件中添加以下配置：

```bash
# ====================
# 微信公众号文章处理配置
# ====================
# 启用微信文章处理功能
WXCHAT_ENABLED=false

# wewe_rss数据库配置（源数据库）
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=your_password
WXCHAT_WEWE_DB_NAME=wewe_rss

# 微信文章基础URL
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/

# PDF生成配置
WXCHAT_PDF_TIMEOUT=60          # 页面加载超时时间（秒）
WXCHAT_IMAGE_WAIT_TIME=20       # 图片加载等待时间（秒）

# 反限流配置
WXCHAT_DOWNLOAD_DELAY=5         # 每篇文章处理后延迟时间（秒）

# 历史查询配置
WXCHAT_MAX_DAYS=30              # 最大查询天数

# SFTP配置
WXCHAT_SFTP_REMOTE_PATH=/wxchat  # SFTP远程路径
```

## 数据库准备

```bash
# 创建数据表
mysql -u root -p test < database/wxchat_tables.sql
```

## 使用方法

### 基本使用

```bash
# 处理最近3天的文章（默认）
python main.py --wxchat

# 处理最近7天的文章
python main.py --wxchat --wxchat-days 7

# 处理最近1天的文章
python main.py --wxchat --wxchat-days 1

# 仅同步账号信息
python main.py --wxchat --wxchat-sync-accounts

# 显示详细日志
python main.py --wxchat --verbose
```

### 定时任务

设置定时任务，每天自动处理最新文章：

```bash
# 添加到crontab (Linux)
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * cd /path/to/baidu-download && python main.py --wxchat --wxchat-days 1
```

Windows任务计划程序：
1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天凌晨2点）
4. 操作：运行程序 `python.exe`，参数 `main.py --wxchat --wxchat-days 1`
5. 起始于：`d:\git\baidu-download`

## 功能特点

### 1. 账号同步
- 自动从wewe_rss数据库同步微信公众号账号信息
- 支持增量更新，避免重复数据
- 数据来源：`wewe_rss.feeds`表

### 2. 文章去重
- 基于article_id进行去重
- 已处理的文章会被跳过
- 智能状态检查，避免重复处理

### 3. PDF生成
- 使用requests获取真实内容
- 智能备用方案，确保处理稳定性
- 支持自定义页面格式和质量
- 完整的HTML内容保存

### 4. SFTP上传
- 按YYMM格式组织文件（2401表示2024年1月）
- 自动创建远程目录
- 智能文件命名：公众号名称_文章标题.pdf
- 文件名清理，移除非法字符

### 5. 错误处理
- 失败的文章会记录错误信息
- 支持错误重试机制
- 详细的日志记录
- 异常情况优雅处理

### 6. 反限流措施
- 真实浏览器请求头模拟
- 每篇文章处理后延迟
- 合理的超时设置
- 智能备用方案

## 监控和日志

### 查看日志

```bash
# 实时查看日志
tail -f logs/transfer.log

# 查找处理结果
grep "处理完成" logs/transfer.log

# 查看错误信息
grep "ERROR" logs/transfer.log
```

### 数据库监控

```sql
-- 查看处理统计
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed,
    COUNT(CASE WHEN pdf_url IS NULL THEN 1 END) as pending
FROM wx_article;

-- 查看最近处理记录
SELECT * FROM wx_article
ORDER BY processed_at DESC
LIMIT 10;

-- 查看失败记录
SELECT article_id, title, error_message, retry_count
FROM wx_article
WHERE pdf_url IS NULL
  AND error_message IS NOT NULL
ORDER BY retry_count DESC
LIMIT 20;

-- 查看账号信息
SELECT * FROM wx_account ORDER BY account_name;
```

## 故障排查

### PDF生成失败
**症状**: 日志显示"PDF生成失败"

**解决方案**:
1. 检查网络连接是否正常
2. 增加超时时间: `WXCHAT_PDF_TIMEOUT=120`
3. 检查文章URL是否有效
4. 查看详细错误日志

### SFTP上传失败
**症状**: 日志显示"SFTP上传失败"

**解决方案**:
1. 检查SFTP连接配置
2. 验证SFTP服务器权限
3. 检查磁盘空间是否充足
4. 测试网络连接
5. 检查远程路径配置

### 数据库连接失败
**症状**: 无法连接到数据库

**解决方案**:
1. 检查数据库配置是否正确
2. 验证数据库服务是否运行
3. 测试网络连接
4. 检查数据库用户权限
5. 确认数据库表已创建

### 文章处理失败
**症状**: 特定文章处理失败

**解决方案**:
1. 检查文章是否存在于wewe_rss数据库
2. 验证article_id是否正确
3. 检查文章是否可公开访问
4. 查看详细错误信息
5. 尝试手动同步账号信息

## 性能优化建议

1. **批量处理**: 适当增加天数参数，减少执行频率
2. **并发控制**: 当前版本为串行处理，已考虑稳定性
3. **资源清理**: 定期清理临时文件和旧日志
4. **数据库优化**: 为常用查询字段建立索引
5. **网络优化**: 合理设置超时和延迟参数

## 安全建议

1. **数据库密码**: 使用强密码，定期更换
2. **SFTP安全**: 使用密钥认证，禁用密码登录
3. **网络隔离**: 在受信任的网络环境中运行
4. **日志保护**: 定期清理敏感日志信息
5. **权限控制**: 限制数据库用户权限

## 扩展功能

未来可能的功能扩展：

- 支持批量并发处理
- 增加处理进度通知
- 提供Web管理界面
- 支持多种文件格式转换
- 增加文章内容分析功能
- 支持自定义PDF模板

## 技术支持

如遇到问题，请查看：
1. 日志文件: `logs/transfer.log`
2. 数据库错误记录: `wx_article.error_message`
3. 系统状态监控
4. GitHub Issues

## 数据结构

### wx_account表
- `account_id`: 账号ID（主键）
- `account_name`: 账号名称
- `app_id`: 所属应用ID
- `created_at`: 记录创建时间
- `updated_at`: 记录更新时间

### wx_article表
- `id`: 自增主键
- `article_id`: 文章ID（唯一）
- `account_id`: 账号ID（外键）
- `title`: 文章标题
- `publish_date`: 发布时间
- `pdf_url`: PDF的SFTP路径
- `processed_at`: 处理完成时间
- `error_message`: 错误信息
- `retry_count`: 重试次数
- `created_at`: 记录创建时间
- `updated_at`: 记录更新时间

---

**版本**: 1.0
**最后更新**: 2026-07-28
**维护状态**: 活跃维护中