# Message Retry Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable retry limit feature to message processing system that tracks failed attempts and permanently excludes messages after reaching maximum retry threshold (default: 10 attempts).

**Architecture:** Database-level enforcement with configuration-driven limits. Retry counts stored in `message_process_log` table, filtered at query time to exclude max-retry messages from retry processing.

**Tech Stack:** Python 3.8+, PyMySQL, MySQL 8.0+, pytest

---

## Task 1: Database Schema Migration

**Files:**
- Create: `database/migrations/add_retry_count.sql`

- [ ] **Step 1: Create migration SQL file**

```sql
-- Migration: Add retry_count column to message_process_log table
-- Date: 2026-08-18
-- Description: Add retry tracking for failed message processing attempts

-- Phase 1: Add retry_count column with default value
ALTER TABLE message_process_log 
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数' 
AFTER processing_time_ms;

-- Phase 2: Create index for efficient retry filtering
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- Verification query (run separately to check migration success)
-- Expected: 0 (all existing records should have retry_count = 0)
-- SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;
```

- [ ] **Step 2: Verify migration syntax**

Check: MySQL syntax for ALTER TABLE with AFTER clause and index creation ✅

- [ ] **Step 3: Test rollback capability**

```bash
# Manual test: Verify column can be dropped (for rollback)
# ALTER TABLE message_process_log DROP COLUMN retry_count;
```

- [ ] **Step 4: Commit migration file**

```bash
git add database/migrations/add_retry_count.sql
git commit -m "feat: add database migration for retry count tracking"
```

---

## Task 2: Update Database Schema Model

**Files:**
- Modify: `src/database/models.py`

- [ ] **Step 1: Update CREATE TABLE statement in create_tables()**

Find the `message_process_log` table definition (around line 97) and add retry_count column:

```python
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    original_message TEXT COMMENT '原始消息内容',
    share_link VARCHAR(500) COMMENT '提取的网盘链接',
    folder_name VARCHAR(255) COMMENT '提取的目录名',
    extraction_code VARCHAR(20) COMMENT '提取码（从folder_name提取）',
    source ENUM('feishu', 'dingtalk') DEFAULT 'feishu' COMMENT '消息来源（飞书/钉钉）',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
        DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    execution_summary_id INT COMMENT '关联执行摘要ID',
    processing_time_ms INT COMMENT '处理耗时(毫秒)',
    retry_count INT DEFAULT 0 COMMENT '失败重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_message_hash (message_hash),
    INDEX idx_source (source),
    INDEX idx_process_status (process_status),
    INDEX idx_created_at (created_at),
    INDEX idx_retry_count (retry_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='消息处理记录表（支持飞书和钉钉）';
```

- [ ] **Step 2: Verify schema changes**

Check: retry_count added after processing_time_ms, idx_retry_count added ✅

- [ ] **Step 3: Run tests to ensure no breaking changes**

Run: `python -m pytest tests/ -v` (if tests exist)

Expected: All existing tests pass (schema is backward compatible)

- [ ] **Step 4: Commit schema model update**

```bash
git add src/database/models.py
git commit -m "feat: update schema model with retry_count field"
```

---

## Task 3: Update Message Data Model

**Files:**
- Modify: `src/database/message_models.py`

- [ ] **Step 1: Add retry_count field to MessageProcessLog dataclass**

