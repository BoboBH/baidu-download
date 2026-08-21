# wxchat-article功能发布说明

## 版本信息
- **版本号**: v1.5.0
- **发布日期**: 2026-08-21
- **功能状态**: 生产就绪 ✅

---

## 功能概述

wxchat-article功能是对现有百度网盘下载系统的扩展，新增了对微信公众号文章链接的自动PDF生成和SFTP上传能力。

### 核心特性

1. **智能消息解析**
   - 自动识别微信文章链接格式
   - 提取文章ID和URL元数据
   - 支持多种消息格式输入

2. **PDF自动生成**
   - 复用现有wxchat的PDF生成引擎
   - 支持长文档和复杂排版
   - 自动处理图片和格式化

3. **SFTP标准化上传**
   - 与wxchat功能使用统一的路径结构
   - 自动创建日期目录 (/wxchat/YYYYMM/)
   - 标准化文件命名 (公众号_文章标题.pdf)

4. **钉钉反馈通知**
   - 实时处理状态反馈
   - 详细的错误信息报告
   - 支持成功/失败场景通知

5. **数据库记录完整性**
   - 完整的处理流程记录
   - 支持消息重试机制
   - 便于问题追踪和审计

---

## 使用方法

### 基本使用流程

1. **发送消息到钉钉群**
   ```
   请下载这篇文章的PDF: https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
   ```

2. **系统自动处理**
   - 消息解析 → 文章下载 → PDF生成 → SFTP上传 → 结果通知

3. **接收反馈通知**
   - ✅ 成功：文章标题、公众号、文件大小、上传路径
   - ❌ 失败：具体错误原因和重试建议

### 支持的消息格式

```
✅ 支持的格式：
- 请下载这篇文章的PDF: [文章URL]
- 生成PDF: [文章URL]
- [文章URL] 下载PDF
- 帮我转成PDF: [文章URL]

❌ 不支持的格式：
- 无效URL格式
- 无法访问的链接
- 需要特殊权限的文章
```

---

## 配置要求

### 必需配置项

#### 1. 核心wxchat配置
```bash
# 启用wxchat功能
WXCHAT_ENABLED=true

# SFTP远程基础路径（与wxchat共享）
WXCHAT_SFTP_REMOTE_PATH=/wxchat

# 微信文章基础URL
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
```

#### 2. PDF生成配置
```bash
# PDF生成超时时间（秒）
WXCHAT_PDF_TIMEOUT=300

# 图片加载等待时间（秒）
WXCHAT_IMAGE_WAIT_TIME=20

# 下载延迟时间（秒）
WXCHAT_DOWNLOAD_DELAY=5

# PDF文件最大大小（MB）
MAX_PDF_SIZE_MB=200
```

#### 3. SFTP配置
```bash
# SFTP服务器配置
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/remote/path
```

#### 4. 钉钉通知配置（至少一种）
```bash
# 方式1: Webhook通知
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 方式2: App通知
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_CHAT_ID=your_chat_id
```

#### 5. 数据库配置
```bash
# MySQL数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=baidu_download
DB_PASSWORD=your_password
DB_NAME=baidu_download
```

### 可选配置项

```bash
# 消息重试配置
MESSAGE_MAX_RETRIES=10
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY_MS=1000

# wxchat数据库配置（用于wechat-db集成）
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=wewe
WXCHAT_WEWE_DB_PASSWORD=wewe_password
WXCHAT_WEWE_DB_NAME=wewe

# 外部SFTP配置（可选的双重上传）
WXCHAT_EXTERNAL_SFTP_HOST=external_host
WXCHAT_EXTERNAL_SFTP_PORT=22
WXCHAT_EXTERNAL_SFTP_USERNAME=external_user
WXCHAT_EXTERNAL_SFTP_PASSWORD=external_password
WXCHAT_EXTERNAL_SFTP_FOLDER=/external/path
```

---

## 部署步骤

### 1. 配置验证

运行配置验证脚本：
```bash
python test/manual/wxchat/verify_wxchat_config.py
```

预期输出：
```
✅ 配置完整且有效，可以进行部署
```

### 2. 数据库表检查

