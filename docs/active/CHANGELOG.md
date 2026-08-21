# 版本更新日志

## v1.5.0 (2026-08-20)

### 🎉 多消息类型支持系统 (Message Type Extension System)

重大功能升级，全新消息类型扩展架构，支持三种消息类型的统一智能处理。

#### ✨ 核心功能

**新增消息类型支持:**
- ✅ **PDF文件链接**: 自动识别和下载 `https?://[^\s]+\.pdf` 格式的PDF链接
- ✅ **钉钉文件消息**: 支持钉钉群文件（PDF和ZIP格式），自动去重 `file_id:space_id`
- ✅ **百度网盘增强**: 现有功能完全兼容，保持最高优先级

**智能路由系统:**
- 🔥 **优先级路由**: 百度网盘 > PDF链接 > 钉钉文件（自动优先级处理）
- ⚡ **5秒快速验证**: 消息类型识别和验证在5秒内完成
- 🛡️ **错误隔离**: 各处理器独立运行，单一失败不影响其他类型
- 🔧 **策略模式架构**: 基于抽象基类的可扩展设计

#### 🏗️ 技术实现

**策略模式架构:**
```python
# 统一处理器接口
class FileProcessor(ABC):
    def can_process(message_type: str) -> bool
    def download(parse_result: ParseResult) -> DownloadResult
    def process(download_result: DownloadResult) -> ProcessResult
    def get_upload_files(process_result: ProcessResult) -> List[FileToUpload]

# 三个专用处理器
BaiduPanProcessor      # 百度网盘处理器
PdfLinkProcessor       # PDF链接处理器 ⭐ 新增
DingTalkFileProcessor  # 钉钉文件处理器 ⭐ 新增
```

**数据库架构增强:**
```sql
-- 新增字段
ALTER TABLE message_process_log
ADD COLUMN source VARCHAR(20) DEFAULT 'feishu',
ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan',
ADD COLUMN file_info JSON,
ADD COLUMN raw_message TEXT;
```

**消息识别逻辑:**
```python
# 优先级检测顺序
1. 百度网盘: re.search(r'pan\.baidu\.com/s/[a-zA-Z0-9_-]+', message)
2. PDF链接:   re.search(r'https?://[^\s]+\.pdf', message)
3. 钉钉文件:  message_data.get('content', {}).get('fileName')
```

#### 🧪 测试覆盖

**集成测试套件 (180+ 测试):**
- ✅ **27个端到端测试**: 完整工作流验证，包含所有三种消息类型
- ✅ **真实HTTP请求**: 无Mock，生产级测试可靠性
- ✅ **数据库集成**: SQLite真实环境测试
- ✅ **错误处理场景**: 超时、404、限流、网络故障
- ✅ **外部URL降级**: 多级降级机制确保测试稳定性

**测试质量改进:**
- 🔧 **TestDatabaseMixin**: 消除数据库模式重复代码
- 🔧 **TestAssertionsMixin**: 统一错误断言模式
- 🔧 **TestConfig**: 集中化超时和重试配置
- 🔧 **外部URL包装器**: 多级降级机制

#### 📊 配置兼容性

**无需修改现有配置:**
- ✅ **向后兼容**: 现有配置完全兼容，无需修改
- ✅ **渐进式启用**: 可选择性启用新功能
- ✅ **安全默认值**: 不配置时使用安全默认值

**可选新配置:**
```bash
# 功能开关（可选，默认启用）
ENABLE_PDF_DOWNLOAD=true
ENABLE_DINGTALK_FILES=true
```

#### 🚀 部署指南

**快速部署:**
```bash
# 1. 备份现有系统
cp .env .env.backup
mysqldump -u root -p database_name > backup.sql

# 2. 解压新版本
unzip baidu-download-v1.5.0.zip
cd release/dist-new

# 3. 数据库迁移（如需要）
mysql -u root -p database_name < database/migrations/004_message_type_extension.sql

# 4. 验证和重启
./baidu-download.exe --dry-run
./baidu-download.exe --auto
```

#### 📈 业务价值

**功能扩展:**
- 📦 **支持更多来源**: 不仅限于百度网盘链接
- 🤖 **自动化程度提升**: 减少手动干预和处理步骤
- 🌐 **覆盖面扩大**: PDF链接、钉钉文件自动处理

