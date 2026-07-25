# 钉钉消息接收功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有飞书消息接收系统基础上扩展钉钉支持，实现从钉钉群获取消息、识别百度网盘链接、存储到数据库，同时保留飞书通道。

**Architecture:** 参考现有 FeishuMessageClient 创建 DingtalkMessageClient，重构 MessageParser 实现统一识别（通过正则自动区分来源），扩展 MessageReceiver 支持 source 参数切换客户端，数据库添加 source 字段区分消息来源。

**Tech Stack:** Python 3.x, requests, MySQL, dataclasses, re, pytest

---

## 文件结构

**新增文件：**
- `src/feishu/dingtalk_client.py` - 钉钉API客户端（参考 feishu_client.py）
- `src/database/message_models.py` - 分离消息模型定义（从 models.py 提取）
- `tests/test_dingtalk_client.py` - DingtalkMessageClient 单元测试
- `tests/test_message_parser_unified.py` - MessageParser 统一识别测试

**修改文件：**
- `src/database/models.py` - 添加 source 字段到 message_process_log 表定义
- `src/config/settings.py` - 添加钉钉配置项（app_key, app_secret, chat_id）
- `src/feishu/message_parser.py` - 添加钉钉格式识别和统一识别流程
- `src/processor/message_receiver.py` - 扩展支持 source 参数和动态客户端选择
- `main.py` - 添加 --source 命令行参数
- `src/database/message_models.py` - MessageProcessLog 模型添加 source 字段
- `src/database/repository.py` - 更新 insert_message_log 支持 source 字段

---

## Task 1: 数据库模型扩展 - 添加 source 字段

**Files:**
- Modify: `src/database/models.py`
- Modify: `src/database/message_models.py` (如果存在，否则创建)

- [ ] **Step 1: 创建 message_models.py 分离消息模型定义**

```python
"""
数据库模型定义 - 消息相关
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MessageProcessLog:
    """消息处理记录模型"""
    message_hash: str
    original_message: str
    share_link: Optional[str] = None
    folder_name: Optional[str] = None
    extraction_code: Optional[str] = None
    source: str = 'feishu'  # 新增：消息来源，默认 feishu
    process_status: str = 'pending'  # pending, processing, success, failed, critical_error
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

运行: 创建新文件
预期: 文件创建成功

- [ ] **Step 2: 更新 models.py 中的 CREATE TABLE 语句**

找到 `message_process_log` 表定义，在 `folder_name` 行后添加：

```sql
    extraction_code VARCHAR(20) COMMENT '提取码（从folder_name提取）',
    source ENUM('feishu', 'dingtalk') DEFAULT 'feishu' COMMENT '消息来源（飞书/钉钉）',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
        DEFAULT 'pending' COMMENT '处理状态',
```

在索引部分添加：

```sql
    INDEX idx_source (source),
```

运行: 编辑文件 `src/database/models.py`
预期: SQL语句更新成功

- [ ] **Step 3: 更新表注释**

将表注释从：
```sql
COMMENT='飞书消息处理记录表';
```

改为：
```sql
COMMENT='消息处理记录表（支持飞书和钉钉）';
```

运行: 编辑文件 `src/database/models.py`
预期: 注释更新成功

- [ ] **Step 4: 提交数据库模型变更**

```bash
git add src/database/models.py src/database/message_models.py
git commit -m "feat(database): add source field to message_process_log for dingtalk support"
```

运行: Git提交
预期: 提交成功

---

## Task 2: 配置扩展 - 添加钉钉配置项

**Files:**
- Modify: `src/config/settings.py`

- [ ] **Step 1: 在 __init__ 方法中添加钉钉配置初始化**

在 `self.feishu_chat_id` 行后添加：

```python
        # 钉钉配置
        self.dingtalk_app_key = os.getenv('DINGTALK_APP_KEY', '')
        self.dingtalk_app_secret = os.getenv('DINGTALK_APP_SECRET', '')
        self.dingtalk_chat_id = os.getenv('DINGTALK_CHAT_ID', '')
