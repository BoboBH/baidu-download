# 百度网盘PDF文件自动传输系统

**版本：** 1.2.3  
**发布日期：** 2026-07-25  
**文件大小：** ~18 MB

---

## 🎯 功能简介

这是一个自动传输百度网盘PDF文件到SFTP服务器的工具，支持：

- **飞书消息接收**：自动从飞书群获取分享链接
- **钉钉消息接收**：支持钉钉群实时消息推送
- **自动下载上传**：自动下载PDF文件并上传到SFTP
- **智能文件名处理**：自动处理特殊字符和长文件名
- **消息去重**：基于哈希的消息去重机制

---

## 📦 包含文件

```
baidu-download-v1.2.3/
├── baidu-download.exe          # 主程序（18MB）
├── BaiduPCS-Go.exe            # 百度网盘CLI工具
├── .env.example                # 配置文件模板
├── baidu-cookies.txt          # 百度网盘Cookies模板
├── README.md                   # 本文件
├── QUICKSTART.md              # 快速入门指南
├── USAGE.md                    # 详细使用说明
└── VERSION_NOTES.md            # 版本更新说明
```

---

## 🚀 快速开始

### 1. 环境准备

**必需软件：**
- Windows 10/11
- MySQL 5.7+
- 网络连接

**无需安装Python**（已打包到exe中）

### 2. 配置设置

**重命名配置文件：**
```cmd
rename .env.example .env
```

**编辑 .env 文件：**
```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download

# 百度网盘配置
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_sftp_user
SFTP_PASSWORD=your_sftp_password
SFTP_REMOTE_PATH=/remote/path

# 钉钉配置（可选）
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret

# 飞书配置（可选）
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_CHAT_ID=your_chat_id
```

### 3. 初始化数据库

**创建数据库：**
```sql
CREATE DATABASE baidu_download;
```

**导入初始化脚本：**
```sql
-- 从源代码中的 middle/db_init.sql 导入表结构
```

### 4. 运行程序

**钉钉服务（实时接收）：**
```cmd
baidu-download.exe --dingtalk-service
```

**飞书自动模式：**
```cmd
baidu-download.exe --auto
```

**手动模式：**
```cmd
baidu-download.exe --link "分享链接" --code "提取码" --folder "目录名"
```

---

## 📱 使用方式

### 钉钉群消息（推荐）

**启动服务：**
```cmd
baidu-download.exe --dingtalk-service
```

**在钉钉群中发送：**
```
@机器人 260723：https://pan.baidu.com/s/xxx
```

**消息格式：**
- 提取码：6位数字（YYDDMM格式）
- 分隔符：中文冒号`：`或英文冒号`:`
- 百度网盘链接：标准 pan.baidu.com/s/ 格式

### 飞书群消息

**自动模式：**
```cmd
baidu-download.exe --auto
```

**分离模式：**
```cmd
# 步骤1：接收飞书消息
baidu-download.exe --receive-messages

# 步骤2：处理待处理消息
baidu-download.exe --process-pending
```

### 手动模式

```cmd
baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
```

---

## ⚙️ 配置说明

### .env 文件详解

**数据库配置（必需）：**
- `DB_HOST` - MySQL服务器地址
- `DB_PORT` - MySQL端口，默认3306
- `DB_USER` - 数据库用户名
- `DB_PASSWORD` - 数据库密码
- `DB_NAME` - 数据库名称

**百度网盘配置（必需）：**
- `BAIDUPCS_GO_PATH` - BaiduPCS-Go.exe路径
- `SFTP_HOST` - SFTP服务器地址
- `SFTP_PORT` - SFTP端口，默认22
- `SFTP_USERNAME` - SFTP用户名
- `SFTP_PASSWORD` - SFTP密码
- `SFTP_REMOTE_PATH` - SFTP远程路径

**钉钉配置（可选）：**
- `DINGTALK_APP_KEY` - 钉钉应用Key
- `DINGTALK_APP_SECRET` - 钉钉应用Secret

**飞书配置（可选）：**
- `FEISHU_APP_ID` - 飞书应用ID
- `FEISHU_APP_SECRET` - 飞书应用Secret
- `FEISHU_CHAT_ID` - 飞书群ID

**日志配置：**
- `LOG_LEVEL` - 日志级别（INFO/DEBUG/ERROR）
- `LOG_FILE` - 日志文件路径

---

## 🔧 故障排除

### 常见问题

**1. 程序启动失败**
- 检查 .env 文件配置是否正确
- 确认数据库服务运行正常
- 查看日志文件 logs/transfer.log

**2. 钉钉消息未接收**
- 确认机器人已在钉钉群中
- 消息必须@机器人才会处理
- 检查 DINGTALK_APP_KEY 和 SECRET 配置

**3. 数据库连接失败**
- 验证数据库配置参数
- 确认数据库用户权限
- 检查网络连接

**4. 文件上传失败**
- 检查 SFTP 配置是否正确
- 确认 SFTP 服务器连接
- 验证远程路径权限

---

## 📊 监控和维护

### 日志文件

**主日志文件：**
```
logs/transfer.log
```

**实时查看日志：**
```cmd
type logs\transfer.log
```

### 数据库检查

**查看最近的处理记录：**
```sql
SELECT * FROM message_process_log 
ORDER BY created_at DESC 
LIMIT 10;
```

**统计处理数量：**
```sql
SELECT 
    source,
    process_status,
    COUNT(*) as count
FROM message_process_log 
GROUP BY source, process_status;
```

---

## 🔒 安全建议

1. **配置文件安全**
   - 不要将包含真实密码的 .env 文件分享
   - 定期更换密钥和密码
   - 设置合适的文件权限

2. **网络安全**
   - 使用强密码
   - 限制数据库访问权限
   - 配置防火墙规则

3. **运行安全**
   - 使用专用服务账户运行
   - 定期更新程序版本
   - 监控日志文件

---

## 📞 技术支持

**详细使用说明：** 查看 `USAGE.md`  
**快速入门指南：** 查看 `QUICKSTART.md`  
**版本更新说明：** 查看 `VERSION_NOTES.md`

**问题反馈：**
- 查看日志文件 `logs/transfer.log`
- 检查配置文件 `.env`
- 验证数据库连接

---

## 🎉 开始使用

1. **重命名配置文件：** `.env.example` → `.env`
2. **编辑配置：** 填写必需的配置信息
3. **初始化数据库：** 创建数据库和表结构
4. **启动服务：** 选择合适的运行模式
5. **发送测试消息：** 在群中发送测试链接

**祝使用愉快！** 🚀

---

*百度网盘PDF文件自动传输系统 v1.2.3*  
*项目整理发布版 - 2026-07-25*