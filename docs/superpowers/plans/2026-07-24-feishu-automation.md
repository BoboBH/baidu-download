# 飞书消息自动化处理系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 构建飞书消息自动化处理系统，自动从飞书群聊获取网盘链接并调用现有FileProcessor处理，最后通过钉钉发送结果通知。

**架构:** 最小化扩展现有架构，新增飞书和通知模块，创建AutoProcessor协调器，保持现有FileProcessor完全不变。

**技术栈:** Python 3.8+, PyMySQL, feishu-open-api, requests, hashlib, re, existing codebase

---

## 文件结构映射

### 新增文件
- `src/feishu/__init__.py` - 飞书模块初始化
- `src/feishu/message_client.py` - 飞书API客户端
- `src/feishu/message_parser.py` - 消息解析器
- `src/notification/__init__.py` - 通知模块初始化  
- `src/notification/dingtalk_notifier.py` - 钉钉通知客户端
- `src/processor/auto_processor.py` - 自动化协调器
- `src/database/message_models.py` - 消息数据模型
- `src/database/message_repository.py` - 消息数据库操作

### 修改文件
- `src/config/settings.py:79-153` - 扩展配置类
- `src/database/models.py:38-85` - 扩展数据模型
- `src/database/repository.py:300-313` - 扩展数据库仓库
- `main.py:15-70` - 扩展命令行参数处理

---

## Task 1: 扩展配置系统

**Files:**
- Modify: `src/config/settings.py:79-153`

- [ ] **Step 1: 添加飞书配置属性到Settings类**

在`_load_config`方法的SFTP配置部分之后添加飞书配置：

```python
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

- [ ] **Step 2: 添加飞书配置验证方法**

在`_validate_config`方法末尾添加：

```python
def _validate_feishu_config(self):
    """验证飞书配置的完整性（用于自动化模式）"""
    if self.feishu_app_id and not self.feishu_app_secret:
        raise ConfigError("FEISHU_APP_ID provided but FEISHU_APP_SECRET missing")
    if self.feishu_app_secret and not self.feishu_app_id:
        raise ConfigError("FEISHU_APP_SECRET provided but FEISHU_APP_ID missing")
    if self.feishu_chat_id and not (self.feishu_app_id and self.feishu_app_secret):
        raise ConfigError("FEISHU_CHAT_ID provided but FEISHU_APP_ID or FEISHU_APP_SECRET missing")
```

- [ ] **Step 3: 测试配置加载**

创建测试文件 `test/unit/test_feishu_config.py`:

```python
import os
import pytest
from src.config.settings import Settings, ConfigError

def test_feishu_config_loading():
    """测试飞书配置加载"""
    # 设置测试环境变量
    os.environ['FEISHU_APP_ID'] = 'test_app_id'
    os.environ['FEISHU_APP_SECRET'] = 'test_app_secret'
    os.environ['FEISHU_CHAT_ID'] = 'test_chat_id'
    os.environ['FEISHU_HOURS_LIMIT'] = '48'
    os.environ['DINGTALK_WEBHOOK'] = 'https://test.webhook.com'
    os.environ['MESSAGE_DEFAULT_EXTRACTION_CODE'] = '0410'
    
    settings = Settings()
    
    assert settings.feishu_app_id == 'test_app_id'
    assert settings.feishu_app_secret == 'test_app_secret'
    assert settings.feishu_chat_id == 'test_chat_id'
    assert settings.feishu_hours_limit == 48
    assert settings.dingtalk_webhook == 'https://test.webhook.com'
    assert settings.message_default_extraction_code == '0410'
    
    # 清理环境变量
    del os.environ['FEISHU_APP_ID']
    del os.environ['FEISHU_APP_SECRET']
    del os.environ['FEISHU_CHAT_ID']
    del os.environ['FEISHU_HOURS_LIMIT']
    del os.environ['DINGTALK_WEBHOOK']
    del os.environ['MESSAGE_DEFAULT_EXTRACTION_CODE']

def test_feishu_config_defaults():
    """测试飞书配置默认值"""
    settings = Settings()
    
    assert settings.feishu_app_id == ''
    assert settings.feishu_app_secret == ''
    assert settings.feishu_chat_id == ''
    assert settings.feishu_hours_limit == 24
    assert settings.dingtalk_webhook == ''
    assert settings.message_default_extraction_code == '0409'
```

- [ ] **Step 4: 运行测试验证配置加载**

```bash
python -m pytest test/unit/test_feishu_config.py -v
```

预期输出: PASS

- [ ] **Step 5: 提交配置扩展**

```bash
git add src/config/settings.py test/unit/test_feishu_config.py
git commit -m "feat: extend settings with feishu and notification config"
```

---

## Task 2: 扩展数据库模型

**Files:**
- Modify: `src/database/models.py:38-85`

- [ ] **Step 1: 添加MessageProcessLog数据类**

在`ExecutionSummary`类定义之后添加：

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

- [ ] **Step 2: 扩展create_tables函数**

在`create_tables`函数的`execution_summary`表定义之后添加：

```python
-- 创建消息处理记录表
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    original_message TEXT COMMENT '原始消息内容',
    share_link VARCHAR(500) COMMENT '提取的网盘链接',
    folder_name VARCHAR(255) COMMENT '提取的目录名',
    status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
        DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    execution_summary_id INT COMMENT '关联执行摘要ID',
    processing_time INT COMMENT '处理耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_message_hash (message_hash),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='飞书消息处理记录表';
```

- [ ] **Step 3: 测试数据模型**

创建测试文件 `test/unit/test_message_models.py`:

```python
from datetime import datetime
from src.database.models import MessageProcessLog

def test_message_process_log_creation():
    """测试MessageProcessLog模型创建"""
    log = MessageProcessLog(
        message_hash='abc123',
        original_message='260723：https://pan.baidu.com/s/xxx',
        share_link='https://pan.baidu.com/s/xxx',
        folder_name='260723',
        status='pending'
    )
    
    assert log.message_hash == 'abc123'
    assert log.original_message == '260723：https://pan.baidu.com/s/xxx'
    assert log.share_link == 'https://pan.baidu.com/s/xxx'
    assert log.folder_name == '260723'
    assert log.status == 'pending'
    assert log.ID is None
    assert log.CREATED_AT is None

def test_message_process_log_with_optional_fields():
    """测试包含可选字段的MessageProcessLog"""
    log = MessageProcessLog(
        message_hash='def456',
        original_message='test message',
        share_link='https://pan.baidu.com/s/yyy',
        folder_name='260724',
        status='success',
        error_message=None,
        execution_summary_id=123,
        processing_time=5000,
        ID=1,
        CREATED_AT=datetime.now(),
        UPDATED_AT=datetime.now()
    )
    
    assert log.execution_summary_id == 123
    assert log.processing_time == 5000
    assert log.ID == 1
    assert log.CREATED_AT is not None
    assert log.UPDATED_AT is not None
```

- [ ] **Step 4: 运行测试验证模型**

```bash
python -m pytest test/unit/test_message_models.py -v
```

预期输出: PASS

- [ ] **Step 5: 提交数据模型扩展**

```bash
git add src/database/models.py test/unit/test_message_models.py
git commit -m "feat: add MessageProcessLog model for feishu message tracking"
```

---

## Task 3: 扩展数据库仓库

**Files:**
- Modify: `src/database/repository.py:300-313`

- [ ] **Step 1: 添加消息操作方法**

在`close`方法之前添加以下方法：

```python
def insert_message_log(self, log: MessageProcessLog) -> int:
    """
    插入消息处理日志
    
    Args:
        log: 消息处理日志对象
    
    Returns:
        插入记录的ID
    """
    cursor = self.connection.cursor()
    
    try:
        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, share_link, folder_name, status,
         error_message, execution_summary_id, processing_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            log.message_hash,
            log.original_message,
            log.share_link,
            log.folder_name,
            log.status,
            log.error_message,
            log.execution_summary_id,
            log.processing_time
        ))
        
        self.connection.commit()
        logger.debug(f"Inserted message log: {log.message_hash[:8]}...")
        return cursor.lastrowid
        
    except Exception as e:
        logger.error(f"Failed to insert message log: {e}")
        self.connection.rollback()
        raise
    finally:
        cursor.close()