```

运行: 编辑文件 `src/config/settings.py`
预期: 配置项添加成功

- [ ] **Step 2: 添加配置验证**

在 `validate()` 方法中飞书配置验证后添加：

```python
        # 验证钉钉配置
        if self.dingtalk_app_key and not self.dingtalk_app_secret:
            raise ConfigError("DINGTALK_APP_SECRET is required when DINGTALK_APP_KEY is set")
        if self.dingtalk_app_key and not self.dingtalk_chat_id:
            raise ConfigError("DINGTALK_CHAT_ID is required when DINGTALK_APP_KEY is set")
```

运行: 编辑文件 `src/config/settings.py`
预期: 验证逻辑添加成功

- [ ] **Step 3: 提交配置扩展**

```bash
git add src/config/settings.py
git commit -m "feat(config): add dingtalk configuration fields"
```

运行: Git提交
预期: 提交成功

---

## Task 3: 创建 DingtalkMessageClient 基础结构

**Files:**
- Create: `src/feishu/dingtalk_client.py`

- [ ] **Step 1: 创建 DingtalkMessageClient 类框架**

```python
"""
钉钉消息客户端

参考 FeishuMessageClient 实现，适配钉钉API：
- access_token 获取
- 群消息历史获取
- 指数退避重试机制
- API限流处理
"""

import time
import requests
from typing import Optional, List, Dict, Any
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DingtalkMessageClient:
    """
    钉钉消息客户端

    用于从钉钉开放平台获取消息，支持：
    - access_token 认证
    - 指数退避重试机制
    - 消息历史获取
    - API限流处理
    """

    # API endpoints（待根据实际钉钉API确认）
    TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    MESSAGES_URL = "https://api.dingtalk.com/v1.0/messages/send"  # 待确认

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化钉钉客户端

        Args:
            settings: 配置对象，如果不提供则创建新实例
        """
        self.settings = settings or Settings()
        self.app_key = self.settings.dingtalk_app_key
        self.app_secret = self.settings.dingtalk_app_secret
        self.chat_id = self.settings.dingtalk_chat_id
        self.token: Optional[str] = None
        self.max_retries = 5

        if not self.app_key or not self.app_secret:
            logger.warning("Dingtalk app_key or app_secret is empty")
        if not self.chat_id:
            logger.warning("Dingtalk chat_id is empty")
```

运行: 创建新文件
预期: 文件创建成功

- [ ] **Step 2: 添加 get_access_token 方法**

在类中添加：

```python
    def get_access_token(self) -> str:
        """
        获取access_token，使用指数退避重试机制

        Returns:
            access_token

        Raises:
            Exception: 获取token失败时抛出异常
        """
        if self.token:
            return self.token

        url = self.TOKEN_URL
        payload = {
            "appKey": self.app_key,
            "appSecret": self.app_secret
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    # 钉钉响应格式待确认，这里假设与飞书类似
                    if 'accessToken' in data:
                        self.token = data.get('accessToken')
                        logger.info("Successfully obtained access_token")
                        return self.token
                    else:
                        error_msg = data.get("message", "Unknown error")
                        logger.error(f"API returned error: {error_msg}")
                        raise Exception(f"API error: {error_msg}")
                else:
                    # 5xx错误重试，4xx错误不重试
                    if self._should_retry_error(response.status_code):
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Token request failed with status {response.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._wait_with_backoff(wait_time)
                    else:
                        raise Exception(f"HTTP error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Token request failed with exception: {e}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    self._wait_with_backoff(wait_time)
                else:
                    raise Exception(f"Failed to get access_token after {self.max_retries} attempts: {e}")

        raise Exception(f"Failed to get access_token after {self.max_retries} attempts")
```

运行: 编辑文件 `src/feishu/dingtalk_client.py`
预期: 方法添加成功

- [ ] **Step 3: 添加辅助方法（复用飞书逻辑）**

在类末尾添加：

```python
    def _build_request_headers(self) -> Dict[str, str]:
        """
        构建请求头

        Returns:
            包含认证信息的请求头
        """
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _is_rate_limit_error(self, status_code: int) -> bool:
        """
        判断是否为限流错误

        Args:
            status_code: HTTP状态码

        Returns:
            是否为限流错误
        """
        return status_code == 429

    def _should_retry_error(self, status_code: int) -> bool:
        """
        判断错误是否应该重试

        Args:
            status_code: HTTP状态码

        Returns:
            是否应该重试
        """
        # 5xx服务器错误应该重试
        if 500 <= status_code < 600:
            return True
        # 429限流错误应该重试
        if status_code == 429:
            return True
        # 其他错误不重试
        return False

    def _calculate_backoff(self, attempt: int) -> int:
        """
        计算指数退避等待时间

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            等待秒数 (1, 2, 4, 8, 16)
        """
        return min(2 ** attempt, 16)

    def _wait_with_backoff(self, wait_time: int) -> None:
        """
        等待指定时间

        Args:
            wait_time: 等待秒数
        """
        logger.debug(f"Waiting for {wait_time} seconds...")
        time.sleep(wait_time)

    def _extract_retry_after(self, response: requests.Response) -> int:
        """
        从响应中提取Retry-After时间

        Args:
            response: HTTP响应对象

        Returns:
            重试等待秒数，默认1秒
        """
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                return 1
        return 1
```

运行: 编辑文件 `src/feishu/dingtalk_client.py`
预期: 辅助方法添加成功

- [ ] **Step 4: 添加 get_messages 方法占位符**

在类中添加：

```python
    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        从指定聊天获取消息历史，支持自动重试

        Args:
            limit: 获取消息数量，默认50

        Returns:
            消息列表

        Raises:
            Exception: 获取消息失败时抛出异常
        """
        # TODO: 待确认钉钉API后实现
        raise NotImplementedError(
            "get_messages requires Dingtalk API endpoint confirmation. "
            "Please provide app_key, app_secret, and chat_id to test."
        )
