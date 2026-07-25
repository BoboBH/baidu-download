# 钉钉消息接收功能设计文档

**创建日期：** 2026-07-25  
**状态：** 待实施  
**版本：** 1.0

## 1. 概述

### 1.1 目标

在现有飞书消息接收系统基础上，扩展支持钉钉群消息接收，实现：
- 从钉钉群主动获取消息（轮询API模式）
- 识别钉钉消息中的百度网盘链接和文件夹信息
- 将消息存储到数据库（与飞书消息共用表，通过`source`字段区分）
- 保留现有飞书通道（并行支持双来源）
- 最小化代码改动，复用现有架构

### 1.2 钉钉消息格式

**示例：** `260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg`

**格式分析：**
- 提取码：6位数字（YYDDMM格式）
- 分隔符：中文冒号`：`或英文冒号`:`
- 百度网盘链接：标准pan.baidu.cn/s/格式

### 1.3 设计原则

- **最小化扩展**：在现有架构基础上新增钉钉支持，避免大规模重构
- **统一处理**：钉钉和飞书消息使用同一处理流程和数据库表
- **自动识别**：通过正则匹配自动识别消息格式和来源
- **向后兼容**：保留现有飞书功能，默认行为不变

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    main.py                           │
│  (添加 --source 参数，支持 feishu/dingtalk 切换)      │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              MessageReceiver                         │
│  (扩展：支持 source 参数，动态选择客户端)              │
└───────┬───────────────┬────────────────────────────┘
        │               │
        ▼               ▼
┌──────────────┐  ┌──────────────────┐
│  Feishu      │  │   Dingtalk       │
│  Message     │  │   Message        │
│  Client      │  │   Client         │
│  (现有)      │  │   (新增)         │
└──────────────┘  └──────────────────┘
        │               │
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │  Message      │
        │  Parser       │
        │ (重构：统一    │
        │  识别逻辑)    │
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │  Database      │
        │  Repository   │
        │ (扩展：source │
        │  字段)        │
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │  Dingtalk     │
        │  Notifier     │
        │ (增强：带上   │
        │  来源标识)    │
        └───────────────┘
```

### 2.2 消息流程

```
钉钉群消息 
    │
    ▼
DingtalkMessageClient.get_messages()
    │ (API调用，带重试)
    ▼
MessageReceiver.receive_messages()
    │
    ├─▶ MessageParser.parse_message()
    │       │
    │       ├─▶ 匹配钉钉格式 (新增)
    │       │   └─▶ 返回 source='dingtalk'
    │       │
    │       └─▶ 匹配飞书格式 (现有)
    │           └─▶ 返回 source='feishu'
    │
    ├─▶ 计算message_hash (去重)
    │
    ├─▶ DatabaseRepository.insert_message_log()
    │       │
    │       └─▶ message_process_log 表
    │           └─▶ source字段存储来源
    │
    └─▶ DingtalkNotifier.send_notification()
            │
            └─▶ 通知带上来源标识
```

## 3. 数据库扩展

### 3.1 表结构变更

**现有表：** `message_process_log`

**新增字段：**
```sql
ALTER TABLE message_process_log 
ADD COLUMN source ENUM('feishu', 'dingtalk') 
DEFAULT 'feishu' 
COMMENT '消息来源（飞书/钉钉）';

CREATE INDEX idx_source ON message_process_log(source);
```

### 3.2 完整表结构

```sql
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    original_message TEXT COMMENT '原始消息内容',
    share_link VARCHAR(500) COMMENT '提取的网盘链接',
    folder_name VARCHAR(255) COMMENT '提取的目录名',
    extraction_code VARCHAR(20) COMMENT '提取码（从folder_name提取）',
    source ENUM('feishu', 'dingtalk') DEFAULT 'feishu' COMMENT '消息来源',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
        DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    execution_summary_id INT COMMENT '关联执行摘要ID',
    processing_time INT COMMENT '处理耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    INDEX idx_message_hash (message_hash),
    INDEX idx_status (process_status),
    INDEX idx_source (source),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='消息处理记录表（支持飞书和钉钉）';
```

### 3.3 数据兼容性

- **现有数据**：`source`字段默认值为'feishu'，自动兼容
- **去重机制**：`message_hash`全局唯一，跨source生效
- **查询影响**：通过`source`字段可按来源筛选统计

## 4. 配置扩展

### 4.1 配置项设计

**新增钉钉配置：**
```bash
# 钉钉应用配置
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_CHAT_ID=your_chat_id
```

**现有飞书配置（保持不变）：**
```bash
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_CHAT_ID=your_chat_id
```

### 4.2 Settings类扩展

**文件：** `src/config/settings.py`

```python
class Settings:
    def __init__(self, config_file: Optional[str] = None):
        # ... 现有配置 ...
        
        # 钉钉配置
        self.dingtalk_app_key = os.getenv('DINGTALK_APP_KEY', '')
        self.dingtalk_app_secret = os.getenv('DINGTALK_APP_SECRET', '')
        self.dingtalk_chat_id = os.getenv('DINGTALK_CHAT_ID', '')
