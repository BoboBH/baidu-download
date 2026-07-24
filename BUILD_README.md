# 百度网盘PDF文件自动传输系统 - Windows构建指南

## 快速开始

### 前提条件
- Python 3.8 或更高版本
- 管理员权限 (用于任务计划程序设置，如需要)

### 构建步骤

1. **安装依赖**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **构建可执行文件**
   ```cmd
   build_exe.bat
   ```

3. **测试构建结果**
   ```cmd
   cd dist
   baidu-download.exe --help
   ```

4. **部署到目标服务器**
   - 复制 `dist/` 目录到目标服务器
   - 配置 `.env` 文件
   - 测试运行

## 详细说明

### 构建模式

- **标准构建**: `build_exe.bat`
- **强制清理构建**: `build_exe.bat clean`
- **调试模式构建**: `build_exe.bat debug`

### 可执行文件特性

- **单文件模式**: 所有依赖打包在一个可执行文件中
- **控制台应用程序**: 显示实时日志输出
- **包含所有依赖**: paramiko, pymysql, python-dotenv, requests, colorama
- **包含工具**: BaiduPCS-Go.exe
- **配置模板**: 包含.env.example

### 文件结构

构建后的文件结构:
```
dist/
├── baidu-download.exe          # 主可执行文件 (包含版本信息 v1.1.5.0)
└── .env.example                # 配置文件模板
```

**注意**: PyInstaller会自动将所有必要的文件嵌入到可执行文件中，包括:
- 数据库脚本 (middle/db_init.sql)
- BaiduPCS-Go.exe 百度网盘CLI工具
- 所有Python依赖和源代码模块

## 部署指南

### 1. 环境准备

确保目标服务器已安装:
- MySQL数据库 (或远程访问权限)
- 网络连接 (访问百度网盘API和SFTP服务器)

### 2. 快速部署

将整个 `dist/` 目录复制到目标服务器:
```cmd
xcopy dist\ C:\path\to\deployment\ /E /I
```

### 3. 配置文件设置

1. 在目标服务器上，复制 `.env.example` 为 `.env`
2. 编辑 `.env` 文件，配置以下参数:

#### 必须配置的参数
```ini
# 百度网盘配置
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# SFTP服务器配置
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/path/to/upload

# MySQL数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download
```

#### 自动模式配置 (可选)
```ini
# 飞书配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_CHAT_ID=your_chat_id
FEISHU_HOURS_LIMIT=24

# 钉钉配置
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token
```

### 3. 数据库初始化

运行数据库初始化脚本:
```cmd
mysql -u root -p < middle\db_init.sql
```

### 4. 测试运行

#### 手动模式测试
```cmd
baidu-download.exe --link "分享链接" --code "提取码" --folder "目录名"
```

#### 自动模式测试
```cmd
baidu-download.exe --auto
```

#### 验证安装
```cmd
baidu-download.exe --help
```

## Windows任务计划程序设置

### 创建定时任务 (自动模式)

1. **打开任务计划程序**
   - Win+R -> `taskschd.msc`

2. **创建基本任务**
   - 点击 "创建基本任务"
   - 名称: `百度网盘自动传输`
   - 描述: `从飞书获取消息并自动传输PDF文件`

3. **触发器设置**
   - 选择 "每天"
   - 设置开始时间和重复间隔

4. **操作设置**
   - 选择 "启动程序"
   - 程序: `C:\path\to\baidu-download.exe`
   - 参数: `--auto`
   - 起始于: `C:\path\to\`

5. **完成设置**
   - 勾选 "打开此任务属性的对话框"
   - 在 "常规" 选项卡中:
     - 选择 "不管用户是否登录都要运行"
     - 勾选 "使用最高权限运行"

### 高级设置

#### 运行多个实例 (手动模式)
创建多个任务，使用不同的参数:
```cmd
baidu-download.exe -l "链接1" -c "提取码1" -f "目录1"
baidu-download.exe -l "链接2" -c "提取码2" -f "目录2"
```

#### 日志管理
配置日志文件路径，定期清理旧日志:
```ini
LOG_FILE=./logs/transfer.log
```

## 故障排除

### 常见问题

1. **可执行文件无法运行**
   - 检查 `.env` 文件是否存在且配置正确
   - 确保所有必需的工具 (BaiduPCS-Go.exe) 在指定路径

2. **数据库连接失败**
   - 验证数据库配置参数
   - 检查MySQL服务是否运行
   - 测试数据库连接

3. **SFTP上传失败**
   - 验证SFTP服务器连接
   - 检查网络连接
   - 确认远程路径权限

4. **飞书集成问题**
   - 验证飞书应用凭证
   - 检查网络连接
   - 查看日志错误信息

### 调试技巧

1. **启用详细日志**
   ```cmd
   baidu-download.exe --auto --verbose
   ```

2. **测试配置**
   ```cmd
   baidu-download.exe --dry-run
   ```

3. **查看日志文件**
   - 检查配置的日志文件路径
   - 默认: `./logs/transfer.log`

## 维护和更新

### 日志文件管理
- 定期清理旧日志文件
- 监控磁盘空间使用情况

### 数据库维护
- 定期备份数据库
- 清理过期的传输记录

### 更新可执行文件
1. 停止正在运行的任务计划
2. 替换可执行文件
3. 更新配置文件 (如有需要)
4. 重新启动任务计划

## 安全建议

1. **文件权限**
   - 限制 `.env` 文件访问权限
   - 保护敏感信息 (密码、密钥)

2. **网络安全**
   - 使用SFTP而非FTP
   - 配置防火墙规则

3. **数据库安全**
   - 使用强密码
   - 限制数据库用户权限
   - 定期更新数据库软件

## 技术支持

如遇到问题:
1. 检查日志文件
2. 查看项目文档
3. 运行诊断命令
4. 联系技术支持团队

---
**版本**: 1.1.5  
**更新日期**: 2026-07-24  
**维护团队**: baidu-download team