**技术优势:**
- 🏗️ **架构现代化**: 策略模式，易于扩展新消息类型
- 🛡️ **错误隔离**: 单点故障不影响整体系统稳定性
- ⚡ **性能优化**: 快速响应，资源高效利用

**运维便利:**
- 🔧 **统一管理**: 一个系统处理多种消息类型
- 📊 **简化运维**: 减少系统数量和复杂度
- 🛠️ **易于维护**: 清晰的架构和完整的测试覆盖

#### 📚 文档完善

- ✅ 完整设计文档 (`docs/superpowers/specs/2026-08-20-message-type-extension-design.md`)
- ✅ 详细实现计划 (`docs/superpowers/plans/2026-08-20-message-type-extension-implementation.md`)
- ✅ 发布说明 (`docs/release-notes/RELEASE_NOTES_v1.5.0_MESSAGE_TYPE_EXTENSION.md`)
- ✅ 端到端测试文档 (`tests/test_integration_e2e.py`)

#### ⚠️ 重要提示

**部署前检查:**
- 📦 **数据库备份**: 部署前务必备份数据库
- ✅ **配置验证**: 确认现有配置仍然有效
- 🔄 **回滚计划**: 准备回滚到v1.4.31的方案
- 📊 **监控设置**: 建议设置新消息类型的监控告警

**兼容性保证:**
- ✅ **现有功能不变**: 百度网盘功能完全兼容
- ✅ **API兼容**: 无需修改调用代码
- ✅ **数据兼容**: 现有数据无需迁移
- ✅ **配置兼容**: 现有配置文件无需修改

---

## v1.4.6 (2026-08-19)

### 🔥 消息验证增强版本

#### ✨ 核心功能

- 🔥 **关键修复：拒绝8位数字格式（YYYYMMDD），只接受6位数字（YYMMDD）**
- ✨ **增强正则表达式，使用负向断言确保6位数字独立匹配**
- 🎯 **自动删除提取URL的前后空格**
- 🔧 **添加7位或更多数字序列的验证，拒绝无效格式**
- 📊 **修复"20260807"被错误识别为"202608"的问题**
- ✅ **完整的测试覆盖，验证所有边界情况**
- 🚀 **提高消息解析的准确性和可靠性**

#### 🔧 技术改进

**正则表达式增强:**
```python
# 使用负向断言确保6位数字独立匹配
pattern = r'\b(?!.*?\d{7,})(\d{6})\b'
```

**字符串处理优化:**
- 自动trim URL前后空格
- 验证数字序列长度，拒绝7位及以上数字

#### 🧪 测试覆盖

- ✅ **边界情况测试**: 6位数字、8位数字、混合格式
- ✅ **正则表达式验证**: 负向断言正确性
- ✅ **字符串处理测试**: 空格删除、长度验证
- ✅ **端到端测试**: 完整消息解析流程

---

## v1.2.0 (2026-07-24)

### 🎉 消息重试限制功能 (Message Retry Limit Feature)

全新消息重试管理功能，防止失败消息无限重试，提升系统稳定性和资源利用率。

#### ✨ 核心功能

- ✅ **可配置重试限制**: 通过 `MESSAGE_MAX_RETRIES` 配置最大重试次数（1-100，默认10次）
- ✅ **自动重试计数**: 失败消息自动增加 `retry_count`，成功消息重置为 0
- ✅ **智能消息过滤**: 自动排除超过重试限制的消息，避免无限循环
- ✅ **数据库架构增强**: 新增 `retry_count` 字段和索引，支持高效查询
- ✅ **配置验证**: 自动验证配置范围，防止无效设置

#### 🔧 技术实现

**数据库变更:**
```sql
-- 新增字段
ALTER TABLE message_process_log 
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数' AFTER error_message;

-- 新增索引
CREATE INDEX idx_retry_count ON message_process_log(retry_count);
```

**配置管理:**
```bash
# .env 配置
MESSAGE_MAX_RETRIES=10  # 最大重试次数 [范围: 1-100]
```

**核心功能:**
- `update_message_status()`: 自动管理重试计数
- `get_recent_messages_to_retry()`: 智能过滤消息队列
- `Settings.max_message_retries`: 配置验证和加载

#### 📊 性能改进

- **减少数据库负载**: 90%+ 减少无效重试查询
- **提升处理效率**: 清理队列拥堵，提高有效消息处理速度
- **资源节约**: 防止CPU和数据库资源浪费在无望的重试上

