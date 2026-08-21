# 微信文章链接处理功能使用指南

## 1. 功能概述

### 1.1 系统功能

微信文章链接处理功能是自动化工具，用于从钉钉群消息中识别微信公众号文章链接，自动将文章转换为高质量PDF格式，并上传到SFTP服务器进行归档存储。

**核心功能：**
- 自动识别微信公众号文章链接
- 智能提取文章标题和公众号名称
- 高质量PDF生成，保留文章原格式和排版
- 自动上传到SFTP服务器归档
- 完整的处理状态记录和监控
- 支持钉钉群消息自动接收和处理

### 1.2 与wxchat PDF功能的区别

| 功能特性 | wxchat-article (本功能) | wxchat PDF (现有功能) |
|---------|------------------------|---------------------|
| **触发方式** | 钉钉群消息自动触发 | CLI命令主动执行 |
| **数据来源** | 钉钉群实时消息 | wewe_rss数据库 |
| **处理时机** | 实时处理（收到消息后） | 批量处理（定时任务） |
| **URL格式** | `https://mp.weixin.qq.com/s/xxx` | 内部文章ID |
| **消息类型** | `wxchat-article` | `wxchat` |
| **去重机制** | 基于文章ID哈希 | 基于数据库记录 |
| **适用场景** | 单篇文章即时处理 | 批量历史文章归档 |

### 1.3 主要特性

- **实时处理**: 收到钉钉消息后立即处理，无需等待定时任务
- **智能识别**: 自动从消息中识别微信文章链接
- **高质量PDF**: 使用Playwright + Chromium确保PDF质量
- **完整元数据**: 自动提取文章标题、公众号名称等元信息
- **自动归档**: 按年月组织PDF文件到SFTP服务器
- **错误处理**: 完善的错误处理和重试机制
- **消息反馈**: 处理结果自动反馈到钉钉群

## 2. 系统架构

### 2.1 技术栈

- **消息接收**: DingTalk Stream API
- **PDF生成**: Playwright + Chromium 浏览器
- **元数据提取**: BeautifulSoup + Requests
- **文件传输**: SFTP协议
- **数据库**: MySQL (消息记录和状态跟踪)
- **路由系统**: 统一处理器路由 (ProcessorRouter)

### 2.2 数据流程

```
用户在钉钉群发送微信文章链接
    ↓
钉钉Stream接收消息
    ↓
检查是否@机器人 (群聊必需)
    ↓
MessageParser识别消息类型
    ↓
提取微信文章URL和ID
    ↓
WxchatArticleProcessor处理：
  - 获取文章页面元数据
  - 提取标题和公众号名称
  - 生成PDF文件
  - 清理文件名
    ↓
SFTP上传到服务器
    ↓
更新处理状态到数据库
    ↓
发送处理结果反馈到钉钉群
```

### 2.3 组件关系

```
dingtalk_group_client.py (消息接收)
  ├── MessageParser (消息解析)
  │   └── 识别 wxchat-article 类型
  ├── ProcessorRouter (路由分发)
  │   └── WxchatArticleProcessor (核心处理)
  │       ├── download() (元数据提取)
  │       ├── process() (PDF生成)
  │       └── get_upload_files() (SFTP上传)
  └── DatabaseRepository (状态记录)
  └── DingtalkNotifier (反馈通知)
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
pip install pymysql click python-dotenv playwright requests beautifulsoup4 dingtalk-stream
```

### 3.2 数据库准备

**确保必要的表结构存在：**
```bash
# 使用现有的消息处理表
mysql -u root -p test < database/migrations/000_init_schema.sql

# 如果需要微信文章专用表，使用wxchat PDF功能的表结构
mysql -u root -p test < database/wxchat_tables.sql
```

**消息处理表结构（必需）：**
```sql
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(32) NOT NULL UNIQUE COMMENT '消息哈希值',
    original_message TEXT COMMENT '原始消息内容',
    share_link VARCHAR(500) COMMENT '分享链接',
    folder_name VARCHAR(255) COMMENT '文件夹名称',
    extraction_code VARCHAR(50) COMMENT '提取码',
    source VARCHAR(50) DEFAULT 'feishu' COMMENT '消息来源',
    message_type VARCHAR(50) DEFAULT 'baidupan' COMMENT '消息类型',
    raw_message TEXT COMMENT '原始消息JSON',
    process_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    processing_time_ms INT COMMENT '处理耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_message_hash (message_hash),
    INDEX idx_status (process_status),
    INDEX idx_type (message_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
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
/sftp01/upload/wxchat/
├── 202408/    # 按年月组织文件
├── 202409/
└── 202410/
```

