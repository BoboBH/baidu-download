# 百度网盘PDF文件自动传输系统 - 项目结构

## 📂 **项目目录结构**

```
baidu-download/
├── src/                          # 源代码目录
│   ├── config/                   # 配置管理
│   ├── database/                 # 数据库操作
│   ├── downloader/               # 百度网盘客户端
│   ├── feishu/                   # 飞书集成
│   ├── notification/             # 通知服务
│   ├── processor/                # 文件处理器
│   ├── uploader/                 # SFTP上传
│   ├── utils/                    # 工具函数
│   └── wxchat/                   # 微信文章处理
│
├── release/                      # 发布版本 ⭐
│   ├── baidu-download-v1.4.3.zip # 最新发布包
│   ├── baidu-download.exe        # 可执行文件
│   ├── BaiduPCS-Go.exe           # 百度网盘工具
│   ├── baidu-cookies.txt        # 认证文件
│   ├── .env                      # 配置文件
│   ├── .env.example             # 配置模板
│   ├── database/                 # 数据库脚本
│   └── middle/                   # 初始化脚本
│
├── docs/                         # 文档目录
│   ├── release-notes/           # 发布说明
│   │   ├── RELEASE_NOTES_v1.4.3.md
│   │   └── RELEASE_NOTES_v1.4.2_FINAL_CORRECT.md
│   ├── active/                  # 活跃文档
│   └── archive/                 # 归档文档
│
├── test/                         # 测试目录
│   ├── manual/                  # 手动测试脚本
│   │   ├── test_baidu_transfer.py
│   │   ├── test_correct_logic.py
│   │   └── test_default_extraction_code.py
│   ├── integration/             # 集成测试
│   ├── unit/                    # 单元测试
│   └── fixtures/                # 测试数据
│
├── scripts/                      # 脚本工具
│   ├── check_db_structure.py
│   ├── init_db_auto.sh
│   └── init_db_auto.bat
│
├── database/                     # 数据库SQL脚本
├── middle/                       # 中间件脚本
├── deployment/                   # 部署相关
│
├── memory/                       # 长期记忆 ⭐
│   └── baidu-download-message-parsing-logic.md
│
├── main.py                       # 程序入口
├── requirements.txt              # 依赖包列表
├── version_info.txt            # 版本信息
└── README.md                     # 项目说明
```

## 📦 **发布版本管理**

### **当前版本**
- **版本**: v1.4.3
- **发布包**: `release/baidu-download-v1.4.3.zip`
- **大小**: 234MB

### **版本命名规则**
- 格式: `baidu-download-vX.Y.Z.zip`
- 简洁递增，无功能描述
- 示例: `v1.4.3` → `v1.4.4` → `v1.4.5`

## 🧪 **测试文件组织**

### **手动测试** (`test/manual/`)
- 功能验证脚本
- 调试工具
- 集成测试

### **单元测试** (`test/unit/`)
- 模块测试
- 功能测试

### **集成测试** (`test/integration/`)
- 端到端测试
- 工作流测试

## 📚 **文档组织**

### **发布说明** (`docs/release-notes/`)
- 各版本详细说明
- 更新记录
- 修复内容

### **活跃文档** (`docs/active/`)
- 当前使用文档
- 配置指南
- 部署说明

### **归档文档** (`docs/archive/`)
- 历史文档
- 旧版本说明

## 🔧 **开发工具**

### **构建工具**
- `baidu_download.spec` - PyInstaller配置
- `build_clean.bat` - 清理构建脚本

### **数据库工具**
- `scripts/init_db_auto.sh` - 自动初始化
- `database/migrations/` - 数据库迁移

## 💾 **重要文件**

### **配置文件**
- `.env` - 环境配置 (包含敏感信息)
- `.env.example` - 配置模板
- `version_info.txt` - 版本元数据

### **认证文件**
- `baidu-cookies.txt` - 百度网盘认证

## 🧠 **长期记忆**

**核心逻辑记录**: `memory/baidu-download-message-parsing-logic.md`
- 消息解析正确逻辑
- 目录名称从消息提取，提取码从配置取
- 避免重复错误

## 🎯 **工作流程**

### **开发流程**
1. 在 `src/` 中开发功能
2. 在 `test/` 中编写测试
3. 更新 `docs/` 中的文档
4. 构建发布版本到 `release/`
5. 更新 `memory/` 中的经验记录

### **发布流程**
1. 更新版本号 (`version_info.txt`)
2. 执行构建 (`build_clean.bat`)
3. 测试发布版本
4. 创建发布说明
5. 打包到 `release/` 目录

---

**项目结构特点**:
- 📂 **清晰分层**: 源码、测试、文档分离
- 📦 **发布管理**: 统一的发布目录
- 🧪 **测试完整**: 手动、单元、集成测试
- 📚 **文档规范**: 发布说明、活跃文档、归档文档
- 🧠 **长期记忆**: 避免重复错误