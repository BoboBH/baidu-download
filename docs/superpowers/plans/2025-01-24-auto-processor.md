# AutoProcessor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create AutoProcessor coordinator class that orchestrates automatic message processing workflow for Windows Task Scheduler integration.

**Architecture:** Thin coordinator that delegates to existing components (FeishuMessageClient, MessageParser, DatabaseRepository, FileProcessor, DingtalkNotifier) with clear separation of concerns and comprehensive error handling.

**Tech Stack:** Python 3.8+, pytest, existing project components (Feishu client, message parser, database repository, file processor, DingTalk notifier)

---

## File Structure

**Create:**
- `tests/unit/test_auto_processor.py` - Unit tests for AutoProcessor
- `src/processor/auto_processor.py` - AutoProcessor coordinator class

**Modify:**
- `src/processor/__init__.py` - Export AutoProcessor class

---

## Task 1: Create Test File Structure and Initial Test Class

**Files:**
- Create: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write the initial test file structure**

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.processor.auto_processor import AutoProcessor
from src.database.message_models import MessageProcessLog
from src.database.models import ExecutionSummary


class TestAutoProcessor:
    """Test suite for AutoProcessor coordinator class"""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock configuration"""
        settings = Mock()
        settings.feishu_app_id = "test_app_id"
        settings.feishu_app_secret = "test_secret"
        settings.feishu_chat_id = "test_chat_id"
        settings.feishu_hours_limit = 24
        settings.dingtalk_webhook = "https://oapi.dingtalk.com/robot/send?access_token=test"
        settings.message_default_extraction_code = "0409"
        settings.db_host = "localhost"
        settings.db_port = 3306
        settings.db_user = "test_user"
        settings.db_password = "test_pass"
        settings.db_name = "test_db"
        return settings
    
    @pytest.fixture
    def auto_processor(self, mock_settings):
        """Create AutoProcessor instance with mocked dependencies"""
        with patch('src.processor.auto_processor.Settings', return_value=mock_settings):
            return AutoProcessor()
```

- [ ] **Step 2: Run test to verify file structure is valid**

Run: `pytest tests/unit/test_auto_processor.py -v`
Expected: FAIL with "cannot import 'AutoProcessor'"

- [ ] **Step 3: Commit test file structure**

```bash
git add tests/unit/test_auto_processor.py
git commit -m "test: add AutoProcessor test file structure"
```

---

## Task 2: Create AutoProcessor Class with Basic Structure

**Files:**
- Create: `src/processor/auto_processor.py`

- [ ] **Step 1: Write the AutoProcessor class structure**

```python
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.database.repository import DatabaseRepository
from src.processor.file_processor import FileProcessor
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """Internal tracking for processing results"""
    folder_name: str
    share_link: str
    status: str  # 'success', 'failed', 'critical_error', 'skipped'
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


class AutoProcessor:
    """Automatic message processing coordinator for Windows Task Scheduler integration"""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize AutoProcessor with all required dependencies
        
        Args:
            settings: Configuration object, defaults to new Settings instance
        """
        self.settings = settings or Settings()
        self.logger = logger
        
        # Initialize components
        self.feishu_client = FeishuMessageClient(self.settings)
        self.message_parser = MessageParser()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.file_processor = FileProcessor()
        self.dingtalk_notifier = DingtalkNotifier(self.settings)
        
        self.logger.info("AutoProcessor initialized successfully")
```

- [ ] **Step 2: Run tests to verify basic structure works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_auto_processor_init -v`
Expected: FAIL with "test_auto_processor_init not found"

- [ ] **Step 3: Write initialization test**

```python
def test_auto_processor_init(self, auto_processor):
    """Test AutoProcessor initialization"""
    assert auto_processor.settings is not None
    assert auto_processor.feishu_client is not None
    assert auto_processor.message_parser is not None
    assert auto_processor.db_repo is not None
    assert auto_processor.file_processor is not None
    assert auto_processor.dingtalk_notifier is not None
```

- [ ] **Step 4: Run test to verify initialization works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_auto_processor_init -v`
Expected: PASS

- [ ] **Step 5: Commit AutoProcessor basic structure**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add AutoProcessor basic class structure"
```

---

## Task 3: Implement Duplicate Detection Method

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write the failing test for duplicate detection**