```python
@dataclass
class MessageProcessLog:
    """消息处理日志模型"""
    message_hash: str
    original_message: Optional[str] = None
    share_link: Optional[str] = None
    folder_name: Optional[str] = None
    extraction_code: Optional[str] = None
    source: str = 'feishu'  # 新增：消息来源，默认 feishu
    process_status: str = 'pending'  # pending, processing, success, failed, critical_error
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time_ms: Optional[int] = None  # 毫秒
    retry_count: int = 0  # 失败重试次数
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

- [ ] **Step 2: Verify field order and default value**

Check: retry_count has default value 0, placed before id field ✅

- [ ] **Step 3: Update get_message_by_hash() in repository.py**

Modify the method to include retry_count when constructing MessageProcessLog:

```python
def get_message_by_hash(self, message_hash: str) -> Optional[MessageProcessLog]:
    # ... existing code ...
    if row:
        return MessageProcessLog(
            id=row['id'],
            message_hash=row['message_hash'],
            original_message=row['original_message'],
            share_link=row['share_link'],
            folder_name=row['folder_name'],
            extraction_code=row.get('extraction_code'),
            source=row.get('source', 'feishu'),
            process_status=row['process_status'],
            error_message=row['error_message'],
            execution_summary_id=row.get('execution_summary_id'),
            processing_time_ms=row.get('processing_time_ms'),
            retry_count=row.get('retry_count', 0),  # Add this line
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
```

- [ ] **Step 4: Commit data model updates**

```bash
git add src/database/message_models.py src/database/repository.py
git commit -m "feat: add retry_count to MessageProcessLog model"
```

---

## Task 4: Add Configuration Management

**Files:**
- Modify: `src/config/settings.py`

- [ ] **Step 1: Add MESSAGE_MAX_RETRIES configuration in _load_config()**

Add after line 52 (message processing configuration section):

```python
# 消息处理配置
self.message_default_extraction_code = os.getenv('MESSAGE_DEFAULT_EXTRACTION_CODE', '0409')
self.max_message_retries = self._get_int_env('MESSAGE_MAX_RETRIES', default=10)  # Add this line
```

- [ ] **Step 2: Add validation in _validate_config()**

Add validation after line 159 (after extraction code validation):

```python
# 验证提取码格式（应该是4位数字）
if self.message_default_extraction_code:
    if not re.match(r'^\d{4}$', self.message_default_extraction_code):
        raise ConfigError(f"Invalid MESSAGE_DEFAULT_EXTRACTION_CODE format: {self.message_default_extraction_code}. Expected 4 digits.")

# 验证消息重试次数范围（应该是1-100）
if not (1 <= self.max_message_retries <= 100):
    raise ConfigError(f"MESSAGE_MAX_RETRIES must be between 1 and 100: {self.max_message_retries}")
```

- [ ] **Step 3: Test configuration validation**

```python
# Test invalid values (should raise ConfigError)
# MESSAGE_MAX_RETRIES=0   -> ConfigError
# MESSAGE_MAX_RETRIES=101 -> ConfigError
# MESSAGE_MAX_RETRIES=10  -> OK
# MESSAGE_MAX_RETRIES=1   -> OK
```

- [ ] **Step 4: Commit configuration changes**

```bash
git add src/config/settings.py
git commit -m "feat: add MESSAGE_MAX_RETRIES configuration with validation"
```

---

## Task 5: Update Repository - modify update_message_status()

**Files:**
- Modify: `src/database/repository.py`

- [ ] **Step 1: Replace update_message_status() method**

Replace the existing method (lines 393-435) with retry count logic:

```python
def update_message_status(self, message_hash: str, status: str,
                         error_message: Optional[str] = None,
                         execution_summary_id: Optional[int] = None,
                         processing_time_ms: Optional[int] = None):
    """
    更新消息处理状态和管理重试次数
    
    Args:
        message_hash: 消息哈希值
        status: 新状态
        error_message: 错误信息
        execution_summary_id: 执行摘要ID
        processing_time_ms: 处理耗时(毫秒)
    
    重试计数逻辑:
        - 失败状态 (failed, critical_error): 增加重试计数
        - 成功状态 (success): 重置重试计数为0
        - 其他状态 (pending, processing): 保持重试计数不变
    """
    cursor = self.connection.cursor()

    try:
        if status in ['failed', 'critical_error']:
            # 失败状态：增加重试计数
            sql = """
            UPDATE message_process_log
            SET process_status = %s,
                error_message = %s,
                execution_summary_id = %s,
                processing_time_ms = %s,
                retry_count = retry_count + 1
            WHERE message_hash = %s
            """
            cursor.execute(sql, (
                status, error_message, execution_summary_id, 
                processing_time_ms, message_hash
            ))
            logger.debug(f"Updated message {message_hash[:8]}... status to {status}, retry_count incremented")
            
        elif status == 'success':
            # 成功状态：重置重试计数
            sql = """
            UPDATE message_process_log
            SET process_status = %s,
                error_message = NULL,
                execution_summary_id = %s,
                processing_time_ms = %s,
                retry_count = 0
            WHERE message_hash = %s
            """
            cursor.execute(sql, (
                status, execution_summary_id, 
                processing_time_ms, message_hash
            ))
            logger.debug(f"Updated message {message_hash[:8]}... status to {status}, retry_count reset to 0")
            
        else:
            # 其他状态：不改变重试计数
            sql = """
            UPDATE message_process_log
            SET process_status = %s,
                error_message = %s,
                execution_summary_id = %s,
                processing_time_ms = %s
            WHERE message_hash = %s
            """
            cursor.execute(sql, (
                status, error_message, execution_summary_id, 
                processing_time_ms, message_hash
            ))
            logger.debug(f"Updated message {message_hash[:8]}... status to {status}, retry_count unchanged")

        self.connection.commit()

    except Exception as e:
        self.connection.rollback()
        logger.error(f"Failed to update message status for {message_hash[:8]}...: {e}")
        raise
    finally:
        cursor.close()
```

- [ ] **Step 2: Verify retry count logic**

Check: Increment on failed/critical_error, reset on success, unchanged for others ✅

- [ ] **Step 3: Test method with different status transitions**

```python
# Test: status='failed' -> retry_count increments
# Test: status='success' -> retry_count resets to 0  
# Test: status='processing' -> retry_count unchanged
```

- [ ] **Step 4: Commit update_message_status changes**

```bash
git add src/database/repository.py
git commit -m "feat: add retry count management to update_message_status"
```

---

## Task 6: Update Repository - modify get_recent_messages_to_retry()

**Files:**
- Modify: `src/database/repository.py`

- [ ] **Step 1: Add settings import at top of file**

Add at line 4 (after other imports):
```python
from src.config.settings import Settings
```

- [ ] **Step 2: Modify DatabaseRepository __init__ to accept settings**

Update the constructor signature (line 13):

```python
def __init__(self, host: str, port: int, user: str, password: str, database: str, settings: Optional[Settings] = None):
```

- [ ] **Step 3: Store settings in constructor**

Add after line 28 (in __init__ method):
```python
self.settings = settings  # Store settings for retry limit access
```

- [ ] **Step 4: Replace get_recent_messages_to_retry() method**

Replace the existing method (lines 437-464) with retry limit filtering:

```python
def get_recent_messages_to_retry(self, hours: int = 24) -> list:
    """
    获取最近N小时内需要重试的消息（排除已达到最大重试次数的消息）
    
    Args:
        hours: 时间范围（小时）
    
    Returns:
        消息哈希列表
    
    过滤条件:
        - 状态必须是 'critical_error'
        - 创建时间在指定时间范围内
        - 重试次数小于配置的最大值 (MESSAGE_MAX_RETRIES)
    """
    cursor = self.connection.cursor()

    try:
        # 获取最大重试次数配置，默认为10
        max_retries = self.settings.max_message_retries if self.settings else 10
        
        sql = """
        SELECT message_hash FROM message_process_log
        WHERE process_status = 'critical_error'
        AND retry_count < %s
        AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        ORDER BY created_at ASC
        """

        cursor.execute(sql, (max_retries, hours))
        results = cursor.fetchall()
        
        message_hashes = [row['message_hash'] for row in results]
        logger.debug(f"Found {len(message_hashes)} messages to retry (max_retries={max_retries})")
        
        return message_hashes

    except Exception as e:
        logger.error(f"Failed to get recent messages to retry: {e}")
        raise
    finally:
        cursor.close()
```

- [ ] **Step 5: Verify retry filtering logic**

Check: Filters by retry_count < max_retries, uses settings with fallback ✅

- [ ] **Step 6: Test retry filtering with different max_retries values**

```python
# Test: max_retries=10, messages with retry_count 9 included, 10 excluded
# Test: max_retries=1, messages with retry_count 0 included, 1 excluded
```

- [ ] **Step 7: Commit get_recent_messages_to_retry changes**

```bash
git add src/database/repository.py
git commit -m "feat: add retry limit filtering to get_recent_messages_to_retry"
```

---

## Task 7: Update .env.example Documentation

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add MESSAGE_MAX_RETRIES to message processing section**

Find line 96-98 and add after MESSAGE_DEFAULT_EXTRACTION_CODE:

```bash
# ===== 消息处理配置 (自动模式) =====
# 默认提取码 (4位数字，当飞书消息中未指定提取码时使用)
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
# 消息最大重试次数 (1-100，默认10)
# 失败的消息会被重试，超过此次数后将不再重试
MESSAGE_MAX_RETRIES=10
```

- [ ] **Step 2: Verify documentation clarity**

Check: Clear description, valid range mentioned, default value specified ✅

- [ ] **Step 3: Commit .env.example update**

```bash
git add .env.example
git commit -m "docs: document MESSAGE_MAX_RETRIES configuration"
```

---

## Task 8: Create Unit Tests

**Files:**
- Create: `tests/database/test_repository_retry.py`

- [ ] **Step 1: Create test file structure**

```python
import pytest
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings
from datetime import datetime

class TestRetryCountManagement:
    """测试重试计数管理功能"""
    
    @pytest.fixture
    def db_repository(self):
        """创建测试数据库仓库"""
        # Use test database configuration
        settings = Settings()
        return DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database='test_baidu_download',  # Use test database
            settings=settings
        )
    
    @pytest.fixture
    def test_message(self, db_repository):
        """创建测试消息"""
        message = MessageProcessLog(
            message_hash='test_hash_123',
            original_message='test message',
            share_link='https://pan.baidu.com/s/test',
            folder_name='test_folder',
            source='feishu',
            process_status='pending'
        )
        message_id = db_repository.insert_message_log(message)
        yield message
        # Cleanup: delete test message
        # db_repository.connection.cursor().execute("DELETE FROM message_process_log WHERE message_hash = 'test_hash_123'")
