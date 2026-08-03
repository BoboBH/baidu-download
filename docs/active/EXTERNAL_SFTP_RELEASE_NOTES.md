# 百度下载系统 - 外部SFTP功能版本

## 🎉 版本信息

- **版本号**: v1.3.0
- **发布日期**: 2026-08-02
- **主要特性**: 外部SFTP双上传功能

---

## ✨ 新功能特性

### 🔥 **外部SFTP双上传功能**

现在支持将微信文章PDF同时上传到两个SFTP服务器：

1. **主SFTP服务器** - 内部使用，存储所有文章PDF
2. **外部SFTP服务器** - 外部用户访问，支持排除特定公众号

#### 📋 **配置示例**

```bash
# 外部SFTP服务器配置
WXCHAT_EXTERNAL_SFTP_HOST=192.168.0.122
WXCHAT_EXTERNAL_SFTP_PORT=22
WXCHAT_EXTERNAL_SFTP_USERNAME=sftp01
WXCHAT_EXTERNAL_SFTP_PASSWORD=123456
WXCHAT_EXTERNAL_SFTP_FOLDER=/sftp01/cms

# 排除的公众号名称列表 (用逗号分隔)
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=测试A,测试B,测试C
```

#### 🎯 **工作流程**

```
1. 从wewe_rss数据库获取文章列表
       ↓
2. 生成PDF文件
       ↓
3. 上传到主SFTP服务器 (所有文章)
       ↓
4. 检查是否需要上传到外部SFTP
       ├─ 检查外部SFTP是否配置
       ├─ 检查公众号是否在排除列表
       └─ 上传到外部SFTP (如果通过检查)
       ↓
5. 记录处理状态到数据库
```

#### 🔍 **排除逻辑**

- 如果公众号名称在 `WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS` 中，跳过外部SFTP上传
- 如果公众号名称不在排除列表，同时上传到主SFTP和外部SFTP
- 外部上传失败不影响主流程，只记录警告日志

---

## 📦 打包内容

### ✅ **主程序**
- `baidu-download.exe` (192MB) - 包含所有功能的可执行文件

### ✅ **配置文件**
- `.env.example` - 完整的配置模板（包含外部SFTP配置）

### ✅ **数据库脚本**
- `database/wxchat_tables.sql` - 微信文章表结构
- `database/migrations/migrate_add_source_field.sql` - 数据库迁移脚本
- `middle/db_init.sql` - 核心数据库表结构

### ✅ **文档**
- 外部SFTP配置指南
- 测试工具和演示脚本
- 详细的使用说明

---

## 🚀 快速开始

### 1️⃣ **配置环境变量**

编辑 `release/dist/.env` 文件：

```bash
# 基础配置
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_NAME=wewe_rss
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=your_password

# 外部SFTP配置
WXCHAT_EXTERNAL_SFTP_HOST=your_external_sftp_host
WXCHAT_EXTERNAL_SFTP_PORT=22
WXCHAT_EXTERNAL_SFTP_USERNAME=external_user
WXCHAT_EXTERNAL_SFTP_PASSWORD=external_password
WXCHAT_EXTERNAL_SFTP_FOLDER=/external/wechat

# 排除公众号 (可选)
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=内部账号,测试账号
```

### 2️⃣ **验证配置**

```bash
# 测试外部SFTP连接
python test/diagnostic/test_external_sftp.py

# 验证打包内容
python test/diagnostic/verify_packed_exe.py
```

### 3️⃣ **运行程序**

```bash
# 处理最近7天的微信文章
release/dist/baidu-download.exe --wxchat --wxchat-days 7
```

---

## 🧪 **测试工具**

### **外部SFTP测试工具**
```bash
python test/diagnostic/test_external_sftp.py
```

测试内容：
- ✅ 外部SFTP连接配置检查
- ✅ 网络连接和权限测试
- ✅ 文件上传功能测试
- ✅ 排除逻辑验证

### **功能演示脚本**
```bash
python test/manual/wxchat/demo_external_sftp.py
```

演示内容：
- ✅ 完整的处理流程展示
- ✅ 双SFTP上传演示
- ✅ 排除逻辑场景演示

---

## 🔧 **技术特性**

### ✅ **完全复用原有方法**
- 扩展了 `SFTPClient` 类支持自定义配置
- 保持原有代码结构不变
- 向后兼容现有功能

