# 微信公众号文章PDF处理系统使用文档

## 1. 功能概述

### 1.1 系统功能

微信公众号文章PDF处理系统是一个自动化工具，用于从wewe_rss系统获取微信公众号文章，将其转换为PDF格式，并上传到SFTP服务器进行归档存储。

**核心功能：**
- 自动获取微信公众号文章信息
- 智能去重，避免重复处理
- 高质量PDF生成，保留文章原格式
- 自动上传到SFTP服务器
- 完整的处理状态记录和监控
- 账号信息同步管理

### 1.2 核心目标

- **自动化归档**: 自动将微信公众号文章转换为PDF并归档到SFTP服务器
- **智能去重**: 基于文章ID的智能去重机制，避免重复处理
- **稳定可靠**: 提供错误处理、自动重试、反限流等机制确保稳定运行
- **易于监控**: 提供完整的日志记录和数据库状态监控

### 1.3 主要特性

- **双数据库架构**: 从wewe_rss数据库读取文章，写入本地test数据库记录状态
- **真实浏览器渲染**: 使用Playwright + Chromium确保PDF质量
- **智能反限流**: 真实浏览器请求头、延迟策略、超时控制等多重措施
- **灵活的配置**: 支持多种参数配置和定时任务
- **完整的监控**: 详细的日志记录和数据库状态查询

## 2. 系统架构

### 2.1 技术栈

- **PDF生成**: Playwright + Chromium 浏览器
- **数据库**: MySQL (双数据库架构)
- **文件传输**: SFTP协议
- **命令行**: Python Click CLI框架
- **配置管理**: Python-dotenv环境变量

### 2.2 数据流程

```
用户执行命令
    ↓
同步微信公众号账号信息（可选）
    ↓
从wewe_rss数据库获取文章列表
    ↓
检查test数据库去重（基于article_id）
    ↓
逐个处理文章：
  - 生成真实浏览器请求头
  - 启动Playwright访问文章页面
  - 等待图片加载完成
  - 转换为PDF
  - 延迟5秒（反限流）
    ↓
上传PDF到SFTP服务器
    ↓
更新处理状态到test数据库
    ↓
输出处理统计报告
```

### 2.3 组件关系

```
main.py (CLI入口)
  ├── src/config/settings.py (配置管理)
  ├── src/wxchat/ (微信处理模块)
  │   ├── commands.py (CLI命令定义)
  │   ├── processor.py (核心业务逻辑)
  │   └── models.py (数据模型)
  ├── src/uploader/sftp_client.py (SFTP上传)
  └── src/database/models.py (数据库模型)
```

## 3. 环境准备

### 3.1 依赖安装

**安装Playwright和浏览器：**
```bash
# 安装Playwright
pip install playwright

# 安装Chromium浏览器
playwright install chromium
```

**安装其他依赖：**
```bash
# 确保所有必需的依赖包已安装
pip install pymysql click python-dotenv playwright
```

### 3.2 数据库准备

**wewe_rss数据库（源数据库）：**
- 确保wewe_rss系统正常运行
- 确认数据库连接参数正确
- 验证account表和article表存在

**test数据库（目标数据库）：**
```bash
# 创建数据库（如果不存在）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS test DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"

# 创建必要的表结构
mysql -u root -p test < database/wxchat_tables.sql
```

**必要的表结构：**
```sql
-- 微信公众号账号表
CREATE TABLE IF NOT EXISTS wx_account (
    account_id VARCHAR(100) PRIMARY KEY COMMENT '账号ID',
    account_name VARCHAR(255) NOT NULL COMMENT '账号名称',
    app_id VARCHAR(100) COMMENT '所属应用ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号账号表';

-- 微信公众号文章表
CREATE TABLE IF NOT EXISTS wx_article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id VARCHAR(100) NOT NULL UNIQUE COMMENT '文章ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    title VARCHAR(500) COMMENT '文章标题',
    publish_date DATETIME COMMENT '发布时间',
    pdf_url VARCHAR(500) COMMENT 'PDF的SFTP路径',
    processed_at DATETIME COMMENT '处理完成时间',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_account_id (account_id),
    INDEX idx_publish_date (publish_date),
    INDEX idx_processed_at (processed_at),
    INDEX idx_pdf_url (pdf_url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号文章表';
```

### 3.3 SFTP服务器配置

**确保SFTP服务器可用：**
```bash
# 测试SFTP连接
sftp -P 22 sftp01@192.168.0.122

# 验证目标目录权限
# 确保SFTP用户有上传权限到目标目录
```