```python
def test_is_duplicate_message_true(self, auto_processor):
    """Test duplicate message detection returns True for existing message"""
    mock_message_log = Mock(spec=MessageProcessLog)
    mock_message_log.message_hash = "abc123"
    auto_processor.db_repo.get_message_by_hash = Mock(return_value=mock_message_log)
    
    result = auto_processor._is_duplicate_message("abc123")
    assert result is True
    auto_processor.db_repo.get_message_by_hash.assert_called_once_with("abc123")

def test_is_duplicate_message_false(self, auto_processor):
    """Test duplicate message detection returns False for new message"""
    auto_processor.db_repo.get_message_by_hash = Mock(return_value=None)
    
    result = auto_processor._is_duplicate_message("new_message")
    assert result is False
    auto_processor.db_repo.get_message_by_hash.assert_called_once_with("new_message")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_is_duplicate_message -v`
Expected: FAIL with "_is_duplicate_message not found"

- [ ] **Step 3: Implement duplicate detection method**

```python
def _is_duplicate_message(self, message_hash: str) -> bool:
    """
    Check if message was already processed
    
    Args:
        message_hash: MD5 hash of message content
        
    Returns:
        True if message exists in database, False otherwise
    """
    existing_message = self.db_repo.get_message_by_hash(message_hash)
    return existing_message is not None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_is_duplicate_message -v`
Expected: PASS