### 3.4 钉钉应用配置

**创建钉钉机器人应用：**
1. 登录钉钉开放平台: https://open.dingtalk.com/
2. 创建企业内部应用机器人
3. 获取 AppKey 和 AppSecret
4. 设置消息接收地址（如使用Stream模式，无需设置）
5. 配置机器人权限和关键词

**在钉钉群中添加机器人：**
1. 进入群设置 → 群机器人 → 添加机器人
2. 选择刚创建的机器人
3. 设置机器人关键词（可选）

## 4. 配置文件设置

### 4.1 必需配置参数

在`.env`文件中配置以下必需参数：

```bash
# ===== 钉钉配置 =====
# 钉钉应用配置（必需）
DINGTALK_APP_KEY=your_app_key_here
DINGTALK_APP_SECRET=your_app_secret_here

# 钉钉反馈通知（可选，用于发送处理结果）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_sftp_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# 微信文章SFTP路径（可选，默认使用SFTP_REMOTE_PATH/wxchat）
WXCHAT_SFTP_REMOTE_PATH=/sftp01/upload/wxchat

# ===== 数据库配置 =====
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

# ===== 网络配置 =====
REQUEST_TIMEOUT=30              # HTTP请求超时（秒）

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

## 5. 使用方式

### 5.1 基本使用

**启动钉钉消息接收服务：**
```bash
# 启动服务
python src/feishu/dingtalk_group_client.py
```

**在钉钉群中发送微信文章链接：**
```
# 群聊消息格式（必须@机器人）
@机器人 https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ

# 私聊消息格式（无需@机器人）
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

### 5.2 支持的消息格式

**标准微信文章链接：**
```
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

**包含其他内容的消息：**
```
请看这篇文章：https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ，很有意思！
```

**多个链接（只处理第一个）：**
```
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
https://mp.weixin.qq.com/s/another_article_id
```

### 5.3 消息处理流程

**完整处理流程：**
1. **消息接收**: 钉钉Stream接收群消息
2. **@检查**: 群聊消息必须@机器人（私聊无需@）
3. **链接识别**: MessageParser识别微信文章链接
4. **去重检查**: 检查文章ID是否已处理
5. **元数据提取**: 获取文章标题和公众号名称
6. **PDF生成**: 使用Playwright生成高质量PDF
7. **SFTP上传**: 上传PDF到服务器
8. **状态记录**: 保存处理记录到数据库
9. **结果反馈**: 发送处理结果到钉钉群

### 5.4 处理结果反馈

**成功处理反馈：**
```
## 消息处理成功

**群聊**: 测试群
**消息**: https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
**状态**: 已记录到数据库，等待处理

已记录微信文章: QfzFNnLB88WFwD6bwSVSjQ
```

**失败处理反馈：**
```
## 消息处理失败

**群聊**: 测试群
**消息**: https://mp.weixin.qq.com/s/invalid_id
**原因**: 无法从页面提取文章标题

## 支持的消息格式

### 1. 百度网盘链接
```
https://pan.baidu.com/s/1aBcDeFgHiJkLmNoPqRsTu 提取码: 260723
```

### 2. PDF文件
直接上传PDF文件到群聊

### 3. PDF链接
```
https://example.com/document.pdf
```

### 4. ZIP文件
直接上传ZIP文件到群聊

### 5. 微信文章链接
```
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

请检查消息格式后重新发送。
```

## 6. 监控和日志

### 6.1 日志管理

**日志文件位置：**
```bash
# 默认日志文件位置
./logs/transfer.log

# 查看最新日志
tail -f logs/transfer.log

# 查看微信文章处理日志
grep "wxchat-article" logs/transfer.log
grep "微信文章" logs/transfer.log
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
grep "$(date +%Y-%m-%d)" logs/transfer.log | grep "微信文章"

# 查看错误信息
grep "ERROR.*微信文章" logs/transfer.log

# 查看处理统计
grep "微信文章处理完成" logs/transfer.log
```

### 6.2 数据库监控