**目录结构建议：**
```
/sftp01/upload/
├── 2024/01/    # 按年月组织文件
├── 2024/02/
└── 2024/03/
```

### 3.4 wewe_rss系统要求

**wewe_rss系统状态：**
- 确保wewe_rss服务正在运行
- 确认数据库可访问
- 验证account表和article表结构

**预期的数据库表结构：**
```sql
-- wewe_rss数据库中的account表
CREATE TABLE account (
    account_id VARCHAR(100),
    account_name VARCHAR(255),
    app_id VARCHAR(100),
    ...
);

-- wewe_rss数据库中的article表
CREATE TABLE article (
    article_id VARCHAR(100),
    account_id VARCHAR(100),
    title VARCHAR(500),
    publish_date DATETIME,
    content_url VARCHAR(500),
    ...
);
```

## 4. 配置文件设置

### 4.1 必需配置参数

在`.env`文件中配置以下必需参数：

```bash
# ===== 微信公众号配置 =====
# 微信文章处理功能开关
WXCHAT_ENABLED=true

# wewe_rss数据库配置（源数据库）
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=your_wewe_db_password_here
WXCHAT_WEWE_DB_NAME=wewe_rss

# 微信文章基础URL
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/

# ===== 其他必需配置 =====
# SFTP服务器配置
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_sftp_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# 目标数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password_here
DB_NAME=test
```

### 4.2 可选配置参数

```bash
# ===== PDF生成配置 =====
WXCHAT_PDF_TIMEOUT=60          # 页面加载超时时间（秒）[范围: 10-300]
WXCHAT_IMAGE_WAIT_TIME=20       # 图片加载等待时间（秒）[范围: 5-120]

# ===== 反限流配置 =====
WXCHAT_DOWNLOAD_DELAY=5         # 每篇文章处理后延迟时间（秒）[范围: 1-60]

# ===== 历史查询配置 =====
WXCHAT_MAX_DAYS=30              # 最大查询天数 [范围: 1-365]

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log
```

### 4.3 配置验证

**验证配置文件：**
```bash
# 检查.env文件是否存在
ls -la .env

# 测试配置加载
python -c "from src.config.settings import Settings; s = Settings(); print('配置加载成功')"
```

**配置参数范围验证：**
- `WXCHAT_PDF_TIMEOUT`: 10-300秒
- `WXCHAT_IMAGE_WAIT_TIME`: 5-120秒
- `WXCHAT_DOWNLOAD_DELAY`: 1-60秒
- `WXCHAT_MAX_DAYS`: 1-365天

### 4.4 配置示例

**开发环境配置示例：**
```bash
WXCHAT_ENABLED=true
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=dev_password_123
WXCHAT_WEWE_DB_NAME=wewe_rss_dev
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20
WXCHAT_DOWNLOAD_DELAY=5
WXCHAT_MAX_DAYS=7
```

**生产环境配置示例：**
```bash
WXCHAT_ENABLED=true
WXCHAT_WEWE_DB_HOST=prod-db-server.example.com
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=wxchat_user
WXCHAT_WEWE_DB_PASSWORD=strong_prod_password_here
WXCHAT_WEWE_DB_NAME=wewe_rss_prod
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
WXCHAT_PDF_TIMEOUT=90
WXCHAT_IMAGE_WAIT_TIME=30
WXCHAT_DOWNLOAD_DELAY=8
WXCHAT_MAX_DAYS=30
```

## 5. 使用方式

### 5.1 基本使用

**处理最近3天的文章（默认）：**
```bash
python main.py --wxchat
```

**处理指定天数的文章：**
```bash
# 处理最近7天的文章
python main.py --wxchat --wxchat-days 7

# 处理最近1天的文章
python main.py --wxchat --wxchat-days 1

# 处理最近30天的文章
python main.py --wxchat --wxchat-days 30
```

**仅同步账号信息：**
```bash
python main.py --wxchat --wxchat-sync-accounts
```

### 5.2 高级使用

**组合使用：**
```bash
# 先同步账号，再处理文章
python main.py --wxchat --wxchat-sync-accounts
python main.py --wxchat --wxchat-days 7
```

**调试模式：**
```bash
# 启用详细日志
LOG_LEVEL=DEBUG python main.py --wxchat --wxchat-days 1
```

**错误处理：**
```bash
# 系统会自动跳过失败的文章并继续处理
# 失败的文章会在下次运行时重试（基于pdf_url是否为NULL判断）
```

### 5.3 定时任务

