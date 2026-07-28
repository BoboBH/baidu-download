# 部署指南

## 📦 百度网盘PDF文件自动传输系统 v1.0.0

### 🚀 快速部署

#### 1. 环境准备

##### 1.1 安装Python 3.8+
```bash
# 检查Python版本
python --version
```

##### 1.2 安装MySQL 5.7+
```bash
# 检查MySQL服务
mysql --version
```

##### 1.3 下载BaiduPCS-Go
**注意**: EXE 发布版本已包含 BaiduPCS-Go.exe，无需单独下载。

如需开发环境或单独下载:
1. 访问: https://github.com/qjfoidnh/BaiduPCS-Go/releases
2. 下载 Windows x64 版本
3. 解压到: `D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/`

#### 2. 项目部署

##### 方案A: EXE版本部署 (推荐) ⭐

**适用场景**: 快速部署，无需Python环境

###### 2.A.1 解压EXE发布包
```bash
# 解压 baidu-download-v1.0.0-exe.zip 到目标目录
# 例如: D:\baidu-download\
```

###### 2.A.2 检查文件完整性
确保以下文件在同一目录中:
```bash
dir D:\baidu-download\
# 应该看到:
# - baidu-download.exe      (主程序)
# - BaiduPCS-Go.exe         (百度网盘工具，已包含)
# - .env                    (配置文件，已包含)
# - .env.example            (配置模板)
# - DEPLOYMENT.md           (部署指南)
# - db_init.sql            (数据库脚本)
```

###### 2.A.3 配置系统
直接跳转到 **第3步: 配置系统**

##### 方案B: Python版本部署

##### 2.1 解压安装包
```bash
# 解压 baidu-download-v1.0.0.zip 到目标目录
# 例如: D:\baidu-download\
```

##### 2.2 创建Python虚拟环境
```bash
cd D:\baidu-download
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

##### 2.3 安装Python依赖
```bash
pip install -r requirements.txt
```

#### 3. 配置系统

#### 3. 配置系统

##### 3.1 EXE版本配置 (方案A) ⭐

###### 配置文件说明
EXE版本已包含预配置的 `.env` 文件，默认使用相对路径:
```ini
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe  # 相对路径，指向同目录下的工具
```

###### 编辑配置文件
```bash
# 编辑 .env 文件，设置必要的配置
notepad .env
```

需要修改的主要配置:
```ini
# SFTP服务器配置
SFTP_HOST=your_sftp_server
SFTP_PORT=22
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/upload/path

# MySQL数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=baidu_download
```

##### 3.2 Python版本配置 (方案B)
```bash
# 复制配置模板
copy .env.example .env
```

###### 创建配置文件
```bash
# 复制配置模板
copy .env.example .env
```

###### 编辑配置文件
编辑 `.env` 文件，配置以下参数：

```ini
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password_here
DB_NAME=baidu_download

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

##### 3.3 配置百度网盘Cookie (通用)
编辑 `.env` 文件，配置以下参数：

```ini
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password_here
DB_NAME=baidu_download

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

##### 3.3 配置百度网盘Cookie
创建 `baidu-cookies.txt` 文件：

```bash
# 通过浏览器获取百度网盘Cookie
# 1. 登录百度网盘网页版
# 2. 打开浏览器开发者工具 (F12)
# 3. 进入 Application -> Cookies -> https://pan.baidu.com
# 4. 复制以下Cookie值到文件中
```

Cookie文件格式：
```
BAIDUID=your_baiduid_value
BDUSS=your_bduss_value
STOKEN=your_stoken_value
```

#### 4. 数据库初始化

##### 4.1 创建数据库
```bash
# 登录MySQL
mysql -u root -p

# 执行初始化脚本
source D:/baidu-download/middle/db_init.sql
```

##### 4.2 验证数据库
```sql
USE baidu_download;
SHOW TABLES;
-- 应该看到: file_transfer_log, execution_summary
```

#### 5. 测试运行

##### 5.1 EXE版本测试 (方案A) ⭐
```bash
# 测试配置是否正确
baidu-download.exe --link "测试链接" --code "测试码" --folder "test" --dry-run
```

##### 5.2 Python版本测试 (方案B)
```bash
# 测试配置是否正确
python main.py --link "测试链接" --code "测试码" --folder "test" --dry-run
```

###### 配置测试
```bash
# 测试配置是否正确
python main.py --link "测试链接" --code "测试码" --folder "test" --dry-run
```

###### 完整测试
```bash
# 运行完整测试
python main.py --link "分享链接" --code "提取码" --folder "test_files" --verbose
```

#### 6. 故障排查

##### 6.1 常见问题

**问题**: BaiduPCS-Go not found
```bash
# EXE版本解决方案:
# 1. 检查 BaiduPCS-Go.exe 是否与 baidu-download.exe 在同一目录
# 2. 验证 .env 中的路径: BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe

