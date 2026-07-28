# 百度网盘PDF文件自动传输系统 v1.2.0 - 快速启动指南

## 📦 文件说明

### 核心文件
- `baidu-download.exe` - 主程序（新版本 v1.2.0）
- `BaiduPCS-Go.exe` - 百度网盘命令行工具
- `baidu-cookies.txt` - 百度网盘登录cookie
- `.env.example` - 配置文件模板

### 支持文件
- `README.txt` - 详细使用说明
- `QUICKSTART.md` - 本快速启动指南
- `middle/db_init.sql` - 数据库初始化脚本

## 🚀 快速启动（3步完成）

### 步骤1: 配置环境变量
```bash
# 复制配置模板
cp .env.example .env

# 编辑.env文件，填入你的配置信息
# 主要配置项：
# - FEISHU_APP_ID: 飞书应用ID
# - FEISHU_APP_SECRET: 飞书应用密钥
# - DINGTALK_WEBHOOK: 钉钉机器人webhook
# - DB_HOST, DB_USER, DB_PASSWORD, DB_NAME: 数据库配置
# - SFTP_HOST, SFTP_USER, SFTP_PASSWORD: SFTP配置
```

### 步骤2: 初始化数据库
```bash
# 连接到MySQL数据库执行初始化脚本
mysql -u your_user -p your_database < middle/db_init.sql
```

### 步骤3: 启动程序
```bash
# 测试配置
baidu-download.exe --help

# 新的分离式架构使用方法
baidu-download.exe --receive-messages    # 专职接收飞书消息
baidu-download.exe --process-pending     # 专职处理待处理消息

# 原有功能仍然可用
baidu-download.exe --auto                # 一站式自动模式
baidu-download.exe --link "分享链接" -c "提取码" -f "目录名"  # 手动模式
```

## 🆕 v1.2.0 新功能

### 分离式架构
- **接收模式** (`--receive-messages`): 专职收取飞书消息，解析并记录到数据库
- **处理模式** (`--process-pending`): 专职处理待处理消息，执行下载和上传
- **保留原有功能**: `--auto`模式、手动模式完整保留

### 生产环境推荐部署
```bash
# Windows定时任务1: 每小时接收消息
schtasks /create /tn "百度下载-接收消息" /tr "baidu-download.exe --receive-messages" /sc hourly

# Windows定时任务2: 每2小时处理消息
schtasks /create /tn "百度下载-处理消息" /tr "baidu-download.exe --process-pending" /sc hourly /mo 2
```

## 📋 配置检查清单

使用前请确认以下配置：

### ✅ 飞书配置
- [ ] FEISHU_APP_ID 已配置
- [ ] FEISHU_APP_SECRET 已配置
- [ ] FEISHU_TENANT_URL 正确（如: https://open.feishu.cn/open-apis/）

### ✅ 数据库配置
- [ ] MySQL数据库已创建
- [ ] db_init.sql 已执行
- [ ] DB_HOST, DB_USER, DB_PASSWORD, DB_NAME 正确

### ✅ 钉钉通知配置
- [ ] DINGTALK_WEBHOOK 已配置
- [ ] 测试钉钉通知是否正常

### ✅ SFTP配置
- [ ] SFTP_HOST, SFTP_PORT 正确
- [ ] SFTP_USER, SFTP_PASSWORD 正确
- [ ] SFTP_UPLOAD_DIR 正确（如: /sftp01/upload/）

### ✅ 百度网盘配置
- [ ] baidu-cookies.txt 文件存在且有效
- [ ] BaiduPCS-Go.exe 可正常执行

## 🔍 故障排除

### 问题1: 数据库连接失败
```bash
# 检查数据库配置
# 确认MySQL服务正在运行
# 测试连接: mysql -h host -u user -p
```

### 问题2: 飞书API调用失败
```bash
# 检查飞书应用ID和密钥
# 确认网络连接正常
# 查看日志文件: logs/baidu-download.log
```

### 问题3: 文件下载失败
```bash
# 检查baidu-cookies.txt是否有效
# 确认百度网盘分享链接和提取码正确
# 查看详细日志: baidu-download.exe --auto --verbose
```

### 问题4: SFTP上传失败
```bash
# 测试SFTP连接
# 确认上传目录存在且有写入权限
# 检查SFTP服务器状态
```

## 📞 技术支持

- 详细文档: `README.txt`
- 配置模板: `.env.example`
- 日志文件: `logs/baidu-download.log`

## ⚡ 性能优化建议

1. **定时策略**: 接收消息每小时一次，处理消息每2小时一次
2. **批量处理**: process-pending模式一次处理所有待处理消息
3. **监控日志**: 定期检查logs目录中的日志文件
4. **数据库维护**: 定期清理已处理的历史消息

---

**版本**: v1.2.0 | **发布时间**: 2026-07-24 | **架构**: 分离式架构