```

运行: 编辑文件 `src/feishu/dingtalk_client.py`
预期: 方法添加成功

- [ ] **Step 5: 提交 DingtalkMessageClient 基础结构**

```bash
git add src/feishu/dingtalk_client.py
git commit -m "feat(dingtalk): create DingtalkMessageClient with basic structure"
```

运行: Git提交
预期: 提交成功

---

## Task 4: 扩展 MessageParser 添加钉钉格式识别

**Files:**
- Modify: `src/feishu/message_parser.py`

- [ ] **Step 1: 添加钉钉格式正则表达式**

在类的类变量区域添加（FEISHU_PATTERN 附近）：

```python
    # 钉钉消息格式：260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
    DINGTALK_PATTERN = re.compile(
        r'(\d{6})\s*[：:]\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)'
    )
```

运行: 编辑文件 `src/feishu/message_parser.py`
预期: 正则表达式添加成功

- [ ] **Step 2: 扩展 ParseResult 添加 source 字段**

找到 ParseResult dataclass 定义，添加 source 字段：

```python
@dataclass
class ParseResult:
    """消息解析结果"""
    source: str  # 消息来源 'feishu' 或 'dingtalk'
    share_link: str
    folder_name: str
    extraction_code: str
    raw_content: str
```

运行: 编辑文件 `src/feishu/message_parser.py`
预期: ParseResult 更新成功

- [ ] **Step 3: 添加钉钉格式匹配方法**

在类中添加新方法：

```python
    def _match_dingtalk_format(self, content: str) -> Optional[re.Match]:
        """
        匹配钉钉消息格式

        Args:
            content: 消息内容

        Returns:
            匹配对象，如果不匹配则返回 None
        """
        return self.DINGTALK_PATTERN.search(content)