```

- [ ] **Step 2: Add test for retry count increment**

```python
    def test_retry_count_increments_on_failure(self, db_repository, test_message):
        """测试失败状态时重试计数增加"""
        # Update status to failed
        db_repository.update_message_status(
            message_hash='test_hash_123',
            status='failed',
            error_message='Test error'
        )
        
        # Verify retry_count incremented
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 1
        
        # Update to critical_error
        db_repository.update_message_status(
            message_hash='test_hash_123',
            status='critical_error',
            error_message='Critical error'
        )
        
        # Verify retry_count incremented again
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 2
```

- [ ] **Step 3: Add test for retry count reset on success**

```python
    def test_retry_count_resets_on_success(self, db_repository, test_message):
        """测试成功状态时重试计数重置"""
        # Fail message twice
        db_repository.update_message_status('test_hash_123', 'failed', 'Error 1')
        db_repository.update_message_status('test_hash_123', 'failed', 'Error 2')
        
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 2
        
        # Update to success
        db_repository.update_message_status('test_hash_123', 'success')
        
        # Verify retry_count reset to 0
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 0
```

- [ ] **Step 4: Add test for retry count unchanged on pending/processing**

```python
    def test_retry_count_unchanged_on_pending_processing(self, db_repository, test_message):
        """测试pending和processing状态不改变重试计数"""
        # Update to processing
        db_repository.update_message_status('test_hash_123', 'processing')
        
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 0
        
        # Update to pending
        db_repository.update_message_status('test_hash_123', 'pending')
        
        message = db_repository.get_message_by_hash('test_hash_123')
        assert message.retry_count == 0
