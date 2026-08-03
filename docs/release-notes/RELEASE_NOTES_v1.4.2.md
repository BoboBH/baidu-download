# 百度网盘PDF文件自动传输系统 v1.4.2 发布说明

## 📦 发布信息
- **版本号**: v1.4.2
- **发布日期**: 2026-08-03
- **包名称**: baidu-download-v1.4.2-default-extraction-code-fix.zip
- **包大小**: 234MB

## 🎯 本次更新重点

### ✅ **核心修复：默认提取码支持**
**问题描述**: 百度网盘转存到个人目录失败

**根本原因**: 消息解析器无法处理缺少明确提取码的消息，导致消息被过滤

**修复内容**:
- ✅ 增强消息解析器，支持使用默认提取码 `MESSAGE_DEFAULT_EXTRACTION_CODE=0409`
- ✅ 添加第3级备用解析逻辑：当消息中只有链接但缺少提取码时，自动使用默认提取码
- ✅ 保持向后兼容：仍支持包含明确提取码的标准格式消息

**技术细节**:
- 修改文件：`src/feishu/message_parser.py`
- 新增通用链接格式识别：`https://pan.baidu.com/s/[A-Za-z0-9_-]+`
- 自动填充配置的默认提取码 `0409`

## 🚀 功能特性

### 消息解析支持
1. **钉钉格式**: `260723：https://pan.baidu.com/s/...` → 提取码: `260723`
2. **飞书格式**: `提取码 260723\n链接：https://...` → 提取码: `260723`  
3. **通用链接格式**: `https://pan.baidu.com/s/...` → 提取码: `0409` (默认) ✨ 新增

### 系统功能
- ✅ 百度网盘文件自动下载和传输
- ✅ SFTP文件上传
- ✅ 飞书/钉钉消息自动处理
- ✅ 微信公众号文章PDF生成
- ✅ 数据库记录和处理状态跟踪
- ✅ 钉钉通知推送

## 📋 包含文件

```
baidu-download-v1.4.2-default-extraction-code-fix.zip
├── baidu-download.exe          # 主程序 (230MB)
├── BaiduPCS-Go.exe             # 百度网盘CLI工具 (13MB)
├── .env.example                 # 配置文件模板
├── database/                    # 数据库脚本
│   └── wxchat_tables.sql       # 微信文章表结构
└── middle/                      # 初始化脚本
```

## 🔧 使用说明

### 1. 解压和配置
```bash
# 解压到目标目录
unzip baidu-download-v1.4.2-default-extraction-code-fix.zip
cd release/dist

# 复制配置文件
cp .env.example .env

# 编辑配置文件，设置必要参数
notepad .env
```

### 2. 关键配置项
```env
# 百度网盘配置
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt

# 默认提取码 (新增功能)
MESSAGE_DEFAULT_EXTRACTION_CODE=0409

# SFTP服务器配置
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=123456
SFTP_REMOTE_PATH=/sftp01/upload

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=test
```

### 3. 运行方式

#### 自动模式 (推荐)
```bash
# 自动接收并处理飞书消息
baidu-download.exe --auto
```

#### 分离模式
```bash
# 步骤1: 接收消息
baidu-download.exe --receive-messages

# 步骤2: 处理待处理消息
baidu-download.exe --process-pending
```

#### 手动模式
```bash
baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "0409" --folder "test"
```

#### 微信模式
```bash
# 处理微信公众号文章
baidu-download.exe --wxchat --wxchat-days 7
```

## 🐛 测试验证

### 消息解析测试
所有测试用例通过：
- ✅ 标准钉钉格式解析
- ✅ 标准飞书格式解析  
- ✅ 纯链接格式 (使用默认提取码)
- ✅ 链接带文字格式 (使用默认提取码)
- ✅ 无效消息正确过滤

### 功能测试
- ✅ 可执行文件正常运行
- ✅ 帮助信息正确显示
- ✅ 配置文件正确加载
- ✅ 默认提取码配置生效

## 🔄 升级说明

### 从 v1.4.1 升级
1. 停止正在运行的程序
2. 替换 `baidu-download.exe`
3. 检查 `.env` 文件中是否包含 `MESSAGE_DEFAULT_EXTRACTION_CODE=0409`
4. 重启程序

### 配置文件更新
如果旧配置文件缺少默认提取码设置，请添加：
```env
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
```

## ⚠️ 重要提示

### 首次运行
- **百度网盘登录**: 需要提供有效的 `baidu-cookies.txt` 文件
- **数据库初始化**: 首次运行会自动创建数据库表
- **Playwright浏览器**: 微信功能首次运行会自动下载Chromium

### Cookies文件获取
1. 浏览器登录百度网盘
2. 开发者工具 → Application → Cookies
3. 复制所有相关Cookie到 `baidu-cookies.txt`

### 系统要求
- Windows 10/11
- 网络连接
- 足够的磁盘空间 (推荐 1GB+)

## 📞 技术支持

如有问题，请检查：
1. 日志文件：`logs/transfer.log`
2. 配置文件：`.env` 
3. 数据库连接：MySQL服务是否运行
4. 网络连接：SFTP和百度网盘API访问

## 📝 版本历史

### v1.4.2 (2026-08-03)
- ✨ 新增默认提取码支持功能
- 🐛 修复消息解析器缺少提取码时的处理问题
- ✅ 增强消息格式兼容性

### v1.4.1 (之前版本)
- 微信公众号文章PDF生成
- 外部SFTP支持
- 钉钉消息接收

---

**制作**: baidu-download team  
**构建**: PyInstaller 6.21.0 + Python 3.8.10  
**测试**: Windows 11 Home China 10.0.26200