```

### 4.3 配置验证

```python
def validate(self):
    """验证配置完整性"""
    if self.dingtalk_app_key and not self.dingtalk_app_secret:
        raise ConfigError("DINGTALK_APP_SECRET is required when DINGTALK_APP_KEY is set")
    # ... 其他验证 ...
```

## 5. 统一消息识别

### 5.1 钉钉格式识别

**正则表达式：**
```python
DINGTALK_PATTERN = re.compile(
    r'(\d{6})\s*[：:]\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)'
)
```

**匹配示例：**
- `260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg`
- `260723:https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg`
- `260723 ： https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg`

### 5.2 统一识别流程

**文件：** `src/feishu/message_parser.py`

```python
class MessageParser:
    # 现有飞书模式
    FEISHU_PATTERN = re.compile(...)
    
    # 新增钉钉模式
    DINGTALK_PATTERN = re.compile(
        r'(\d{6})\s*[：:]\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)'
    )
    
    def parse_message(self, content: str) -> Optional[ParseResult]:
        """
        统一消息识别流程
        
        优先级：
        1. 钉钉格式（新增）
        2. 飞书格式（现有）
        """
        # 1. 尝试钉钉格式
        dingtalk_match = self._match_dingtalk_format(content)
        if dingtalk_match:
            extraction_code = dingtalk_match.group(1)  # 260723
            share_link = dingtalk_match.group(2)       # https://...
            folder_name = extraction_code  # 直接使用提取码作为文件夹名
            
            return ParseResult(
                source='dingtalk',
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,
                raw_content=content
            )
        
        # 2. 尝试飞书格式
        feishu_match = self._match_feishu_format(content)
        if feishu_match:
            # ... 现有逻辑 ...
            return ParseResult(
                source='feishu',
                share_link=...,
                folder_name=...,
                extraction_code=...,
                raw_content=content
            )
        
        # 3. 无法识别
        return None
    
    def _match_dingtalk_format(self, content: str) -> Optional[re.Match]:
        """匹配钉钉格式"""
        return self.DINGTALK_PATTERN.search(content)
```

### 5.3 ParseResult扩展

```python
@dataclass
class ParseResult:
    source: str  # 新增：消息来源 'feishu' 或 'dingtalk'
    share_link: str
    folder_name: str
    extraction_code: str
    raw_content: str
