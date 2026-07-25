# 飞书消息自动化处理系统设计文档

**日期**: 2026-07-24  
**版本**: 1.0  
**作者**: Claude (AI Assistant)

---

## 1. 概述

### 1.1 项目背景

现有的百度网盘PDF文件自动传输系统需要手动复制飞书群聊消息中的网盘链接和目录名，然后通过命令行参数执行。此设计旨在自动化这一流程，通过飞书开放平台API自动获取群聊消息，提取网盘链接和目录名，复用现有的文件处理流程，并通过钉钉发送处理结果通知。

### 1.2 核心需求

1. **自动化消息接收**：从飞书特定群聊获取最近N小时内的消息
2. **智能消息解析**：通过正则表达式提取网盘链接和目录名（YYMMDD格式）
3. **消息去重处理**：使用消息内容哈希值避免重复处理
4. **复用现有流程**：不修改现有的FileProcessor文件处理逻辑
5. **状态记录**：记录消息处理状态到数据库
6. **钉钉通知**：发送简化版处理结果摘要
7. **模块化设计**：遵循现有项目架构模式
8. **可执行文件**：最终打包成baidu-download.exe

### 1.3 设计原则

- **最小化改动**：保持现有手动模式完全不变
- **架构一致性**：遵循现有模块化设计模式
- **职责分离**：自动化逻辑独立，便于维护
- **错误容错**：分层错误处理，保证系统稳定性
- **可扩展性**：便于后续添加其他消息源

---

## 2. 系统架构

### 2.1 架构设计

```
main.py (模式判断)
├── 有参数 → 现有FileProcessor流程 (零改动)
└── 无参数 → 新增AutoProcessor流程

AutoProcessor (新增自动化协调器)
├── FeishuMessageClient (获取消息)
├── MessageParser (解析链接和目录)  
├── FileProcessor (复用现有文件处理)
├── MessageRepository (消息状态管理)
└── DingtalkNotifier (钉钉通知)
```

### 2.2 目录结构

```
src/
├── config/
│   └── settings.py                  # 扩展：添加飞书、钉钉配置
├── database/
│   ├── models.py                    # 扩展：添加MessageProcessLog模型
│   └── repository.py                # 扩展：添加消息操作方法
├── feishu/                          # 新增：遵循downloader/模式
│   ├── __init__.py
│   ├── message_client.py           # 飞书API客户端
│   └── message_parser.py           # 消息解析器
├── notification/                    # 新增：遵循uploader/模式
│   ├── __init__.py
│   └── dingtalk_notifier.py        # 钉钉通知客户端
└── processor/
    ├── file_processor.py            # 现有：保持不变
    └── auto_processor.py            # 新增：自动化协调器
```

### 2.3 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `auto_processor.py` | 协调整个自动化流程 | FeishuMessageClient, MessageParser, FileProcessor, MessageRepository, DingtalkNotifier |
| `message_client.py` | 飞书API调用，获取群聊消息 | Settings |
| `message_parser.py` | 解析消息，提取链接和目录 | 无 |
| `dingtalk_notifier.py` | 发送钉钉通知 | Settings, ExecutionSummary |
| `MessageRepository` | 消息状态数据库操作 | DatabaseRepository |
| `FileProcessor` | 文件下载和上传（复用现有） | BaiduClient, SFTPClient, DatabaseRepository |

---

## 3. 数据模型设计

### 3.1 消息处理表

```sql
CREATE TABLE message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    original_message TEXT COMMENT '原始消息内容',
    share_link VARCHAR(500) COMMENT '提取的网盘链接',
    folder_name VARCHAR(255) COMMENT '提取的目录名',
    status ENUM('pending', 'processing', 'success', 'failed', 'critical_error') DEFAULT 'pending',
    error_message TEXT COMMENT '错误信息',
    execution_summary_id INT COMMENT '关联执行摘要ID',
    processing_time INT COMMENT '处理耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_message_hash (message_hash),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='飞书消息处理记录表';
```

### 3.2 数据模型定义

```python
@dataclass
class MessageProcessLog:
    """消息处理日志模型"""
    message_hash: str
    original_message: Optional[str] = None
    share_link: Optional[str] = None
    folder_name: Optional[str] = None
    status: str = 'pending'  # pending, processing, success, failed, critical_error
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time: Optional[int] = None  # 毫秒
    ID: Optional[int] = None
    CREATED_AT: Optional[datetime] = None
    UPDATED_AT: Optional[datetime] = None
```