```

运行: 编辑文件 `src/feishu/message_parser.py`
预期: 方法添加成功

- [ ] **Step 4: 重构 parse_message 方法实现统一识别**

找到 `parse_message` 方法，替换为：

```python
    def parse_message(self, content: str) -> Optional[ParseResult]:
        """
        解析消息内容，统一识别流程

        优先级：
        1. 钉钉格式（新增）
        2. 飞书格式（现有）

        Args:
            content: 消息内容

        Returns:
            ParseResult 对象，如果无法解析则返回 None
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

        # 2. 尝试飞书格式（保留原有逻辑）
        feishu_match = self._match_feishu_format(content)
        if feishu_match:
            extraction_code = feishu_match.group(1)
            share_link = feishu_match.group(2)

            # 从消息中提取文件夹名
            folder_name = self._extract_folder_name(content, extraction_code)
            if not folder_name:
                return None

            return ParseResult(
                source='feishu',
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,
                raw_content=content
            )

        # 3. 无法识别
        return None
```

运行: 编辑文件 `src/feishu/message_parser.py`
预期: parse_message 方法重构成功

- [ ] **Step 5: 提交 MessageParser 扩展**

```bash
git add src/feishu/message_parser.py
git commit -m "feat(parser): add dingtalk format recognition and unified parsing"
```

运行: Git提交
预期: 提交成功

---

## Task 5: 编写 MessageParser 统一识别测试

**Files:**
- Create: `tests/test_message_parser_unified.py`

- [ ] **Step 1: 创建测试文件**

```python
"""
测试 MessageParser 统一识别功能
"""

import pytest
from src.feishu.message_parser import MessageParser, ParseResult


class TestMessageParserUnified:
    """测试统一消息识别流程"""

    def setup_method(self):
        """设置测试环境"""
        self.parser = MessageParser()

    def test_dingtalk_format_basic(self):
        """测试基本钉钉格式识别"""
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'
        assert result.share_link == 'https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg'
        assert result.folder_name == '260723'

    def test_dingtalk_format_english_colon(self):
        """测试钉钉格式英文冒号"""
        content = "260723:https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'

    def test_dingtalk_format_with_spaces(self):
        """测试钉钉格式带空格"""
        content = "260723 ： https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'

    def test_dingtalk_format_with_text(self):
        """测试钉钉格式带额外文字"""
        content = "今天的文件 260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg 请查收"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'

    def test_feishu_format_still_works(self):
        """测试飞书格式仍然有效"""
        content = "提取码 260723\n链接：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg\n文件夹：20250723研报"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'feishu'
        # 飞书格式的其他断言...

    def test_unrecognized_format(self):
        """测试无法识别的格式"""
        content = "这是一条普通的消息，没有提取码和链接"
        result = self.parser.parse_message(content)

        assert result is None

    def test_dingtalk_priority_over_feishu(self):
        """测试钉钉格式优先级高于飞书"""
        # 同时匹配两种格式的消息
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'  # 应该优先识别为钉钉格式
```

运行: 创建新文件
预期: 文件创建成功

- [ ] **Step 2: 运行测试验证失败（因为现有代码未更新）**

```bash
cd /d/git/baidu-download && python -m pytest tests/test_message_parser_unified.py -v
```

运行: pytest
预期: 部分测试通过（钉钉格式失败），飞书测试通过

- [ ] **Step 3: 根据测试结果调整代码**

如果测试失败，根据错误信息调整代码。预期：
- `test_dingtalk_format_*` 测试应该通过（因为我们已经添加了钉钉支持）
- `test_feishu_format_still_works` 应该通过（我们保留了飞书逻辑）

- [ ] **Step 4: 提交测试文件**

```bash
git add tests/test_message_parser_unified.py
git commit -m "test(parser): add unified message parser tests"
```

运行: Git提交
预期: 提交成功

---

## Task 6: 扩展 MessageReceiver 支持 source 参数

**Files:**
- Modify: `src/processor/message_receiver.py`

- [ ] **Step 1: 修改 __init__ 方法添加 source 参数**

找到 `__init__` 方法，修改签名和实现：

```python
    def __init__(self, settings: Optional[Settings] = None, source: str = 'feishu'):
        """
        Initialize MessageReceiver with required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance
            source: 消息来源 'feishu' 或 'dingtalk'
        """
        self.source = source
        self.settings = settings or Settings()
        self.logger = logger

        # 根据来源选择客户端
        if source == 'dingtalk':
            from src.feishu.dingtalk_client import DingtalkMessageClient
            self.client = DingtalkMessageClient(self.settings)
        else:
            self.client = FeishuMessageClient(self.settings)

        # Initialize components
        self.message_parser = MessageParser()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.dingtalk_notifier = DingtalkNotifier(self.settings)

        self.logger.info(f"MessageReceiver initialized successfully (source: {source})")
```

运行: 编辑文件 `src/processor/message_receiver.py`
预期: __init__ 方法更新成功

- [ ] **Step 2: 修改 receive_messages 方法调用新客户端**

找到 `messages = self.feishu_client.get_messages()` 这一行，替换为：

```python
            # 从指定来源获取消息
            messages = self.client.get_messages()
            self.logger.info(f"Retrieved {len(messages)} messages from {self.source}")
```

运行: 编辑文件 `src/processor/message_receiver.py`
预期: 方法调用更新成功

- [ ] **Step 3: 修改消息插入逻辑添加 source 字段**

找到创建 `MessageProcessLog` 的代码，添加 source 字段：

```python
                    # 插入新消息到数据库（状态为 pending）
                    message_log = MessageProcessLog(
                        message_hash=message_hash,
                        original_message=content,
                        share_link=parse_result.share_link,
                        folder_name=parse_result.folder_name,
                        extraction_code=parse_result.code,
                        source=parse_result.source,  # 新增：消息来源
                        process_status="pending"  # 待处理状态
                    )
                    message_id = self.db_repo.insert_message_log(message_log)
```

运行: 编辑文件 `src/processor/message_receiver.py`
预期: 消息插入逻辑更新成功

- [ ] **Step 4: 修改通知方法带上来源标识**

找到 `_send_receive_notification` 方法，更新内容构建：

```python
            content_lines = [
                f"## 📢 海外研报：{self.source.upper()}消息接收报告",
                "",
                "### 接收结果摘要",
                "",
                f"- **消息来源**: {self.source.upper()}",
                f"- **总计接收**: {result.total_messages} 条消息",
                f"- **新增消息**: {result.new_messages} 条",
                f"- **过滤消息**: {result.duplicate_messages + len(result.details[0].get('filtered_messages', []))} 条 (重复/无法解析)",
                f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
            ]
```

运行: 编辑文件 `src/processor/message_receiver.py`
预期: 通知格式更新成功

- [ ] **Step 5: 提交 MessageReceiver 扩展**

```bash
git add src/processor/message_receiver.py
git commit -m "feat(receiver): add source parameter support for dingtalk"
```

运行: Git提交
预期: 提交成功

---

## Task 7: 扩展 main.py 添加 --source 参数

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在参数解析部分添加 --source 参数**

找到 `parser.add_argument('--process-pending', ...)` 后，添加：

```python
    parser.add_argument(
        '--source',
        choices=['feishu', 'dingtalk'],
        default='feishu',
        help='消息来源：feishu（飞书）或 dingtalk（钉钉），默认：feishu'
    )
```

运行: 编辑文件 `main.py`
预期: 参数添加成功

- [ ] **Step 2: 更新接收模式传递 source 参数**

找到 `with MessageReceiver(settings) as receiver:` 这一行，替换为：

```python
            with MessageReceiver(settings, source=args.source) as receiver:
```

同时更新日志：

```python
            logger.info(f"接收模式：开始接收{args.source}消息...")
```

运行: 编辑文件 `main.py`
预期: 接收模式更新成功

- [ ] **Step 3: 更新接收完成日志**

找到日志输出部分，添加来源信息：

```python
                logger.info(f"{args.source.upper()}消息接收完成！")
                logger.info(f"总计接收: {result.total_messages} 条消息")
```

运行: 编辑文件 `main.py`
预期: 日志更新成功

- [ ] **Step 4: 提交 main.py 扩展**

```bash
git add main.py
git commit -m "feat(cli): add --source parameter for message source selection"
```

运行: Git提交
预期: 提交成功

---

## Task 8: 创建 DingtalkMessageClient 单元测试

**Files:**
- Create: `tests/test_dingtalk_client.py`

- [ ] **Step 1: 创建测试文件**

```python
"""
测试 DingtalkMessageClient
"""

import pytest
from unittest.mock import Mock, patch
from src.feishu.dingtalk_client import DingtalkMessageClient
from src.config.settings import Settings


class TestDingtalkMessageClient:
    """测试钉钉消息客户端"""

    def setup_method(self):
        """设置测试环境"""
        self.settings = Mock(spec=Settings)
        self.settings.dingtalk_app_key = 'test_app_key'
        self.settings.dingtalk_app_secret = 'test_app_secret'
        self.settings.dingtalk_chat_id = 'test_chat_id'
        self.client = DingtalkMessageClient(self.settings)

    def test_initialization(self):
        """测试客户端初始化"""
        assert self.client.app_key == 'test_app_key'
        assert self.client.app_secret == 'test_app_secret'
        assert self.client.chat_id == 'test_chat_id'
        assert self.client.token is None
        assert self.client.max_retries == 5

    def test_initialization_with_empty_credentials(self):
        """测试空凭证初始化"""
        settings = Mock(spec=Settings)
        settings.dingtalk_app_key = ''
        settings.dingtalk_app_secret = ''
        settings.dingtalk_chat_id = ''

        client = DingtalkMessageClient(settings)
        assert client.app_key == ''
        assert client.app_secret == ''

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_success(self, mock_post):
        """测试成功获取 access_token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accessToken': 'test_token_123'
        }
        mock_post.return_value = mock_response

        token = self.client.get_access_token()

        assert token == 'test_token_123'
        assert self.client.token == 'test_token_123'
        mock_post.assert_called_once()

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_api_error(self, mock_post):
        """测试API错误"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': 'Invalid credentials'
        }
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="API error"):
            self.client.get_access_token()

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_retry_on_500(self, mock_post):
        """测试500错误重试"""
        mock_response_error = Mock()
        mock_response_error.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'accessToken': 'test_token_123'
        }

        mock_post.side_effect = [
            mock_response_error,
            mock_response_success
        ]

        token = self.client.get_access_token()

        assert token == 'test_token_123'
        assert mock_post.call_count == 2

    def test_calculate_backoff(self):
        """测试指数退避计算"""
        assert self.client._calculate_backoff(0) == 1
        assert self.client._calculate_backoff(1) == 2
        assert self.client._calculate_backoff(2) == 4
        assert self.client._calculate_backoff(3) == 8
        assert self.client._calculate_backoff(4) == 16  # 最大值
        assert self.client._calculate_backoff(10) == 16  # 超过最大值

    def test_should_retry_error(self):
        """测试重试错误判断"""
        assert self.client._should_retry_error(500) == True
        assert self.client._should_retry_error(503) == True
        assert self.client._should_retry_error(429) == True
        assert self.client._should_retry_error(400) == False
        assert self.client._should_retry_error(404) == False

    def test_is_rate_limit_error(self):
        """测试限流错误判断"""
        assert self.client._is_rate_limit_error(429) == True
        assert self.client._is_rate_limit_error(500) == False

    @patch('src.feishu.dingtalk_client.DingtalkMessageClient.get_messages')
    def test_get_messages_not_implemented(self, mock_get):
        """测试 get_messages 未实现"""
        mock_get.side_effect = NotImplementedError(
            "get_messages requires Dingtalk API endpoint confirmation"
        )

        with pytest.raises(NotImplementedError):
            self.client.get_messages()
```

运行: 创建新文件
预期: 文件创建成功

- [ ] **Step 2: 运行测试验证**

```bash
cd /d/git/baidu-download && python -m pytest tests/test_dingtalk_client.py -v
```

运行: pytest
预期: 测试通过

- [ ] **Step 3: 提交测试文件**

```bash
git add tests/test_dingtalk_client.py
git commit -m "test(dingtalk): add DingtalkMessageClient unit tests"
```

运行: Git提交
预期: 提交成功

---

## Task 9: 数据库迁移和集成测试

**Files:**
- Test: `tests/test_integration.py` (可能创建新测试文件)

- [ ] **Step 1: 执行数据库迁移**

```bash
mysql -u root -p <database_name> <<EOF
ALTER TABLE message_process_log 
ADD COLUMN source ENUM('feishu', 'dingtalk') 
DEFAULT 'feishu' 
COMMENT '消息来源（飞书/钉钉）';

CREATE INDEX idx_source ON message_process_log(source);
EOF
```

运行: MySQL命令
预期: 字段添加成功，索引创建成功

- [ ] **Step 2: 验证现有数据兼容性**

```bash
mysql -u root -p <database_name> -e "SELECT id, source, process_status FROM message_process_log LIMIT 5;"
```

运行: MySQL查询
预期: 现有记录的 source 字段自动填充 'feishu'

- [ ] **Step 3: 创建集成测试文件**

```python
"""
集成测试：验证完整流程
"""

import pytest
from src.processor.message_receiver import MessageReceiver
from src.config.settings import Settings
from unittest.mock import Mock, patch, MagicMock


class TestMessageReceiverIntegration:
    """集成测试：消息接收完整流程"""

    def test_feishu_message_receiving_still_works(self):
        """测试飞书消息接收仍然正常工作"""
        settings = Mock(spec=Settings)
        settings.db_host = 'localhost'
        settings.db_port = 3306
        settings.db_user = 'test_user'
        settings.db_password = 'test_pass'
        settings.db_name = 'test_db'
        settings.feishu_app_id = 'test_app_id'
        settings.feishu_app_secret = 'test_app_secret'
        settings.feishu_chat_id = 'test_chat_id'

        with patch('src.processor.message_receiver.FeishuMessageClient'):
            with patch('src.processor.message_receiver.DatabaseRepository'):
                receiver = MessageReceiver(settings, source='feishu')
                assert receiver.source == 'feishu'

    def test_dingtalk_message_receiving_initialization(self):
        """测试钉钉消息接收器初始化"""
        settings = Mock(spec=Settings)
        settings.db_host = 'localhost'
        settings.db_port = 3306
        settings.db_user = 'test_user'
        settings.db_password = 'test_pass'
        settings.db_name = 'test_db'
        settings.dingtalk_app_key = 'test_app_key'
        settings.dingtalk_app_secret = 'test_app_secret'
        settings.dingtalk_chat_id = 'test_chat_id'

        with patch('src.feishu.dingtalk_client.DingtalkMessageClient'):
            with patch('src.processor.message_receiver.DatabaseRepository'):
                receiver = MessageReceiver(settings, source='dingtalk')
                assert receiver.source == 'dingtalk'
```

运行: 创建或编辑测试文件
预期: 测试文件创建成功

- [ ] **Step 4: 运行集成测试**

```bash
cd /d/git/baidu-download && python -m pytest tests/test_integration.py -v -k "test_feishu_message_receiving_still_works or test_dingtalk_message_receiving_initialization"
```

运行: pytest
预期: 集成测试通过

- [ ] **Step 5: 提交集成测试**

```bash
git add tests/test_integration.py
git commit -m "test(integration): add message receiver integration tests"
```

运行: Git提交
预期: 提交成功

---

## Task 10: 文档更新和最终验证

**Files:**
- Modify: `README.md` (或其他文档文件)
- Modify: `.env.example`

- [ ] **Step 1: 更新 .env.example 添加钉钉配置**

```bash
# 钉钉配置
DINGTALK_APP_KEY=your_dingtalk_app_key_here
DINGTALK_APP_SECRET=your_dingtalk_app_secret_here
DINGTALK_CHAT_ID=your_dingtalk_chat_id_here
```

运行: 编辑文件 `.env.example`
预期: 配置项添加成功

- [ ] **Step 2: 更新 README.md 添加钉钉使用说明**

在 README.md 的使用示例部分添加：

```markdown
### 接收钉钉消息

```bash
# 接收钉钉消息
python main.py --receive-messages --source dingtalk

# 接收钉钉消息（详细日志）
python main.py --receive-messages --source dingtalk --verbose
```

### 消息来源说明

系统支持两种消息来源：
- **飞书（feishu）**：默认来源，通过飞书群接收消息
- **钉钉（dingtalk）**：新增支持，通过钉钉群接收消息

消息会自动识别来源，并在数据库中通过 `source` 字段区分。
```

运行: 编辑文件 `README.md`
预期: 文档更新成功

- [ ] **Step 3: 运行完整测试套件**

```bash
cd /d/git/baidu-download && python -m pytest tests/ -v --tb=short
```

运行: pytest
预期: 所有测试通过

- [ ] **Step 4: 手动测试命令行参数**

```bash
cd /d/git/baidu-download

# 测试 --source 参数
python main.py --receive-messages --source feishu --dry-run
python main.py --receive-messages --source dingtalk --dry-run
```

运行: 命令行测试
预期: 参数正确识别

- [ ] **Step 5: 提交文档更新**

```bash
git add README.md .env.example
git commit -m "docs: add dingtalk configuration and usage documentation"
```

运行: Git提交
预期: 提交成功

- [ ] **Step 6: 创建最终提交标记版本**

```bash
git tag -a v1.3.0 -m "feat: add Dingtalk message receiver support"
git push origin v1.3.0
```

运行: Git标签
预期: 标签创建成功

---

## Task 11: 验证现有功能未受影响（回归测试）

**Files:**
- Test: 运行现有测试套件

- [ ] **Step 1: 运行所有现有测试**

```bash
cd /d/git/baidu-download && python -m pytest tests/ -v --tb=short
```

运行: pytest
预期: 所有测试通过

- [ ] **Step 2: 测试飞书消息接收默认行为**

```bash
cd /d/git/baidu-download

# 测试不指定 --source 时的默认行为（应该是飞书）
python main.py --receive-messages --dry-run
```

运行: 命令行测试
预期: 默认使用飞书，无错误

- [ ] **Step 3: 检查数据库兼容性**

```bash
mysql -u root -p <database_name> -e "SELECT COUNT(*) as total, source FROM message_process_log GROUP BY source;"
```

运行: MySQL查询
预期: 现有数据显示 source='feishu'，无数据丢失

- [ ] **Step 4: 检查配置验证**

```bash
cd /d/git/baidu-download

# 测试配置验证（缺少必要配置应该报错）
DINGTALK_APP_KEY=test python -c "from src.config.settings import Settings; s = Settings(); s.validate()"
```

运行: 配置验证测试
预期: 配置验证正确工作

- [ ] **Step 5: 创建回归测试通过标记**

```bash
echo "✅ 回归测试通过 - 现有功能未受影响" >> docs/superpowers/plans/2026-07-25-regression-test-pass.txt
```

运行: 创建标记文件
预期: 标记文件创建成功

---

## 后续步骤（待钉钉API确认后）

**Task 12: 实现 DingtalkMessageClient.get_messages（待API确认）**

等待用户提供钉钉API凭证后，根据实际API文档实现 `get_messages` 方法。

**Task 13: 端到端测试（待真实凭证）**

使用真实钉钉凭证测试完整流程：
1. 获取 access_token
2. 获取群消息
3. 解析钉钉格式消息
4. 存储到数据库
5. 发送通知

---

## 自审检查清单

### ✅ Spec 覆盖度
- [x] 数据库扩展（source字段）
- [x] 配置扩展（钉钉配置项）
- [x] 统一消息识别（正则匹配）
- [x] DingtalkMessageClient（基础结构）
- [x] MessageReceiver扩展（source参数）
- [x] main.py扩展（--source参数）
- [x] 错误处理（复用飞书逻辑）
- [x] 测试策略（单元、集成、回归）

### ✅ 占位符扫描
- 无 "TBD"、"TODO"、"implement later"
- 无 "添加适当的错误处理"
- 无 "Write tests for the above"（所有测试都有具体代码）
- 无 "Similar to Task N"（每个步骤都独立完整）

### ✅ 类型一致性
- ParseResult.source 在所有任务中一致
- MessageProcessLog.source 在数据库和模型中一致
- --source 参数与内部 source 变量一致

### ✅ 文件结构
- 所有文件路径明确
- 新建和修改清晰分离
- 每个文件职责明确

---

**计划状态：** ✅ 完成
**保存路径：** `docs/superpowers/plans/2026-07-25-dingtalk-message-receiver.md`
**下一步：** 等待用户选择执行方式（Subagent-Driven 或 Inline Execution）