**Linux crontab配置：**
```bash
# 编辑crontab
crontab -e

# 添加定时任务
# 每天凌晨2点处理昨天的文章
0 2 * * * cd /path/to/baidu-download && python main.py --wxchat --wxchat-days 1 >> logs/cron.log 2>&1

# 每6小时处理最近1天的文章
0 */6 * * * cd /path/to/baidu-download && python main.py --wxchat --wxchat-days 1 >> logs/cron.log 2>&1

# 每周日凌晨3点处理最近7天的文章
0 3 * * 0 cd /path/to/baidu-download && python main.py --wxchat --wxchat-days 7 >> logs/cron.log 2>&1
```

**Windows任务计划程序：**
```powershell
# 创建任务计划程序任务
# 程序或脚本: python
# 参数: main.py --wxchat --wxchat-days 1
# 起始于: d:\git\baidu-download
```

### 5.4 使用场景

**日常归档：**
```bash
# 每天处理昨天的文章，形成日常归档习惯
python main.py --wxchat --wxchat-days 1
```

**补录历史文章：**
```bash
# 处理最近30天的文章，补充历史数据
python main.py --wxchat --wxchat-days 30
```

**新账号初始化：**
```bash
# 先同步账号信息
python main.py --wxchat --wxchat-sync-accounts
# 然后处理该账号的文章
python main.py --wxchat --wxchat-days 7
```

**数据恢复：**
```bash
# 重新处理失败的文章（系统会自动重试pdf_url为NULL的记录）
python main.py --wxchat --wxchat-days 7
```

## 6. 监控和日志

### 6.1 日志管理

**日志文件位置：**
```bash
# 默认日志文件位置
./logs/transfer.log

# 查看最新日志
tail -f logs/transfer.log

# 查看处理结果
grep "处理完成" logs/transfer.log
grep "微信文章处理完成" logs/transfer.log
```

**日志级别说明：**
- `DEBUG`: 详细的调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

**日志查看技巧：**
```bash
# 查看今天的处理日志
grep "$(date +%Y-%m-%d)" logs/transfer.log | grep "微信文章处理"

# 查看错误信息
grep "ERROR\|错误" logs/transfer.log

# 查看处理统计
grep "总计文章\|成功处理\|失败文章" logs/transfer.log

# 统计处理成功率
grep "微信文章处理完成" logs/transfer.log | tail -1
```

### 6.2 数据库监控

**查看处理统计：**
```sql
-- 总体处理统计
SELECT 
    COUNT(*) as total_articles,
    COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed_articles,
    COUNT(CASE WHEN pdf_url IS NULL THEN 1 END) as pending_articles,
    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_articles
FROM wx_article;

-- 处理成功率
SELECT 
    CONCAT(ROUND(COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2), '%') as success_rate
FROM wx_article;
```

**查看最近处理记录：**
```sql
-- 查看最近10条处理记录
SELECT 
    article_id,
    title,
    publish_date,
    CASE 
        WHEN pdf_url IS NOT NULL THEN '成功'
        WHEN error_message IS NOT NULL THEN '失败'
        ELSE '待处理'
    END as status,
    processed_at,
    error_message
FROM wx_article 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看今天处理的记录
SELECT 
    DATE(processed_at) as process_date,
    COUNT(*) as count,
    COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as success,
    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed
FROM wx_article 
WHERE processed_at >= CURDATE()
GROUP BY DATE(processed_at);
```

**查看错误记录：**
```sql
-- 查看所有失败的文章
SELECT 
    article_id,
    title,
    error_message,
    retry_count,
    created_at,
    updated_at
FROM wx_article 
WHERE error_message IS NOT NULL
ORDER BY created_at DESC;

-- 按错误类型统计
SELECT 
    SUBSTRING_INDEX(error_message, ':', 1) as error_type,
    COUNT(*) as count
FROM wx_article 
WHERE error_message IS NOT NULL
GROUP BY error_type
ORDER BY count DESC;
```

**查看账号信息：**
```sql
-- 查看所有同步的账号
SELECT 
    account_id,
    account_name,
    app_id,
    created_at,
    updated_at
FROM wx_account
ORDER BY account_name;

-- 查看账号文章统计
SELECT 
    a.account_name,
    COUNT(*) as article_count,
    COUNT(CASE WHEN w.pdf_url IS NOT NULL THEN 1 END) as processed_count
FROM wx_account a
LEFT JOIN wx_article w ON a.account_id = w.account_id
GROUP BY a.account_id, a.account_name
ORDER BY article_count DESC;
```

### 6.3 性能指标

