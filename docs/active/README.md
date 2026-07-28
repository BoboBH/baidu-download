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

### 🔧 开发相关
- **[打包脚本](build/)** - 打包构建脚本和说明
- **[发布文件](release/)** - 最新发布版本和说明

## 🎯 核心功能

- ✅ **百度网盘集成** - 使用BaiduPCS-Go实现文件操作
- ✅ **自动下载** - 批量下载PDF文件到本地
- ✅ **SFTP上传** - 自动上传到指定SFTP服务器  
- ✅ **数据库日志** - 完整的MySQL数据库日志记录
- ✅ **错误处理** - 完善的重试机制和错误处理
- ✅ **临时文件管理** - 自动清理临时文件

## 💻 使用示例

```bash
# 基本使用
baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "docs"

# 详细日志
baidu-download.exe -l "链接" -c "码" -f "目录" --verbose

# 仅测试配置
baidu-download.exe -l "链接" -c "码" -f "目录" --dry-run
```

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

**v1.0.1** (2026-07-11)

### 主要特性
- 修复BaiduPCS-Go下载路径问题
- 优化文件查找算法  
- 改进错误处理机制
- 支持EXE单文件部署

---

**详细文档请查看 [docs/](docs/) 目录** 📚