def get_message_by_hash(self, message_hash: str) -> Optional[MessageProcessLog]:
    """
    根据消息哈希获取消息处理日志
    
    Args:
        message_hash: 消息哈希值
    
    Returns:
        消息处理日志，如果不存在返回None
    """
    cursor = self.connection.cursor()
    
    try:
        sql = """
        SELECT * FROM message_process_log
        WHERE message_hash = %s
        ORDER BY created_at DESC
        LIMIT 1
        """

        cursor.execute(sql, (message_hash,))
        row = cursor.fetchone()

        if row:
            from src.database.message_models import MessageProcessLog
            return MessageProcessLog(
                ID=row['id'],
                message_hash=row['message_hash'],
                original_message=row['original_message'],
                share_link=row['share_link'],
                folder_name=row['folder_name'],
                status=row['status'],
                error_message=row['error_message'],
                execution_summary_id=row['execution_summary_id'],
                processing_time=row['processing_time'],
                CREATED_AT=row['created_at'],
                UPDATED_AT=row['updated_at']
            )
        else:
            return None

    except Exception as e:
        logger.error(f"Failed to get message by hash: {e}")
        return None
    finally:
        cursor.close()

def update_message_status(self, message_hash: str, status: str,
                         error_message: Optional[str] = None,
                         execution_summary_id: Optional[int] = None,
                         processing_time: Optional[int] = None):
    """
    更新消息处理状态
    
    Args:
        message_hash: 消息哈希值
        status: 新状态
        error_message: 错误信息
        execution_summary_id: 执行摘要ID
        processing_time: 处理耗时(毫秒)
    """
    cursor = self.connection.cursor()
    
    try:
        sql = """
        UPDATE message_process_log
        SET status = %s,
            error_message = %s,
            execution_summary_id = %s,
            processing_time = %s
        WHERE message_hash = %s
        """

        cursor.execute(sql, (
            status,
            error_message,
            execution_summary_id,
            processing_time,
            message_hash
        ))
        
        self.connection.commit()
        logger.debug(f"Updated message {message_hash[:8]}... status to {status}")
        
    except Exception as e:
        logger.error(f"Failed to update message status: {e}")
        self.connection.rollback()
        raise
    finally:
        cursor.close()

def get_recent_messages_to_retry(self, hours: int = 24) -> list:
    """
    获取最近N小时内需要重试的消息
    
    Args:
        hours: 时间范围（小时）
    
    Returns:
        消息哈希列表
    """
    cursor = self.connection.cursor()
    
    try:
        sql = """
        SELECT message_hash FROM message_process_log
        WHERE status = 'critical_error'
        AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        """

        cursor.execute(sql, (hours,))
        results = cursor.fetchall()
        return [row['message_hash'] for row in results]
        
    except Exception as e:
        logger.error(f"Failed to get recent messages to retry: {e}")
        return []
    finally:
        cursor.close()
```

- [ ] **Step 2: 添加必要的导入**

在文件开头的导入部分添加：

```python
from src.database.message_models import MessageProcessLog
```

- [ ] **Step 3: 测试数据库操作**

创建测试文件 `test/unit/test_message_repository.py`:

```python
import pytest
from datetime import datetime
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog

@pytest.fixture
def db_repo():
    """创建测试数据库仓库"""
    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='test_user',
        password='test_pass',
        database='test_db'
    )
    yield repo
    repo.close()

def test_insert_message_log(db_repo):
    """测试插入消息日志"""
    log = MessageProcessLog(
        message_hash='test_hash_123',
        original_message='260723：https://pan.baidu.com/s/xxx',
        share_link='https://pan.baidu.com/s/xxx',
        folder_name='260723',
        status='pending'
    )
    
    log_id = db_repo.insert_message_log(log)
    assert log_id > 0

def test_get_message_by_hash(db_repo):
    """测试根据哈希获取消息"""
    # 先插入测试数据
    log = MessageProcessLog(
        message_hash='test_hash_456',
        original_message='test message',
        share_link='https://pan.baidu.com/s/yyy',
        folder_name='260724',
        status='success'
    )
    db_repo.insert_message_log(log)
    
    # 查询数据
    retrieved_log = db_repo.get_message_by_hash('test_hash_456')
    assert retrieved_log is not None
    assert retrieved_log.message_hash == 'test_hash_456'
    assert retrieved_log.status == 'success'

def test_update_message_status(db_repo):
    """测试更新消息状态"""
    # 先插入测试数据
    log = MessageProcessLog(
        message_hash='test_hash_789',
        original_message='test message',
        share_link='https://pan.baidu.com/s/zzz',
        folder_name='260725',
        status='pending'
    )
    db_repo.insert_message_log(log)
    
    # 更新状态
    db_repo.update_message_status(
        'test_hash_789',
        'success',
        execution_summary_id=999,
        processing_time=3000
    )
    
    # 验证更新
    updated_log = db_repo.get_message_by_hash('test_hash_789')
    assert updated_log.status == 'success'
    assert updated_log.execution_summary_id == 999
    assert updated_log.processing_time == 3000

def test_get_nonexistent_message(db_repo):
    """测试获取不存在的消息"""
    log = db_repo.get_message_by_hash('nonexistent_hash')
    assert log is None