```

- [ ] **Step 5: Add test for max retry filtering**

```python
    def test_max_retry_messages_excluded(self, db_repository):
        """测试超过最大重试次数的消息被排除"""
        # Create messages with different retry counts
        for retry_count in range(12):
            message_hash = f'test_hash_{retry_count}'
            message = MessageProcessLog(
                message_hash=message_hash,
                original_message='test message',
                source='feishu',
                process_status='critical_error'
            )
            db_repository.insert_message_log(message)
            
            # Set retry_count manually
            cursor = db_repository.connection.cursor()
            cursor.execute(
                "UPDATE message_process_log SET retry_count = %s WHERE message_hash = %s",
                (retry_count, message_hash)
            )
            db_repository.connection.commit()
        
        # Get messages to retry (default max_retries=10)
        messages_to_retry = db_repository.get_recent_messages_to_retry(hours=24)
        
        # Should only include messages with retry_count < 10
        assert 'test_hash_9' in messages_to_retry
        assert 'test_hash_10' not in messages_to_retry
        assert 'test_hash_11' not in messages_to_retry
```

- [ ] **Step 6: Add test for configuration validation**

```python
class TestConfigurationValidation:
    """测试配置验证"""
    
    def test_valid_max_retries_values(self):
        """测试有效的max_retries值"""
        valid_values = [1, 10, 50, 100]
        for value in valid_values:
            # Temporarily set environment variable
            import os
            os.environ['MESSAGE_MAX_RETRIES'] = str(value)
            settings = Settings()
            assert settings.max_message_retries == value
    
    def test_invalid_max_retries_values(self):
        """测试无效的max_retries值"""
        invalid_values = [0, -1, 101, 1000]
        for value in invalid_values:
            import os
            os.environ['MESSAGE_MAX_RETRIES'] = str(value)
            with pytest.raises(Exception):  # Should raise ConfigError
                Settings()