- [ ] **Step 5: Commit duplicate detection implementation**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add duplicate message detection method"
```

---

## Task 4: Implement Main Process Messages Method Structure

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write the failing test for process_messages structure**

```python
def test_process_messages_returns_exit_code(self, auto_processor):
    """Test process_messages returns integer exit code"""
    with patch.object(auto_processor, 'feishu_client') as mock_feishu:
        mock_feishu.get_messages.return_value = []
        
        exit_code = auto_processor.process_messages()
        assert isinstance(exit_code, int)
        assert exit_code in [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_returns_exit_code -v`
Expected: FAIL with "process_messages not found"

- [ ] **Step 3: Implement process_messages basic structure**

```python
def process_messages(self) -> int:
    """
    Main workflow orchestration method
    
    Returns:
        Exit code: 0 = success (even with partial failures), 
                  1 = critical system failure
    """
    try:
        self.logger.info("Starting automatic message processing")
        
        # Retrieve messages from Feishu
        messages = self.feishu_client.get_messages()
        self.logger.info(f"Retrieved {len(messages)} messages from Feishu")
        
        # Process messages logic will be added in next tasks
        return 0
        
    except Exception as e:
        self.logger.error(f"Critical failure during message processing: {e}")
        return 1
```

- [ ] **Step 4: Run test to verify basic structure works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_returns_exit_code -v`
Expected: PASS

- [ ] **Step 5: Commit process_messages structure**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add process_messages basic structure"
```

---

## Task 5: Implement Message Parsing and Filtering Logic

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write failing test for message parsing workflow**

```python
@patch('src.processor.auto_processor.ProcessResult')
def test_process_messages_parses_valid_message(self, mock_result_class, auto_processor):
    """Test process_messages parses valid Feishu messages"""
    # Mock Feishu messages
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
        {"message_id": "msg2", "content": '{"text":"invalid message"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    # Mock message parser
    mock_parse_result = Mock()
    mock_parse_result.folder_name = "260723"
    mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
    mock_parse_result.code = "0409"
    auto_processor.message_parser.parse_message = Mock(side_effect=[mock_parse_result, None])
    
    # Mock duplicate check - no duplicates
    auto_processor._is_duplicate_message = Mock(return_value=False)
    
    # Mock database insertion
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    exit_code = auto_processor.process_messages()
    
    assert exit_code == 0
    assert auto_processor.message_parser.parse_message.call_count == 2
    auto_processor.db_repo.insert_message_log.assert_called_once()

def test_process_messages_skips_duplicate_messages(self, auto_processor):
    """Test process_messages skips duplicate messages"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    mock_parse_result = Mock()
    mock_parse_result.folder_name = "260723"
    mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
    mock_parse_result.code = "0409"
    auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
    
    # Mock duplicate check - message is duplicate
    auto_processor._is_duplicate_message = Mock(return_value=True)
    
    # Should NOT insert duplicate message
    auto_processor.db_repo.insert_message_log = Mock()
    
    exit_code = auto_processor.process_messages()
    
    assert exit_code == 0
    auto_processor.db_repo.insert_message_log.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_parses_valid_message -v`
Expected: FAIL with logic errors or assertion failures

- [ ] **Step 3: Implement message parsing and filtering logic**

```python
def process_messages(self) -> int:
    """
    Main workflow orchestration method
    
    Returns:
        Exit code: 0 = success (even with partial failures), 
                  1 = critical system failure
    """
    try:
        self.logger.info("Starting automatic message processing")
        
        # Retrieve messages from Feishu
        messages = self.feishu_client.get_messages()
        self.logger.info(f"Retrieved {len(messages)} messages from Feishu")
        
        results = []
        
        for message in messages:
            try:
                # Extract message content from JSON
                content = message.get("content", "")
                if not content:
                    self.logger.warning(f"Empty message content for message_id: {message.get('message_id')}")
                    continue
                
                # Parse message content
                parse_result = self.message_parser.parse_message(content)
                if not parse_result:
                    self.logger.debug(f"Failed to parse message: {content[:50]}...")
                    continue
                
                # Calculate message hash
                message_hash = self.message_parser.calculate_message_hash(content)
                
                # Check for duplicates
                if self._is_duplicate_message(message_hash):
                    self.logger.info(f"Skipping duplicate message: {parse_result.folder_name}")
                    results.append(ProcessResult(
                        folder_name=parse_result.folder_name,
                        share_link=parse_result.share_link,
                        status="skipped"
                    ))
                    continue
                
                # Insert new message to database
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=content,
                    share_link=parse_result.share_link,
                    folder_name=parse_result.folder_name,
                    status="pending"
                )
                self.db_repo.insert_message_log(message_log)
                self.logger.info(f"Inserted new message: {parse_result.folder_name}")
                
                # Process logic will be added in next task
                results.append(ProcessResult(
                    folder_name=parse_result.folder_name,
                    share_link=parse_result.share_link,
                    status="pending"
                ))
                
            except Exception as e:
                self.logger.error(f"Error processing individual message: {e}")
                continue
        
        return 0
        
    except Exception as e:
        self.logger.error(f"Critical failure during message processing: {e}")
        return 1
```

- [ ] **Step 4: Run tests to verify parsing logic works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_parses_valid_message tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_skips_duplicate_messages -v`
Expected: PASS

- [ ] **Step 5: Commit message parsing implementation**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add message parsing and filtering logic"
```

---

## Task 6: Implement FileProcessor Integration

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write failing test for FileProcessor integration**

```python
@patch('src.processor.auto_processor.ProcessResult')
def test_process_messages_calls_file_processor(self, mock_result_class, auto_processor):
    """Test process_messages processes new messages via FileProcessor"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    mock_parse_result = Mock()
    mock_parse_result.folder_name = "260723"
    mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
    mock_parse_result.code = "0409"
    auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
    auto_processor.message_parser.calculate_message_hash = Mock(return_value="hash123")
    auto_processor._is_duplicate_message = Mock(return_value=False)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    # Mock FileProcessor success
    mock_summary = Mock(spec=ExecutionSummary)
    mock_summary.SUCCESS_COUNT = 5
    mock_summary.FAILED_COUNT = 0
    auto_processor.file_processor.process_files = Mock(return_value=mock_summary)
    
    exit_code = auto_processor.process_messages()
    
    assert exit_code == 0
    auto_processor.file_processor.process_files.assert_called_once_with(
        "https://pan.baidu.com/s/abc123",
        "0409",
        "260723"
    )

def test_process_messages_handles_file_processor_failure(self, auto_processor):
    """Test process_messages handles FileProcessor failures gracefully"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    mock_parse_result = Mock()
    mock_parse_result.folder_name = "260723"
    mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
    mock_parse_result.code = "0409"
    auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
    auto_processor.message_parser.calculate_message_hash = Mock(return_value="hash123")
    auto_processor._is_duplicate_message = Mock(return_value=False)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    # Mock FileProcessor failure
    auto_processor.file_processor.process_files = Mock(return_value=None)
    
    exit_code = auto_processor.process_messages()
    
    # Should still return 0 (success with partial failures)
    assert exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_calls_file_processor -v`
Expected: FAIL with assertion errors

- [ ] **Step 3: Implement FileProcessor integration logic**

```python
def process_messages(self) -> int:
    """
    Main workflow orchestration method
    
    Returns:
        Exit code: 0 = success (even with partial failures), 
                  1 = critical system failure
    """
    try:
        self.logger.info("Starting automatic message processing")
        
        # Retrieve messages from Feishu
        messages = self.feishu_client.get_messages()
        self.logger.info(f"Retrieved {len(messages)} messages from Feishu")
        
        results = []
        
        for message in messages:
            try:
                # Extract message content from JSON
                content = message.get("content", "")
                if not content:
                    self.logger.warning(f"Empty message content for message_id: {message.get('message_id')}")
                    continue
                
                # Parse message content
                parse_result = self.message_parser.parse_message(content)
                if not parse_result:
                    self.logger.debug(f"Failed to parse message: {content[:50]}...")
                    continue
                
                # Calculate message hash
                message_hash = self.message_parser.calculate_message_hash(content)
                
                # Check for duplicates
                if self._is_duplicate_message(message_hash):
                    self.logger.info(f"Skipping duplicate message: {parse_result.folder_name}")
                    results.append(ProcessResult(
                        folder_name=parse_result.folder_name,
                        share_link=parse_result.share_link,
                        status="skipped"
                    ))
                    continue
                
                # Insert new message to database
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=content,
                    share_link=parse_result.share_link,
                    folder_name=parse_result.folder_name,
                    status="pending"
                )
                message_id = self.db_repo.insert_message_log(message_log)
                self.logger.info(f"Inserted new message: {parse_result.folder_name}")
                
                # Update status to processing
                self.db_repo.update_message_status(message_hash, "processing")
                
                # Process via FileProcessor
                start_time = datetime.now()
                summary = self.file_processor.process_files(
                    parse_result.share_link,
                    parse_result.code,
                    parse_result.folder_name
                )
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Update database status based on result
                if summary and summary.SUCCESS_COUNT > 0:
                    status = "success"
                    error_message = None
                else:
                    status = "failed"
                    error_message = "File processing failed or no files transferred"
                
                self.db_repo.update_message_status(
                    message_hash,
                    status,
                    error_message=error_message,
                    processing_time=processing_time
                )
                
                results.append(ProcessResult(
                    folder_name=parse_result.folder_name,
                    share_link=parse_result.share_link,
                    status=status,
                    error_message=error_message,
                    processing_time_ms=processing_time
                ))
                
            except Exception as e:
                self.logger.error(f"Error processing individual message: {e}")
                # Update status to critical_error for this message
                if 'message_hash' in locals():
                    self.db_repo.update_message_status(
                        message_hash,
                        "critical_error",
                        error_message=str(e)
                    )
                continue
        
        return 0
        
    except Exception as e:
        self.logger.error(f"Critical failure during message processing: {e}")
        return 1
```

- [ ] **Step 4: Run tests to verify FileProcessor integration works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_calls_file_processor tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_handles_file_processor_failure -v`
Expected: PASS

- [ ] **Step 5: Commit FileProcessor integration**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add FileProcessor integration"
```

---

## Task 7: Implement Notification Method

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write failing test for notification formatting and sending**

```python
def test_send_result_notification_success(self, auto_processor):
    """Test notification formatting for successful processing"""
    results = [
        ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
        ProcessResult(folder_name="260724", share_link="https://pan.baidu.com/s/abc2", status="success"),
    ]
    
    auto_processor.dingtalk_notifier.send_notification = Mock(return_value=True)
    
    result = auto_processor._send_result_notification(results)
    
    assert result is True
    auto_processor.dingtalk_notifier.send_notification.assert_called_once()
    
    # Verify notification content
    call_args = auto_processor.dingtalk_notifier.send_notification.call_args
    title = call_args[0][0]
    content = call_args[0][1]
    
    assert "成功" in title or "处理报告" in title
    assert "2 条消息" in content or "2" in content
    assert "260723" in content
    assert "260724" in content

def test_send_result_notification_with_failures(self, auto_processor):
    """Test notification formatting includes failures"""
    results = [
        ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
        ProcessResult(folder_name="260724", share_link="https://pan.baidu.com/s/abc2", status="failed", error_message="Download timeout"),
    ]
    
    auto_processor.dingtalk_notifier.send_notification = Mock(return_value=True)
    
    result = auto_processor._send_result_notification(results)
    
    assert result is True
    
    # Verify error messages included
    call_args = auto_processor.dingtalk_notifier.send_notification.call_args
    content = call_args[0][1]
    
    assert "失败" in content
    assert "Download timeout" in content or "timeout" in content.lower()

def test_send_result_notification_failure_handling(self, auto_processor):
    """Test notification failure is handled gracefully"""
    results = [
        ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
    ]
    
    auto_processor.dingtalk_notifier.send_notification = Mock(return_value=False)
    
    result = auto_processor._send_result_notification(results)
    
    # Should return False but not raise exception
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_send_result_notification -v`
Expected: FAIL with "_send_result_notification not found"

- [ ] **Step 3: Implement notification method**

```python
def _send_result_notification(self, results: List[ProcessResult]) -> bool:
    """
    Format and send notification to DingTalk
    
    Args:
        results: List of processing results
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        # Count results by status
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        skipped_count = sum(1 for r in results if r.status == "skipped")
        total_count = len(results)
        
        # Build notification content
        content_lines = [
            "## 处理结果摘要",
            "",
            f"- 总计处理: {total_count} 条消息",
            f"- 成功: {success_count} 条",
            f"- 失败: {failed_count} 条",
            f"- 跳过: {skipped_count} 条",
        ]
        
        # Add successful processing details
        success_results = [r for r in results if r.status == "success"]
        if success_results:
            content_lines.extend([
                "",
                "## 成功处理",
                ""
            ])
            for result in success_results:
                content_lines.append(f"✅ {result.folder_name} - 文件传输成功")
        
        # Add failed processing details
        failed_results = [r for r in results if r.status == "failed"]
        if failed_results:
            content_lines.extend([
                "",
                "## 处理失败",
                ""
            ])
            for result in failed_results:
                error_msg = result.error_message or "未知错误"
                content_lines.append(f"❌ {result.folder_name} - {error_msg}")
        
        # Add timestamp
        content_lines.extend([
            "",
            f"## 处理时间",
            "",
            f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        content = "\n".join(content_lines)
        
        # Send notification
        title = "百度网盘文件处理报告"
        success = self.dingtalk_notifier.send_notification(title, content)
        
        if success:
            self.logger.info("DingTalk notification sent successfully")
        else:
            self.logger.warning("Failed to send DingTalk notification")
        
        return success
        
    except Exception as e:
        self.logger.error(f"Error sending notification: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify notification logic works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_send_result_notification -v`
Expected: PASS

- [ ] **Step 5: Commit notification implementation**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: add DingTalk notification method"
```

---

## Task 8: Integrate Notification into Main Workflow

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write failing test for notification integration**

```python
def test_process_messages_sends_notification(self, auto_processor):
    """Test process_messages sends notification at the end"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    mock_parse_result = Mock()
    mock_parse_result.folder_name = "260723"
    mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
    mock_parse_result.code = "0409"
    auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
    auto_processor.message_parser.calculate_message_hash = Mock(return_value="hash123")
    auto_processor._is_duplicate_message = Mock(return_value=False)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    mock_summary = Mock(spec=ExecutionSummary)
    mock_summary.SUCCESS_COUNT = 5
    mock_summary.FAILED_COUNT = 0
    auto_processor.file_processor.process_files = Mock(return_value=mock_summary)
    
    # Mock notification
    auto_processor._send_result_notification = Mock(return_value=True)
    
    exit_code = auto_processor.process_messages()
    
    assert exit_code == 0
    auto_processor._send_result_notification.assert_called_once()
    
    # Verify results passed to notification
    call_args = auto_processor._send_result_notification.call_args
    results = call_args[0][0]
    assert len(results) == 1
    assert results[0].folder_name == "260723"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_sends_notification -v`
Expected: FAIL with "_send_result_notification not called"

- [ ] **Step 3: Integrate notification into main workflow**

```python
def process_messages(self) -> int:
    """
    Main workflow orchestration method
    
    Returns:
        Exit code: 0 = success (even with partial failures), 
                  1 = critical system failure
    """
    try:
        self.logger.info("Starting automatic message processing")
        start_time = datetime.now()
        
        # Retrieve messages from Feishu
        messages = self.feishu_client.get_messages()
        self.logger.info(f"Retrieved {len(messages)} messages from Feishu")
        
        results = []
        
        for message in messages:
            try:
                # Extract message content from JSON
                content = message.get("content", "")
                if not content:
                    self.logger.warning(f"Empty message content for message_id: {message.get('message_id')}")
                    continue
                
                # Parse message content
                parse_result = self.message_parser.parse_message(content)
                if not parse_result:
                    self.logger.debug(f"Failed to parse message: {content[:50]}...")
                    continue
                
                # Calculate message hash
                message_hash = self.message_parser.calculate_message_hash(content)
                
                # Check for duplicates
                if self._is_duplicate_message(message_hash):
                    self.logger.info(f"Skipping duplicate message: {parse_result.folder_name}")
                    results.append(ProcessResult(
                        folder_name=parse_result.folder_name,
                        share_link=parse_result.share_link,
                        status="skipped"
                    ))
                    continue
                
                # Insert new message to database
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=content,
                    share_link=parse_result.share_link,
                    folder_name=parse_result.folder_name,
                    status="pending"
                )
                message_id = self.db_repo.insert_message_log(message_log)
                self.logger.info(f"Inserted new message: {parse_result.folder_name}")
                
                # Update status to processing
                self.db_repo.update_message_status(message_hash, "processing")
                
                # Process via FileProcessor
                process_start = datetime.now()
                summary = self.file_processor.process_files(
                    parse_result.share_link,
                    parse_result.code,
                    parse_result.folder_name
                )
                processing_time = int((datetime.now() - process_start).total_seconds() * 1000)
                
                # Update database status based on result
                if summary and summary.SUCCESS_COUNT > 0:
                    status = "success"
                    error_message = None
                else:
                    status = "failed"
                    error_message = "File processing failed or no files transferred"
                
                self.db_repo.update_message_status(
                    message_hash,
                    status,
                    error_message=error_message,
                    processing_time=processing_time
                )
                
                results.append(ProcessResult(
                    folder_name=parse_result.folder_name,
                    share_link=parse_result.share_link,
                    status=status,
                    error_message=error_message,
                    processing_time_ms=processing_time
                ))
                
            except Exception as e:
                self.logger.error(f"Error processing individual message: {e}")
                # Update status to critical_error for this message
                if 'message_hash' in locals():
                    self.db_repo.update_message_status(
                        message_hash,
                        "critical_error",
                        error_message=str(e)
                    )
                    results.append(ProcessResult(
                        folder_name=parse_result.folder_name if 'parse_result' in locals() else "unknown",
                        share_link=parse_result.share_link if 'parse_result' in locals() else "unknown",
                        status="critical_error",
                        error_message=str(e)
                    ))
                continue
        
        # Send notification
        self._send_result_notification(results)
        
        self.logger.info(f"Processing completed in {int((datetime.now() - start_time).total_seconds())}s")
        return 0
        
    except Exception as e:
        self.logger.error(f"Critical failure during message processing: {e}")
        return 1
```

- [ ] **Step 4: Run test to verify notification integration works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_process_messages_sends_notification -v`
Expected: PASS

- [ ] **Step 5: Commit notification integration**

```bash
git add src/processor/auto_processor.py tests/unit/test_auto_processor.py
git commit -m "feat: integrate notification into main workflow"
```

---

## Task 9: Implement Exit Code Logic

**Files:**
- Modify: `src/processor/auto_processor.py`
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write failing test for exit code scenarios**

```python
def test_exit_code_success_with_partial_failures(self, auto_processor):
    """Test exit code 0 when some messages fail but processing completes"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc1"}'},
        {"message_id": "msg2", "content": '{"text":"260724：https://pan.baidu.com/s/abc2"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    auto_processor.message_parser.parse_message = Mock(side_effect=[
        Mock(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", code="0409"),
        Mock(folder_name="260724", share_link="https://pan.baidu.com/s/abc2", code="0409"),
    ])
    auto_processor.message_parser.calculate_message_hash = Mock(side_effect=["hash1", "hash2"])
    auto_processor._is_duplicate_message = Mock(return_value=False)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    # First message succeeds, second fails
    auto_processor.file_processor.process_files = Mock(side_effect=[
        Mock(SUCCESS_COUNT=5, FAILED_COUNT=0),
        None  # Failure
    ])
    
    exit_code = auto_processor.process_messages()
    
    # Should return 0 (success even with partial failures)
    assert exit_code == 0

def test_exit_code_critical_failure_on_retrieval_error(self, auto_processor):
    """Test exit code 1 when Feishu message retrieval fails"""
    auto_processor.feishu_client.get_messages = Mock(side_effect=Exception("API timeout"))
    
    exit_code = auto_processor.process_messages()
    
    # Should return 1 (critical failure)
    assert exit_code == 1

def test_exit_code_critical_failure_on_config_error(self, auto_processor):
    """Test exit code 1 when configuration is invalid"""
    # Test with missing database connection
    with patch('src.processor.auto_processor.DatabaseRepository', side_effect=Exception("DB connection failed")):
        with patch('src.processor.auto_processor.Settings', return_value=auto_processor.settings):
            processor = AutoProcessor(auto_processor.settings)
            exit_code = processor.process_messages()
            assert exit_code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_exit_code -v`
Expected: FAIL with various assertion errors

- [ ] **Step 3: The exit code logic is already implemented, verify it works correctly**

The existing implementation already handles exit codes correctly:
- Returns 0 for successful processing (even with partial failures)
- Returns 1 for critical failures (config, retrieval errors)

- [ ] **Step 4: Run tests to verify exit code logic works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_exit_code -v`
Expected: PASS

- [ ] **Step 5: Commit exit code tests**

```bash
git add tests/unit/test_auto_processor.py
git commit -m "test: add exit code scenario tests"
```

---

## Task 10: Update Package Exports

**Files:**
- Modify: `src/processor/__init__.py`

- [ ] **Step 1: Write test for AutoProcessor import**

```python
def test_auto_processor_importable_from_processor(self):
    """Test AutoProcessor can be imported from processor module"""
    from src.processor import AutoProcessor
    assert AutoProcessor is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_auto_processor_importable_from_processor -v`
Expected: FAIL with "cannot import 'AutoProcessor'"

- [ ] **Step 3: Update processor module exports**

```python
from src.processor.file_processor import FileProcessor
from src.processor.auto_processor import AutoProcessor

__all__ = ['FileProcessor', 'AutoProcessor']
```

- [ ] **Step 4: Run test to verify export works**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_auto_processor_importable_from_processor -v`
Expected: PASS

- [ ] **Step 5: Commit package exports update**

```bash
git add src/processor/__init__.py tests/unit/test_auto_processor.py
git commit -m "feat: export AutoProcessor from processor module"
```

---

## Task 11: Final Integration Test and Verification

**Files:**
- Modify: `tests/unit/test_auto_processor.py`

- [ ] **Step 1: Write comprehensive integration test**

```python
def test_full_workflow_integration(self, auto_processor):
    """Test complete workflow from message retrieval to notification"""
    # Setup realistic message flow
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/success1"}'},
        {"message_id": "msg2", "content": '{"text":"260724：https://pan.baidu.com/s/fail1"}'},
        {"message_id": "msg3", "content": '{"text":"260725：https://pan.baidu.com/s/success2"}'},
        {"message_id": "msg4", "content": '{"text":"invalid message format"}'},
        {"message_id": "msg5", "content": '{"text":"260726：https://pan.baidu.com/s/duplicate"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    # Setup parsing results (msg4 should fail to parse)
    parse_results = [
        Mock(folder_name="260723", share_link="https://pan.baidu.com/s/success1", code="0409"),
        Mock(folder_name="260724", share_link="https://pan.baidu.com/s/fail1", code="0409"),
        Mock(folder_name="260725", share_link="https://pan.baidu.com/s/success2", code="0409"),
        None,  # Invalid format
        Mock(folder_name="260726", share_link="https://pan.baidu.com/s/duplicate", code="0409"),
    ]
    auto_processor.message_parser.parse_message = Mock(side_effect=parse_results)
    auto_processor.message_parser.calculate_message_hash = Mock(side_effect=["hash1", "hash2", "hash3", "hash5"])
    
    # Setup duplicate check (msg5 is duplicate)
    def duplicate_check(hash_val):
        return hash_val == "hash5"
    auto_processor._is_duplicate_message = Mock(side_effect=duplicate_check)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    # Setup FileProcessor results
    file_processor_results = [
        Mock(SUCCESS_COUNT=3, FAILED_COUNT=0),  # success1
        Mock(SUCCESS_COUNT=0, FAILED_COUNT=2),  # fail1
        Mock(SUCCESS_COUNT=5, FAILED_COUNT=0),  # success2
    ]
    auto_processor.file_processor.process_files = Mock(side_effect=file_processor_results)
    
    # Mock notification
    auto_processor._send_result_notification = Mock(return_value=True)
    
    # Execute
    exit_code = auto_processor.process_messages()
    
    # Verify results
    assert exit_code == 0  # Overall success despite some failures
    
    # Should have parsed 5 messages, but skipped invalid and duplicate
    assert auto_processor.message_parser.parse_message.call_count == 5
    assert auto_processor.file_processor.process_files.call_count == 3  # Only non-duplicate valid messages
    
    # Should have inserted 3 messages (skipped msg4 invalid, msg5 duplicate)
    assert auto_processor.db_repo.insert_message_log.call_count == 3
    
    # Should have sent notification
    auto_processor._send_result_notification.assert_called_once()
    
    # Verify notification results
    notification_results = auto_processor._send_result_notification.call_args[0][0]
    assert len(notification_results) == 4  # 2 success + 1 failed + 1 skipped
    
    status_counts = {"success": 0, "failed": 0, "skipped": 0}
    for result in notification_results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
    
    assert status_counts["success"] == 2
    assert status_counts["failed"] == 1
    assert status_counts["skipped"] == 1

def test_handles_empty_message_list(self, auto_processor):
    """Test handling of empty message list from Feishu"""
    auto_processor.feishu_client.get_messages = Mock(return_value=[])
    auto_processor._send_result_notification = Mock(return_value=True)
    
    exit_code = auto_processor.process_messages()
    
    # Should still succeed (0 messages processed is valid)
    assert exit_code == 0
    auto_processor._send_result_notification.assert_called_once_with([])

def test_continues_processing_after_individual_message_errors(self, auto_processor):
    """Test that processing continues even when individual messages fail"""
    mock_messages = [
        {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc1"}'},
        {"message_id": "msg2", "content": '{"text":"260724：https://pan.baidu.com/s/abc2"}'},
        {"message_id": "msg3", "content": '{"text":"260725：https://pan.baidu.com/s/abc3"}'},
    ]
    auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)
    
    auto_processor.message_parser.parse_message = Mock(side_effect=[
        Mock(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", code="0409"),
        Exception("Parse error"),  # Second message fails during parsing
        Mock(folder_name="260725", share_link="https://pan.baidu.com/s/abc3", code="0409"),
    ])
    auto_processor.message_parser.calculate_message_hash = Mock(side_effect=["hash1", "hash3"])
    auto_processor._is_duplicate_message = Mock(return_value=False)
    auto_processor.db_repo.insert_message_log = Mock(return_value=1)
    
    auto_processor.file_processor.process_files = Mock(return_value=Mock(SUCCESS_COUNT=1, FAILED_COUNT=0))
    auto_processor._send_result_notification = Mock(return_value=True)
    
    exit_code = auto_processor.process_messages()
    
    # Should still succeed and process remaining messages
    assert exit_code == 0
    assert auto_processor.file_processor.process_files.call_count == 2  # msg1 and msg3
```

- [ ] **Step 2: Run integration tests to verify they pass**

Run: `pytest tests/unit/test_auto_processor.py::TestAutoProcessor::test_full_workflow_integration tests/unit/test_auto_processor.py::TestAutoProcessor::test_handles_empty_message_list tests/unit/test_auto_processor.py::TestAutoProcessor::test_continues_processing_after_individual_message_errors -v`
Expected: PASS

- [ ] **Step 3: Run all AutoProcessor tests**

Run: `pytest tests/unit/test_auto_processor.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit integration tests**

```bash
git add tests/unit/test_auto_processor.py
git commit -m "test: add comprehensive integration tests"
```

---

## Task 12: Final Documentation and Code Review

**Files:**
- No files created or modified

- [ ] **Step 1: Run all tests to ensure everything works**

Run: `pytest tests/unit/test_auto_processor.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Verify code quality and documentation**

Run: Check that all methods have docstrings and type hints

- [ ] **Step 3: Create final summary of implementation**

```bash
echo "AutoProcessor implementation complete. Components integrated:"
echo "- FeishuMessageClient for message retrieval"
echo "- MessageParser for message parsing and hashing"
echo "- DatabaseRepository for duplicate detection and status tracking"
echo "- FileProcessor for file transfer processing"
echo "- DingtalkNotifier for notification sending"
echo ""
echo "Features implemented:"
echo "- One-time batch processing for Windows Task Scheduler"
echo "- Database-first duplicate detection"
echo "- Continue-on-failure error handling"
echo "- Standard DingTalk notifications"
echo "- Clear exit codes (0/1) for monitoring"
```

- [ ] **Step 4: Final commit with implementation complete marker**

```bash
git add src/processor/auto_processor.py src/processor/__init__.py tests/unit/test_auto_processor.py
git commit -m "feat: add AutoProcessor for automatic message processing

Complete implementation of AutoProcessor coordinator class:
- Integrates FeishuMessageClient, MessageParser, DatabaseRepository, FileProcessor, DingtalkNotifier
- Implements one-time batch processing for Windows Task Scheduler
- Database-first duplicate detection
- Continue-on-failure error handling with comprehensive status tracking
- Standard DingTalk notifications with success/failure reporting
- Clear exit codes (0=success, 1=critical failure) for monitoring
- Comprehensive unit tests with full workflow coverage

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review Results

**Spec Coverage:**
✅ AutoProcessor class structure - Task 2
✅ Component initialization - Task 2  
✅ Duplicate detection method - Task 3
✅ Main process_messages workflow - Task 4, 5, 6
✅ FileProcessor integration - Task 6
✅ Notification method - Task 7
✅ Notification integration - Task 8
✅ Exit code logic - Task 9
✅ Package exports - Task 10
✅ Comprehensive testing - Task 11, 12

**Placeholder Scan:** ✅ No placeholders found - all steps contain complete code and commands

**Type Consistency:** ✅ Method signatures and types consistent across all tasks

**No Spec Gaps:** All requirements from design spec are implemented:
- Core coordination ✅
- Message parsing and filtering ✅  
- Duplicate detection ✅
- File processing integration ✅
- Notification system ✅
- Exit codes ✅
- Error handling ✅
- Testing coverage ✅

Plan is complete and ready for execution.