**查看处理统计：**
```sql
-- 微信文章处理统计
SELECT 
    COUNT(*) as total_articles,
    COUNT(CASE WHEN process_status = 'completed' THEN 1 END) as processed,
    COUNT(CASE WHEN process_status = 'failed' THEN 1 END) as failed,
    COUNT(CASE WHEN process_status = 'pending' THEN 1 END) as pending
FROM message_process_log 
WHERE message_type = 'wxchat-article';

-- 处理成功率
SELECT 
    CONCAT(
        ROUND(
            COUNT(CASE WHEN process_status = 'completed' THEN 1 END) * 100.0 / 
            NULLIF(COUNT(*), 0), 2
        ), '%'
    ) as success_rate
FROM message_process_log 
WHERE message_type = 'wxchat-article';
```

**查看最近处理记录：**
```sql
-- 查看最近10条微信文章处理记录
SELECT 
    id,
    SUBSTRING(original_message, 1, 50) as message,
    process_status,
    retry_count,
    created_at,
    updated_at
FROM message_process_log 
WHERE message_type = 'wxchat-article'
ORDER BY created_at DESC 
LIMIT 10;

-- 查看今天的处理记录
SELECT 
    DATE(created_at) as process_date,
    COUNT(*) as count,
    COUNT(CASE WHEN process_status = 'completed' THEN 1 END) as success,
    COUNT(CASE WHEN process_status = 'failed' THEN 1 END) as failed
FROM message_process_log 
WHERE message_type = 'wxchat-article'
  AND created_at >= CURDATE()
GROUP BY DATE(created_at);
```

**查看错误记录：**
```sql
-- 查看所有失败的微信文章处理记录
SELECT 
    id,
    original_message,
    process_status,
    retry_count,
    created_at,
    updated_at
FROM message_process_log 
WHERE message_type = 'wxchat-article'
  AND process_status = 'failed'
ORDER BY created_at DESC;

-- 按错误类型统计
SELECT 
    process_status,
    COUNT(*) as count,
    AVG(processing_time_ms) as avg_time_ms
FROM message_process_log 
WHERE message_type = 'wxchat-article'
GROUP BY process_status
ORDER BY count DESC;
```

### 6.3 性能指标

**处理时间分析：**
```sql
-- 平均处理时间（按天统计）
SELECT 
    DATE(created_at) as process_date,
    COUNT(*) as article_count,
    AVG(processing_time_ms) as avg_time_ms,
    MAX(processing_time_ms) as max_time_ms,
    MIN(processing_time_ms) as min_time_ms
FROM message_process_log 
WHERE message_type = 'wxchat-article'
  AND processing_time_ms IS NOT NULL
GROUP BY DATE(created_at)
ORDER BY process_date DESC;
```

**SFTP存储统计：**
```bash
# 查看微信文章PDF文件数量
find /sftp01/upload/wxchat -name "*.pdf" | wc -l

# 查看存储空间使用
du -sh /sftp01/upload/wxchat

# 按月份统计PDF数量
find /sftp01/upload/wxchat -name "*.pdf" | cut -d'/' -f6 | cut -d'/' -f1 | sort | uniq -c
```

## 7. 故障排查

### 7.1 常见问题

**问题1：消息未处理**
```
现象: 发送消息后没有任何响应
可能原因:
  - 消息未@机器人（群聊必需）
  - 钉钉服务未启动
  - 链接格式不正确
  - 消息已被处理（去重）

解决方案:
  1. 确保群聊消息@机器人
  2. 检查钉钉服务状态: ps aux | grep dingtalk
  3. 验证链接格式: https://mp.weixin.qq.com/s/xxx
  4. 查看数据库是否已有记录
```

**问题2：PDF生成失败**
```
错误信息: PDF生成失败
可能原因: 
  - Playwright未正确安装
  - Chromium浏览器未安装
  - 网络连接问题
  - 文章URL无效或页面结构变化

解决方案:
  1. 检查Playwright安装: pip show playwright
  2. 重新安装浏览器: playwright install chromium
  3. 检查网络连接: ping mp.weixin.qq.com
  4. 验证文章URL有效性
```

**问题3：元数据提取失败**
```
错误信息: 无法从页面提取文章标题
可能原因:
  - 文章页面结构变化
  - 文章已被删除
  - 网络请求超时
  - 反爬虫机制

解决方案:
  1. 增加请求超时时间
  2. 检查文章是否可正常访问
  3. 更新BeautifulSoup解析逻辑
  4. 添加更多错误处理
```

