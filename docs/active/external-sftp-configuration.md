# 微信文章外部SFTP配置指南

## 🎯 功能说明

微信文章PDF生成功能现在支持同时上传到两个SFTP服务器：

1. **主SFTP服务器** - 内部使用，存储所有文章PDF
2. **外部SFTP服务器** - 外部用户访问，可排除特定公众号

## 📋 配置步骤

### 1. 配置环境变量

在 `.env` 文件中添加以下配置：

```bash
# ===== 微信文章外部SFTP配置 (可选) =====
# 外部用户SFTP服务器配置
WXCHAT_EXTERNAL_SFTP_HOST=external_sftp.example.com
WXCHAT_EXTERNAL_SFTP_PORT=22
WXCHAT_EXTERNAL_SFTP_USERNAME=external_user
WXCHAT_EXTERNAL_SFTP_PASSWORD=external_password
WXCHAT_EXTERNAL_SFTP_FOLDER=/external/wechat

# 排除的公众号名称列表 (用逗号分隔)
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=内部账号,测试账号,临时账号
```

### 2. 测试外部SFTP连接

使用测试工具验证配置是否正确：

```bash
python test/diagnostic/test_external_sftp.py
```

测试工具会检查：
- ✅ 外部SFTP连接配置
- ✅ 网络连接测试
- ✅ 文件上传测试
- ✅ 排除逻辑测试

### 3. 运行微信文章处理

配置完成后，正常使用微信文章处理命令：

```bash
# 处理最近7天的文章
python main.py --wxchat --wxchat-days 7

# 使用打包的exe
baidu-download.exe --wxchat --wxchat-days 7
```

## 🔧 工作原理

### 文件处理流程

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

### 排除逻辑

公众号排除检查：
1. 检查公众号名称是否在 `WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS` 中
2. 如果在排除列表中，跳过外部SFTP上传
3. 如果不在排除列表，正常上传到外部SFTP

### 文件组织结构

**主SFTP服务器结构：**
```
/wxchat/
├── 2407/
│   ├── 公众号A_文章标题1.pdf
│   ├── 公众号B_文章标题2.pdf
│   └── ...
└── 2408/
    └── ...
```

**外部SFTP服务器结构：**
```
/external/wechat/
├── 2407/
│   ├── 公众号B_文章标题2.pdf  (排除账号A的文件)
│   └── ...
└── 2408/
    └── ...
```

## 🧪 测试场景

### 场景1：仅配置主SFTP

```bash
# .env 配置
WXCHAT_EXTERNAL_SFTP_HOST=     # 留空

# 结果：所有文章上传到主SFTP，无外部上传
```

### 场景2：配置外部SFTP，无排除

```bash
# .env 配置
WXCHAT_EXTERNAL_SFTP_HOST=external.example.com
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=   # 留空

# 结果：所有文章同时上传到主SFTP和外部SFTP
```

### 场景3：配置外部SFTP，有排除

```bash
# .env 配置
WXCHAT_EXTERNAL_SFTP_HOST=external.example.com
WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS=内部账号,测试账号

# 结果：
# - "内部账号"和"测试账号"的文章只上传到主SFTP
# - 其他公众号的文章同时上传到两个SFTP
```

## 🔍 故障排查

### 问题1：外部SFTP连接失败

**错误信息：** `外部SFTP上传异常: Connection refused`

**解决方案：**
1. 检查 `WXCHAT_EXTERNAL_SFTP_HOST` 是否正确
2. 检查 `WXCHAT_EXTERNAL_SFTP_PORT` 是否正确
3. 确认网络连接正常
4. 验证用户名和密码

### 问题2：外部SFTP目录创建失败

**错误信息：** `外部SFTP上传异常: Permission denied`

**解决方案：**
1. 检查 `WXCHAT_EXTERNAL_SFTP_FOLDER` 路径是否正确
2. 确认SFTP用户有目录创建权限
3. 手动创建目标目录并设置权限

### 问题3：特定公众号未按预期排除

**检查方法：**
```python
# 查看当前排除配置
python -c "from src.config.settings import Settings; config = Settings(); print('排除列表:', config.wxchat_external_exclude_accounts)"
```

**解决方案：**
1. 检查公众号名称是否完全匹配
2. 确认使用的是原始公众号名称，不是安全文件名
3. 检查 `.env` 文件中配置格式是否正确

## 📊 日志输出

正常处理时的日志示例：

```
[INFO] 处理文章: 技术分享_Git入门教程 (abc123)
[INFO] PDF生成成功，文件大小: 1.2MB
[INFO] PDF上传成功: /wxchat/2407/技术分享_Git入门教程.pdf
[INFO] 开始上传到外部SFTP: external.example.com
[INFO] 外部SFTP上传成功: /external/wechat/2407/技术分享_Git入门教程.pdf
```

排除公众号时的日志示例：

```
[INFO] 处理文章: 内部测试_机密文档 (xyz789)
[INFO] PDF生成成功，文件大小: 0.8MB
[INFO] PDF上传成功: /wxchat/2407/内部测试_机密文档.pdf
[INFO] 公众号 '内部测试' 在排除列表中，跳过外部SFTP上传
```

## 🎉 总结

外部SFTP功能提供了灵活的文件分发机制：

✅ **安全可控** - 通过排除机制控制内容分发
✅ **自动运行** - 无需手动干预，自动处理上传
✅ **容错设计** - 外部上传失败不影响主流程
✅ **易于测试** - 提供专门的测试工具

配置完成后，系统会自动将合适的文章分发到外部用户SFTP服务器！