确认数据库表存在：
```bash
python -c "from src.database.models import DatabaseManager; from src.config.settings import Settings; db = DatabaseManager(Settings()); print(db.get_all_tables())"
```

必需表：
- `messages` (消息记录表)
- `transfers` (传输记录表)

### 3. SFTP路径验证

运行SFTP验证脚本：
```bash
python test/manual/wxchat/validate_sftp_upload.py
```

预期输出：
```
✅ SFTP配置验证通过，可以进行部署
   基础路径: /wxchat
   路径结构: /wxchat/YYYYMM/公众号_文章标题.pdf
```

### 4. 钉钉通知测试

运行钉钉通知测试：
```bash
python test/manual/wxchat/test_dingtalk_notification.py
```

预期输出：
```
✅ 钉钉通知配置验证通过
   Webhook: 已配置
   AppKey: 已配置
```

### 5. 完整集成测试

运行完整流程测试：
```bash
python test/manual/wxchat/test_wxchat_article_full_flow.py
```

预期输出：
```
✅ 就绪 - 测试通过率 90.0% >= 80%
🚀 wxchat-article功能已准备就绪，可以进行生产部署！
```

### 6. 部署启动

```bash
# 启动自动处理模式
python main.py auto

# 或指定消息源
python main.py auto --source dingtalk
```

---

## 升级注意事项

### 从 v1.4.x 升级

1. **配置更新**
   - 新增 `WXCHAT_SFTP_REMOTE_PATH` 配置
   - 新增钉钉通知配置项

2. **数据库迁移**
   - 无需数据库结构变更
   - 现有表结构完全兼容

3. **路径变化**
   - wxchat-article与wxchat共享 `/wxchat/` 基础路径
   - 确保SFTP路径权限正确

4. **依赖更新**
   - 确保安装了所有必需依赖：`beautifulsoup4`, `requests`, `playwright`

### 兼容性说明

- ✅ 完全兼容现有百度网盘下载功能
- ✅ 完全兼容现有wxchat PDF功能
- ✅ 不影响现有消息处理流程
- ✅ 现有配置文件无需修改（新增配置有默认值）

---

## 已知限制

### 功能限制

1. **文章访问限制**
   - 需要公开访问权限的文章
   - 不支持付费/会员专属文章
   - 部分需要登录的文章无法处理

2. **PDF生成限制**
   - 超大文件可能生成失败（>200MB）
   - 复杂排版可能影响PDF质量
   - 图片加载需要稳定网络环境

3. **网络依赖**
   - 需要稳定的微信文章访问
   - 需要稳定的SFTP连接
   - 需要稳定的钉钉通知服务

### 性能限制

1. **处理时间**
   - 单篇文章处理时间: 30-300秒
   - PDF生成时间: 20-240秒
   - SFTP上传时间: 根据文件大小变化

2. **并发限制**
   - 当前版本支持单文件处理
   - 建议间隔发送多个文章请求

### 环境要求

1. **系统要求**
   - Python 3.8+
   - Windows/Linux操作系统
   - 足够的临时存储空间（建议5GB+）

2. **网络要求**
   - 可访问微信公众号服务器
   - 可访问SFTP服务器
   - 可访问钉钉API服务

---

## 故障排除

### 常见问题

#### 1. 消息解析失败
**症状**: 无法识别文章链接

**解决方案**:
```bash
# 检查消息格式
# 测试URL有效性
python -c "from src.processor.parsers.wxchat_article_processor import WxchatArticleProcessor; from src.config.settings import Settings; processor = WxchatArticleProcessor(Settings())"
```

#### 2. PDF生成失败
**症状**: PDF生成超时或失败

**解决方案**:
```bash
# 增加超时时间
export WXCHAT_PDF_TIMEOUT=600

# 检查Playwright安装
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

#### 3. SFTP上传失败
**症状**: 文件生成成功但上传失败

**解决方案**:
```bash
# 测试SFTP连接
python test/manual/wxchat/validate_sftp_upload.py

# 检查路径权限
# 确保 /wxchat/YYYYMM/ 路径可写
```

#### 4. 钉钉通知不发送
**症状**: 处理完成但无通知

**解决方案**:
```bash
# 检查钉钉配置
python test/manual/wxchat/test_dingtalk_notification.py