```

- [ ] **Step 7: Run unit tests and verify they pass**

```bash
python -m pytest tests/database/test_repository_retry.py -v
```

Expected: All 6 tests pass ✅

- [ ] **Step 8: Commit unit tests**

```bash
git add tests/database/test_repository_retry.py
git commit -m "test: add unit tests for retry count functionality"
```

---

## Task 9: Create Integration Tests

**Files:**
- Create: `tests/integration/test_retry_integration.py`

- [ ] **Step 1: Create integration test file**

```python
import pytest
import time
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings

class TestRetryIntegration:
    """集成测试：端到端重试流程"""
    
    @pytest.fixture
    def integration_repository(self):
        """创建集成测试仓库"""
        settings = Settings()
        return DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database='test_baidu_download',
            settings=settings
        )
```

- [ ] **Step 2: Add end-to-end retry flow test**

```python
    def test_message_retry_to_exclusion(self, integration_repository):
        """测试消息重试直到被排除"""
        # Create initial message
        message_hash = 'integration_test_retry_exclusion'
        message = MessageProcessLog(
            message_hash=message_hash,
            original_message='test message for retry exclusion',
            source='feishu',
            process_status='pending'
        )
        integration_repository.insert_message_log(message)
        
        # Simulate 10 failure attempts
        for i in range(10):
            integration_repository.update_message_status(
                message_hash=message_hash,
                status='critical_error',
                error_message=f'Attempt {i+1} failed'
            )
        
        # Verify retry_count == 10
        final_message = integration_repository.get_message_by_hash(message_hash)
        assert final_message.retry_count == 10
        
        # Verify message is excluded from retry queue
        messages_to_retry = integration_repository.get_recent_messages_to_retry(hours=24)
        assert message_hash not in messages_to_retry
```

- [ ] **Step 3: Add successful recovery test**

```python
    def test_successful_recovery_resets_retries(self, integration_repository):
        """测试成功恢复后重置重试计数"""
        message_hash = 'integration_test_recovery'
        message = MessageProcessLog(
            message_hash=message_hash,
            original_message='test message for recovery',
            source='feishu',
            process_status='pending'
        )
        integration_repository.insert_message_log(message)
        
        # Fail message 5 times
        for i in range(5):
            integration_repository.update_message_status(
                message_hash=message_hash,
                status='failed',
                error_message=f'Failure {i+1}'
            )
        
        # Verify retry_count == 5
        message = integration_repository.get_message_by_hash(message_hash)
        assert message.retry_count == 5
        
        # Update to success
        integration_repository.update_message_status(message_hash, 'success')
        
        # Verify retry_count == 0
        message = integration_repository.get_message_by_hash(message_hash)
        assert message.retry_count == 0
        
        # Verify message is eligible for retry on next failure
        integration_repository.update_message_status(
            message_hash=message_hash,
            status='failed',
            error_message='New failure after recovery'
        )
        
        message = integration_repository.get_message_by_hash(message_hash)
        assert message.retry_count == 1  # Should be 1, not 6