**问题4：SFTP上传失败**
```
错误信息: SFTP上传失败
可能原因:
  - SFTP服务器连接失败
  - 权限不足
  - 磁盘空间不足
  - 网络问题

解决方案:
  1. 检查SFTP连接: sftp -P 22 sftp01@192.168.0.122
  2. 验证目标目录权限: ls -la /sftp01/upload/wxchat
  3. 检查磁盘空间: df -h
  4. 查看详细错误日志
```

### 7.2 错误信息

**配置相关错误：**
```
Missing required environment variable: DINGTALK_APP_KEY
解决方案: 检查.env文件中的钉钉配置

Invalid WXCHAT_PDF_TIMEOUT value: abc
解决方案: 确保参数值为数字且在有效范围内

WXCHAT_ENABLED must be set to 'true' in .env file
解决方案: 本功能不依赖此配置，可忽略
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

**消息处理错误：**
```
No parser matched message
解决方案: 检查消息格式是否包含正确的微信文章链接

Duplicate message hash detected
解决方案: 这是正常的去重机制，消息已被处理

Message type not supported by processor
解决方案: 检查ProcessorRouter是否正确注册了WxchatArticleProcessor
```

### 7.3 调试方法

**启用调试日志：**
```bash
# 修改.env文件
LOG_LEVEL=DEBUG

# 或命令行指定
LOG_LEVEL=DEBUG python src/feishu/dingtalk_group_client.py
```

**单篇文章调试：**
```bash
# 使用Python测试脚本
python -c "
from src.feishu.message_parser import MessageParser
parser = MessageParser()
result = parser.parse_message('https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ')
print(result)
"
```

**数据库查询调试：**
```sql
-- 检查特定文章的处理状态
SELECT * FROM message_process_log 
WHERE message_type = 'wxchat-article' 
  AND original_message LIKE '%QfzFNnLB88WFwD6bwSVSjQ%';

-- 检查是否有重复记录
SELECT message_hash, COUNT(*) as count 
FROM message_process_log 
WHERE message_type = 'wxchat-article'
GROUP BY message_hash 
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

### 8.1 使用建议

**消息发送建议：**
- 确保群聊消息@机器人，否则会被忽略
- 发送标准的微信文章链接格式
- 避免发送失效或删除的文章链接
- 一次消息只发送一个文章链接（避免混淆）

**处理时间建议：**
- PDF生成通常需要10-30秒，请耐心等待
- 处理时间与文章长度和图片数量相关
- 避免在高峰期频繁发送大量文章链接

**存储管理建议：**
- 定期清理SFTP服务器上的旧PDF文件
- 监控SFTP存储空间使用情况
- 按年月组织文件便于管理和查找

### 8.2 性能优化

**建议配置：**
```bash
# 生产环境推荐配置
WXCHAT_PDF_TIMEOUT=90           # 适当增加超时时间
WXCHAT_IMAGE_WAIT_TIME=25       # 确保图片完全加载
REQUEST_TIMEOUT=30              # HTTP请求超时
```

**性能优化建议：**
- 避免在短时间内发送大量文章链接
- 在低峰期处理大批量文章
- 合理设置超时参数，平衡处理速度和成功率
- 定期清理数据库中的历史记录

**批处理策略：**
```bash
# 如需处理大量历史文章，建议使用wxchat PDF功能
python main.py --wxchat --wxchat-days 7
```

### 8.3 安全建议

**配置文件安全：**
```bash
# 确保.env文件不在版本控制中
echo ".env" >> .gitignore

# 设置适当的文件权限
chmod 600 .env

# 使用强密码
# 定期更换敏感密码
```

**数据库安全：**
```sql
-- 使用专用数据库用户，限制权限
CREATE USER 'wxchat_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE ON test.message_process_log TO 'wxchat_user'@'localhost';

-- 定期备份数据
mysqldump -u root -p test message_process_log > backup_message_log.sql
```

**网络安全：**
```bash
# 使用SSH隧道连接远程数据库
ssh -L 3307:remote-db-server:3306 user@remote-server

# 限制SFTP访问IP
# 配置防火墙规则
```

### 8.4 监控告警建议

**设置监控指标：**
```bash
# 处理成功率告警
# 当成功率低于90%时发送通知

# 错误数量告警
# 当连续错误超过5次时发送通知

# 处理时间告警
# 当处理时间超过60秒时发送通知
```

**日志监控：**
```bash
# 监控错误日志
tail -f logs/transfer.log | grep ERROR

# 监控微信文章处理
tail -f logs/transfer.log | grep "微信文章"

# 统计处理结果
grep "微信文章处理完成" logs/transfer.log | wc -l
```