### 3.3 状态流转

```
pending → processing → success/failed/critical_error
             ↑              |
             |______________| (critical_error状态会重试)
```

**状态说明**：
- `pending`: 消息已提取，待处理
- `processing`: 正在处理中
- `success`: 处理成功（包括部分文件失败的情况）
- `failed`: 解析失败或可恢复错误（不重试）
- `critical_error`: 致命错误（下次收到消息时重试）

---

## 4. 配置文件扩展

### 4.1 新增环境变量

```bash
# 飞书配置
FEISHU_APP_ID=your_app_id_here
FEISHU_APP_SECRET=your_app_secret_here  
FEISHU_CHAT_ID=your_chat_id_here
FEISHU_HOURS_LIMIT=24  # 获取最近24小时内的消息

# 钉钉配置
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token_here

# 消息处理配置
MESSAGE_DEFAULT_EXTRACTION_CODE=0409  # 默认提取码
```

### 4.2 Settings类扩展

```python
# 在Settings类中添加：

# 飞书配置
self.feishu_app_id = os.getenv('FEISHU_APP_ID', '')
self.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', '')
self.feishu_chat_id = os.getenv('FEISHU_CHAT_ID', '')
self.feishu_hours_limit = self._get_int_env('FEISHU_HOURS_LIMIT', default=24)

# 钉钉配置
self.dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK', '')

# 消息处理配置
self.message_default_extraction_code = os.getenv('MESSAGE_DEFAULT_EXTRACTION_CODE', '0409')
```

### 4.3 配置验证

- 飞书配置为可选（手动模式不需要）
- 钉钉webhook为可选（无通知模式）
- 无参数模式时验证飞书配置完整性

---

## 5. 自动化处理流程

### 5.1 主流程设计

```python
def process_automatically():
    """自动化处理流程"""
    
    # 1. 检查配置完整性
    if not feishu_config_complete():
        logger.error("飞书配置不完整，无法运行自动化模式")
        return
    
    # 2. 获取最近N小时内的飞书消息
    messages = get_feishu_messages(hours_limit)
    
    # 3. 对每条消息进行处理
    for message in messages:
        # a. 计算消息MD5哈希
        message_hash = calculate_md5(message.content)
        
        # b. 检查数据库是否已处理
        existing_log = get_message_by_hash(message_hash)
        
        if existing_log:
            if existing_log.status == 'success':
                logger.info(f"消息已处理成功，跳过: {message_hash[:8]}...")
                continue
            elif existing_log.status == 'critical_error':
                logger.info(f"消息上次处理失败，重新处理: {message_hash[:8]}...")
                # 继续处理
        else:
            logger.info(f"新消息，开始处理: {message_hash[:8]}...")
        
        # c. 解析链接和目录名
        parse_result = parse_message(message.content)
        if not parse_result:
            # 解析失败，记录failed状态
            record_message_failed(message_hash, "消息解析失败")
            send_dingtalk_notification(parse_result=None, error="消息解析失败")
            continue
        
        # d. 更新状态为processing
        update_message_status(message_hash, 'processing')
        
        # e. 调用FileProcessor处理
        start_time = datetime.now()
        summary = FileProcessor.process_files(
            share_link=parse_result.link,
            code=parse_result.code,
            folder_name=parse_result.folder
        )
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        # f. 根据返回结果记录消息状态
        if summary:
            # 处理成功（包括部分文件失败）
            update_message_status(
                message_hash, 
                'success',
                execution_summary_id=summary.ID,
                processing_time=processing_time
            )
            send_dingtalk_notification(summary)
        else:
            # 处理完全失败
            update_message_status(
                message_hash,
                'critical_error',
                error_message="FileProcessor处理失败",
                processing_time=processing_time
            )
            send_dingtalk_notification(summary=None, error="FileProcessor处理失败")
```

### 5.2 消息去重逻辑

- 使用消息内容的MD5哈希作为唯一键
- `success`状态：跳过，不重复处理
- `failed`状态：跳过，不重复处理（解析错误不会自动恢复）
- `critical_error`状态：重新处理（可能是临时网络问题）

