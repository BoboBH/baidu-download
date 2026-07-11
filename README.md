# 百度网盘PDF文件自动传输系统

## 项目概述

百度网盘PDF文件自动传输系统是一个自动化工具，专门用于从百度网盘分享链接中批量下载PDF文件，并自动上传到指定的SFTP服务器。该系统通过集成百度网盘API、SFTP协议和MySQL数据库，实现了文件传输的全程追踪、错误处理和日志记录，适用于需要将网盘资料批量迁移到企业内部服务器的场景。

### 主要特点

- **全自动化流程**: 从下载到上传全程自动化，无需人工干预
- **智能错误处理**: 失败文件自动跳过，支持重试机制，不影响整体流程
- **完整日志追踪**: 所有传输过程记录到MySQL数据库，便于审计和排错
- **批量文件处理**: 支持批量处理多个PDF文件，提高工作效率
- **Windows环境优化**: 专门针对Windows 11环境进行优化和测试

## 功能特性

### 核心功能

✅ **自动下载**: 从百度网盘分享链接自动下载PDF文件  
✅ **批量上传**: 批量上传文件到指定SFTP服务器  
✅ **数据库日志**: 详细的传输日志记录到MySQL数据库  
✅ **错误重试**: 支持可配置的重试机制，提高传输成功率  
✅ **临时文件管理**: 自动清理临时文件，节省磁盘空间  
✅ **状态追踪**: 实时追踪每个文件的传输状态  
✅ **执行摘要**: 提供整体执行情况的统计摘要  
✅ **并发控制**: 支持配置并发上传数量  

### 高级功能

✅ **配置验证**: 启动前验证配置文件正确性  
✅ **Dry-run模式**: 仅测试配置，不实际执行传输  
✅ **详细日志**: 支持verbose模式，显示详细日志信息  
✅ **目录自动管理**: 自动删除和创建目标目录  
✅ **文件类型过滤**: 自动识别并只处理PDF文件  

## 系统要求

### 硬件要求

- **操作系统**: Windows 11 或更高版本
- **内存**: 最低4GB RAM，推荐8GB以上
- **磁盘空间**: 根据传输文件大小而定，建议预留10GB以上临时空间
- **网络**: 稳定的网络连接，能够访问百度网盘和SFTP服务器

### 软件依赖

- **Python**: 3.8 或更高版本
- **MySQL**: 5.7 或更高版本
- **BaiduPCS-Go**: v4.0.1 或更高版本（百度网盘命令行工具）

### Python依赖包

```
paramiko>=2.12.0      # SFTP连接库
pymysql>=1.1.1       # MySQL数据库连接
python-dotenv>=1.0.1  # 环境变量管理
colorama==0.4.6       # 终端颜色输出
pytest==7.4.0         # 测试框架
pytest-mock==3.11.1   # 测试模拟工具
```

## 快速开始

### 1. 环境准备

#### 安装Python依赖

```bash
pip install -r requirements.txt
```

#### 安装BaiduPCS-Go

