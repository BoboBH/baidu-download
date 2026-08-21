# 微信文章链接钉钉消息类型设计文档

## 概述

新增微信文章链接的钉钉消息类型`wxchat-article`，允许用户在钉钉中私发或群中@机器人发送微信文章链接，系统自动将文章下载成PDF并上传到SFTP。

**设计日期:** 2026-08-21
**功能状态:** 新功能设计
**优先级:** 中等

---

## 功能需求

### 核心功能
1. **消息识别**: 识别微信文章链接格式 `https://mp.weixin.qq.com/s/[article_id]`
2. **PDF生成**: 使用现有wxchat PDF生成核心逻辑，将文章转换为PDF
3. **文件命名**: 使用文章标题作为PDF文件名
4. **SFTP上传**: 上传到与wxchat相同的路径结构
5. **钉钉反馈**: 处理完成后通过钉钉发送成功/失败通知

### 用户场景
- 用户在钉钉群聊中@机器人发送微信文章链接
- 用户私聊机器人发送微信文章链接
- 系统自动处理并反馈结果

---

## 技术架构

### 1. 消息路由扩展

**文件**: `src/feishu/message_parser.py`

**扩展内容**:
```python
# 添加微信文章链接识别模式
WXCHAT_ARTICLE_PATTERN = re.compile(
    r'(https://mp\.weixin\.qq\.com/s/[a-zA-Z0-9_-]+)'
)

# 优先级顺序: Baidu Pan > PDF Link > 微信文章 > DingTalk
```

**优先级设计**:
1. Baidu Pan (最高优先级，保持向后兼容)
2. PDF Link
3. **微信文章链接** (新增)
4. DingTalk文件

### 2. 处理器架构

**新增文件**: `src/processor/parsers/wxchat_article_processor.py`

**处理器职责**:
- 链接验证和article_id提取
- 文章标题提取（通过网页解析）
- 复用wxchat PDF生成核心代码
- SFTP上传路径管理
- 错误处理和重试逻辑

**核心设计原则**:
- **代码复用**: 直接复用`src/wxchat/processor.py`中的`PDFGenerator`类
- **路径一致**: 使用相同的`wxchat_sftp_remote_path`配置
- **独立处理器**: 作为独立的processor类，便于维护和测试

### 3. 数据库设计

**使用现有表**: `message_process_log`

**记录内容**:
```sql
INSERT INTO message_process_log (
    message_type,        -- 'wxchat-article'
    original_message,    -- 原始微信文章链接
    parsed_data,         -- JSON: {article_id, title, pdf_url}
    status,              -- 'processing', 'completed', 'failed'
    error_message,       -- 错误信息（如果失败）
    retry_count,         -- 重试次数
    created_at,          -- 创建时间
    updated_at           -- 更新时间
) VALUES (...)
```

**无需新建表**: 简化设计，直接使用现有的message_process_log表。

### 4. PDF生成核心代码复用

**复用来源**: `src/wxchat/processor.py`中的`PDFGenerator`类

**关键方法**:
```python
class PDFGenerator:
    def generate_pdf(self, article_id: str, output_path: str) -> bool:
        """使用Playwright生成PDF"""
        # 页面加载
        # 滚动模拟
        # 图片等待
        # PDF生成
```

**集成方式**:
```python
# 在wxchat_article_processor.py中
from src.wxchat.processor import PDFGenerator

class WxchatArticleProcessor:
    def __init__(self, settings):
        self.pdf_generator = PDFGenerator(settings)
        self.wxchat_base_path = settings.wxchat_sftp_remote_path
```

---

## 数据流程

### 1. 消息接收流程

```
钉钉消息 → MessageReceiver → MessageParser → ParseResult
                                     ↓
                             识别微信文章链接
                                     ↓
                             message_type='wxchat-article'
```

### 2. 异步处理流程

```
AutoProcessor → ProcessorRouter → WxchatArticleProcessor
                                      ↓
                              1. 提取article_id
                              2. 提取文章标题（HTTP请求）
                              3. 调用PDFGenerator.generate_pdf()
                              4. 生成SFTP上传路径
                              5. SFTP上传
                                      ↓
                              更新message_process_log状态
                                      ↓
                              发送钉钉反馈通知
```

### 3. 错误处理流程

```
任何步骤失败 → 记录错误到message_process_log
              ↓
              更新status='failed'
              ↓
              发送钉钉错误通知
              ↓
              判断retryable → 是：increment retry_count
                               否：标记为永久失败
```

---

## 文件命名策略

### 命名规则
使用**文章标题**作为PDF文件名，与现有wxchat处理保持一致。

### 实现方式
1. **标题提取**: 通过HTTP请求微信文章页面，解析`<meta property="og:title">`标签
2. **文件名清理**: 移除特殊字符，限制长度，保留中文
3. **路径结构**: `/wxchat/YYYYMM/公众号名称_文章标题.pdf`

### 示例
```python
# 输入链接: https://mp.weixin.qq.com/s/ABC123
# 提取标题: "如何提高工作效率"
# 公众号: "技术分享号"
# 最终文件: /wxchat/202608/技术分享号_如何提高工作效率.pdf
```

---

## SFTP上传路径

### 路径配置
使用现有配置: `settings.wxchat_sftp_remote_path = '/wxchat'`

