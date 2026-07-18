# 📦 打包规则与发布流程

## 🎯 打包规则

本规则适用于百度网盘PDF文件自动传输系统的版本发布和打包流程。

---

## 📁 构建目录结构

```
build/                               # 🔨 编译打包目录 ⭐
├── README.md                       # 构建工具说明
├── update_version.py               # 版本号管理
├── quick_version.py                # 快速版本更新
├── full_release.py                 # 完整打包流程
├── build_to_venv.py                # 开发版本编译
├── build_to_venv.bat               # 快速编译(批处理)
└── quick_build.bat                 # 最快编译方式
```

---

## 📋 打包前检查清单

### 1. 版本号管理 ✅
在打包前必须更新版本号：

#### 版本号格式
- **主版本.次版本.修订号**
- **示例**: v1.0.0 → v1.0.1 → v1.1.0 → v2.0.0

#### 使用版本管理脚本
```bash
cd build
python update_version.py v1.0.1
```

#### 自动更新的文件
- `docs/CHANGELOG.md` - 版本日志
- `README.md` - 项目主页
- 其他相关文档

### 2. 代码质量检查 ✅
- [ ] 主要功能已测试
- [ ] 文档已更新
- [ ] CHANGELOG.md已更新

### 3. 配置文件检查 ✅
- [ ] `.env.example` 配置完整
- [ ] `requirements.txt` 依赖正确
- [ ] `middle/db_init.sql` 脚本正确

---

## 📦 打包规则详解

### 规则1: EXE编译规范

#### 开发版本编译 (venv/Scripts/)
```bash
cd build
python build_to_venv.py
# 或双击: quick_build.bat

# 输出: venv/Scripts/baidu-download.exe (~11MB)
# 用途: 代码修改后快速测试
```

#### 发布版本编译 (release/dist/)
```bash
cd build
python full_release.py v1.0.1

# 输出: release/dist/baidu-download.exe (~11MB)
# 用途: 正式发布版本
```

### 规则2: 包含文件清单

#### 必须包含的文件
发布包必须包含以下文件：
```
发布包/
├── baidu-download.exe              # 主程序
├── BaiduPCS-Go.exe                 # 百度网盘工具 ⭐ 新增
├── .env                            # 生产环境配置 ⭐ 新增
├── .env.example                     # 配置模板
├── README.md                        # 使用说明
├── DEPLOYMENT.md                    # 部署指南
├── QUICK_START.md                   # 快速开始
├── CHANGELOG.md                     # 版本日志
├── INSTALL.txt                      # 安装说明
├── middle/db_init.sql              # 数据库脚本
├── diagnose_sftp.py                # 诊断工具
└── interactive_sftp_test.py      # 测试工具
```

### 规则3: BaiduPCS-Go.exe 配置 ⭐ 重要

#### 开发环境配置
在开发环境中，`.env` 文件使用绝对路径：
```ini
BAIDUPCS_GO_PATH=D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe
```

#### 生产环境配置
在打包后的发布版本中，使用相对路径：
```ini
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
```

#### 自动化处理
`create_final_package.py` 脚本会自动：
1. 复制 `BaiduPCS-Go.exe` 到 `release/dist/` 目录
2. 创建生产环境的 `.env` 配置文件
3. 将两者打包到发布包中

### 规则4: 文档同步要求

#### 打包前必须更新的文档
1. **docs/CHANGELOG.md** - 记录新版本变更
2. **README.md** - 更新版本信息
3. **docs/README.md** - 更新文档导航

#### 文档更新检查
```bash
# 确认文档已更新
cat docs/CHANGELOG.md | head -10
cat README.md | head -10
```

---

## 🔄 完整打包流程

### 步骤1: 版本号更新 (✅ 自动化)
```bash
cd build
python update_version.py v1.0.1

# 自动更新:
# - docs/CHANGELOG.md
# - README.md
# - build相关文件
```

### 步骤2: 代码验证 (手动检查)
```bash
# 检查主要功能
# - 测试下载功能
# - 验证配置文件
# - 确认文档更新
```

### 步骤3: 完整打包 (✅ 自动化)
```bash
cd build
python full_release.py v1.0.1

# 自动执行:
# 1. 验证打包前条件
# 2. 更新版本号
# 3. 编译发布版本EXE → release/dist/
# 4. 编译开发版本EXE → venv/Scripts/
# 5. 创建发布包 → release/*.zip
# 6. 复制 BaiduPCS-Go.exe ⭐
# 7. 生成校验文件
# 8. 验证打包结果
```

### 步骤4: 功能测试 (手动验证)
```bash
# 测试开发版本
./venv/Scripts/baidu-download.exe --help

# 测试发布版本
cd release/dist
./baidu-download.exe --dry-run
```

---

## 🎯 开发测试流程

### 场景1: 代码修改后快速测试
```bash
# 修改代码后快速重新编译
cd build
python build_to_venv.py
# 或双击: quick_build.bat

# 测试新功能
./venv/Scripts/baidu-download.exe --link "测试" --code "测试" --folder "test" --dry-run
```

### 场景2: 版本发布
```bash
# 1. 更新CHANGELOG.md
# 2. 执行完整打包
cd build
python update_version.py v1.0.1
python full_release.py v1.0.1
# 3. 测试发布版本
cd ../release/dist
./baidu-download.exe --help
```

### 场景3: 快速重新编译
```bash
# 最快速的重新编译方式
cd build
quick_build.bat
# 或直接双击quick_build.bat
```

---

## 📋 打包检查清单

### 编译前检查 ✅
- [ ] 版本号已更新
- [ ] CHANGELOG.md已更新
- [ ] 文档已同步
- [ ] 测试已通过