### 5.3 错误处理流程

**流程图**：
```
收到消息 → 计算哈希 → 检查状态
                  ↓
         已处理success → 跳过
         已处理critical_error → 重新处理
         未处理 → 解析消息
                  ↓
         解析失败 → 记录failed → 钉钉通知 → 跳过下一条
         解析成功 → 调用FileProcessor
                  ↓
         返回ExecutionSummary → 记录success → 钉钉通知
         返回None → 记录critical_error → 钉钉通知
```

---

## 6. 钉钉通知格式

### 6.1 成功消息

```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "百度网盘文件传输完成",
    "text": "### ✅ 文件传输成功\n\n**目录**: 260723\n**总数**: 15个文件\n**成功**: 15个\n**失败**: 0个\n**跳过**: 0个\n**总大小**: 125.5 MB\n**耗时**: 8.2分钟\n\n**时间**: 2026-07-24 14:30:25"
  }
}
```

### 6.2 失败消息

```json
{
  "msgtype": "markdown", 
  "markdown": {
    "title": "⚠️ 文件传输失败",
    "text": "### ❌ 文件传输失败\n\n**目录**: 260723\n**状态**: critical_error\n**错误**: Baidu login failed\n\n**消息**: 260723：https://pan.baidu.com/s/xxx\n\n**时间**: 2026-07-24 14:25:10"
  }
}
```

### 6.3 解析失败消息

```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "⚠️ 消息解析失败",
    "text": "### ⚠️ 消息解析失败\n\n**原始消息**: 无效的消息内容\n\n**错误**: 无法提取网盘链接或目录名\n\n**时间**: 2026-07-24 14:20:05"
  }
}
```

---

## 7. 正则表达式设计

### 7.1 消息解析正则

```python
# 匹配格式：260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw
pattern = r'^(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9]+)'

# 提取组：
# Group 1: 目录名 (260723)
# Group 2: 网盘链接
```

### 7.2 解析逻辑

```python
def parse_message(content: str) -> Optional[ParseResult]:
    """解析飞书消息"""
    import re
    
    pattern = r'^(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9]+)'
    match = re.match(pattern, content.strip())
    
    if match:
        folder_name = match.group(1)  # 260723
        share_link = match.group(2)   # https://pan.baidu.com/s/xxx
        code = settings.message_default_extraction_code  # 0409
        
        return ParseResult(
            folder_name=folder_name,
            share_link=share_link,
            code=code
        )
    else:
        logger.warning(f"无法解析消息: {content[:50]}...")
        return None
```

### 7.3 支持的消息格式

- `260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw` ✅
- `260723: https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw` ✅
- `260723：https://pan.baidu.com/s/xxx` ✅
- 其他格式 ❌

---

## 8. 错误处理策略

### 8.1 分层错误处理

**Level 1: 飞书API错误**
```python
# 指数退避重试
for attempt in range(5):
    try:
        messages = feishu_client.get_messages()
        break
    except FeishuAPIError as e:
        wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
        logger.warning(f"飞书API调用失败，{wait_time}秒后重试: {e}")
        time.sleep(wait_time)
else:
    # 最终失败
    logger.error("飞书API调用失败，已达到最大重试次数")
    send_dingtalk_alert("飞书API调用失败")
    return  # 跳过本次处理
```

**Level 2: 消息解析错误**
```python
# 解析失败，记录failed状态（不重试）
if not parse_result:
    record_message_failed(message_hash, "消息解析失败")
    send_dingtalk_notification(error="消息解析失败")
    continue  # 跳过当前消息，处理下一条
```

**Level 3: FileProcessor处理错误**
```python
# 返回None：标记critical_error（下次重试）
if not summary:
    update_message_status(message_hash, 'critical_error', 
                          error_message="FileProcessor处理失败")
    send_dingtalk_notification(error="FileProcessor处理失败")
    continue
```

**Level 4: 钉钉通知错误**
```python
# 仅记录日志，不影响主流程
try:
    dingtalk_notifier.send_notification(summary)
except Exception as e:
    logger.error(f"钉钉通知发送失败: {e}")
```

### 8.2 重试策略