```

## 6. DingtalkMessageClient设计

### 6.1 类结构

**文件：** `src/feishu/dingtalk_client.py`

```python
class DingtalkMessageClient:
    """
    钉钉消息客户端
    
    参考 FeishuMessageClient 实现，适配钉钉API：
    - access_token 获取
    - 群消息历史获取
    - 指数退避重试
    - API限流处理
    """
    
    # API endpoints（需根据实际钉钉API确认）
    TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    MESSAGES_URL = "https://api.dingtalk.com/v1.0/messages/send"  # 待确认
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.app_key = self.settings.dingtalk_app_key
        self.app_secret = self.settings.dingtalk_app_secret
        self.chat_id = self.settings.dingtalk_chat_id
        self.token: Optional[str] = None
        self.max_retries = 5
    
    def get_access_token(self) -> str:
        """获取钉钉access_token（参考飞书实现）"""
        # 指数退避重试机制
        # ...
    
    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取群消息历史（参考飞书实现）"""
        # 自动重试机制
        # ...
```

### 6.2 复用特性

**从 FeishuMessageClient 复用：**
- ✅ 指数退避重试：`_calculate_backoff()`, `_wait_with_backoff()`
- ✅ 错误判断：`_should_retry_error()`, `_is_rate_limit_error()`
- ✅ 请求构建：`_build_request_headers()`, `_extract_retry_after()`

**适配点：**
- API endpoints（钉钉特定）
- 请求参数格式（可能略有差异）
- 响应解析（钉钉特定字段）

### 6.3 等待确认项

- [ ] 钉钉获取群消息的具体API端点
- [ ] 钉钉消息的响应格式
- [ ] 钉钉API的认证方式（是否和飞书类似）

## 7. MessageReceiver扩展

### 7.1 类扩展

**文件：** `src/processor/message_receiver.py`

```python
class MessageReceiver:
    """消息接收器（支持飞书和钉钉）"""
    
    def __init__(self, settings: Optional[Settings] = None, source: str = 'feishu'):
        """
        Args:
            settings: 配置对象
            source: 消息来源 'feishu' 或 'dingtalk'
        """
        self.source = source
        self.settings = settings or Settings()
        self.logger = logger
        
        # 根据来源选择客户端
        if source == 'dingtalk':
            self.client = DingtalkMessageClient(self.settings)
        else:
            self.client = FeishuMessageClient(self.settings)
        
        # 其他组件保持不变（统一处理）
        self.message_parser = MessageParser()  # 自动识别格式
        self.db_repo = DatabaseRepository(...)
        self.dingtalk_notifier = DingtalkNotifier(self.settings)
```

### 7.2 数据存储扩展

```python
def receive_messages(self) -> ReceiveResult:
    """接收消息的主要工作流程"""
    # ... 现有逻辑 ...
    
    # 插入新消息时带上来源
    message_log = MessageProcessLog(
        message_hash=message_hash,
        original_message=content,
        share_link=parse_result.share_link,
        folder_name=parse_result.folder_name,
        extraction_code=parse_result.code,
        source=parse_result.source,  # 新增：消息来源
        process_status="pending"
    )
    message_id = self.db_repo.insert_message_log(message_log)
```

### 7.3 通知增强

```python
def _send_receive_notification(self, result: ReceiveResult) -> bool:
    """发送消息接收结果通知到钉钉"""
    content_lines = [
        f"## 📢 海外研报：{self.source.upper()}消息接收报告",  # 动态来源
        "",
        "### 接收结果摘要",
        "",
        f"- **消息来源**: {self.source.upper()}",
        f"- **总计接收**: {result.total_messages} 条消息",
        f"- **新增消息**: {result.new_messages} 条",
        f"- **过滤消息**: {filtered_count} 条 (重复/无法解析)",
        f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
    ]
    # ...
```

## 8. main.py扩展

### 8.1 参数扩展

```python
parser.add_argument(
    '--source',
    choices=['feishu', 'dingtalk'],
    default='feishu',
    help='消息来源：feishu（飞书）或 dingtalk（钉钉），默认：feishu'
)
```

### 8.2 接收模式扩展

```python
# 接收模式：专职接收消息
if args.receive_messages:
    logger.info(f"接收模式：开始接收{args.source}消息...")
    
    with MessageReceiver(settings, source=args.source) as receiver:
        result = receiver.receive_messages()
        
        logger.info("=" * 60)
        logger.info(f"{args.source.upper()}消息接收完成！")
        logger.info(f"总计接收: {result.total_messages} 条消息")
        # ...
```

### 8.3 使用示例

```bash
# 接收飞书消息（现有行为，默认）
python main.py --receive-messages

# 接收钉钉消息（新增）
python main.py --receive-messages --source dingtalk

# 显式指定飞书
python main.py --receive-messages --source feishu
```

## 9. 错误处理

### 9.1 API错误处理

**复用飞书的成熟机制：**

- ✅ **指数退避重试**：1s, 2s, 4s, 8s, 16s（最多5次）
- ✅ **限流处理**：429错误自动等待Retry-After时间
- ✅ **5xx错误重试**：服务器临时问题自动重试
- ✅ **4xx错误不重试**：客户端错误直接失败

### 9.2 消息级错误处理

**现有机制（保持不变）：**

- ✅ **单条消息失败不中断整体**：循环继续处理下一条
- ✅ **重复消息自动跳过**：基于message_hash去重
- ✅ **解析失败过滤**：无法识别的消息记录到filtered_messages
- ✅ **系统级异常**：只有真正的系统异常才返回failed_messages

### 9.3 数据库错误处理

- ✅ **连接失败**：抛出系统异常，返回failed_messages=1
- ✅ **插入失败**：记录错误，继续处理下一条消息
- ✅ **查询失败**：抛出系统异常，中断处理

## 10. 测试策略

### 10.1 单元测试

**测试覆盖：**

1. **MessageParser**
   - 测试钉钉格式识别（各种变体）
   - 测试飞书格式识别（确保未破坏）
   - 测试无法识别的消息
   - 测试ParseResult的source字段

2. **DingtalkMessageClient**
   - Mock API响应测试get_access_token()
   - Mock API响应测试get_messages()
   - 测试重试机制（指数退避）
   - 测试错误处理（4xx, 5xx, 429）

3. **MessageReceiver**
   - 测试source参数切换
   - Mock不同客户端测试统一流程
   - 测试通知格式带上来源

### 10.2 集成测试

**测试场景：**

1. **API连接测试**
   - 使用真实钉钉凭证测试token获取
   - 测试消息获取（需真实群消息）
   - 验证响应格式解析

2. **完整流程测试**
   - 从钉钉获取消息 → 解析 → 存储 → 通知
   - 验证数据库source字段正确存储
   - 验证通知包含来源标识

3. **并行测试**
   - 同时运行飞书和钉钉接收
   - 验证去重机制跨source工作
   - 验证通知正确区分来源

### 10.3 回归测试

**确保现有功能未破坏：**

- [ ] 飞书消息接收正常
- [ ] 默认行为（--source feishu）不变
- [ ] 数据库现有数据兼容
- [ ] 通知格式飞书部分正常

## 11. 实施计划

### 11.1 实施步骤

**步骤1：数据库扩展（5分钟）**
```sql
ALTER TABLE message_process_log 
ADD COLUMN source ENUM('feishu', 'dingtalk') 
DEFAULT 'feishu' 
COMMENT '消息来源';

CREATE INDEX idx_source ON message_process_log(source);
```

**步骤2：创建DingtalkMessageClient（30分钟）**
- 创建文件：`src/feishu/dingtalk_client.py`
- 实现类结构和API调用方法
- 复用飞书的重试逻辑（复制相关方法）
- 单元测试

**步骤3：重构MessageParser（20分钟）**
- 修改文件：`src/feishu/message_parser.py`
- 添加DINGTALK_PATTERN和_match_dingtalk_format()
- 修改parse_message()实现统一识别流程
- 扩展ParseResult添加source字段
- 单元测试

**步骤4：扩展MessageReceiver（15分钟）**
- 修改文件：`src/processor/message_receiver.py`
- 添加source参数支持
- 实现客户端动态选择逻辑
- 修改通知格式带上来源
- 修改数据库插入带上source字段
- 集成测试

**步骤5：配置和main.py（10分钟）**
- 修改文件：`src/config/settings.py`
- 添加钉钉配置项
- 修改文件：`main.py`
- 添加--source参数
- 更新接收模式支持source参数
- 更新文档

**步骤6：测试和验证（20分钟）**
- 单元测试所有修改
- 集成测试（需钉钉凭证）
- 回归测试确保飞书功能正常
- 文档更新

**总预计时间：** 约100分钟

### 11.2 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 钉钉API端点不确定 | 高 | 等用户提供凭证后确认具体端点 |
| 消息格式可能有差异 | 中 | 保留调整空间，真实消息验证 |
| 破坏现有飞书功能 | 低 | 回归测试，默认行为不变 |
| 数据库迁移影响 | 低 | 默认值兼容，索引异步创建 |

### 11.3 回滚计划

- **数据库回滚**：`ALTER TABLE message_process_log DROP COLUMN source;`
- **代码回滚**：git revert提交
- **配置回滚**：移除新增的环境变量

## 12. 待确认事项

### 12.1 钉钉API信息（需要用户提供）

- [ ] 钉钉获取群消息的API端点
- [ ] 钉钉API的认证方式（access_token获取）
- [ ] 钉钉消息的响应格式示例
- [ ] 钉钉应用的app_key和app_secret（测试用）

### 12.2 设计确认（需要用户确认）

- [x] 数据库扩展方案（source字段）
- [x] 统一消息识别流程（正则匹配）
- [x] DingtalkMessageClient设计（参考飞书）
- [x] MessageReceiver扩展（source参数）
- [x] 通知格式增强（带上来源）
- [x] 实施步骤和顺序

## 13. 后续扩展

### 13.1 可能的增强

1. **命令行增强**
   - 同时接收飞书和钉钉：`--source all`
   - 按来源统计：`--stats-by-source`

2. **数据库增强**
   - 添加source字段统计查询
   - 按来源筛选消息处理

3. **通知增强**
   - 飞书通知（如果需要）
   - 邮件通知（汇总报告）

### 13.2 长期考虑

- 支持更多消息来源（企业微信等）
- 统一的消息处理框架
- 消息来源配置化（非硬编码）

## 14. 参考资料

- 现有飞书实现：`src/feishu/feishu_client.py`
- 消息解析器：`src/feishu/message_parser.py`
- 消息接收器：`src/processor/message_receiver.py`
- 数据库模型：`src/database/models.py`
- 配置管理：`src/config/settings.py`

---

**文档版本：** 1.0  
**最后更新：** 2026-07-25  
**状态：** 待用户确认后实施