# 验证webhook有效性
curl -X POST "$DINGTALK_WEBHOOK" -H 'Content-Type: application/json' -d '{"text":"测试消息"}'
```

### 日志检查

```bash
# 查看处理日志
tail -f logs/transfer.log | grep wxchat

# 查看错误日志
grep "ERROR" logs/transfer.log | grep wxchat

# 查看完整处理流程
grep "wxchat-article" logs/transfer.log
```

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG

# 运行单个URL测试
python test/manual/wxchat/test_wxchat_article_full_flow.py
```

---

## 监控和维护

### 关键指标监控

1. **处理成功率**
   ```sql
   SELECT
       COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as success_rate
   FROM messages
   WHERE message_type = 'wxchat-article'
   AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);
   ```

2. **平均处理时间**
   ```sql
   SELECT
       AVG(TIMESTAMPDIFF(SECOND, created_at, completed_at)) as avg_processing_seconds
   FROM messages
   WHERE message_type = 'wxchat-article'
   AND status = 'completed'
   AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);
   ```

3. **存储空间使用**
   ```bash
   # 检查SFTP存储空间
   # 通过SFTP客户端检查 /wxchat 目录大小
   ```

### 定期维护任务

1. **清理临时文件**
   ```bash
   # 清理7天前的临时PDF文件
   find ./temp -name "wxchat_article_*" -mtime +7 -delete
   ```

2. **数据库优化**
   ```sql
   -- 清理旧的处理记录
   DELETE FROM messages WHERE message_type = 'wxchat-article' AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
   ```

3. **日志归档**
   ```bash
   # 归档30天前的日志
   tar -czf logs_$(date +%Y%m%d).tar.gz logs/*.log
   ```

---

## 安全建议

### 数据安全

1. **敏感信息保护**
   - 钉钉密钥存储在环境变量中
   - SFTP密码使用加密存储
   - 避免在日志中记录敏感信息

2. **访问控制**
   - 限制SFTP路径访问权限
   - 定期更换访问密钥
   - 监控异常访问行为

### 网络安全

1. **连接加密**
   - 使用SFTP加密传输
   - 验证钉钉Webhook证书
   - 限制数据库访问来源

2. **API限流**
   - 控制微信文章访问频率
   - 实现钉钉通知限流
   - 防止SFTP连接过载

---

## 支持和联系

### 技术支持

- **文档**: `docs/wxchat-article-release.md`
- **测试脚本**: `test/manual/wxchat/`
- **示例代码**: `test/manual/wxchat/demo_*.py`

### 反馈渠道

- **问题报告**: 通过现有项目issue系统
- **功能建议**: 通过项目讨论区
- **紧急支持**: 联系系统管理员

---

## 版本历史

### v1.5.0 (2026-08-21)
- ✅ wxchat-article功能首次发布
- ✅ 完整的消息解析和处理流程
- ✅ SFTP标准化上传
- ✅ 钉钉反馈通知
- ✅ 数据库记录完整性
- ✅ 综合集成测试通过

### 后续计划

- **v1.5.1**: 性能优化和错误处理增强
- **v1.6.0**: 批量处理支持
- **v1.7.0**: 自定义PDF样式支持

---

## 附录

### A. 测试URL示例

有效的微信文章URL：
```
https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ
```

### B. 路径结构示例

标准上传路径：
```
/wxchat/202608/技术公众号_深入理解Python异步编程.pdf
/wxchat/202608/新闻公众号_2026年科技趋势分析.pdf
```

### C. 通知消息示例

成功通知：
```
✅ 微信文章PDF生成成功
📄 文章: 深入理解Python异步编程
🏢 公众号: 技术公众号
📁 文件大小: 2.45MB
📂 远程路径: /wxchat/202608/技术公众号_深入理解Python异步编程.pdf
```

失败通知：
```
❌ 微信文章处理失败
原因: PDF生成超时
```

---

**文档版本**: 1.0
**最后更新**: 2026-08-21
**维护状态**: 活跃维护中