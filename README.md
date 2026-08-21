# 百度网盘PDF文件自动传输系统

## 🚀 快速开始

### 📦 最新版本
- **EXE版本**: [release/baidu-download-v1.0.0-exe.zip](release/baidu-download-v1.0.0-exe.zip) ⭐ 推荐
- **Python版本**: [release/baidu-download-v1.0.0.zip](release/baidu-download-v1.0.0.zip)

### 🎯 快速部署
```bash
# 1. 下载EXE版本
unzip release/baidu-download-v1.0.0-exe.zip

# 2. 配置系统
copy .env.example .env
# 编辑.env文件填写配置

# 3. 初始化数据库  
mysql -u root -p < middle/db_init.sql

# 4. 运行程序
baidu-download.exe --link "分享链接" --code "提取码" --folder "目录名"
```

## 📚 完整文档

详细的文档和说明请查看 [docs/](docs/) 目录：

### 📋 主要文档
- **[快速开始](docs/QUICK_START.md)** - 5分钟快速部署指南
- **[使用说明](docs/README.md)** - 完整功能说明
- **[部署指南](docs/DEPLOYMENT.md)** - 详细部署步骤
- **[项目结构](docs/PROJECT_STRUCTURE.md)** - 项目架构说明
- **[版本更新](docs/CHANGELOG.md)** - 版本更新日志
- **[EXE测试](docs/HOW_TO_TEST_EXE.md)** - EXE文件测试指南

### 📱 功能专题文档
- **[微信文章处理](docs/active/wxchat-article-usage.md)** - 微信文章PDF自动生成和归档 ⭐ 新功能
- **[微信PDF处理](docs/wxchat_usage.md)** - 微信公众号文章PDF批量处理
- **[消息类型扩展](docs/active/MESSAGE_TYPE_EXTENSION_USER_GUIDE.md)** - 多消息类型支持指南

### 🔧 开发相关
- **[打包脚本](build/)** - 打包构建脚本和说明
- **[发布文件](release/)** - 最新发布版本和说明

## 🎯 核心功能

### 多消息类型支持 (v1.5.0+)
- ✅ **百度网盘集成** - 使用BaiduPCS-Go实现文件操作
- ✅ **PDF文件链接** - 自动识别和下载PDF文件链接
- ✅ **钉钉文件处理** - 支持钉钉群文件（PDF和ZIP）自动处理
- ✅ **微信文章处理** - 钉钉消息自动识别微信文章链接并生成PDF ⭐ 新功能
- ✅ **智能消息路由** - 基于优先级的自动消息类型识别
- ✅ **策略模式架构** - 可扩展的处理器设计

### 自动化处理
- ✅ **自动下载** - 批量下载PDF文件到本地
- ✅ **SFTP上传** - 自动上传到指定SFTP服务器  
- ✅ **数据库日志** - 完整的MySQL数据库日志记录
- ✅ **错误处理** - 完善的重试机制和错误处理
- ✅ **临时文件管理** - 自动清理临时文件
- ✅ **消息重试管理** - 智能重试限制，防止无限循环
- ✅ **分离式架构** - 消息接收与文件处理独立执行
- ✅ **智能文件名处理** - 自动处理超长文件名问题
- ✅ **PDF质量保证** - 使用Playwright + Chromium确保高质量PDF生成

## 💻 使用示例

```bash
# 基本使用
baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "docs"

# 详细日志
baidu-download.exe -l "链接" -c "码" -f "目录" --verbose

# 仅测试配置
baidu-download.exe -l "链接" -c "码" -f "目录" --dry-run
```

### 接收钉钉消息

```bash
# 接收钉钉消息
python main.py --receive-messages --source dingtalk

# 接收钉钉消息（详细日志）
python main.py --receive-messages --source dingtalk --verbose
```

### 消息来源说明

系统支持两种消息来源：
- **飞书（feishu）**：默认来源，通过飞书群接收消息
- **钉钉（dingtalk）**：新增支持，通过钉钉群接收消息

消息会自动识别来源，并在数据库中通过 `source` 字段区分。

## 🛠️ 系统要求

### EXE版本 (推荐)
- Windows 11 或更高版本
- MySQL 5.7 或更高版本  
- BaiduPCS-Go v4.0.1 或更高版本

### Python版本
- Python 3.8 或更高版本
- MySQL 5.7 或更高版本
- BaiduPCS-Go v4.0.1 或更高版本

## 📞 技术支持

### 📚 完整文档
- **[docs/](docs/)** - 文档中心
- **[docs/QUICK_START.md](docs/QUICK_START.md)** - 5分钟快速开始
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - 详细部署指南
- **[docs/PACKAGING_RULES.md](docs/PACKAGING_RULES.md)** - 打包规则 ⭐

### 🔧 开发工具
- **[build/](build/)** - 编译打包工具
- **[PACKAGING_RULES_SUMMARY.md](PACKAGING_RULES_SUMMARY.md)** - 打包规则总结
- **[update_version.py](update_version.py)** - 版本管理
- **[full_release.py](build/full_release.py)** - 完整打包

### 🧪 测试工具
- **[diagnose_sftp.py](diagnose_sftp.py)** - SFTP诊断
- **[interactive_sftp_test.py](interactive_sftp_test.py)** - 凭证测试

## 📊 当前版本

**v1.4.6** (2026-08-19)

### 主要特性
- 🔥 消息验证增强：拒绝8位数字格式，只接受6位数字（YYMMDD）
- ✨ 增强正则表达式，确保6位数字独立匹配
- 🎯 消息重试限制功能：防止失败消息无限重试（v1.2.0+）
- 📊 分离式架构：消息接收与文件处理独立执行（v1.2.0+）
- 🔧 智能文件名处理：解决超长文件名问题（v1.1.0+）
- ✅ 完善的重试机制和错误处理
- 🚀 支持EXE单文件部署

### 最新功能 (v1.2.0+)

**消息重试管理系统:**
- ✅ 可配置重试限制（`MESSAGE_MAX_RETRIES`，默认10次）
- ✅ 自动重试计数和智能消息过滤
- ✅ 防止无限循环，提升系统稳定性
- 📊 详见：[版本更新日志](docs/active/CHANGELOG.md#v120-2026-07-24)

---

**详细文档请查看 [docs/](docs/) 目录** 📚