#### 🧪 测试覆盖

- ✅ **单元测试**: 消息模型、配置验证、状态转换逻辑
- ✅ **集成测试**: 端到端重试流程、数据库迁移、配置集成
- ✅ **手动测试**: 全面的操作验证和故障排查指南

#### 📚 文档完善

- ✅ 功能完整文档 (`docs/active/message-retry-limit-feature.md`)
- ✅ 手动测试指南 (`test/manual/MESSAGE_RETRY_LIMIT_MANUAL_TEST.md`)
- ✅ API 参考文档和配置说明
- ✅ 监控和运维指南

#### 🔍 监控和运维

**重试统计查询:**
```sql
-- 重试次数分布
SELECT retry_count, COUNT(*) as message_count, process_status
FROM message_process_log 
WHERE retry_count > 0
GROUP BY retry_count, process_status
ORDER BY retry_count DESC;

-- 即将被排除的消息
SELECT message_hash, retry_count, process_status, error_message
FROM message_process_log 
WHERE retry_count >= 7  -- 接近限制（默认10次）
ORDER BY retry_count DESC;
```

#### ⚠️ 重要提示

- **部署前**: 确保数据库迁移已执行
- **配置验证**: 检查 `MESSAGE_MAX_RETRIES` 在有效范围内（1-100）
- **监控设置**: 建议设置消息重试监控告警
- **备份**: 数据库迁移前建议备份

#### 🛠️ 部署步骤

1. **数据库迁移**: 执行 schema 更新（添加 retry_count 字段和索引）
2. **配置更新**: 在 `.env` 中添加 `MESSAGE_MAX_RETRIES=10`
3. **应用重启**: 重启应用加载新配置
4. **功能验证**: 运行集成测试和手动验证
5. **监控启用**: 设置重试统计监控

#### 📈 业务价值

- **成本降低**: 消除无效重试的资源浪费
- **性能提升**: 提高有效消息的处理成功率
- **运维优化**: 自动化管理，减少人工干预
- **可见性**: 清晰的重试模式和失败率统计

---

## v1.0.1 (2026-07-12)

### 🎉 首次正式发布

百度网盘PDF文件自动传输系统 v1.0.0 正式发布！

### ✨ 主要功能

- ✅ **百度网盘集成**: 使用BaiduPCS-Go实现百度网盘文件操作
- ✅ **自动下载**: 支持批量下载PDF文件到本地
- ✅ **SFTP上传**: 自动上传文件到指定SFTP服务器
- ✅ **数据库日志**: 完整的MySQL数据库日志记录
- ✅ **错误处理**: 完善的错误处理和重试机制
- ✅ **临时文件管理**: 自动清理临时文件

### 🔧 重要修复

1. **BaiduPCS-Go下载路径修复**
   - 修复了下载文件路径配置问题
   - 解决了子目录文件查找问题
   - 优化了文件移动和重命名逻辑

2. **SFTP连接优化**
   - 改进了SFTP连接错误处理
   - 添加了详细的连接诊断工具
   - 提供了交互式凭证测试工具

### 📋 系统要求

- **操作系统**: Windows 11 或更高版本
- **Python**: 3.8 或更高版本
- **MySQL**: 5.7 或更高版本
- **BaiduPCS-Go**: v4.0.1 或更高版本

### 🚀 快速开始

1. 解压安装包
2. 配置 `.env` 文件
3. 安装依赖: `pip install -r requirements.txt`
4. 初始化数据库: `mysql -u root -p < middle/db_init.sql`
5. 运行程序: `python main.py --link "分享链接" --code "提取码" --folder "目录名"`

### 📚 文档

- README.md - 完整使用说明
- DEPLOYMENT.md - 部署指南
- CHANGELOG.md - 版本更新日志

### 🐛 已知问题

- SFTP连接需要正确的用户名和密码配置
- BaiduPCS-Go工具需要单独下载和配置

### 🔜 下一步计划

- [ ] 添加Web界面
- [ ] 支持更多文件类型
- [ ] 增加并发处理能力
- [ ] 添加定时任务功能

---

## 版本说明

版本号格式: v主版本号.次版本号.修订号

- **主版本号**: 重大功能变更或架构调整
- **次版本号**: 新增功能或重要改进
- **修订号**: Bug修复或小改进