# 多消息类型支持系统 - 用户指南

## 📋 概述

百度网盘PDF文件自动传输系统 v1.5.0 引入了全新的多消息类型支持功能，扩展了系统的自动化处理能力。现在系统可以智能识别和处理三种不同类型的消息：

1. **百度网盘共享链接** (现有功能)
2. **PDF文件链接** (新增功能) 
3. **钉钉文件消息** (新增功能)

## 🎯 核心特性

### 智能消息识别

系统使用优先级路由算法，自动识别消息类型并分配给对应的处理器：

```
消息接收 → 类型路由 → 分处理器 → SFTP上传 → 状态更新
(5秒验证)  (优先级)  (独立执行)  (冲突处理)  (重试机制)
```

**优先级顺序：**
1. **百度网盘** - 最高优先级 ⭐⭐⭐
2. **PDF链接** - 中等优先级 ⭐⭐
3. **钉钉文件** - 最低优先级 ⭐

### 关键优势

- ✅ **5秒快速验证**: 消息类型识别和验证在5秒内完成
- ✅ **错误隔离**: 各处理器独立运行，单一失败不影响其他类型
- ✅ **向后兼容**: 现有百度网盘功能完全不受影响
- ✅ **可扩展性**: 基于策略模式，易于添加新消息类型

## 🚀 使用指南

### 1. 百度网盘共享链接 (现有功能)

**消息格式:**
```
百度网盘文件: https://pan.baidu.com/s/xxxxx
```

**识别规则:**
- 正则表达式: `https://pan.baidu.com/s/[a-zA-Z0-9_-]+`
- 最高优先级处理
- 使用统一提取码 (默认: `0409`)

**处理流程:**
1. 识别百度网盘链接
2. 自动应用统一提取码
3. 下载文件到本地临时目录
4. 通过SFTP上传到目标服务器
5. 记录处理日志

### 2. PDF文件链接 (新增功能)

**消息格式:**
```
PDF文档: https://example.com/document.pdf
```

**识别规则:**
- 正则表达式: `https?://[^\s]+\.pdf`
- 中等优先级处理
- 支持HTTP和HTTPS协议

**处理流程:**
1. 识别PDF链接格式
2. 流式下载PDF文件（内存高效）
3. 实时监控文件大小
4. 验证PDF完整性
5. 通过SFTP上传到目标服务器

**配置选项:**
```bash
# PDF文件大小限制（MB）
MAX_PDF_SIZE_MB=200  # 默认200MB

# PDF下载超时设置（秒）
PDF_DOWNLOAD_TIMEOUT=300  # 默认5分钟
```

**使用示例:**
```python
# 飞书/钉钉消息发送
"请处理这份PDF报告: https://example.com/financial-report.pdf"

# 系统自动识别并下载PDF文件
# 处理完成后上传到SFTP服务器
```

### 3. 钉钉文件消息 (新增功能)

**消息格式:**
```json
{
  "content": {
    "fileName": "report.pdf",
    "fileId": "file_v1_xxxxx",
    "spaceId": "space_v1_yyyyy"
  }
}
```

**识别规则:**
- 检测消息JSON中的 `content.fileName` 字段
- 最低优先级处理
- 支持PDF和ZIP文件格式

**处理流程:**
1. 解析钉钉消息JSON结构
2. 提取 `fileId` 和 `spaceId` 信息
3. 使用消息级别去重: `file_id:space_id`
4. 下载文件到本地
5. 通过SFTP上传到目标服务器

**去重机制:**
- 使用 `file_id:space_id` 组合作为唯一标识
- 防止重复处理相同文件
- 自动跳过已处理的文件

## 🔧 配置说明

### 环境变量配置

系统使用标准的 `.env` 文件进行配置，新增功能无需修改现有配置：

```bash
# ========== 现有配置（无需修改）==========
# 百度网盘配置
BAIDUPCS_GO_PATH=/path/to/baidupcs-go
BAIDU_COOKIES_PATH=./baidu-cookies.txt
MESSAGE_DEFAULT_EXTRACTION_CODE=0409

# SFTP配置
SFTP_HOST=sftp.example.com
SFTP_PORT=22
SFTP_USERNAME=user
SFTP_PASSWORD=password
SFTP_REMOTE_PATH=/uploads

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=baidu_download

# ========== 新增配置（可选）==========
# PDF下载功能开关
ENABLE_PDF_DOWNLOAD=true  # 默认启用

# PDF文件大小限制（MB）
MAX_PDF_SIZE_MB=200

# PDF下载超时（秒）
PDF_DOWNLOAD_TIMEOUT=300

# 钉钉文件处理开关
ENABLE_DINGTALK_FILES=true  # 默认启用

# 钉钉API配置
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_CHAT_ID=your_chat_id
```

### 配置兼容性

✅ **完全向后兼容** - 现有配置无需任何修改即可使用新功能。

如果不配置新增选项，系统使用以下安全默认值：
- `ENABLE_PDF_DOWNLOAD=true` - PDF下载功能启用
- `MAX_PDF_SIZE_MB=200` - 200MB文件大小限制
- `ENABLE_DINGTALK_FILES=true` - 钉钉文件处理启用

## 📊 监控和排查

### 消息类型分布查询

```sql
-- 查看最近24小时的消息类型分布
SELECT message_type, COUNT(*) as count, process_status
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY message_type, process_status
ORDER BY message_type, process_status;
```