# Python版本解决方案:
# 1. 检查 .env 中的 BAIDUPCS_GO_PATH 配置
# 2. 确保文件路径使用正斜杠 / 而不是反斜杠 \
# 3. 确认 BaiduPCS-Go.exe 文件存在
```
```bash
# 解决方案: 检查BAIDUPCS_GO_PATH配置是否正确
# 确保文件路径使用正斜杠 / 而不是反斜杠 \
```

**问题**: 数据库连接失败
```bash
# 解决方案:
# 1. 检查MySQL服务是否启动
# 2. 验证DB_HOST, DB_PORT, DB_USER, DB_PASSWORD配置
# 3. 确保数据库baidu_download已创建
```

**问题**: SFTP连接失败
```bash
# 解决方案:
# 1. 使用交互式测试工具确认凭证
python interactive_sftp_test.py

# 2. 检查SFTP服务器是否可访问
# 3. 验证用户名和密码是否正确
```

**问题**: Cookie认证失败
```bash
# 解决方案:
# 1. 重新获取百度网盘Cookie
# 2. 确保Cookie格式正确
# 3. 检查Cookie是否过期
```

##### 6.2 日志查看
```bash
# 查看日志文件
type logs\transfer.log

# 查看最后几行
powershell Get-Content logs\transfer.log -Tail 50
```

#### 7. 生产环境部署

##### 7.1 EXE版本优势 ⭐

**为什么推荐使用EXE版本**:
1. **开箱即用**: 无需Python环境和依赖安装
2. **包含完整工具**: BaiduPCS-Go.exe 已自动包含
3. **预配置**: .env 文件已配置好相对路径
4. **简化部署**: 解压即可使用，适合生产环境

**适用场景**:
- 生产环境部署
- 快速测试和验证
- 无Python环境的机器
- 自动化运维部署

#### 7.2 安全建议
1. 不要将.env文件提交到版本控制系统
2. 定期更新百度网盘Cookie
3. 使用强密码保护SFTP和MySQL
4. 限制数据库用户权限

##### 7.2 性能优化
1. 调整MAX_RETRIES参数优化重试机制
2. 修改CONCURRENT_UPLOADS提升并发性能
3. 定期清理数据库日志记录
4. 监控磁盘空间使用情况

##### 7.3 监控和维护
1. 定期检查日志文件
2. 监控传输成功率
3. 定期清理临时文件
4. 备份数据库数据

### 📋 文件结构

```
# EXE版本发布包结构:
baidu-download-v1.0.0-exe/
├── baidu-download.exe              # 主程序 ⭐
├── BaiduPCS-Go.exe                 # 百度网盘工具 ⭐ 已包含
├── .env                            # 配置文件 ⭐ 已包含
├── .env.example                     # 配置模板
├── README.md                        # 使用说明
├── CHANGELOG.md                     # 版本更新日志
├── DEPLOYMENT.md                    # 部署指南
├── QUICK_START.md                   # 快速开始
├── db_init.sql                     # 数据库初始化脚本
└── 工具脚本/
    ├── diagnose_sftp.py            # SFTP诊断工具
    └── interactive_sftp_test.py    # 交互式测试工具

# Python版本项目结构:
baidu-download-v1.0.0/
├── main.py                      # 主程序入口
├── requirements.txt             # Python依赖包
├── .env.example                 # 配置文件模板
├── README.md                    # 使用说明
├── CHANGELOG.md                 # 版本更新日志
├── DEPLOYMENT.md                # 部署指南
│
├── middle/                      # 中间文件
│   └── db_init.sql             # 数据库初始化脚本
│
├── src/                         # 源代码目录
│   ├── config/                  # 配置模块
│   ├── downloader/              # 下载模块
│   ├── uploader/                # 上传模块
│   ├── database/                # 数据库模块
│   ├── processor/               # 处理模块
│   └── utils/                   # 工具模块
│
└── 工具脚本/
    ├── diagnose_sftp.py        # SFTP诊断工具
    └── interactive_sftp_test.py # 交互式SFTP测试
```

### 🎯 使用示例

#### EXE版本基本使用 ⭐
```bash
# 传输单个分享链接的文件
baidu-download.exe --link "https://pan.baidu.com/s/1ABC123" --code "1234" --folder "test_files"
```

#### Python版本基本使用
```bash
# 传输单个分享链接的文件
python main.py --link "https://pan.baidu.com/s/1ABC123" --code "1234" --folder "test_files"
```

#### EXE版本详细日志模式 ⭐
```bash
# 使用verbose模式查看详细日志
baidu-download.exe -l "分享链接" -c "提取码" -f "目录名" --verbose
```

#### Python版本详细日志模式
```bash
# 使用verbose模式查看详细日志
python main.py -l "分享链接" -c "提取码" -f "目录名" --verbose
```

#### EXE版本测试配置 ⭐
```bash
# 仅测试配置，不实际执行传输
baidu-download.exe -l "分享链接" -c "提取码" -f "目录名" --dry-run
```

#### Python版本测试配置
```bash
# 仅测试配置，不实际执行传输
python main.py -l "分享链接" -c "提取码" -f "目录名" --dry-run
```

### 🔗 相关链接

- [BaiduPCS-Go下载](https://github.com/qjfoidnh/BaiduPCS-Go)
- [Python下载](https://www.python.org/downloads/)
- [MySQL下载](https://dev.mysql.com/downloads/mysql/)

### 💡 技术支持

如遇问题，请查看：
1. README.md - 完整使用说明
2. DEPLOYMENT.md - 部署指南
3. 日志文件 - logs/transfer.log

---

**部署完成后，系统即可自动处理百度网盘PDF文件的传输！** 🚀