**处理时间分析：**
```sql
-- 平均处理时间（按天统计）
SELECT 
    DATE(created_at) as process_date,
    COUNT(*) as article_count,
    AVG(TIMESTAMPDIFF(SECOND, MIN(created_at), MAX(created_at))) as avg_duration_seconds
FROM wx_article 
WHERE processed_at IS NOT NULL
GROUP BY DATE(created_at)
ORDER BY process_date DESC;
```

**SFTP存储统计：**
```sql
-- 按月份统计PDF数量
SELECT 
    DATE_FORMAT(processed_at, '%Y-%m') as month,
    COUNT(*) as pdf_count,
    AVG(SUBSTRING_INDEX(pdf_url, '/', -1)) as avg_filename
FROM wx_article 
WHERE pdf_url IS NOT NULL
GROUP BY DATE_FORMAT(processed_at, '%Y-%m')
ORDER BY month DESC;
```

## 7. 故障排查

### 7.1 常见问题

**问题1：PDF生成失败**
```
错误信息: PDF生成失败
可能原因: 
  - Playwright未正确安装
  - Chromium浏览器未安装
  - 网络连接问题
  - 文章URL无效

解决方案:
  1. 检查Playwright安装: pip show playwright
  2. 重新安装浏览器: playwright install chromium
  3. 检查网络连接: ping mp.weixin.qq.com
  4. 验证文章URL有效性
```

**问题2：SFTP上传失败**
```
错误信息: SFTP上传失败
可能原因:
  - SFTP服务器连接失败
  - 权限不足
  - 磁盘空间不足
  - 网络问题

解决方案:
  1. 检查SFTP连接: sftp -P 22 sftp01@192.168.0.122
  2. 验证目标目录权限: ls -la /sftp01/upload
  3. 检查磁盘空间: df -h
  4. 查看详细错误日志
```

**问题3：数据库连接失败**
```
错误信息: 数据库连接失败
可能原因:
  - 数据库服务未启动
  - 连接参数错误
  - 权限不足
  - 网络问题

解决方案:
  1. 检查MySQL服务: systemctl status mysql
  2. 验证连接参数: mysql -h localhost -u root -p
  3. 检查数据库权限
  4. 验证网络连接
```

**问题4：账号同步失败**
```
错误信息: 账号同步失败
可能原因:
  - wewe_rss数据库连接失败
  - account表不存在
  - 表结构不匹配

解决方案:
  1. 检查wewe_rss数据库连接
  2. 验证account表结构: DESC account
  3. 检查数据库权限
  4. 查看详细错误日志
```

### 7.2 错误信息

**配置相关错误：**
```
Missing required environment variable: WXCHAT_WEWE_DB_HOST
解决方案: 检查.env文件中的数据库配置

Invalid WXCHAT_PDF_TIMEOUT value: abc
解决方案: 确保参数值为数字且在有效范围内

WXCHAT_ENABLED must be set to 'true' in .env file
解决方案: 在.env文件中设置WXCHAT_ENABLED=true
```

**数据库相关错误：**
```
Database connection failed: Access denied for user 'root'@'localhost'
解决方案: 检查数据库用户名和密码

Table 'wewe_rss.account' doesn't exist
解决方案: 确认wewe_rss数据库表结构正确

Duplicate entry 'xxx' for key 'article_id'
解决方案: 系统会自动处理，使用UPSERT机制
```

**网络相关错误：**
```
Timeout waiting for network idle
解决方案: 增加WXCHAT_PDF_TIMEOUT配置值

Network connection lost
解决方案: 检查网络连接，增加重试次数

SFTP connection timeout
解决方案: 检查SFTP服务器状态和网络连接
```

### 7.3 调试方法

**启用调试日志：**
```bash
# 修改.env文件
LOG_LEVEL=DEBUG

# 或命令行指定
LOG_LEVEL=DEBUG python main.py --wxchat --wxchat-days 1
```

**单篇文章调试：**
```bash
# 修改processor.py中的days参数为较小值
# 或手动指定测试文章ID进行调试
```

**数据库查询调试：**
```sql
-- 检查特定文章的处理状态
SELECT * FROM wx_article WHERE article_id = 'specific_article_id';

-- 检查是否有重复记录
SELECT article_id, COUNT(*) as count 
FROM wx_article 
GROUP BY article_id 
HAVING count > 1;
```

**网络连接测试：**
```bash
# 测试微信文章服务器连接
curl -I https://mp.weixin.qq.com/s/test_article_id

# 测试SFTP连接
sftp -P 22 sftp01@192.168.0.122

# 测试数据库连接
mysql -h localhost -u root -p -e "SHOW DATABASES;"
```

## 8. 注意事项和最佳实践

### 8.1 性能优化