### ✅ **灵活的配置机制**
- 支持三种配置场景：
  1. 仅主SFTP (外部SFTP未配置)
  2. 完全外部分发 (无排除公众号)
  3. 选择性外部分发 (排除特定公众号)

### ✅ **安全可控**
- 通过公众号名称控制内容分发
- 外部上传失败不影响主流程
- 完整的错误处理和日志记录

### ✅ **易于测试**
- 提供专业的测试工具
- 详细的配置验证
- 完整的功能演示

---

## 📊 **日志输出示例**

### **正常处理流程**
```
[INFO] 处理文章: 技术分享_Git入门教程 (abc123)
[INFO] PDF生成成功，文件大小: 1.2MB
[INFO] PDF上传成功: /wxchat/202407/技术分享_Git入门教程.pdf
[INFO] 开始上传到外部SFTP: 192.168.0.122
[INFO] 外部SFTP上传成功: /sftp01/cms/202407/技术分享_Git入门教程.pdf
```

### **排除公众号场景**
```
[INFO] 处理文章: 测试A_机密文档 (xyz789)
[INFO] PDF生成成功，文件大小: 0.8MB
[INFO] PDF上传成功: /wxchat/202407/测试A_机密文档.pdf
[INFO] 公众号 '测试A' 在排除列表中，跳过外部SFTP上传
```

### **外部SFTP配置未设置**
```
[INFO] 处理文章: 公开分享_新功能介绍 (def456)
[INFO] PDF生成成功，文件大小: 1.5MB
[INFO] PDF上传成功: /wxchat/202407/公开分享_新功能介绍.pdf
[DEBUG] 外部SFTP未配置，跳过外部上传
```

---

## 🎯 **使用场景**

### **场景1：内部使用**
```bash
# 不配置外部SFTP
WXCHAT_EXTERNAL_SFTP_HOST=    # 留空

结果：所有文章只上传到主SFTP
```

### **场景2：完全外部分发**
```bash
# 配置外部SFTP，不排除任何公众号
WXCHAT_EXTERNAL_SFTP_HOST=external.example.com
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=    # 留空

结果：所有文章同时上传到主SFTP和外部SFTP
```

### **场景3：选择性外部分发**
```bash
# 配置外部SFTP，排除特定公众号
WXCHAT_EXTERNAL_SFTP_HOST=external.example.com
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=测试A,测试B,内部账号

结果：排除特定公众号，其他文章正常外部分发
```

---

## 🔗 **相关文档**

- 📖 [外部SFTP配置指南](docs/active/external-sftp-configuration.md) - 详细配置和使用说明
- 🧪 [测试工具说明](test/diagnostic/test_external_sftp.py) - 配置验证工具
- 🎭 [功能演示](test/manual/wxchat/demo_external_sftp.py) - 功能演示脚本

---

## ⚡ **性能优化**

- ✅ 外部SFTP上传失败不影响主流程
- ✅ 异步处理提高效率
- ✅ 详细的日志记录便于问题排查
- ✅ 智能的错误重试机制

---

## 🛠️ **故障排查**

### **问题1：外部SFTP连接失败**
- 检查 `WXCHAT_EXTERNAL_SFTP_HOST` 是否正确
- 验证网络连接和防火墙设置
- 确认用户名和密码正确

### **问题2：排除逻辑未生效**
- 检查公众号名称是否完全匹配
- 确认使用原始公众号名称，不是文件名
- 验证 `.env` 文件配置格式

### **问题3：文件大小异常**
- 检查PDF生成是否完整
- 验证Playwright浏览器是否正确安装
- 查看详细日志排查问题

---

## 📈 **版本兼容性**

- ✅ **Python版本**: 3.8+
- ✅ **操作系统**: Windows 10/11
- ✅ **数据库**: MySQL 5.7+
- ✅ **依赖工具**: BaiduPCS-Go, Playwright

---

## 🎉 **总结**

这是一个功能完整的微信文章PDF处理系统，现在支持：

✅ **双SFTP上传** - 主SFTP + 外部SFTP同时上传
✅ **智能排除机制** - 通过公众号名称控制外部分发
✅ **灵活配置** - 支持多种使用场景
✅ **完整测试** - 提供专业测试和演示工具
✅ **向后兼容** - 不影响现有功能

**外部SFTP功能已完全就绪，可以立即使用！** 🚀