### 编译后检查 ✅
- [ ] 发布EXE已生成: `release/dist/baidu-download.exe`
- [ ] 百度网盘工具已复制: `release/dist/BaiduPCS-Go.exe` ⭐
- [ ] 生产配置已创建: `release/dist/.env` ⭐
- [ ] 开发EXE已更新: `venv/Scripts/baidu-download.exe`
- [ ] 发布包已创建: `release/baidu-download-v1.0.0-exe.zip`
- [ ] 校验文件已生成: `release/*-checksum.txt`
- [ ] EXE功能测试通过

---

## 🔧 快速打包命令

### 完整发布 (推荐)
```bash
cd build
python update_version.py v1.0.1
python full_release.py v1.0.1
```

### 快速开发编译
```bash
cd build
python build_to_venv.py
# 或
quick_build.bat
```

### 仅编译发布版本
```bash
cd build
python full_release.py v1.0.1
```

---

## 📊 编译时间估算

| 操作 | 时间估算 | 说明 |
|------|----------|------|
| 版本号更新 | 1分钟 | 自动更新6个文件 |
| 代码验证 | 5分钟 | 手动检查 |
| EXE编译 | 3-5分钟 | PyInstaller编译 |
| 发布包创建 | 1分钟 | 打包和校验 |
| 功能测试 | 10分钟 | 测试基本功能 |
| **总计** | **20-22分钟** | 完整发布流程 |

---

## 🚨 常见错误预防

### 错误1: 版本号不一致
**现象**: 不同文件中的版本号不匹配
**预防**: 使用 `update_version.py` 统一更新

### 错误2: EXE文件过期
**现象**: venv/Scripts/ 中的EXE不是最新版本
**预防**: 代码修改后运行 `build_to_venv.py`

### 错误3: 缺少 BaiduPCS-Go.exe ⭐
**现象**: 打包后缺少百度网盘工具
**预防**: 使用 `create_final_package.py` 自动复制

### 错误4: 配置路径错误 ⭐
**现象**: 程序无法找到 BaiduPCS-Go.exe
**预防**: 生产环境使用相对路径 `./BaiduPCS-Go.exe`

### 错误5: 缺少必要文件
**现象**: 打包后缺少重要文件
**预防**: 使用打包前检查清单

### 错误6: EXE无法运行
**现象**: 编译的EXE文件无法启动
**预防**: 编译后进行功能测试

---

## 🎯 版本发布规范

### 发布类型

#### 主版本 (Major)
- **格式**: vX.0.0
- **时机**: 重大功能变更或架构调整
- **示例**: v1.0.0 → v2.0.0

#### 次版本 (Minor)
- **格式**: v1.X.0
- **时机**: 新增重要功能或重要改进
- **示例**: v1.0.0 → v1.1.0

#### 修订版本 (Patch)
- **格式**: v1.0.X
- **时机**: Bug修复或小改进
- **示例**: v1.0.0 → v1.0.1

### 文件命名规范

#### EXE文件
```
release/dist/baidu-download.exe       # 发布版本
venv/Scripts/baidu-download.exe     # 开发版本
release/dist/BaiduPCS-Go.exe        # 百度网盘工具 ⭐
```

#### 发布包
```
baidu-download-v1.0.0-exe.zip         # EXE版本
baidu-download-v1.0.0.zip             # Python版本
baidu-download-v1.0.0-exe-checksum.txt  # EXE校验
baidu-download-v1.0.0-checksum.txt     # Python校验
```

---

## 🏗️ 项目规则总结

### 核心规则
1. **版本管理**: 使用 `update_version.py` 统一更新版本号
2. **编译规范**: 开发版本→venv/Scripts/，发布版本→release/dist/
3. **文件包含**: 必须包含所有必要文件、文档和BaiduPCS-Go.exe ⭐
4. **文档同步**: 打包前必须更新相关文档
5. **配置管理**: 生产环境使用相对路径配置 ⭐

### 开发规则
1. **代码修改**: 修改后运行 `build_to_venv.py` 重新编译
2. **快速测试**: 使用 `venv/Scripts/baidu-download.exe` 测试
3. **版本发布**: 使用 `full_release.py` 完整打包
4. **工具打包**: 自动复制 BaiduPCS-Go.exe ⭐

### 质量保证
1. **功能测试**: 打包前进行功能验证
2. **文档更新**: 保持文档与代码同步
3. **版本控制**: 使用Git进行版本管理
4. **配置验证**: 确保打包后配置正确 ⭐

---

## 🔍 部署后配置说明

### 生产环境配置 ⭐

#### 1. 解压发布包
```bash
# 解压 baidu-download-v1.0.0-exe.zip
# 确保以下文件在同一目录:
# - baidu-download.exe
# - BaiduPCS-Go.exe
# - .env
```

#### 2. 检查配置
```bash
# 编辑 .env 文件
# BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe  # 已自动配置
```

#### 3. 配置其他参数
```bash
# 在 .env 中设置:
# - SFTP服务器信息
# - MySQL数据库信息
# - 百度网盘Cookie
```

### 常见问题解决 ⭐

#### BaiduPCS-Go not found
**解决方案**: 确保 `BaiduPCS-Go.exe` 与 `baidu-download.exe` 在同一目录

#### 配置路径错误
**解决方案**: 检查 `.env` 中的路径是否使用相对路径 `./BaiduPCS-Go.exe`

#### 工具版本不兼容
**解决方案**: 使用项目推荐的 BaiduPCS-Go v4.0.1 版本

---

**严格遵循打包规则可以确保发布质量和用户体验！** 🎯

## 📞 获取帮助

- **打包指南**: `build/README.md`
- **文档中心**: `docs/README.md`
- **部署指南**: `docs/DEPLOYMENT.md`
- **配置说明**: `.env.example`
