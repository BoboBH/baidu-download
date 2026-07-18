# 百度网盘PDF文件自动传输系统 - 项目结构

## 📁 整理后的项目结构

```
baidu-download/
├── main.py                    # 主程序入口
├── README.md                  # 项目说明文档
├── VERSION                    # 版本信息
├── .env.example              # 环境变量示例
├── .gitignore               # Git忽略配置
├── BaiduPCS-Go.exe          # 百度网盘客户端
├── baidu-download.spec      # PyInstaller配置
│
├── src/                      # 源代码目录
│   ├── config/              # 配置管理
│   ├── database/            # 数据库操作
│   ├── downloader/          # 百度网盘下载器
│   ├── processor/           # 文件处理器
│   ├── uploader/            # SFTP上传器
│   └── utils/               # 工具函数
│
├── test/                     # 测试代码目录
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   ├── manual/              # 手动测试
│   ├── diagnostic/          # 诊断工具
│   ├── legacy/              # 遗留测试代码
│   └── fixtures/            # 测试数据
│
├── scripts/                  # 脚本目录
│   ├── build.bat            # Windows构建脚本
│   ├── init_db.bat          # Windows数据库初始化
│   ├── init_db.sh           # Linux数据库初始化
│   ├── init_db_auto.bat     # 自动数据库初始化
│   └── init_db_auto.sh      # 自动数据库初始化
│
├── docs/                     # 文档目录
│   ├── superpowers/         # Claude Code技能文档
│   ├── DEPLOYMENT.md        # 部署指南
│   ├── CHANGELOG.md         # 变更日志
│   ├── PACKAGING_RULES.md   # 打包规范
│   └── ...                  # 其他文档
│
├── release/                  # 发布目录
│   ├── dist/                # 可执行文件输出
│   │   ├── baidu-download.exe    # 主程序
│   │   ├── BaiduPCS-Go.exe      # 百度网盘客户端
│   │   ├── .env                 # 配置文件
│   │   └── baidu-cookies.txt    # 百度网盘Cookies
│   └── archive/             # 历史版本存档
│
├── logs/                     # 日志目录
├── temp/                     # 临时文件目录
└── venv/                     # Python虚拟环境
```

## 📋 文件组织说明

### 核心文件（根目录）
- **main.py**: 程序主入口，包含参数解析和流程控制
- **README.md**: 项目说明文档
- **VERSION**: 版本信息和更新历史
- **BaiduPCS-Go.exe**: 百度网盘命令行客户端
- **baidu-download.spec**: PyInstaller打包配置

### 源代码结构（src/）
- **config/**: 配置管理，环境变量加载和验证
- **database/**: 数据库操作，数据模型和仓储模式
- **downloader/**: 百度网盘文件下载客户端
- **processor/**: 文件处理协调器，整合下载和上传流程
- **uploader/**: SFTP文件上传客户端
- **utils/**: 通用工具函数，日志记录等

### 测试结构（test/）
- **unit/**: 单元测试，测试各个模块的独立功能
- **integration/**: 集成测试，测试完整的工作流程
- **manual/**: 手动测试脚本，用于验证功能
- **diagnostic/**: 诊断工具，用于问题排查
- **legacy/**: 遗留测试代码，保留用于参考
- **fixtures/**: 测试数据和Mock对象

### 脚本结构（scripts/）
- **build.bat**: 项目构建脚本，生成可执行文件
- **init_db.***: 数据库初始化脚本
- **init_db_auto.***: 自动数据库初始化脚本

### 文档结构（docs/）
- **DEPLOYMENT.md**: 部署指南
- **CHANGELOG.md**: 版本变更记录
- **PACKAGING_RULES.md**: 打包规范说明
- **superpowers/**: Claude Code技能文档
- 其他技术文档和报告

### 发布结构（release/）
- **dist/**: 最终可执行文件和依赖
- **archive/**: 历史版本存档

## 🎯 整理要点

### 已清理的内容
- ❌ 删除了根目录下的测试文件（移至test/legacy/和test/diagnostic/）
- ❌ 删除了重复的诊断工具（tools/目录）
- ❌ 删除了过时的打包脚本（create_final_package.py, manual_package.py）
- ❌ 删除了构建临时目录（build/, dist/）
- ❌ 删除了测试用的假文件（fake/目录）
- ❌ 删除了中间文件目录（middle/）
- ❌ 归档了旧版本文件（release/archive/）

### 优化后的结构
- ✅ 测试代码统一管理在test/目录
- ✅ 脚本文件集中在scripts/目录
- ✅ 文档文件整理到docs/目录
- ✅ 根目录保持简洁，只包含核心文件
- ✅ 发布目录清晰分离
- ✅ 便于维护和查找

## 🚀 快速开始

### 使用示例
```bash
# 基本使用
python main.py --link "分享链接" --code "提取码" --folder "目录名"

# 使用--no-sftp参数（不上传到SFTP）
python main.py -l "链接" -c "码" -f "目录" --no-sftp

# 详细日志
python main.py -l "链接" -c "码" -f "目录" --verbose

# 仅测试配置
python main.py -l "链接" -c "码" -f "目录" --dry-run
```

### 构建可执行文件
```bash
# 使用构建脚本
cd scripts
./build.bat

# 或直接使用PyInstaller
pyinstaller --onefile --name baidu-download --add-data "BaiduPCS-Go.exe;." --hidden-import paramiko --hidden-import pymysql --hidden-import dotenv --distpath release/dist main.py
```

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest test/unit/test_processor.py

# 运行集成测试
pytest test/integration/
```

## 📝 维护建议

1. **新增测试**: 放置在test/unit/或test/integration/中
2. **新增脚本**: 放置在scripts/目录中
3. **新增文档**: 放置在docs/目录中
4. **发布版本**: 使用build.bat构建，输出到release/dist/
5. **清理临时文件**: 定期清理temp/和logs/目录

## 📊 版本信息

### 当前版本: v1.0.8 (2026-07-15)
- **重大修复**: 修复--no-sftp时错误设置upload_time的问题
- **关键修复**: 修复先用--no-sftp再启用SFTP时文件不上传的致命问题
- **逻辑改进**: 完善智能跳过逻辑，检查upload_time判断是否需要重新上传
- **测试增强**: 新增16个测试用例验证所有场景

### 项目整理: 2026-07-16
- **结构优化**: 统一测试代码到test/目录
- **脚本整理**: 构建和部署脚本集中到scripts/目录
- **文档归集**: 所有文档整理到docs/目录
- **清理冗余**: 删除过时和重复的文件

---

**最后整理日期**: 2026-07-16  
**当前版本**: v1.0.8  
**项目状态**: 生产就绪 ✅