| 错误类型 | 重试策略 | 最终状态 |
|---------|---------|---------|
| 飞书API调用失败 | 指数退避，最多5次 | 跳过本次处理 |
| 消息解析失败 | 不重试 | failed（不重试） |
| FileProcessor返回None | 下次收到消息时重试 | critical_error |
| FileProcessor部分失败 | 不重试 | success（部分成功） |
| 钉钉通知失败 | 不重试 | 仅记录日志 |

---

## 9. 实施顺序

### 9.1 分阶段实施

**阶段1: 基础设施**
- [ ] 扩展`src/config/settings.py`添加新配置项
- [ ] 扩展`src/database/models.py`添加MessageProcessLog模型
- [ ] 扩展`src/database/repository.py`添加消息操作方法

**阶段2: 飞书集成**
- [ ] 创建`src/feishu/__init__.py`
- [ ] 创建`src/feishu/message_client.py`
- [ ] 创建`src/feishu/message_parser.py`

**阶段3: 通知和协调**
- [ ] 创建`src/notification/__init__.py`
- [ ] 创建`src/notification/dingtalk_notifier.py`
- [ ] 创建`src/processor/auto_processor.py`

**阶段4: 主程序集成**
- [ ] 修改`main.py`支持无参数模式
- [ ] 集成测试完整流程

**阶段5: 部署准备**
- [ ] 更新`.env`配置文件示例
- [ ] 更新项目文档
- [ ] PyInstaller打包测试

### 9.2 测试计划

1. **单元测试**：各模块独立功能测试
2. **集成测试**：完整自动化流程测试
3. **打包测试**：`release\dist\baidu-download.exe`测试
4. **长期运行测试**：Windows计划任务定时执行测试

---

## 10. 打包和部署

### 10.1 PyInstaller打包配置

**打包命令**：
```bash
pyinstaller --onefile --name baidu-download ^
  --add-data "src;src" ^
  --add-data ".env;." ^
  --hidden-import=pymysql ^
  --hidden-import=dotenv ^
  main.py
```

### 10.2 打包后目录结构

```
release/
├── dist/
│   └── baidu-download.exe          # 主程序
├── .env                            # 配置文件
├── baidu-cookies.txt              # 百度cookies
├── BaiduPCS-Go.exe                # 百度网盘工具
└── logs/                          # 日志目录
    └── transfer.log
```

### 10.3 Windows计划任务配置

**任务设置**：
- 触发器：每天/每小时（用户自定义）
- 操作：启动 `release\dist\baidu-download.exe`（无参数）
- 运行账户：SYSTEM或用户账户
- 其他：不管用户是否登录都要运行

---

## 11. 安全考虑

### 11.1 敏感信息保护

- 飞书App Secret存储在`.env`文件中，不提交到代码仓库
- 钉钉Webhook URL存储在`.env`文件中
- 百度Cookies文件独立管理

### 11.2 API限流处理

- 飞书API调用增加适当的延迟，避免触发限流
- 失败重试采用指数退避策略
- 记录API调用日志，便于监控

### 11.3 数据库安全

- 使用参数化查询，避免SQL注入
- 数据库连接信息存储在环境变量中
- 定期备份消息处理日志

---

## 12. 监控和日志

### 12.1 日志级别

- **DEBUG**: 详细的调试信息（文件名、路径等）
- **INFO**: 正常流程信息（开始处理、完成处理等）
- **WARNING**: 警告信息（重试、跳过消息等）
- **ERROR**: 错误信息（API失败、处理失败等）

### 12.2 关键监控指标

- 消息处理成功率
- FileProcessor处理成功率
- 飞书API调用失败率
- 钉钉通知发送成功率
- 平均处理耗时

---

## 13. 总结

本设计通过最小化扩展现有架构，实现了飞书消息自动化处理功能：

✅ **保持现有手动模式完全不变** - 有参数模式零改动  
✅ **复用现有FileProcessor模块** - 不修改核心文件处理逻辑  
✅ **模块化架构遵循现有模式** - feishu/、notification/新模块  
✅ **完整的错误处理和重试机制** - 分层处理，保证系统稳定性  
✅ **支持最终打包成exe** - 配置文件路径处理正确  
✅ **钉钉通知简化摘要** - 成功失败都发送，便于监控  

此设计为后续扩展留有空间，可以轻松添加其他消息源（如企业微信、Slack等）或其他通知方式（如邮件、企业微信等）。