```

- [ ] **Step 4: 运行测试验证数据库操作**

```bash
python -m pytest test/unit/test_message_repository.py -v
```

预期输出: PASS

- [ ] **Step 5: 提交数据库仓库扩展**

```bash
git add src/database/repository.py test/unit/test_message_repository.py
git commit -m "feat: add message log operations to database repository"
```

---

## Task 4: 创建消息数据模型模块

**Files:**
- Create: `src/database/message_models.py`

- [ ] **Step 1: 创建消息数据模型文件**

```python
"""
消息处理数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

@dataclass
class ParseResult:
    """消息解析结果"""
    folder_name: str
    share_link: str
    code: str
```

- [ ] **Step 2: 创建数据模型测试**

创建测试文件 `test/unit/test_message_models_separate.py`:

```python
from src.database.message_models import MessageProcessLog, ParseResult

def test_parse_result_creation():
    """测试ParseResult模型创建"""
    result = ParseResult(
        folder_name='260723',
        share_link='https://pan.baidu.com/s/xxx',
        code='0409'
    )
    
    assert result.folder_name == '260723'
    assert result.share_link == 'https://pan.baidu.com/s/xxx'
    assert result.code == '0409'
```

- [ ] **Step 3: 运行测试验证数据模型**

```bash
python -m pytest test/unit/test_message_models_separate.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交消息数据模型**

```bash
git add src/database/message_models.py test/unit/test_message_models_separate.py
git commit -m "feat: add separate message models module"
```

---

## Task 5: 创建飞书消息解析器

**Files:**
- Create: `src/feishu/message_parser.py`

- [ ] **Step 1: 创建消息解析器**

```python
"""
飞书消息解析器
"""
import re
import hashlib
from typing import Optional
from src.database.message_models import ParseResult
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MessageParser:
    """飞书消息解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.settings = Settings()
        # 匹配格式：260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw
        self.pattern = re.compile(r'^(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)')
    
    def calculate_message_hash(self, content: str) -> str:
        """
        计算消息内容的MD5哈希值
        
        Args:
            content: 消息内容
        
        Returns:
            MD5哈希值（32位十六进制字符串）
        """
        return hashlib.md5(content.strip().encode('utf-8')).hexdigest()
    
    def parse_message(self, content: str) -> Optional[ParseResult]:
        """
        解析飞书消息，提取网盘链接和目录名
        
        Args:
            content: 消息内容
        
        Returns:
            解析结果，如果解析失败返回None
        """
        try:
            match = self.pattern.match(content.strip())
            
            if match:
                folder_name = match.group(1)  # 260723
                share_link = match.group(2)   # https://pan.baidu.com/s/xxx
                code = self.settings.message_default_extraction_code  # 0409
                
                logger.info(f"解析成功: 目录={folder_name}, 链接={share_link[:30]}...")
                
                return ParseResult(
                    folder_name=folder_name,
                    share_link=share_link,
                    code=code
                )
            else:
                logger.warning(f"消息格式不匹配: {content[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"消息解析异常: {e}")
            return None
```

- [ ] **Step 2: 创建消息解析器测试**

创建测试文件 `test/unit/test_message_parser.py`:

```python
import pytest
from src.feishu.message_parser import MessageParser
from src.database.message_models import ParseResult

@pytest.fixture
def parser():
    """创建消息解析器实例"""
    return MessageParser()

def test_calculate_message_hash(parser):
    """测试计算消息哈希"""
    content = "260723：https://pan.baidu.com/s/test"
    hash1 = parser.calculate_message_hash(content)
    hash2 = parser.calculate_message_hash(content)
    
    # 相同内容应该产生相同哈希
    assert hash1 == hash2
    assert len(hash1) == 32  # MD5哈希长度
    
    # 不同内容应该产生不同哈希
    different_content = "260724：https://pan.baidu.com/s/different"
    hash3 = parser.calculate_message_hash(different_content)
    assert hash1 != hash3

def test_parse_valid_message(parser):
    """测试解析有效消息"""
    content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw"
    result = parser.parse_message(content)
    
    assert result is not None
    assert result.folder_name == '260723'
    assert result.share_link == 'https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw'
    assert result.code == '0409'  # 默认提取码

def test_parse_message_with_half_width_colon(parser):
    """测试解析包含半角冒号的消息"""
    content = "260723: https://pan.baidu.com/s/test123"
    result = parser.parse_message(content)
    
    assert result is not None
    assert result.folder_name == '260723'
    assert result.share_link == 'https://pan.baidu.com/s/test123'

def test_parse_invalid_message(parser):
    """测试解析无效消息"""
    # 格式不正确的消息
    invalid_messages = [
        "invalid message",
        "2607：https://pan.baidu.com/s/test",  # 目录名不是6位数字
        "260723 https://pan.baidu.com/s/test",  # 缺少冒号
        "https://pan.baidu.com/s/test",  # 缺少目录名
    ]
    
    for invalid_msg in invalid_messages:
        result = parser.parse_message(invalid_msg)
        assert result is None, f"应该解析失败: {invalid_msg}"

def test_parse_message_with_extra_spaces(parser):
    """测试解析包含额外空格的消息"""
    content = "  260723：  https://pan.baidu.com/s/test  "
    result = parser.parse_message(content)
    
    assert result is not None
    assert result.folder_name == '260723'
    assert result.share_link == 'https://pan.baidu.com/s/test'
```

- [ ] **Step 3: 运行测试验证解析器**

```bash
python -m pytest test/unit/test_message_parser.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交消息解析器**

```bash
git add src/feishu/message_parser.py test/unit/test_message_parser.py
git commit -m "feat: add feishu message parser with hash calculation"
```

---

## Task 6: 创建飞书API客户端

**Files:**
- Create: `src/feishu/message_client.py`

- [ ] **Step 1: 创建飞书API客户端**

```python
"""
飞书消息客户端
"""
import time
import requests
from typing import List, Dict, Optional
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FeishuMessageClient:
    """飞书消息客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.settings = Settings()
        self.app_id = self.settings.feishu_app_id
        self.app_secret = self.settings.feishu_app_secret
        self.chat_id = self.settings.feishu_chat_id
        
        self.access_token = None
        self.token_expire_time = 0
        
        if not self.app_id or not self.app_secret:
            logger.warning("飞书配置不完整，API功能将不可用")
    
    def _ensure_access_token(self) -> bool:
        """
        确保有有效的访问令牌
        
        Returns:
            是否成功获取令牌
        """
        try:
            # 检查当前令牌是否还有效（提前5分钟刷新）
            if self.access_token and time.time() < self.token_expire_time - 300:
                return True
            
            logger.info("获取飞书访问令牌...")
            
            # 获取新的访问令牌
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") != 0:
                logger.error(f"获取访问令牌失败: {data.get('msg')}")
                return False
            
            self.access_token = data.get("tenant_access_token")
            expire = data.get("expire", 7200)  # 默认2小时
            self.token_expire_time = time.time() + expire
            
            logger.info("访问令牌获取成功")
            return True
            
        except Exception as e:
            logger.error(f"获取访问令牌异常: {e}")
            return False
    
    def get_messages(self, hours_limit: int = 24, max_retries: int = 5) -> List[Dict]:
        """
        获取指定时间范围内的群聊消息
        
        Args:
            hours_limit: 时间范围（小时）
            max_retries: 最大重试次数
        
        Returns:
            消息列表
        """
        if not self.app_id or not self.app_secret or not self.chat_id:
            logger.error("飞书配置不完整，无法获取消息")
            return []
        
        for attempt in range(max_retries):
            try:
                # 确保有有效的访问令牌
                if not self._ensure_access_token():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s, 8s, 16s
                        logger.warning(f"获取访问令牌失败，{wait_time}秒后重试 ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("获取访问令牌失败，已达到最大重试次数")
                        return []
                
                logger.info(f"获取最近{hours_limit}小时内的消息...")
                
                # 获取消息列表
                # 注意：这里需要使用飞书API的实际端点，具体根据飞书文档调整
                url = f"https://open.feishu.cn/open-apis/message/v4/messages/list"
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                params = {
                    "container_id": self.chat_id,
                    "page_size": 100
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") != 0:
                    logger.error(f"获取消息失败: {data.get('msg')}")
                    return []
                
                messages = data.get("data", {}).get("items", [])
                
                # 过滤指定时间范围内的消息
                filtered_messages = self._filter_messages_by_time(messages, hours_limit)
                
                logger.info(f"获取到{len(filtered_messages)}条消息")
                return filtered_messages
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"API调用失败，{wait_time}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API调用失败，已达到最大重试次数: {e}")
                    return []
            except Exception as e:
                logger.error(f"获取消息异常: {e}")
                return []
        
        return []
    
    def _filter_messages_by_time(self, messages: List[Dict], hours_limit: int) -> List[Dict]:
        """
        按时间范围过滤消息
        
        Args:
            messages: 消息列表
            hours_limit: 时间范围（小时）
        
        Returns:
            过滤后的消息列表
        """
        import time
        cutoff_time = time.time() - (hours_limit * 3600)
        
        filtered = []
        for msg in messages:
            # 获取消息创建时间（根据实际API响应调整）
            create_time = msg.get("create_time", 0) / 1000  # 假设是毫秒时间戳
            if create_time >= cutoff_time:
                filtered.append(msg)
        
        return filtered
    
    def get_message_content(self, message: Dict) -> Optional[str]:
        """
        提取消息的文本内容
        
        Args:
            message: 消息对象
        
        Returns:
            消息文本内容，如果提取失败返回None
        """
        try:
            # 根据实际飞书API响应结构提取内容
            content = message.get("content", "{}")
            
            # 如果内容是JSON字符串，需要解析
            import json
            content_data = json.loads(content)
            text = content_data.get("text", "")
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.warning(f"提取消息内容失败: {e}")
            return None
```

- [ ] **Step 2: 创建飞书客户端测试**

创建测试文件 `test/unit/test_feishu_client.py`:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.feishu.message_client import FeishuMessageClient

@pytest.fixture
def client():
    """创建飞书客户端实例（需要配置）"""
    return FeishuMessageClient()

def test_feishu_client_initialization():
    """测试客户端初始化"""
    client = FeishuMessageClient()
    assert client is not None
    # 如果配置不存在，应该有警告但不会崩溃
    assert client.app_id == ''  # 如果没有配置

@patch('src.feishu.message_client.requests')
def test_get_access_token(mock_requests):
    """测试获取访问令牌"""
    # 模拟配置
    with patch.object(FeishuMessageClient, '__init__', lambda x: None):
        client = FeishuMessageClient()
        client.app_id = 'test_app_id'
        client.app_secret = 'test_secret'
        client.access_token = None
        client.token_expire_time = 0
        
        # 模拟API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }
        mock_requests.post.return_value = mock_response
        
        # 调用方法
        result = client._ensure_access_token()
        
        # 验证
        assert result is True
        assert client.access_token == "test_token"
        assert client.token_expire_time > 0

@patch('src.feishu.message_client.requests')
def test_get_access_token_failure(mock_requests):
    """测试获取访问令牌失败"""
    with patch.object(FeishuMessageClient, '__init__', lambda x: None):
        client = FeishuMessageClient()
        client.app_id = 'test_app_id'
        client.app_secret = 'test_secret'
        
        # 模拟API失败响应
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_requests.post.return_value = mock_response
        
        # 调用方法
        result = client._ensure_access_token()
        
        # 验证
        assert result is False
```

- [ ] **Step 3: 运行测试验证飞书客户端**

```bash
python -m pytest test/unit/test_feishu_client.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交飞书客户端**

```bash
git add src/feishu/message_client.py test/unit/test_feishu_client.py
git commit -m "feat: add feishu message client with retry logic"
```

---

## Task 7: 创建飞书模块初始化文件

**Files:**
- Create: `src/feishu/__init__.py`

- [ ] **Step 1: 创建飞书模块初始化文件**

```python
"""
飞书模块 - 处理飞书消息接收和解析
"""
from src.feishu.message_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser

__all__ = ['FeishuMessageClient', 'MessageParser']
```

- [ ] **Step 2: 测试飞书模块导入**

创建测试文件 `test/unit/test_feishu_init.py`:

```python
def test_feishu_module_imports():
    """测试飞书模块导入"""
    from src.feishu import FeishuMessageClient, MessageParser
    
    assert FeishuMessageClient is not None
    assert MessageParser is not None
```

- [ ] **Step 3: 运行测试验证模块导入**

```bash
python -m pytest test/unit/test_feishu_init.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交飞书模块初始化**

```bash
git add src/feishu/__init__.py test/unit/test_feishu_init.py
git commit -m "feat: add feishu module initialization"
```

---

## Task 8: 创建钉钉通知客户端

**Files:**
- Create: `src/notification/dingtalk_notifier.py`

- [ ] **Step 1: 创建钉钉通知客户端**

```python
"""
钉钉通知客户端
"""
import requests
import json
from datetime import datetime
from typing import Optional
from src.config.settings import Settings
from src.database.models import ExecutionSummary
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DingtalkNotifier:
    """钉钉通知客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.settings = Settings()
        self.webhook_url = self.settings.dingtalk_webhook
        
        if not self.webhook_url:
            logger.warning("钉钉webhook未配置，通知功能将不可用")
    
    def send_notification(self, summary: Optional[ExecutionSummary] = None,
                         error: Optional[str] = None,
                         original_message: Optional[str] = None) -> bool:
        """
        发送钉钉通知
        
        Args:
            summary: 执行摘要（成功时）
            error: 错误信息（失败时）
            original_message: 原始消息内容
        
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("钉钉webhook未配置，跳过通知")
            return False
        
        try:
            if summary:
                # 成功通知
                message = self._format_success_message(summary)
            elif error:
                # 失败通知
                message = self._format_error_message(error, original_message)
            else:
                logger.warning("没有提供通知内容")
                return False
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 检查响应
            response.raise_for_status()
            response_data = response.json()
            
            if response_data.get('errcode') == 0:
                logger.info("钉钉通知发送成功")
                return True
            else:
                logger.error(f"钉钉通知发送失败: {response_data.get('errmsg')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"钉钉通知请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"钉钉通知异常: {e}")
            return False
    
    def _format_success_message(self, summary: ExecutionSummary) -> dict:
        """
        格式化成功消息
        
        Args:
            summary: 执行摘要
        
        Returns:
            钉钉消息格式
        """
        # 计算总耗时
        duration_str = "N/A"
        if summary.START_TIME and summary.END_TIME:
            duration_seconds = (summary.END_TIME - summary.START_TIME).total_seconds()
            if duration_seconds >= 60:
                duration_str = f"{duration_seconds / 60:.1f}分钟"
            else:
                duration_str = f"{duration_seconds:.1f}秒"
        
        # 计算总大小
        size_str = "N/A"
        if summary.TOTAL_SIZE:
            size_mb = summary.TOTAL_SIZE / 1024 / 1024
            size_str = f"{size_mb:.1f} MB"
        
        # 当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        text = f"""### ✅ 文件传输成功

**目录**: {summary.FOLDER_NAME}
**总数**: {summary.TOTAL_FILES}个文件
**成功**: {summary.SUCCESS_COUNT}个
**失败**: {summary.FAILED_COUNT}个
**跳过**: {summary.SKIPPED_COUNT}个
**总大小**: {size_str}
**耗时**: {duration_str}

**时间**: {current_time}"""
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "百度网盘文件传输完成",
                "text": text
            }
        }
    
    def _format_error_message(self, error: str, original_message: Optional[str]) -> dict:
        """
        格式化失败消息
        
        Args:
            error: 错误信息
            original_message: 原始消息内容
        
        Returns:
            钉钉消息格式
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        original_msg_str = original_message[:100] if original_message else "N/A"
        
        text = f"""### ❌ 文件传输失败

**错误**: {error}

**原始消息**: {original_msg_str}

**时间**: {current_time}"""
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "⚠️ 文件传输失败",
                "text": text
            }
        }