### 处理成功率统计

```sql
-- 各消息类型的成功率统计
SELECT message_type, 
       SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as success,
       COUNT(*) as total,
       ROUND(SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY message_type;
```

### 日志监控

```bash
# 查看新消息类型处理日志
grep "PdfLinkProcessor\|DingTalkFileProcessor" logs/transfer.log

# 查看PDF下载相关日志
grep "PDF download" logs/transfer.log

# 查看钉钉文件处理日志
grep "DingTalk file" logs/transfer.log
```

### 故障排查

**PDF下载失败:**
```bash
# 检查网络连接
curl -I https://example.com/document.pdf

# 验证URL可访问性
./baidu-download.exe --test-url "https://example.com/document.pdf"

# 查看详细错误日志
tail -f logs/transfer.log | grep "PDF"
```

**钉钉文件处理失败:**
```bash
# 验证钉钉API配置
./baidu-download.exe --verify-dingtalk-config

# 检查文件权限
./baidu-download.exe --check-file-access "file_id"

# 查看钉钉相关日志
tail -f logs/transfer.log | grep "DingTalk"
```

## 🛠️ 高级功能

### 消息级别去重

钉钉文件处理使用智能去重机制：

```python
# 去重标识生成
file_key = f"{file_id}:{space_id}"

# 数据库查询检查
existing = get_message_by_hash(file_key)
if existing:
    logger.info(f"Skipping duplicate DingTalk file: {file_key}")
    return
```

### 流式下载处理

PDF文件使用流式下载，优化内存使用：

```python
# 流式下载配置
CHUNK_SIZE = 8192  # 8KB块大小
MAX_SIZE = 200 * 1024 * 1024  # 200MB限制

# 内存高效处理
with requests.get(pdf_url, stream=True) as response:
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        if total_size + len(chunk) > MAX_SIZE:
            raise FileSizeExceededError()
        file.write(chunk)
        total_size += len(chunk)
```

### 错误处理和重试

所有消息类型都使用统一的错误处理和重试机制：

```python
# 重试配置
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY_MS=1000
RETRY_MAX_DELAY_MS=16000

# 错误分类
- 可重试错误: 网络超时、连接失败、临时服务器错误
- 不可重试错误: 404文件不存在、403权限拒绝、文件过大
```

## 🚦 部署检查清单

### 部署前准备

- [ ] 备份现有数据库
- [ ] 备份当前配置文件 (.env)
- [ ] 验证现有配置完整性
- [ ] 准备回滚计划

### 部署步骤

1. **备份操作**
   ```bash
   cp .env .env.backup
   mysqldump -u root -p database_name > backup.sql
   ```

2. **版本升级**
   ```bash
   unzip baidu-download-v1.5.0.zip
   cd release/dist-new
   ```

3. **数据库迁移** (如需要)
   ```bash
   mysql -u root -p database_name < database/migrations/004_message_type_extension.sql
   ```

4. **配置验证**
   ```bash
   ./baidu-download.exe --dry-run
   ```

5. **服务重启**
   ```bash
   ./baidu-download.exe --auto
   ```

### 部署后验证

- [ ] 检查日志无错误信息
- [ ] 验证百度网盘功能正常
- [ ] 测试PDF链接处理
- [ ] 测试钉钉文件处理
- [ ] 检查数据库记录完整性
- [ ] 验证SFTP上传功能

## 📚 相关文档

### 官方文档
- [主README](docs/active/README.md) - 系统概述
- [部署指南](docs/active/DEPLOYMENT.md) - 详细部署步骤
- [快速开始](docs/active/QUICK_START.md) - 5分钟快速部署
- [变更日志](docs/active/CHANGELOG.md) - 版本更新历史

### 技术文档
- [设计文档](docs/superpowers/specs/2026-08-20-message-type-extension-design.md) - 架构设计
- [实现计划](docs/superpowers/plans/2026-08-20-message-type-extension-implementation.md) - 实现细节
- [发布说明](docs/release-notes/RELEASE_NOTES_v1.5.0_MESSAGE_TYPE_EXTENSION.md) - 版本发布信息

### 测试文档
- [集成测试](tests/test_integration_e2e.py) - 端到端测试
- [重试机制测试](tests/test_retry_integration.py) - 重试逻辑测试

## 🔗 技术支持

### 常见问题

**Q: 新功能会影响现有百度网盘功能吗？**
A: 不会。系统设计完全向后兼容，现有百度网盘功能不受任何影响。

**Q: 如何禁用某个新功能？**
A: 在 `.env` 文件中设置对应的开关为 `false`，如 `ENABLE_PDF_DOWNLOAD=false`。

**Q: PDF文件大小限制可以调整吗？**
A: 可以。修改 `MAX_PDF_SIZE_MB` 配置项，建议不要超过500MB。

**Q: 如何监控新消息类型的处理情况？**
A: 使用文档提供的SQL查询和日志监控命令，可以实时了解各消息类型的处理状态。

### 获取帮助

- 📧 **邮件支持**: support@baidu-download.com
- 📚 **文档中心**: [docs/](docs/)
- 🐛 **问题报告**: GitHub Issues
- 💬 **社区讨论**: GitHub Discussions

---

**版本**: v1.5.0  
**最后更新**: 2026-08-20  
**维护团队**: baidu-download team