## 9. 示例和模板

### 9.1 完整配置示例

```bash
# ===== 钉钉配置 =====
DINGTALK_APP_KEY=ding_xxxxxxxxx
DINGTALK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxx

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=123456
SFTP_REMOTE_PATH=/sftp01/upload
WXCHAT_SFTP_REMOTE_PATH=/sftp01/upload/wxchat

# ===== 数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=test

# ===== PDF生成配置 =====
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20

# ===== 网络配置 =====
REQUEST_TIMEOUT=30

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log
```

### 9.2 使用示例

**基本使用示例：**
```
# 群聊消息
@机器人 https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ

# 私聊消息
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ

# 带说明文字的消息
这是一篇很好的技术文章：https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

**脚本启动示例：**
```bash
# 启动钉钉消息接收服务
nohup python src/feishu/dingtalk_group_client.py > logs/dingtalk.log 2>&1 &

# 查看服务状态
ps aux | grep dingtalk_group_client

# 停止服务
pkill -f dingtalk_group_client
```

### 9.3 监控脚本示例

**创建监控脚本 `monitor_wxchat_article.sh`:**
```bash
#!/bin/bash

# 监控微信文章处理统计
echo "=== 微信文章处理统计 ==="
mysql -u root -p123456 test -e "
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN process_status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN process_status = 'failed' THEN 1 END) as failed,
    COUNT(CASE WHEN process_status = 'pending' THEN 1 END) as pending
FROM message_process_log 
WHERE message_type = 'wxchat-article'
  AND created_at >= CURDATE();
"

# 查看最近的处理记录
echo "=== 最近10条处理记录 ==="
mysql -u root -p123456 test -e "
SELECT 
    id,
    SUBSTRING(original_message, 1, 40) as message,
    process_status,
    created_at
FROM message_process_log 
WHERE message_type = 'wxchat-article'
ORDER BY created_at DESC 
LIMIT 10;
"
```

**使用监控脚本：**
```bash
chmod +x monitor_wxchat_article.sh
./monitor_wxchat_article.sh
```

---

## 附录

### A. 微信文章链接格式说明

**标准格式：**
```
https://mp.weixin.qq.com/s/[article_id]
```

**参数说明：**
- `https://mp.weixin.qq.com/s/`: 固定前缀
- `[article_id]`: 文章唯一标识，通常为字母数字混合

**示例：**
```
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

### B. 支持的消息类型对比

| 消息类型 | 格式示例 | 触发方式 | 处理方式 |
|---------|---------|---------|---------|
| wxchat-article | `https://mp.weixin.qq.com/s/xxx` | 钉钉消息 | 实时PDF生成 |
| baidupan | `https://pan.baidu.com/s/xxx` | 钉钉消息 | 百度网盘下载 |
| pdf_link | `https://example.com/file.pdf` | 钉钉消息 | 直接下载PDF |
| dingtalk_pdf | 钉钉文件上传 | 钉钉文件 | 直接下载PDF |

### C. 常用命令参考

```bash
# 启动钉钉消息接收服务
python src/feishu/dingtalk_group_client.py

# 后台启动服务
nohup python src/feishu/dingtalk_group_client.py > logs/dingtalk.log 2>&1 &

# 查看日志
tail -f logs/transfer.log

# 查看微信文章处理日志
grep "微信文章" logs/transfer.log

# 数据库查询
mysql -u root -p test -e "SELECT * FROM message_process_log WHERE message_type = 'wxchat-article' ORDER BY created_at DESC LIMIT 10;"

# 系统维护
mysqldump -u root -p test message_process_log > backup.sql
```

### D. 技术支持

**问题反馈：**
- 遇到问题时，请提供详细的错误日志
- 包含配置信息（隐藏敏感信息）
- 说明文章URL和操作步骤
- 提供处理时间和其他相关信息

**调试信息收集：**
```bash
# 收集系统信息
python --version
pip list | grep -E "playwright|requests|beautifulsoup4|dingtalk-stream"

# 收集配置信息
cat .env | grep -v "PASSWORD\|SECRET"

# 收集日志信息
tail -100 logs/transfer.log
```

---

**文档版本**: 1.0  
**最后更新**: 2026-08-21  
**适用系统版本**: v1.3.0+  
**功能状态**: 已完成实现和测试