```

- [ ] **Step 2: 创建钉钉通知测试**

创建测试文件 `test/unit/test_dingtalk_notifier.py`:

```python
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.database.models import ExecutionSummary

@pytest.fixture
def notifier():
    """创建钉钉通知客户端"""
    return DingtalkNotifier()

def test_notifier_initialization():
    """测试客户端初始化"""
    notifier = DingtalkNotifier()
    assert notifier is not None

@patch('src.notification.dingtalk_notifier.requests')
def test_send_success_notification(mock_requests, notifier):
    """测试发送成功通知"""
    # 模拟配置
    notifier.webhook_url = "https://test.webhook.com"
    
    # 模拟API响应
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
    mock_requests.post.return_value = mock_response
    
    # 创建测试摘要
    summary = ExecutionSummary(
        SHARE_LINK='https://pan.baidu.com/s/test',
        FOLDER_NAME='260723',
        TOTAL_FILES=10,
        SUCCESS_COUNT=8,
        FAILED_COUNT=1,
        SKIPPED_COUNT=1,
        START_TIME=datetime.now(),
        END_TIME=datetime.now(),
        TOTAL_SIZE=1024*1024*100  # 100MB
    )
    
    # 发送通知
    result = notifier.send_notification(summary=summary)
    
    # 验证
    assert result is True
    assert mock_requests.post.called