### 路径结构
```
/wxchat/
    └── YYYYMM/
        ├── 公众号A_文章1.pdf
        ├── 公众号A_文章2.pdf
        └── 公众号B_文章3.pdf
```

### 代码实现
```python
remote_path = f"{settings.wxchat_sftp_remote_path}/{year_month}/{filename}"
```

---

## 钉钉反馈通知

### 成功通知
```json
{
  "msgtype": "text",
  "text": {
    "content": "✅ 微信文章处理成功\n文件: 技术分享号_如何提高工作效率.pdf\n已上传到: /wxchat/202608/"
  }
}
```

### 失败通知
```json
{
  "msgtype": "text", 
  "text": {
    "content": "❌ 微信文章处理失败\n链接: https://mp.weixin.qq.com/s/ABC123\n错误: PDF生成超时"
  }
}
```

### 通知时机
- **立即反馈**: 消息接收后立即发送"开始处理"通知
- **完成反馈**: 处理完成后发送成功/失败通知
- **重试反馈**: 如果重试，通知用户正在重试

---

## 错误处理和重试

### 可重试错误
- 网络超时
- PDF生成临时失败
- SFTP连接问题
- 微信服务器临时不可用

### 不可重试错误
- 无效的微信文章链接
- 文章已被删除
- 文件系统错误
- 权限问题

### 重试配置
使用现有`message_retry_limit`配置（默认3次）。

---

## 性能考虑

### PDF生成性能
- 使用现有Playwright配置
- 默认超时: 300秒（可配置）
- 图片等待时间: 20秒（可配置）

### 并发处理
- 每个消息独立异步处理
- 不阻塞其他消息处理
- 支持多个微信文章同时处理

### 资源清理
- 使用临时目录存储中间文件
- 处理完成后自动清理
- 即使失败也清理临时文件

---

## 测试策略

### 单元测试
1. **链接识别测试**: 验证各种微信文章链接格式
2. **标题提取测试**: 测试各种文章页面结构
3. **PDF生成测试**: Mock PDFGenerator，测试调用流程
4. **文件命名测试**: 验证文件名清理和生成逻辑

### 集成测试
1. **完整流程测试**: 从消息接收到SFTP上传
2. **错误处理测试**: 模拟各种失败场景
3. **钉钉通知测试**: 验证反馈消息正确性

### 手动测试
1. 发送真实的微信文章链接
2. 验证PDF生成质量
3. 检查SFTP上传结果
4. 确认钉钉通知内容

---

## 配置项

### 现有配置复用
- `wxchat_sftp_remote_path`: SFTP上传基础路径
- `wxchat_pdf_timeout`: PDF生成超时时间
- `wxchat_image_wait_time`: 图片等待时间
- `message_retry_limit`: 消息重试次数限制

### 无需新增配置
所有功能都使用现有配置项，保持配置简洁。

---

## 向后兼容性

### 现有功能影响
- **无影响**: 新增消息类型，不影响现有baidupan、pdf_link、dingtalk处理
- **优先级明确**: 微信文章优先级低于Baidu Pan，确保向后兼容

### 数据库兼容性
- 使用现有表结构，无需迁移
- 不影响现有数据记录

---

## 部署计划

### 阶段1: 核心功能实现
1. 扩展MessageParser添加微信文章链接识别
2. 创建WxchatArticleProcessor处理器
3. 实现PDF生成和SFTP上传

### 阶段2: 反馈和错误处理
1. 集成钉钉反馈通知
2. 实现错误处理和重试逻辑
3. 完善日志记录

### 阶段3: 测试和优化
1. 单元测试和集成测试
2. 性能优化
3. 文档完善

---

## 未来扩展

### 可能的功能增强
1. 支持批量处理多个微信文章链接
2. 添加文章内容缓存机制
3. 支持自定义PDF样式
4. 添加文章元数据提取（作者、发布时间等）

### 扩展性考虑
- 处理器设计独立，便于未来功能扩展
- 核心代码复用，确保一致性
- 配置化设计，便于灵活调整

---

## 风险和缓解

### 技术风险
1. **微信文章页面结构变化**: 缓解使用多种标题提取方法
2. **PDF生成失败**: 缓解完善的重试机制和错误处理
3. **SFTP连接问题**: 缓解使用现有成熟的SFTP客户端

### 业务风险
1. **用户发送无效链接**: 缓解良好的错误提示和反馈
2. **文章已删除**: 缓解友好的错误通知
3. **文件命名冲突**: 缓解使用时间戳避免冲突

---

## 附录

### 微信文章链接格式
```
标准格式: https://mp.weixin.qq.com/s/[article_id]
示例: https://mp.weixin.qq.com/s/ABC123XYZ
```

### 现有wxchat处理器位置
- PDF生成: `src/wxchat/processor.py` (PDFGenerator类)
- 配置: `src/config/settings.py` (wxchat_* 配置项)
- 数据库: `message_process_log` 表

### 相关文档
- 现有wxchat功能: `docs/wxchat_usage.md`
- SFTP配置: `docs/active/WXCHAT_SFTP_CONFIG.md`
- 钉钉集成: `docs/active/dingtalk-message-receiver-usage.md`

---

**设计文档版本:** 1.0
**最后更新:** 2026-08-21
**设计者:** Claude (Subagent-Driven Development)