1. 下载BaiduPCS-Go工具：[官方发布页面](https://github.com/qjfoidnh/BaiduPCS-Go)
2. 解压到指定目录，例如：`D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/`
3. 确保可执行文件路径：`D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe`

#### 安装MySQL数据库

如果尚未安装MySQL：
1. 下载并安装MySQL Server
2. 创建数据库用户和权限

### 2. 项目配置

#### 复制配置文件

```bash
copy .env.example .env
```

#### 编辑配置文件

编辑`.env`文件，配置以下参数：

```ini
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_secure_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_password_here
DB_NAME=baidu_download

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

### 3. 数据库初始化

#### 执行初始化脚本

```bash
mysql -u root -p < middle/db_init.sql
```

或手动执行SQL：

```sql
CREATE DATABASE IF NOT EXISTS baidu_download
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE baidu_download;

-- 创建文件传输记录表
CREATE TABLE IF NOT EXISTS file_transfer_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_link VARCHAR(500) NOT NULL COMMENT '分享链接',
    extraction_code VARCHAR(20) NOT NULL COMMENT '提取码',
    folder_name VARCHAR(255) NOT NULL COMMENT '目录名称',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    transfer_status ENUM('pending', 'downloading', 'uploading', 'success', 'failed', 'skipped')
        DEFAULT 'pending' COMMENT '传输状态',
    error_message TEXT COMMENT '错误信息',
    start_time DATETIME COMMENT '开始时间',
    download_time DATETIME COMMENT '下载完成时间',
    upload_time DATETIME COMMENT '上传完成时间',
    file_size BIGINT COMMENT '文件大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    INDEX idx_share_link (share_link(255)),
    INDEX idx_folder_name (folder_name),
    INDEX idx_status (transfer_status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建执行摘要表
CREATE TABLE IF NOT EXISTS execution_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_link VARCHAR(500) NOT NULL,
    folder_name VARCHAR(255) NOT NULL,
    total_files INT DEFAULT 0 COMMENT '总文件数',
    success_count INT DEFAULT 0 COMMENT '成功数量',
    failed_count INT DEFAULT 0 COMMENT '失败数量',
    skipped_count INT DEFAULT 0 COMMENT '跳过数量',
    start_time DATETIME COMMENT '执行开始时间',
    end_time DATETIME COMMENT '执行结束时间',
    total_size BIGINT COMMENT '总文件大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4. 百度网盘Cookie配置

创建百度网盘Cookie文件`baidu-cookies.txt`：

```bash
# 通过浏览器获取百度网盘Cookie
# 1. 登录百度网盘网页版
# 2. 打开浏览器开发者工具 (F12)
# 3. 进入Application/Storage -> Cookies
# 4. 复制相关Cookie值到以下格式
```

Cookie文件格式示例：

```
# 必需的Cookie项
BAIDUID=xxxxx
BDUSS=xxxxx
STOKEN=xxxxx
```

### 5. 运行程序

#### 基本使用

```bash
python main.py --link "分享链接" --code "提取码" --folder "目录名"
```

#### 详细示例

```bash
# 传输单个分享链接的文件
python main.py --link "https://pan.baidu.com/s/1ABC123" --code "1234" --folder "test_files"

# 使用verbose模式查看详细日志
python main.py -l "https://pan.baidu.com/s/1ABC123" -c "1234" -f "test_files" --verbose

# 仅测试配置，不实际执行
python main.py -l "https://pan.baidu.com/s/1ABC123" -c "1234" -f "test_files" --dry-run
```

## 使用指南

### 命令行参数详解

| 参数 | 简写 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| `--link` | `-l` | 是 | 百度网盘分享链接 | `"https://pan.baidu.com/s/1ABC123"` |
| `--code` | `-c` | 是 | 分享链接提取码 | `"1234"` |
| `--folder` | `-f` | 是 | 目标目录名称 | `"test_files"` |
| `--config` | | 否 | 配置文件路径 | `"./custom.env"` |
| `--dry-run` | | 否 | 仅测试配置，不实际执行 | |
| `--verbose` | `-v` | 否 | 显示详细日志 | |

### 使用场景示例

#### 场景1：批量传输文档

```bash
python main.py \
  --link "https://pan.baidu.com/s/1ABC123XYZ" \
  --code "abcd" \
  --folder "finance_reports_2024" \
  --verbose
```

#### 场景2：配置测试

```bash
# 在正式传输前测试配置是否正确
python main.py \
  --link "https://pan.baidu.com/s/1ABC123XYZ" \
  --code "abcd" \
  --folder "test_folder" \
  --dry-run
```

#### 场景3：自定义配置文件

```bash
# 使用非默认配置文件
python main.py \
  --link "https://pan.baidu.com/s/1ABC123XYZ" \
  --code "abcd" \
  --folder "production_files" \
  --config "./production.env"
```

### 执行流程说明

1. **配置验证**: 验证所有配置项是否正确
2. **登录百度网盘**: 使用配置的Cookie登录
3. **目录准备**: 删除已存在的同名目录
4. **转存分享链接**: 将分享链接转存到网盘指定目录
5. **文件列表获取**: 获取目录中所有PDF文件列表
6. **批量下载上传**: 逐个下载并上传文件，记录状态
7. **生成执行摘要**: 统计并保存整体执行情况
8. **清理临时文件**: 删除本地临时文件

## 百度网盘Cookie配置指南

### 获取Cookie的详细步骤

#### 方法1：使用浏览器开发者工具（推荐）

1. **登录百度网盘**
   - 打开浏览器，访问：https://pan.baidu.com
   - 使用手机号或百度账号登录

2. **打开开发者工具**
   - Windows: 按 `F12` 或 `Ctrl+Shift+I`
   - Mac: 按 `Cmd+Option+I`

3. **找到Cookie**
   - 在开发者工具中，点击 `Application` 或 `存储` 标签
   - 左侧菜单找到 `Cookies` -> `https://pan.baidu.com`

4. **复制关键Cookie**
   ```
   必需的Cookie项：
   - BDUSS (最重要的认证信息)
   - STOKEN (安全令牌)
   - BAIDUID (用户ID)
   ```

5. **创建Cookie文件**
   - 创建文件：`./baidu-cookies.txt`
   - 按以下格式粘贴Cookie：
     ```
     BDUSS=你的BDUSS值
     STOKEN=你的STOKEN值
     BAIDUID=你的BAIDUID值
     ```

#### 方法2：使用浏览器扩展

1. 安装Cookie导出扩展（如"EditThisCookie"）
2. 登录百度网盘
3. 使用扩展导出Cookie
4. 粘贴到`baidu-cookies.txt`文件中

### Cookie有效期和更新

- **有效期**: 通常7-30天，具体取决于百度安全策略
- **更新时机**: 当程序报告认证失败时
- **存储位置**: `.env`文件中的`BAIDU_COOKIES_PATH`指定的路径

### Cookie安全建议

- 不要将Cookie文件提交到版本控制系统
- 定期更新Cookie以确保安全性
- 使用专用百度账号，避免使用个人主账号

## 数据库查询示例

### 查看传输记录

#### 查看最近的传输记录

```sql
SELECT 
    id,
    file_name,
    transfer_status,
    file_size,
    start_time,
    upload_time
FROM file_transfer_log
ORDER BY created_at DESC
LIMIT 20;
```

#### 查看特定传输任务的记录

```sql
SELECT 
    file_name,
    transfer_status,
    error_message,
    file_size,
    start_time,
    download_time,
    upload_time
FROM file_transfer_log
WHERE folder_name = 'your_folder_name'
ORDER BY start_time;
```

#### 统计传输成功率

```sql
SELECT 
    transfer_status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM file_transfer_log) as percentage
FROM file_transfer_log
GROUP BY transfer_status;
```

### 查看执行摘要

#### 查看所有执行摘要

```sql
SELECT 
    id,
    folder_name,
    total_files,
    success_count,
    failed_count,
    skipped_count,
    start_time,
    end_time,
    TIMESTAMPDIFF(SECOND, start_time, end_time) as duration_seconds
FROM execution_summary
ORDER BY created_at DESC;
```

#### 查看特定时间段的执行记录

```sql
SELECT 
    folder_name,
    total_files,
    success_count,
    failed_count,
    skipped_count,
    start_time,
    end_time
FROM execution_summary
WHERE start_time BETWEEN '2024-01-01' AND '2024-12-31'
ORDER BY start_time DESC;
```

### 故障排查查询

#### 查找失败的传输记录

```sql
SELECT 
    file_name,
    error_message,
    start_time,
    file_size
FROM file_transfer_log
WHERE transfer_status = 'failed'
ORDER BY start_time DESC;
```

#### 查看传输时间过长的文件

```sql
SELECT 
    file_name,
    file_size,
    start_time,
    upload_time,
    TIMESTAMPDIFF(SECOND, start_time, upload_time) as transfer_duration
FROM file_transfer_log
WHERE transfer_status = 'success'
    AND upload_time IS NOT NULL
ORDER BY transfer_duration DESC
LIMIT 10;
```

## 项目结构

```
baidu-download/
├── main.py                      # 主程序入口
├── requirements.txt             # Python依赖包列表
├── README.md                    # 项目说明文档
├── .env.example                 # 配置文件示例
├── .gitignore                   # Git忽略文件
│
├── middle/                      # 中间文件和脚本
│   └── db_init.sql             # 数据库初始化脚本
│
├── src/                         # 源代码目录
│   ├── __init__.py
│   ├── config/                  # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py         # 配置类
│   │
│   ├── downloader/              # 下载模块
│   │   ├── __init__.py
│   │   └── baidu_client.py     # 百度网盘客户端
│   │
│   ├── uploader/                # 上传模块
│   │   ├── __init__.py
│   │   └── sftp_client.py      # SFTP客户端
│   │
│   ├── database/                # 数据库模块
│   │   ├── __init__.py
│   │   ├── models.py           # 数据模型
│   │   └── repository.py       # 数据库操作
│   │
│   ├── processor/               # 处理模块
│   │   ├── __init__.py
│   │   └── file_processor.py   # 文件处理协调器
│   │
│   └── utils/                   # 工具模块
│       ├── __init__.py
│       └── logger.py            # 日志工具
│
├── test/                        # 测试目录
│   ├── __init__.py
│   ├── fixtures/                # 测试数据
│   │   └── test_cookies.txt
│   └── unit/                    # 单元测试
│       ├── __init__.py
│       ├── test_config.py
│       ├── test_downloader.py
│       ├── test_uploader.py
│       ├── test_models.py
│       ├── test_logger.py
│       └── test_processor.py
│
├── logs/                        # 日志目录（运行时创建）
├── temp/                        # 临时文件目录（运行时创建）
└── .env                         # 配置文件（需自行创建）
```

### 模块功能说明

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| 主程序 | `main.py` | 程序入口，参数解析，流程控制 |
| 配置管理 | `config/settings.py` | 配置文件读取，环境变量管理 |
| 百度网盘 | `downloader/baidu_client.py` | 百度网盘API调用，文件下载 |
| SFTP上传 | `uploader/sftp_client.py` | SFTP连接管理，文件上传 |
| 数据库 | `database/models.py` | 数据模型定义 |
| 数据库 | `database/repository.py` | 数据库操作封装 |
| 文件处理 | `processor/file_processor.py` | 传输流程协调 |
| 日志工具 | `utils/logger.py` | 统一日志管理 |

## 故障排查

### 常见问题及解决方案

#### 1. 配置相关错误

**问题**: `ConfigError: Configuration file not found`
```
原因：找不到.env配置文件
解决方案：
1. 确保已复制.env.example到.env
2. 检查当前工作目录是否正确
3. 使用--config参数指定配置文件路径
```

**问题**: 数据库连接失败
```
原因：MySQL数据库配置错误或服务未启动
解决方案：
1. 检查MySQL服务是否运行
2. 验证DB_HOST, DB_PORT, DB_USER, DB_PASSWORD配置
3. 确保数据库baidu_download已创建
4. 测试数据库连接：mysql -h localhost -u root -p
```

#### 2. 百度网盘相关错误

**问题**: `百度登录失败`
```
原因：Cookie配置错误或已过期
解决方案：
1. 检查baidu-cookies.txt文件是否存在
2. 更新Cookie（参考Cookie配置指南）
3. 确保Cookie格式正确（每行一个Cookie）
4. 检查BAIDU_COOKIES_PATH路径配置
```

**问题**: `找不到PDF文件`
```
原因：分享链接中没有PDF文件或链接无效
解决方案：
1. 手动访问分享链接确认文件类型
2. 检查提取码是否正确
3. 确认分享链接是否有效（未过期）
```

#### 3. SFTP相关错误

**问题**: `SFTP连接失败`
```
原因：SFTP服务器配置错误或网络问题
解决方案：
1. 检查SFTP_HOST和SFTP_PORT配置
2. 验证用户名和密码
3. 测试网络连接：ping 192.168.0.122
4. 使用SFTP客户端手动测试连接
```

**问题**: `上传失败：权限不足`
```
原因：SFTP目标目录权限不足
解决方案：
1. 检查SFTP_REMOTE_PATH路径是否存在
2. 确认用户有写入权限
3. 联系SFTP服务器管理员
```

#### 4. 文件传输错误

**问题**: `下载失败，重试3次后仍失败`
```
原因：网络不稳定或文件被删除
解决方案：
1. 检查网络连接稳定性
2. 在百度网盘中确认文件是否还存在
3. 增加MAX_RETRIES配置值
4. 查看详细错误日志
```

**问题**: `临时文件清理失败`
```
原因：文件被占用或权限不足
解决方案：
1. 检查TEMP_DIR目录权限
2. 手动清理temp目录
3. 关闭可能占用文件的程序
```

#### 5. 性能问题

**问题**: 传输速度慢
```
优化建议：
1. 检查网络带宽
2. 调整CONCURRENT_UPLOADS参数
3. 在非高峰时段执行传输
4. 考虑使用更快的网络环境
```

### 日志文件分析

#### 查看日志文件

```bash
# Windows
type logs\transfer.log

# 查看最后几行
powershell Get-Content logs\transfer.log -Tail 50
```

#### 日志级别说明

- **DEBUG**: 详细调试信息
- **INFO**: 一般信息（默认）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

#### 启用详细日志

```bash
# 在.env文件中设置
LOG_LEVEL=DEBUG

# 或使用--verbose参数
python main.py --link "..." --code "..." --folder "..." --verbose
```

## 开发指南

### 开发环境设置

#### 1. 克隆项目

```bash
git clone <repository-url>
cd baidu-download
```

#### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows激活
venv\Scripts\activate

# Linux/Mac激活
source venv/bin/activate
```

#### 3. 安装开发依赖

```bash
pip install -r requirements.txt
```

### 运行测试

#### 运行所有测试

```bash
pytest
```

#### 运行特定测试文件

```bash
pytest test/unit/test_config.py
```

#### 运行特定测试函数

```bash
pytest test/unit/test_config.py::test_settings_init
```

#### 查看测试覆盖率

```bash
pytest --cov=src --cov-report=html
```

#### 详细测试输出

```bash
pytest -v
pytest -vv  # 更详细
```

### 代码结构指南

#### 添加新功能

1. **确定功能位置**
   - 配置相关：`src/config/`
   - 网盘操作：`src/downloader/`
   - 上传操作：`src/uploader/`
   - 数据库操作：`src/database/`
   - 业务逻辑：`src/processor/`

2. **创建相应的测试**
   - 单元测试：`test/unit/`
   - 测试数据：`test/fixtures/`

3. **更新文档**
   - 更新README.md
   - 添加使用示例

#### 代码规范

- 遵循PEP 8规范
- 使用类型注解
- 添加文档字符串
- 编写单元测试

### 调试技巧

#### 1. 使用日志调试

```python
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

#### 2. 使用断点调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()
```

#### 3. 测试单个功能

```python
# 直接运行Python模块进行测试
python -m src.config.settings
```

## 技术支持

### 获取帮助

#### 文档资源
- 项目README.md（本文件）
- 代码中的文档字符串
- 测试用例作为使用示例

#### 问题反馈
如遇到问题，请提供以下信息：
1. 错误信息完整截图
2. 配置文件（隐藏敏感信息）
3. 日志文件内容
4. 系统环境信息

### 联系方式

- 技术支持：[联系方式]
- 问题反馈：[反馈渠道]
- 文档更新：[更新地址]

## 许可证

本项目采用 [许可证类型] 许可证。

### 版权信息

Copyright (c) 2024 [公司名称/个人名称]

### 使用许可

[详细的使用许可说明]

## 更新日志

### Version 1.0.0 (2024-01-01)

#### 新功能
- 初始版本发布
- 支持百度网盘PDF文件自动下载
- 支持SFTP服务器自动上传
- 实现MySQL数据库日志记录
- 添加配置验证和错误处理

#### 已知问题
- [列出当前版本的已知问题]

#### 下一步计划
- [ ] 添加Web界面
- [ ] 支持更多文件类型
- [ ] 增加并发处理能力
- [ ] 添加定时任务功能

---

## 附录

### A. 完整配置示例

```ini
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_secure_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_password_here
DB_NAME=baidu_download

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

### B. 常用命令速查

```bash
# 基本使用
python main.py -l "分享链接" -c "提取码" -f "目录名"

# 详细日志模式
python main.py -l "分享链接" -c "提取码" -f "目录名" -v

# 测试配置
python main.py -l "分享链接" -c "提取码" -f "目录名" --dry-run

# 运行测试
pytest
pytest -v
pytest --cov=src

# 查看日志
type logs\transfer.log
powershell Get-Content logs\transfer.log -Tail 50
```

### C. 数据库速查

```sql
-- 查看最近的传输记录
SELECT * FROM file_transfer_log ORDER BY created_at DESC LIMIT 20;

-- 查看执行摘要
SELECT * FROM execution_summary ORDER BY created_at DESC;

-- 统计传输状态
SELECT transfer_status, COUNT(*) FROM file_transfer_log GROUP BY transfer_status;
```

---

**项目地址**: [GitHub仓库地址]  
**最后更新**: 2024-01-01  
**维护者**: [维护者信息]  
**许可证**: [许可证类型]