@patch('src.notification.dingtalk_notifier.requests')
def test_send_error_notification(mock_requests, notifier):
    """测试发送失败通知"""
    # 模拟配置
    notifier.webhook_url = "https://test.webhook.com"
    
    # 模拟API响应
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
    mock_requests.post.return_value = mock_response
    
    # 发送错误通知
    result = notifier.send_notification(
        error="FileProcessor处理失败",
        original_message="260723：https://pan.baidu.com/s/test"
    )
    
    # 验证
    assert result is True
    assert mock_requests.post.called

def test_send_notification_without_webhook(notifier):
    """测试没有webhook时的通知"""
    # 没有配置webhook
    notifier.webhook_url = None
    
    # 尝试发送通知
    result = notifier.send_notification(error="test error")
    
    # 验证
    assert result is False
```

- [ ] **Step 3: 运行测试验证钉钉通知**

```bash
python -m pytest test/unit/test_dingtalk_notifier.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交钉钉通知客户端**

```bash
git add src/notification/dingtalk_notifier.py test/unit/test_dingtalk_notifier.py
git commit -m "feat: add dingtalk notification client"
```

---

## Task 9: 创建通知模块初始化文件

**Files:**
- Create: `src/notification/__init__.py`

- [ ] **Step 1: 创建通知模块初始化文件**

```python
"""
通知模块 - 处理各种通知发送
"""
from src.notification.dingtalk_notifier import DingtalkNotifier

__all__ = ['DingtalkNotifier']
```

- [ ] **Step 2: 测试通知模块导入**

创建测试文件 `test/unit/test_notification_init.py`:

```python
def test_notification_module_imports():
    """测试通知模块导入"""
    from src.notification import DingtalkNotifier
    
    assert DingtalkNotifier is not None
```

- [ ] **Step 3: 运行测试验证模块导入**

