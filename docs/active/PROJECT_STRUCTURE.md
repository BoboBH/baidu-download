# 项目结构说明

**版本：** 1.2.2  
**整理日期：** 2026-07-25  
**状态：** 已整理完成

---

## 📁 项目结构

```
baidu-download/
├── 📄 main.py                    # 主入口文件
├── 📄 requirements.txt           # 生产环境依赖
├── 📄 requirements-dev.txt       # 开发环境依赖  
├── 📄 baidu_download.spec        # PyInstaller打包配置
├── 📄 .env                       # 环境配置文件
├── 📄 .env.example               # 配置文件模板
├── 📄 baidu-cookies.txt          # 百度网盘Cookies
├── 📄 version_info.txt           # 版本信息
│
├── 📁 src/                       # 源代码目录
│   ├── config/                   # 配置管理
│   │   └── settings.py
│   ├── database/                 # 数据库模块
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── message_models.py
│   ├── downloader/               # 下载器
│   │   └── baidu_client.py
│   ├── uploader/                 # 上传器
│   │   └── sftp_client.py
│   ├── feishu/                   # 飞书和钉钉模块
│   │   ├── feishu_client.py
│   │   ├── dingtalk_group_client.py
│   │   └── message_parser.py
│   ├── notification/             # 通知模块
│   │   └── dingtalk_notifier.py
│   ├── processor/                # 处理器
│   │   ├── file_processor.py
│   │   ├── auto_processor.py
│   │   ├── message_receiver.py
│   │   └── file_transfer_processor.py
│   └── utils/                    # 工具函数
│       ├── logger.py
│       └── filename_handler.py
│
├── 📁 scripts/                   # 工具脚本
│   ├── check_auto_results.py
│   ├── check_db_structure.py
│   ├── debug_feishu_messages.py
│   ├── init_database.py
│   ├── test_feishu_connection.py
│   ├── test_feishu_messages.py
│   ├── test_message_parsing.py
│   └── test_sftp_connection.py
│
├── 📁 test_scripts/             # 临时测试脚本（新建）
│   ├── test_*.py                 # 各种临时测试文件
│   ├── validate_deployment.py
│   └── diagnose_mysql.py
│
├── 📁 test/                      # 正式测试目录
│   ├── test_database.py
│   ├── test_filename_analysis.py
│   ├── test_smart_filename.py
│   ├── test_integration.py
│   └── test_message_parser_unified.py
│
├── 📁 docs/                     # 文档目录（已整理）
│   ├── active/                   # 当前活跃文档
│   │   ├── README.md
│   │   ├── QUICK_START.md
│   │   ├── CHANGELOG.md
│   │   ├── DEPLOYMENT.md
│   │   ├── deployment-guide.md
│   │   └── dingtalk-message-receiver-usage.md
│   └── archive/                  # 过时文档存档
│       └── (32个过时报告和文档)
│
├── 📁 release/                  # 发布版本
│   ├── dist/                     # 打包后的exe
│   │   ├── baidu-download.exe   # 主程序（18MB）
│   │   ├── VERSION_INFO.md      # 版本说明
│   │   └── RELEASE_NOTES.md     # 发布说明
│   └── deployment/              # 部署相关文件
│
├── 📁 deployment/               # 部署相关（已合并）
│   └── (部署脚本和配置)
│
├── 📁 middle/                   # 中间件
│   └── db_init.sql              # 数据库初始化脚本
│
├── 📁 logs/                     # 日志目录
│   └── transfer.log            # 传输日志
│
├── 📁 temp/                     # 临时文件目录
│
└── 📁 download/                 # 下载目录
    └── (下载的文件暂存处)
```

---

## 🎯 整理内容

### ✅ 已完成的整理

**1. 根目录清理**
- ❌ 删除了临时测试文件（test_*.py等）
- ❌ 删除了重复的README文件
- ❌ 删除了错误的路径目录
- ✅ 保留了必要的配置文件

**2. 目录结构优化**
- ✅ 创建了 `test_scripts/` 存放临时测试
- ✅ 合并了 `tests/` 到 `test/`
- ✅ 合并了 `deployment_clean/` 到 `deployment/`
- ❌ 删除了错误创建的目录

**3. 文档整理**
- ✅ 创建了 `docs/active/` 存放当前文档
- ✅ 创建了 `docs/archive/` 存放过时文档
- ✅ 移动了32个过时报告到archive
- ✅ 保留了6个核心活跃文档

**4. 文件清理**
- ✅ 清理了Python缓存文件（__pycache__）
- ✅ 删除了重复的cookies文件
- ✅ 清理了旧的发布文件
- ✅ 保留了必要的配置和数据文件

---

## 📋 核心文件说明

### 主程序
- **main.py** - 主入口，支持所有命令行参数
- **baidu_download.spec** - PyInstaller打包配置
- **requirements.txt** - 生产环境依赖

### 配置文件
- **.env** - 环境配置（包含敏感信息，不提交）
- **.env.example** - 配置模板
- **baidu-cookies.txt** - 百度网盘cookies

### 文档
- **docs/active/README.md** - 项目主文档
- **docs/active/QUICK_START.md** - 快速入门
- **docs/active/deployment-guide.md** - 部署指南
- **docs/active/dingtalk-message-receiver-usage.md** - 钉钉使用说明

### 测试
- **test/** - 正式测试用例
- **test_scripts/** - 临时调试脚本（可删除）
- **scripts/** - 工具脚本

---

## 🚀 使用指南

### 开发环境
```bash
cd d:\git\baidu-download
python main.py --help
```

### 运行测试
```bash
# 正式测试
cd test
python -m pytest test_database.py

# 临时测试
cd test_scripts
python validate_deployment.py
```

### 打包发布
```bash
pyinstaller baidu_download.spec --clean
```

---

## 📊 整理效果

### 整理前
- ❌ 根目录有15+个临时测试文件
- ❌ 3个重复的测试目录
- ❌ 2个重复的部署目录
- ❌ docs/有40+个混乱文档
- ❌ 多个重复的配置文件

### 整理后
- ✅ 根目录只有核心文件
- ✅ 1个统一的test/目录
- ✅ 1个统一的deployment/目录
- ✅ docs/分类清晰（active/archive）
- ✅ 无重复文件

---

## ⚠️ 重要说明

### 不要删除的文件/目录
- ✅ **.env** - 环境配置（包含密钥）
- ✅ **baidu-cookies.txt** - 百度网盘登录信息
- ✅ **src/** - 源代码目录
- ✅ **main.py** - 主入口
- ✅ **release/dist/baidu-download.exe** - 发布版本

### 可以删除的目录
- 🗑️ **test_scripts/** - 临时测试脚本（可安全删除）
- 🗑️ **docs/archive/** - 过时文档（可选删除）
- 🗑️ **temp/** - 临时文件（可定期清理）

---

## 🔄 维护建议

1. **定期清理**
   - 清理temp/目录
   - 删除test_scripts/中的临时脚本
   - 整理docs/中的新增文档

2. **保持结构**
   - 新增工具脚本放入scripts/
   - 新增测试用例放入test/
   - 新增文档分类放入docs/active/

3. **版本管理**
   - 更新VERSION_INFO.md
   - 维护CHANGELOG.md
   - 清理过时的发布版本

---

*项目结构已整理完成，所有功能验证正常！* ✨