**建议配置：**
```bash
# 生产环境推荐配置
WXCHAT_PDF_TIMEOUT=90           # 适当增加超时时间
WXCHAT_IMAGE_WAIT_TIME=25       # 确保图片完全加载
WXCHAT_DOWNLOAD_DELAY=8         # 更保守的延迟策略
WXCHAT_MAX_DAYS=30              # 合理的查询范围
```

**性能优化建议：**
- 避免处理过长时间范围的文章，建议不超过30天
- 在低峰期运行大量文章处理任务
- 合理设置延迟参数，平衡处理速度和反限流需求
- 定期清理数据库中的历史错误记录

**批处理策略：**
```bash
# 分批处理大量文章
python main.py --wxchat --wxchat-days 7   # 先处理最近7天
python main.py --wxchat --wxchat-days 14  # 再处理7-14天
python main.py --wxchat --wxchat-days 30  # 最后处理14-30天
```

### 8.2 安全建议

**配置文件安全：**
```bash
# 确保.env文件不在版本控制中
echo ".env" >> .gitignore

# 设置适当的文件权限
chmod 600 .env

# 使用强密码
# 定期更换数据库密码
```

**数据库安全：**
```sql
-- 使用专用数据库用户，限制权限
CREATE USER 'wxchat_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE ON test.wx_article TO 'wxchat_user'@'localhost';
GRANT SELECT ON test.wx_account TO 'wxchat_user'@'localhost';

-- 定期备份数据
mysqldump -u root -p test wx_article > backup_wx_article.sql
```

**网络安全：**
```bash
# 使用SSH隧道连接远程数据库
ssh -L 3307:remote-db-server:3306 user@remote-server

# 限制SFTP访问IP
# 配置防火墙规则
```

### 8.3 使用建议

**定时任务建议：**
- 每天凌晨处理昨天的文章，避免高峰期
- 设置合理的邮件或通知告警
- 定期检查日志文件大小，及时清理

**数据库维护：**
```sql
-- 定期清理过期的错误记录
DELETE FROM wx_article 
WHERE error_message IS NOT NULL 
AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- 优化表性能
OPTIMIZE TABLE wx_article;
OPTIMIZE TABLE wx_account;

-- 检查表结构
SHOW TABLE STATUS LIKE 'wx_article';
```

**故障恢复：**
```bash
# 定期备份配置文件
cp .env .env.backup

# 定期备份数据库
mysqldump -u root -p test > backup_test_$(date +%Y%m%d).sql

# 保留处理日志
cp logs/transfer.log logs/transfer_$(date +%Y%m%d).log
```

**监控告警建议：**
```bash
# 设置处理成功率告警
# 当成功率低于90%时发送通知

# 设置错误数量告警
# 当错误数量超过10时发送通知

# 设置处理时间告警
# 当处理时间过长时发送通知
```

---

## 附录

### A. 完整配置示例

```bash
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=123456
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=test

# ===== 微信公众号配置 =====
WXCHAT_ENABLED=true
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=123456
WXCHAT_WEWE_DB_NAME=wewe_rss
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20
WXCHAT_DOWNLOAD_DELAY=5
WXCHAT_MAX_DAYS=30

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

### B. 常用命令参考

```bash
# 基本处理命令
python main.py --wxchat                           # 处理最近3天文章
python main.py --wxchat --wxchat-days 7         # 处理最近7天文章
python main.py --wxchat --wxchat-sync-accounts  # 仅同步账号

# 日志查看命令
tail -f logs/transfer.log                       # 实时查看日志
grep "处理完成" logs/transfer.log                # 查看处理结果
grep "ERROR" logs/transfer.log                   # 查看错误信息

# 数据库查询命令
mysql -u root -p test -e "SELECT COUNT(*) FROM wx_article;"
mysql -u root -p test -e "SELECT * FROM wx_article ORDER BY processed_at DESC LIMIT 10;"

# 系统维护命令
mysqldump -u root -p test > backup.sql          # 备份数据库
mysql -u root -p test < backup.sql              # 恢复数据库
```

### C. 技术支持

**问题反馈：**
- 遇到问题时，请提供详细的错误日志
- 包含配置信息（隐藏敏感信息）
- 说明操作系统和环境信息

**调试信息收集：**
```bash
# 收集系统信息
python --version
pip list | grep -E "playwright|pymysql|click"
mysql --version

# 收集配置信息
cat .env | grep -v "PASSWORD\|SECRET"

# 收集日志信息
tail -100 logs/transfer.log
```

---

**文档版本**: 1.0  
**最后更新**: 2026-07-28  
**适用系统版本**: v1.2.0+