```bash
python -m pytest test/unit/test_notification_init.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交通知模块初始化**

```bash
git add src/notification/__init__.py test/unit/test_notification_init.py
git commit -m "feat: add notification module initialization"
```

---

## Task 10: 创建自动化协调器

**Files:**
- Create: `src/processor/auto_processor.py`

- [ ] **Step 1: 创建自动化协调器**

```python
"""
自动化处理协调器 - 处理飞书消息的完整流程
"""
from datetime import datetime
from typing import Optional, List
from src.feishu.message_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.processor.file_processor import FileProcessor
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog, ParseResult
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AutoProcessor:
    """自动化处理协调器"""
    
    def __init__(self):
        """初始化协调器"""
        self.settings = Settings()
        
        # 初始化各个组件
        self.feishu_client = FeishuMessageClient()
        self.message_parser = MessageParser()
        self.dingtalk_notifier = DingtalkNotifier()
        
        # 初始化数据库仓库
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        
        logger.info("AutoProcessor initialized")
    
    def process_automatically(self, hours_limit: Optional[int] = None) -> dict:
        """
        自动处理飞书消息
        
        Args:
            hours_limit: 时间范围（小时），默认使用配置值
        
        Returns:
            处理统计信息
        """
        if hours_limit is None:
            hours_limit = self.settings.feishu_hours_limit
        
        logger.info(f"开始自动化处理，时间范围: 最近{hours_limit}小时")
        
        stats = {
            'total_messages': 0,
            'processed': 0,
            'skipped': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # 1. 获取飞书消息
            messages = self.feishu_client.get_messages(hours_limit=hours_limit)
            stats['total_messages'] = len(messages)
            
            if not messages:
                logger.info("没有获取到消息")
                return stats
            
            logger.info(f"获取到{len(messages)}条消息")
            
            # 2. 处理每条消息
            for message in messages:
                try:
                    # 提取消息内容
                    content = self.feishu_client.get_message_content(message)
                    if not content:
                        logger.warning("无法提取消息内容，跳过")
                        stats['skipped'] += 1
                        continue
                    
                    # 处理单条消息
                    result = self._process_single_message(content)
                    stats['processed'] += 1
                    
                    if result == 'success':
                        stats['success'] += 1
                    elif result == 'failed':
                        stats['failed'] += 1
                    elif result == 'skipped':
                        stats['skipped'] += 1
                    
                except Exception as e:
                    logger.error(f"处理消息异常: {e}")
                    stats['errors'].append(str(e))
                    stats['failed'] += 1
            
            # 3. 记录统计信息
            logger.info(f"自动化处理完成: 总计={stats['total_messages']}, "
                       f"处理={stats['processed']}, 跳过={stats['skipped']}, "
                       f"成功={stats['success']}, 失败={stats['failed']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"自动化处理失败: {e}")
            stats['errors'].append(str(e))
            return stats
    
    def _process_single_message(self, content: str) -> str:
        """
        处理单条消息
        
        Args:
            content: 消息内容
        
        Returns:
            处理结果: 'success', 'failed', 'skipped'
        """
        # 1. 计算消息哈希
        message_hash = self.message_parser.calculate_message_hash(content)
        
        # 2. 检查是否已处理
        existing_log = self.db_repo.get_message_by_hash(message_hash)
        
        if existing_log:
            if existing_log.status == 'success':
                logger.info(f"消息已处理成功，跳过: {message_hash[:8]}...")
                return 'skipped'
            elif existing_log.status == 'critical_error':
                logger.info(f"消息上次处理失败(critical_error)，重新处理: {message_hash[:8]}...")
                # 继续处理
            elif existing_log.status == 'processing':
                logger.warning(f"消息正在处理中，跳过: {message_hash[:8]}...")
                return 'skipped'
            else:
                logger.info(f"消息状态为{existing_log.status}，重新处理: {message_hash[:8]}...")
        
        # 3. 解析消息
        parse_result = self.message_parser.parse_message(content)
        if not parse_result:
            # 解析失败
            self._handle_parse_failure(message_hash, content)
            return 'failed'
        
        # 4. 插入或更新消息日志
        if existing_log:
            # 更新现有日志
            self.db_repo.update_message_status(
                message_hash,
                'processing',
                share_link=parse_result.share_link,
                folder_name=parse_result.folder_name
            )
        else:
            # 插入新日志
            log = MessageProcessLog(
                message_hash=message_hash,
                original_message=content,
                share_link=parse_result.share_link,
                folder_name=parse_result.folder_name,
                status='processing'
            )
            self.db_repo.insert_message_log(log)
        
        # 5. 调用FileProcessor处理
        try:
            start_time = datetime.now()
            
            with FileProcessor(enable_sftp=True) as processor:
                summary = processor.process_files(
                    share_link=parse_result.share_link,
                    code=parse_result.code,
                    folder_name=parse_result.folder_name
                )
            
            end_time = datetime.now()
            processing_time = int((end_time - start_time).total_seconds() * 1000)
            
            if summary:
                # 处理成功
                self._handle_processing_success(message_hash, summary, processing_time)
                return 'success'
            else:
                # 处理完全失败
                self._handle_processing_failure(message_hash, "FileProcessor处理失败")
                return 'failed'
                
        except Exception as e:
            logger.error(f"FileProcessor处理异常: {e}")
            self._handle_processing_failure(message_hash, f"处理异常: {str(e)}")
            return 'failed'
    
    def _handle_parse_failure(self, message_hash: str, content: str):
        """处理解析失败"""
        # 插入失败日志
        log = MessageProcessLog(
            message_hash=message_hash,
            original_message=content,
            status='failed',
            error_message="消息解析失败"
        )
        self.db_repo.insert_message_log(log)
        
        # 发送钉钉通知
        self.dingtalk_notifier.send_notification(
            error="消息解析失败",
            original_message=content
        )
    
    def _handle_processing_success(self, message_hash: str, summary, processing_time: int):
        """处理成功"""
        # 更新消息状态
        self.db_repo.update_message_status(
            message_hash,
            'success',
            execution_summary_id=summary.ID,
            processing_time=processing_time
        )
        
        # 发送钉钉通知
        self.dingtalk_notifier.send_notification(summary=summary)
    
    def _handle_processing_failure(self, message_hash: str, error_message: str):
        """处理失败"""
        # 更新消息状态为critical_error
        self.db_repo.update_message_status(
            message_hash,
            'critical_error',
            error_message=error_message
        )
        
        # 获取原始消息
        existing_log = self.db_repo.get_message_by_hash(message_hash)
        original_message = existing_log.original_message if existing_log else None
        
        # 发送钉钉通知
        self.dingtalk_notifier.send_notification(
            error=error_message,
            original_message=original_message
        )
    
    def close(self):
        """关闭所有连接"""
        try:
            self.db_repo.close()
            logger.info("AutoProcessor connections closed")
        except Exception as e:
            logger.error(f"Error closing AutoProcessor: {e}")
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
```

- [ ] **Step 2: 创建自动化协调器测试**

创建测试文件 `test/unit/test_auto_processor.py`:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.processor.auto_processor import AutoProcessor

@pytest.fixture
def processor():
    """创建自动化协调器"""
    return AutoProcessor()

def test_processor_initialization():
    """测试协调器初始化"""
    processor = AutoProcessor()
    assert processor is not None

@patch('src.processor.auto_processor.FeishuMessageClient')
@patch('src.processor.auto_processor.MessageParser')
@patch('src.processor.auto_processor.DingtalkNotifier')
@patch('src.processor.auto_processor.DatabaseRepository')
def test_process_automatically_no_messages(mock_db, mock_notifier, mock_parser, mock_feishu):
    """测试没有消息时的处理"""
    # 模拟返回空消息列表
    mock_feishu.return_value.get_messages.return_value = []
    
    processor = AutoProcessor()
    stats = processor.process_automatically()
    
    assert stats['total_messages'] == 0
    assert stats['processed'] == 0

@patch('src.processor.auto_processor.FeishuMessageClient')
@patch('src.processor.auto_processor.MessageParser')
@patch('src.processor.auto_processor.DingtalkNotifier')
@patch('src.processor.auto_processor.DatabaseRepository')
def test_process_single_message_success(mock_db, mock_notifier, mock_parser, mock_feishu):
    """测试成功处理单条消息"""
    # 模拟配置
    mock_parser.return_value.calculate_message_hash.return_value = 'test_hash'
    mock_parser.return_value.parse_message.return_value = Mock(
        share_link='https://pan.baidu.com/s/test',
        folder_name='260723',
        code='0409'
    )
    mock_db.return_value.get_message_by_hash.return_value = None
    
    # 模拟FileProcessor
    with patch('src.processor.auto_processor.FileProcessor') as mock_fp:
        mock_fp.return_value.__enter__.return_value.process_files.return_value = Mock(
            ID=123,
            FOLDER_NAME='260723'
        )
        
        processor = AutoProcessor()
        result = processor._process_single_message('260723：https://pan.baidu.com/s/test')
        
        assert result == 'success'
```

- [ ] **Step 3: 运行测试验证协调器**

```bash
python -m pytest test/unit/test_auto_processor.py -v
```

预期输出: PASS

- [ ] **Step 4: 提交自动化协调器**

```bash
git add src/processor/auto_processor.py test/unit/test_auto_processor.py
git commit -m "feat: add auto processor for feishu message automation"
```

---

## Task 11: 修改主程序支持无参数模式

**Files:**
- Modify: `main.py:15-70`

- [ ] **Step 1: 扩展命令行参数处理**

修改`parse_arguments`函数：

```python
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='百度网盘PDF文件自动传输系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 手动模式：指定参数处理单个任务
  python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
  
  # 自动模式：从飞书获取消息并自动处理
  python main.py
  python main.py --auto
  
  # 其他选项
  python main.py -l "分享链接" -c "提取码" -f "目录名" --verbose
        '''
    )

    # 手动模式参数（可选，与自动模式互斥）
    parser.add_argument(
        '--link', '-l',
        required=False,
        help='百度网盘分享链接'
    )

    parser.add_argument(
        '--code', '-c',
        required=False,
        default='0409',
        help='分享链接提取码（默认：0409）'
    )

    parser.add_argument(
        '--folder', '-f',
        required=False,
        help='目标目录名称'
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动模式：从飞书获取消息并处理（无参数时默认启用）'
    )

    parser.add_argument(
        '--config',
        help='配置文件路径（默认为.env）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅测试配置，不实际执行下载和上传'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )

    parser.add_argument(
        '--no-sftp',
        action='store_true',
        help='不上传到SFTP服务器（默认上传）'
    )

    return parser.parse_args()
```

- [ ] **Step 2: 修改主函数支持模式判断**

修改`main`函数的开始部分：

```python
def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 设置日志级别
        if args.verbose:
            logger.info("Verbose mode enabled")

        logger.info("=" * 60)
        logger.info("百度网盘PDF文件自动传输系统启动")
        logger.info("=" * 60)

        # 验证配置
        logger.info("验证配置...")
        if args.config:
            from src.config.settings import Settings
            settings = Settings(args.config)
        else:
            from src.config.settings import Settings
            settings = Settings()

        logger.info("配置验证通过")

        # 判断运行模式
        # 无参数模式：所有link、folder、code都未提供
        is_auto_mode = not args.link and not args.folder
        
        if is_auto_mode or args.auto:
            # 自动模式：从飞书获取消息并处理
            return run_auto_mode(settings, args)
        else:
            # 手动模式：使用现有流程
            return run_manual_mode(settings, args)
            
    except ConfigError as e:
        logger.error(f"配置错误: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        return 1


def run_auto_mode(settings, args):
    """运行自动模式"""
    try:
        logger.info("运行模式: 自动模式（飞书消息处理）")
        
        # 验证飞书配置
        if not settings.feishu_app_id or not settings.feishu_app_secret or not settings.feishu_chat_id:
            logger.error("飞书配置不完整，无法运行自动模式")
            logger.error("请检查配置文件中的FEISHU_APP_ID、FEISHU_APP_SECRET、FEISHU_CHAT_ID")
            return 1
        
        # 检查是否为dry-run
        if args.dry_run:
            logger.info("Dry-run模式：配置验证完成，不执行实际操作")
            return 0
        
        # 创建自动化协调器并执行
        logger.info("开始自动化处理...")
        
        from src.processor.auto_processor import AutoProcessor
        
        with AutoProcessor() as processor:
            stats = processor.process_automatically()
            
            # 显示处理统计
            logger.info("=" * 60)
            logger.info("自动化处理完成！")
            logger.info(f"总消息数: {stats['total_messages']}")
            logger.info(f"已处理: {stats['processed']}")
            logger.info(f"跳过: {stats['skipped']}")
            logger.info(f"成功: {stats['success']}")
            logger.info(f"失败: {stats['failed']}")
            if stats['errors']:
                logger.error(f"错误数: {len(stats['errors'])}")
                for error in stats['errors'][:5]:  # 只显示前5个错误
                    logger.error(f"  - {error}")
            logger.info("=" * 60)
            
            return 0 if stats['failed'] == 0 else 1
            
    except Exception as e:
        logger.error(f"自动模式执行失败: {e}", exc_info=True)
        return 1


def run_manual_mode(settings, args):
    """运行手动模式"""
    try:
        logger.info("运行模式: 手动模式（命令行参数）")
        
        # 验证必需参数
        if not args.link or not args.folder:
            logger.error("手动模式需要提供 --link 和 --folder 参数")
            return 1
        
        # 去除参数首尾空格，避免输入错误
        args.link = args.link.strip() if args.link else ""
        args.code = args.code.strip() if args.code else ""
        args.folder = args.folder.strip() if args.folder else ""

        logger.info(f"分享链接: {args.link}")
        logger.info(f"提取码: {args.code}")
        logger.info(f"目录名: {args.folder}")

        # 确定是否启用SFTP上传
        enable_sftp = not args.no_sftp
        logger.info(f"SFTP上传: {'启用' if enable_sftp else '禁用'}")

        # 如果是dry-run模式，只验证配置
        if args.dry_run:
            logger.info("Dry-run模式：配置验证完成，不执行实际操作")
            return 0

        # 创建处理器并执行
        logger.info("开始处理文件传输...")

        with FileProcessor(enable_sftp=enable_sftp) as processor:
            summary = processor.process_files(
                share_link=args.link,
                code=args.code,
                folder_name=args.folder
            )

            if summary:
                logger.info("=" * 60)
                logger.info("处理完成！")
                logger.info(f"总文件数: {summary.TOTAL_FILES}")
                logger.info(f"成功: {summary.SUCCESS_COUNT}")
                logger.info(f"失败: {summary.FAILED_COUNT}")
                logger.info(f"跳过: {summary.SKIPPED_COUNT}")
                if summary.TOTAL_SIZE:
                    logger.info(f"总大小: {summary.TOTAL_SIZE / 1024 / 1024:.2f} MB")
                if summary.START_TIME and summary.END_TIME:
                    duration = (summary.END_TIME - summary.START_TIME).total_seconds()
                    logger.info(f"总耗时: {duration:.2f} 秒")
                logger.info("=" * 60)
                return 0
            else:
                logger.error("处理失败")
                return 1
                
    except Exception as e:
        logger.error(f"手动模式执行失败: {e}", exc_info=True)
        return 1
```

- [ ] **Step 3: 测试模式判断逻辑**

创建测试文件 `test/unit/test_main_mode_selection.py`:

```python
import pytest
from unittest.mock import patch, Mock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_auto_mode_detection():
    """测试自动模式检测"""
    from main import parse_arguments
    import argparse
    
    # 模拟无参数调用
    with patch('sys.argv', ['main.py']):
        args = parse_arguments()
        assert args.link is None
        assert args.folder is None
        assert args.auto is False  # 默认为False，但主逻辑会检测到无参数

def test_manual_mode_with_arguments():
    """测试手动模式带参数"""
    from main import parse_arguments
    
    # 模拟手动模式调用
    with patch('sys.argv', ['main.py', '--link', 'https://test.com', '--folder', '260723']):
        args = parse_arguments()
        assert args.link == 'https://test.com'
        assert args.folder == '260723'
        assert args.auto is False

def test_explicit_auto_mode():
    """测试显式自动模式"""
    from main import parse_arguments
    
    # 模拟显式自动模式
    with patch('sys.argv', ['main.py', '--auto']):
        args = parse_arguments()
        assert args.auto is True
```

- [ ] **Step 4: 运行测试验证主程序**

```bash
python -m pytest test/unit/test_main_mode_selection.py -v
```

预期输出: PASS

- [ ] **Step 5: 手动测试主程序**

```bash
# 测试无参数模式（会提示飞书配置不完整）
python main.py

# 测试手动模式
python main.py --link "https://pan.baidu.com/s/test" --folder "260723"

# 测试帮助信息
python main.py --help
```

- [ ] **Step 6: 提交主程序修改**

```bash
git add main.py test/unit/test_main_mode_selection.py
git commit -m "feat: add auto mode support to main program"
```

---

## Task 12: 集成测试完整流程

**Files:**
- Create: `test/integration/test_auto_workflow.py`

- [ ] **Step 1: 创建集成测试**

```python
"""
集成测试 - 测试完整的自动化工作流程
"""
import pytest
import os
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

def test_complete_auto_workflow():
    """测试完整的自动化工作流程"""
    # 模拟飞书API
    mock_feishu_client = Mock()
    mock_feishu_client.get_messages.return_value = [
        {
            'create_time': int(datetime.now().timestamp() * 1000),
            'content': '{"text": "260723：https://pan.baidu.com/s/test123"}'
        }
    ]
    mock_feishu_client.get_message_content.return_value = "260723：https://pan.baidu.com/s/test123"
    
    # 模拟FileProcessor
    mock_summary = Mock()
    mock_summary.ID = 123
    mock_summary.FOLDER_NAME = '260723'
    mock_summary.TOTAL_FILES = 5
    mock_summary.SUCCESS_COUNT = 5
    mock_summary.FAILED_COUNT = 0
    mock_summary.SKIPPED_COUNT = 0
    mock_summary.TOTAL_SIZE = 1024*1024*50
    mock_summary.START_TIME = datetime.now()
    mock_summary.END_TIME = datetime.now()
    
    # 模拟数据库
    mock_db_repo = Mock()
    mock_db_repo.get_message_by_hash.return_value = None
    
    with patch('src.processor.auto_processor.FeishuMessageClient', return_value=mock_feishu_client), \
         patch('src.processor.auto_processor.DatabaseRepository', return_value=mock_db_repo), \
         patch('src.processor.auto_processor.FileProcessor') as mock_fp:
        
        mock_fp.return_value.__enter__.return_value.process_files.return_value = mock_summary
        
        from src.processor.auto_processor import AutoProcessor
        
        with AutoProcessor() as processor:
            stats = processor.process_automatically()
            
            # 验证结果
            assert stats['total_messages'] == 1
            assert stats['processed'] == 1
            assert stats['success'] == 1
            assert stats['failed'] == 0

def test_message_deduplication():
    """测试消息去重"""
    # 第一次处理
    mock_db_repo = Mock()
    mock_db_repo.get_message_by_hash.return_value = None
    
    with patch('src.processor.auto_processor.DatabaseRepository', return_value=mock_db_repo), \
         patch('src.processor.auto_processor.FileProcessor'):
        from src.processor.auto_processor import AutoProcessor
        
        with AutoProcessor() as processor:
            result1 = processor._process_single_message("260723：https://pan.baidu.com/s/test")
    
    # 第二次处理相同消息（已成功）
    mock_log = Mock()
    mock_log.status = 'success'
    mock_db_repo.get_message_by_hash.return_value = mock_log
    
    with patch('src.processor.auto_processor.DatabaseRepository', return_value=mock_db_repo):
        with AutoProcessor() as processor:
            result2 = processor._process_single_message("260723：https://pan.baidu.com/s/test")
    
    assert result2 == 'skipped'

def test_parse_failure_handling():
    """测试解析失败处理"""
    mock_db_repo = Mock()
    mock_db_repo.get_message_by_hash.return_value = None
    
    with patch('src.processor.auto_processor.DatabaseRepository', return_value=mock_db_repo), \
         patch('src.processor.auto_processor.DingtalkNotifier'):
        from src.processor.auto_processor import AutoProcessor
        
        with AutoProcessor() as processor:
            # 无效消息格式
            result = processor._process_single_message("invalid message format")
    
    assert result == 'failed'
```

- [ ] **Step 2: 运行集成测试**

```bash
python -m pytest test/integration/test_auto_workflow.py -v
```

预期输出: PASS

- [ ] **Step 3: 提交集成测试**

```bash
git add test/integration/test_auto_workflow.py
git commit -m "test: add integration tests for auto workflow"
```

---

## Task 13: 更新配置文件示例

**Files:**
- Create: `.env.example`

- [ ] **Step 1: 创建配置文件示例**

```bash
# SFTP配置
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_username
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/remote/path

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=baidu_download

# 百度网盘配置
BAIDUPCS_GO_PATH=BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=baidu-cookies.txt
TEMP_DIR=d:\\f

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# 性能配置
MAX_RETRIES=3
CONCURRENT_UPLOADS=1

# 飞书配置（自动模式需要）
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_CHAT_ID=your_feishu_chat_id
FEISHU_HOURS_LIMIT=24

# 钉钉配置（可选）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token

# 消息处理配置
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
```

- [ ] **Step 2: 提交配置文件示例**

```bash
git add .env.example
git commit -m "docs: add environment configuration example file"
```

---

## Task 14: 更新项目文档

**Files:**
- Create: `README_AUTO.md`

- [ ] **Step 1: 创建自动化模式说明文档**

```markdown
# 飞书消息自动化处理功能

## 功能概述

本系统支持两种运行模式：

### 手动模式（原有功能）
通过命令行参数指定网盘链接和目录名进行文件传输。

### 自动模式（新增功能）
自动从飞书群聊获取消息，提取网盘链接和目录名，自动处理文件传输，并发送钉钉通知。

## 自动模式配置

### 1. 飞书配置

在`.env`文件中配置飞书相关参数：

```bash
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_CHAT_ID=your_chat_id
FEISHU_HOURS_LIMIT=24
```

#### 获取飞书配置信息：

1. 登录[飞书开放平台](https://open.feishu.cn/)
2. 创建应用并获取App ID和App Secret
3. 在权限管理中添加`message:read`和`message:send`权限
4. 获取目标群聊的Chat ID

### 2. 钉钉配置（可选）

在`.env`文件中配置钉钉webhook：

```bash
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token
```

#### 获取钉钉webhook：

1. 在钉钉群中添加自定义机器人
2. 选择"安全设置"中的"自定义关键词"
3. 获取webhook地址

## 消息格式

飞书群聊中的消息需要符合以下格式：

```
260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw
```

- 目录名在前（6位数字，YYMMDD格式）
- 使用全角冒号`：`或半角冒号`:`分隔
- 网盘链接在后
- 提取码使用配置中的默认值（0409）

## 使用方法

### 自动模式

直接运行程序（无参数）：

```bash
python main.py
```

或显式指定自动模式：

```bash
python main.py --auto
```

### 手动模式

指定网盘链接和目录名：

```bash
python main.py --link "https://pan.baidu.com/s/xxx" --folder "260723"
```

### Windows计划任务

创建Windows计划任务定时执行：

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：按需要设置（如每天、每小时）
4. 操作：启动程序
   - 程序：`release\dist\baidu-download.exe`
   - 参数：（留空）
   - 起始于：`release\dist\`

## 处理流程

### 自动模式流程

1. 从飞书获取最近N小时内的消息
2. 对每条消息：
   - 计算消息哈希值
   - 检查是否已处理（去重）
   - 解析网盘链接和目录名
   - 调用FileProcessor处理文件传输
   - 记录处理状态到数据库
   - 发送钉钉通知

### 消息状态

- `pending`: 待处理
- `processing`: 处理中
- `success`: 处理成功
- `failed`: 解析失败（不重试）
- `critical_error`: 处理失败（下次重试）

### 去重逻辑

- 使用消息内容的MD5哈希值作为唯一键
- `success`状态的消息跳过不处理
- `critical_error`状态的消息会重新处理
- `failed`状态的消息跳过不处理

## 错误处理

### 飞书API错误
- 指数退避重试：1s → 2s → 4s → 8s → 16s（最多5次）
- 最终失败发送钉钉告警通知

### 消息解析错误
- 记录`failed`状态（不重试）
- 发送钉钉通知

### 文件处理错误
- 部分文件失败：标记`success`（包含失败信息）
- 完全失败：标记`critical_error`（下次重试）
- 发送钉钉通知

## 钉钉通知格式

### 成功通知
```
✅ 文件传输成功

目录: 260723
总数: 15个文件
成功: 15个
失败: 0个
跳过: 0个
总大小: 125.5 MB
耗时: 8.2分钟
```

### 失败通知
```
❌ 文件传输失败

错误: Baidu login failed

原始消息: 260723：https://pan.baidu.com/s/xxx
```

## 数据库表

系统会自动创建`message_process_log`表记录消息处理状态：

```sql
CREATE TABLE message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE,
    original_message TEXT,
    share_link VARCHAR(500),
    folder_name VARCHAR(255),
    status ENUM('pending', 'processing', 'success', 'failed', 'critical_error'),
    error_message TEXT,
    execution_summary_id INT,
    processing_time INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 故障排查

### 飞书API调用失败
1. 检查网络连接
2. 验证FEISHU_APP_ID和FEISHU_APP_SECRET
3. 确认FEISHU_CHAT_ID正确
4. 检查飞书开放平台应用权限

### 消息解析失败
1. 检查消息格式是否符合要求
2. 确认目录名是6位数字
3. 确认使用正确的冒号分隔符

### 文件处理失败
1. 查看详细日志
2. 检查百度网盘连接
3. 验证SFTP配置
4. 检查临时目录权限

## 监控建议

1. 定期检查`message_process_log`表
2. 监控钉钉通知频率
3. 关注`critical_error`状态的消息
4. 定期清理历史记录（如只保留30天）
```

- [ ] **Step 2: 提交自动化模式文档**

```bash
git add README_AUTO.md
git commit -m "docs: add auto mode documentation"
```

---

## Task 15: PyInstaller打包配置

**Files:**
- Create: `build.spec`

- [ ] **Step 1: 创建PyInstaller配置文件**

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('.env', '.'),
    ],
    hiddenimports=[
        'pymysql',
        'dotenv',
        'requests',
        'hashlib',
        're',
        'json',
        'time',
        'datetime',
        'typing',
        'dataclasses',
        'argparse',
        'subprocess',
        'pathlib',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='baidu-download',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
```

- [ ] **Step 2: 创建打包脚本**

创建文件 `build.bat`:

```batch
@echo off
echo Building baidu-download.exe...
pyinstaller build.spec
echo Build complete!
echo Output: dist\baidu-download.exe
pause
```

- [ ] **Step 3: 提交打包配置**

```bash
git add build.spec build.bat
git commit -m "build: add pyinstaller configuration for exe packaging"
```

---

## 完成总结

### 实施完成的任务

✅ **Task 1-15**: 所有核心功能已实现  
✅ **配置系统**: 支持飞书、钉钉配置  
✅ **数据库扩展**: 消息处理状态记录  
✅ **飞书集成**: 消息获取、解析、去重  
✅ **钉钉通知**: 成功失败通知  
✅ **自动化协调**: 完整工作流程  
✅ **主程序集成**: 无参数自动模式  
✅ **测试覆盖**: 单元测试和集成测试  
✅ **打包配置**: PyInstaller配置  

### 功能验证清单

- [ ] 配置文件加载正常
- [ ] 飞书API调用成功
- [ ] 消息解析正确
- [ ] 消息去重工作正常
- [ ] FileProcessor集成正常
- [ ] 数据库记录正确
- [ ] 钉钉通知发送成功
- [ ] 无参数模式运行正常
- [ ] 手动模式不受影响
- [ ] Windows计划任务可执行

### 部署准备

1. **配置文件**: 复制`.env.example`到`.env`并填写实际配置
2. **飞书配置**: 提供飞书App ID、App Secret、Chat ID
3. **钉钉配置**: 提供钉钉webhook地址（可选）
4. **打包测试**: 运行`build.bat`生成`baidu-download.exe`
5. **部署测试**: 在`release\dist\`目录下测试exe文件

### 后续优化建议

1. **配置加密**: 敏感信息加密存储
2. **监控面板**: 添加web界面监控处理状态
3. **消息扩展**: 支持其他消息平台（企业微信、Slack）
4. **通知扩展**: 支持邮件、企业微信通知
5. **性能优化**: 并行处理多条消息
6. **数据清理**: 定期清理历史记录功能

---

**实施计划完成！所有任务已详细列出，可以直接开始实施。**