```

- [ ] **Step 4: Add database migration test**

```python
    def test_database_migration(self, integration_repository):
        """测试数据库迁移兼容性"""
        # Check if retry_count column exists
        cursor = integration_repository.connection.cursor()
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'message_process_log' 
            AND COLUMN_NAME = 'retry_count'
        """)
        result = cursor.fetchone()
        assert result is not None, "retry_count column should exist"
        
        # Check if index exists
        cursor.execute("""
            SHOW INDEX FROM message_process_log WHERE Key_name = 'idx_retry_count'
        """)
        result = cursor.fetchone()
        assert result is not None, "idx_retry_count index should exist"
        
        # Verify existing data has retry_count = 0
        cursor.execute("SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL")
        null_count = cursor.fetchone()
        assert null_count[0] == 0, "All existing records should have retry_count = 0"
```

- [ ] **Step 5: Add retry distribution test**

```python
    def test_retry_count_distribution(self, integration_repository):
        """测试重试计数分布统计"""
        # Create test messages with various retry counts
        test_data = [
            ('retry_0', 0, 'success'),
            ('retry_1', 1, 'failed'),
            ('retry_5', 5, 'failed'),
            ('retry_10', 10, 'critical_error'),
        ]
        
        for message_hash, retry_count, status in test_data:
            message = MessageProcessLog(
                message_hash=message_hash,
                original_message='test message',
                source='feishu',
                process_status=status
            )
            integration_repository.insert_message_log(message)
            
            # Set specific retry_count
            cursor = integration_repository.connection.cursor()
            cursor.execute(
                "UPDATE message_process_log SET retry_count = %s WHERE message_hash = %s",
                (retry_count, message_hash)
            )
            integration_repository.connection.commit()
        
        # Get retry distribution
        cursor = integration_repository.connection.cursor()
        cursor.execute("""
            SELECT retry_count, COUNT(*) as count
            FROM message_process_log
            WHERE message_hash LIKE 'retry_%'
            GROUP BY retry_count
            ORDER BY retry_count
        """)
        distribution = cursor.fetchall()
        
        # Verify distribution
        assert len(distribution) == 4  # Should have 4 different retry counts
        assert distribution[0] == (0, 1)
        assert distribution[1] == (1, 1)
        assert distribution[2] == (5, 1)
        assert distribution[3] == (10, 1)
```

- [ ] **Step 6: Run integration tests and verify they pass**

```bash
python -m pytest tests/integration/test_retry_integration.py -v
```

Expected: All 4 tests pass ✅

- [ ] **Step 7: Commit integration tests**

```bash
git add tests/integration/test_retry_integration.py
git commit -m "test: add integration tests for retry functionality"
```

---

## Task 10: Manual Testing and Verification

**Files:**
- Manual verification steps (no code changes)

- [ ] **Step 1: Apply database migration to test database**

```bash
# Backup database first
mysqldump -u root -p test_baidu_download > backup_before_retry.sql

# Apply migration
mysql -u root -p test_baidu_download < database/migrations/add_retry_count.sql

# Verify migration
mysql -u root -p test_baidu_download -e "SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;"
# Expected: 0
```

- [ ] **Step 2: Test configuration with .env file**

Create `.env.test` file:
```bash
MESSAGE_MAX_RETRIES=3
```

Test configuration loading:
```python
from src.config.settings import Settings
settings = Settings('.env.test')
assert settings.max_message_retries == 3
```

- [ ] **Step 3: Test retry limit with real message processing**

```python
# Create test message
message = MessageProcessLog(
    message_hash='manual_test_message',
    original_message='manual test message',
    source='feishu',
    process_status='pending'
)
repo.insert_message_log(message)

# Simulate 3 failures (using MESSAGE_MAX_RETRIES=3 from .env.test)
for i in range(3):
    repo.update_message_status('manual_test_message', 'critical_error', f'Error {i+1}')

# Check message is excluded from retry queue
messages_to_retry = repo.get_recent_messages_to_retry(hours=24)
assert 'manual_test_message' not in messages_to_retry

# Verify retry_count in database
message = repo.get_message_by_hash('manual_test_message')
assert message.retry_count == 3
```

- [ ] **Step 4: Test retry reset on success**

```python
# Update manual_test_message to success
repo.update_message_status('manual_test_message', 'success')

# Verify retry_count reset
message = repo.get_message_by_hash('manual_test_message')
assert message.retry_count == 0

# Fail again and verify retry_count = 1
repo.update_message_status('manual_test_message', 'failed', 'New error')
message = repo.get_message_by_hash('manual_test_message')
assert message.retry_count == 1
```

- [ ] **Step 5: Verify retry count distribution in database**

```sql
-- Check retry distribution
SELECT retry_count, COUNT(*) as count, process_status
FROM message_process_log
GROUP BY retry_count, process_status
ORDER BY retry_count DESC;

-- Verify messages at retry limit
SELECT message_hash, retry_count, process_status, created_at
FROM message_process_log
WHERE retry_count >= (SELECT @max_retries:=10)
ORDER BY retry_count DESC, created_at DESC;
```

- [ ] **Step 6: Test rollback capability**

```bash
# Test rollback (safety verification)
mysql -u root -p test_baidu_download -e "ALTER TABLE message_process_log DROP COLUMN retry_count;"
# Should succeed without error
```

- [ ] **Step 7: Restore database after testing**

```bash
# Restore from backup if needed
mysql -u root -p test_baidu_download < backup_before_retry.sql
```

---

## Task 11: Final Integration and Documentation

**Files:**
- Create: `docs/retry_limit_feature.md` (optional documentation)
- Modify: Update any relevant documentation

- [ ] **Step 1: Verify all tests pass**

```bash
python -m pytest tests/ -v --cov=src/database --cov=src/config
```

Expected: All tests pass, coverage > 80% ✅

- [ ] **Step 2: Run existing test suite to ensure no breaking changes**

```bash
python -m pytest tests/ -v
```

Expected: All existing tests still pass ✅

- [ ] **Step 3: Create feature documentation (optional)**

```markdown
# Message Retry Limit Feature

## Overview
Messages that fail processing are now limited to a configurable number of retry attempts (default: 10). After reaching the limit, messages are permanently excluded from retry processing.

## Configuration
Set `MESSAGE_MAX_RETRIES` in your `.env` file (range: 1-100, default: 10).

## Behavior
- Failed messages increment retry count
- Successful messages reset retry count to 0
- Messages at retry limit are silently excluded from retry queue

## Monitoring
Check retry distribution:
```sql
SELECT retry_count, COUNT(*) FROM message_process_log GROUP BY retry_count;
```
```

- [ ] **Step 4: Update deployment documentation**

Add migration step to deployment guide:
```bash
# Database migration required
mysql -u user -p database < database/migrations/add_retry_count.sql
```

- [ ] **Step 5: Final commit for all changes**

```bash
git add .
git commit -m "feat: complete message retry limit feature implementation"
```

---

## Task 12: Production Deployment Preparation

**Files:**
- Deployment checklist and migration scripts

- [ ] **Step 1: Create production migration script**

Create `database/migrations/production_add_retry_count.sql`:

```sql
-- Production migration for retry limit feature
-- IMPORTANT: Backup database before running this migration
-- Run: mysqldump -u user -p database > backup_$(date +%Y%m%d).sql

-- Phase 1: Add retry_count column
ALTER TABLE message_process_log 
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数' 
AFTER processing_time_ms;

-- Phase 2: Create index for efficient filtering
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- Phase 3: Verification
-- Run this to verify: SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;
-- Expected result: 0
```

- [ ] **Step 2: Create deployment checklist**

Create `deployment/retry_limit_checklist.md`:

```markdown
# Message Retry Limit Feature Deployment Checklist

## Pre-deployment
- [ ] Backup production database
- [ ] Test migration on staging environment
- [ ] Review migration SQL
- [ ] Prepare rollback plan

## Deployment
- [ ] Add MESSAGE_MAX_RETRIES to production .env file
- [ ] Apply database migration
- [ ] Deploy application code
- [ ] Verify application starts without errors
- [ ] Check logs for retry count operations

## Post-deployment
- [ ] Monitor retry count distribution
- [ ] Check for errors in application logs
- [ ] Verify system performance
- [ ] Document any issues

## Rollback (if needed)
- [ ] Remove retry filter from application code
- [ ] Revert code changes
- [ ] Keep retry_count column (harmless if unused)
```

- [ ] **Step 3: Test migration on staging environment**

```bash
# Apply migration to staging
mysql -u user -p staging_database < database/migrations/production_add_retry_count.sql

# Verify migration success
mysql -u user -p staging_database -e "SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;"
# Expected: 0
```

- [ ] **Step 4: Prepare rollback script**

Create `database/migrations/rollback_add_retry_count.sql`:

```sql
-- Rollback script for retry limit feature
-- WARNING: Only use if feature needs to be completely removed

-- Drop retry_count column
ALTER TABLE message_process_log DROP COLUMN retry_count;

-- Note: Dropping column is irreversible. Consider keeping column if rollback is temporary.
```

- [ ] **Step 5: Final verification and sign-off**

```bash
# Verify all changes are committed
git status

# Verify tests pass
python -m pytest tests/ -v

# Create deployment tag
git tag -a v1.5.0 -m "Message retry limit feature"
```

---

## Completion Criteria

✅ **All tasks completed:**
- Database schema updated with retry_count field
- Configuration management implemented with validation
- Repository methods updated for retry counting
- Retry filtering applied to message retrieval
- Comprehensive unit and integration tests written
- Manual testing completed successfully
- Documentation updated
- Deployment migration scripts prepared
- Rollback procedures documented

**Feature is ready for production deployment after staging environment validation.**