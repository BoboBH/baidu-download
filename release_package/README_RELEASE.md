# 百度网盘PDF文件自动传输系统 - 微信功能版 v1.2.3

## 系统功能

本系统整合了**百度网盘文件传输**和**微信公众号文章PDF处理**两大功能：

### 核心功能
- 📥 **飞书/钉钉消息处理**: 自动接收并处理分享链接
- 📤 **SFTP自动上传**: 文件自动上传到SFTP服务器
- 📰 **微信文章处理**: 从wewe_rss数据库获取微信文章，生成PDF并上传
- 🔄 **智能去重**: 避免重复处理相同内容
- 📊 **统计监控**: 详细的处理日志和统计信息

## 快速开始

### 1. 环境准备

确保系统已安装：
- Windows 10/11
- MySQL数据库
- SFTP服务器
- （可选）wewe_rss系统（用于微信文章功能）

### 2. 配置文件

复制`.env.example`为`.env`并配置：

```bash
# 基础配置
SFTP_HOST=your_sftp_server
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/path/to/upload

# 数据库配置
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=test

# 微信功能配置（可选）
WXCHAT_ENABLED=false
# 如需启用微信功能，设置为true并配置wewe_rss数据库
```

### 3. 数据库初始化

```bash
# 创建基础数据库表
mysql -u root -p test < middle/db_init.sql

# 创建微信功能表（如启用微信功能）
mysql -u root -p test < wxchat_tables.sql
```

### 4. 运行程序

```bash
# 飞书消息处理
baidu-download.exe --auto

# 微信文章处理
baidu-download.exe --wxchat

# 查看帮助
baidu-download.exe --help
```

## 主要命令

### 飞书/钉钉功能
```bash
baidu-download.exe --auto                    # 自动处理模式
baidu-download.exe --receive-messages         # 接收消息
baidu-download.exe --process-pending          # 处理待处理消息
baidu-download.exe --dingtalk-service         # 启动钉钉服务
```

### 微信文章功能
```bash
baidu-download.exe --wxchat                   # 处理最近3天文章
baidu-download.exe --wxchat --wxchat-days 7   # 处理最近7天文章
baidu-download.exe --wxchat --wxchat-sync-accounts  # 同步账号
```

### 手动模式
```bash
baidu-download.exe --link "分享链接" --code "提取码" --folder "目录名"
```

## 目录结构

```
baidu-download-wxchat-v1.2.3/
├── baidu-download.exe           # 主程序
├── BaiduPCS-Go.exe              # 百度网盘工具
├── .env.example                 # 配置文件模板
├── wxchat_tables.sql            # 微信功能数据库表
├── README_WXCHAT.md             # 微信功能详细说明
├── QUICKSTART.md                # 快速开始指南
└── README.txt                   # 原功能说明
```

## 配置说明

### 必需配置
- `SFTP_HOST`: SFTP服务器地址
- `SFTP_USERNAME`: SFTP用户名
- `SFTP_PASSWORD`: SFTP密码
- `SFTP_REMOTE_PATH`: SFTP远程路径
- `DB_HOST`: 数据库主机
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码
- `DB_NAME`: 数据库名称

### 微信功能配置（可选）
如需使用微信文章处理功能，需要额外配置：
- `WXCHAT_ENABLED=true`
- `WXCHAT_WEWE_DB_HOST`: wewe_rss数据库地址
- `WXCHAT_WEWE_DB_USER`: wewe_rss数据库用户
- `WXCHAT_WEWE_DB_PASSWORD`: wewe_rss数据库密码
- `WXCHAT_WEWE_DB_NAME`: wewe_rss数据库名称

详细说明请参考 `README_WXCHAT.md`

## 依赖说明

### 自动包含
本程序已打包所有必需的Python依赖，无需额外安装：
- 数据库驱动
- SFTP客户端
- 配置管理
- 日志系统
- 消息处理

### 微信功能依赖
如需使用微信文章PDF功能，需要安装：
```bash
pip install playwright
playwright install chromium
```

## 日志和监控

### 日志文件
- 位置: `logs/transfer.log`
- 自动创建，按日期滚动
- 包含详细的处理信息和错误记录

### 监控数据库
```sql
-- 查看处理统计
SELECT COUNT(*), transfer_status FROM file_transfer_log GROUP BY transfer_status;

-- 查看微信文章处理统计
SELECT COUNT(*) as total, 
       COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed
FROM wx_article;
```

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查`.env`文件中的数据库配置
   - 确保数据库服务正在运行
   - 验证用户名和密码

2. **SFTP上传失败**
   - 检查SFTP服务器连接
   - 确认远程路径存在且有写权限
   - 验证用户名和密码

3. **微信PDF生成失败**
   - 确保已安装Playwright: `pip install playwright`
   - 安装浏览器: `playwright install chromium`
   - 检查wewe_rss数据库连接

## 技术支持

- 查看日志文件: `logs/transfer.log`
- 微信功能详细文档: `README_WXCHAT.md`
- 原功能文档: `README.txt`
- 快速开始指南: `QUICKSTART.md`

## 版本信息

- **版本**: v1.2.3
- **发布日期**: 2026-07-28
- **Python版本**: 3.8+
- **系统要求**: Windows 10/11

## 更新日志

### v1.2.3 (2026-07-28)
- ✨ 新增微信公众号文章PDF处理功能
- ✨ 新增wewe_rss数据库集成
- ✨ 新增Playwright浏览器PDF生成
- ✨ 新增SFTP按YYMM格式组织文件
- 🐛 修复配置验证问题
- 🐛 修复CLI集成兼容性问题
- ✅ 完整测试覆盖（53个测试）
- ✅ 完整用户文档

---

**注意事项**:
1. 首次使用请先配置`.env`文件
2. 确保数据库和SFTP服务可访问
3. 微信功能需要额外配置wewe_rss数据库
4. 建议定期检查日志文件监控系统运行状态