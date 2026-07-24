# AutoProcessor Design Specification

**Date:** 2025-01-24
**Status:** Approved
**Component:** src/processor/auto_processor.py

## Overview

AutoProcessor is a coordinator class that orchestrates the entire automatic message processing workflow for Windows Task Scheduler integration. It serves as a one-time batch processor that retrieves messages from Feishu, processes new messages through the file transfer pipeline, and sends notifications via DingTalk.

## Design Philosophy

- **Minimal Integration**: Thin coordinator that delegates to existing components
- **Separation of Concerns**: Each component has a single responsibility
- **Fault Tolerance**: Continue processing even when individual messages fail
- **Clear Exit Codes**: Simple binary status for Windows Task Scheduler monitoring
- **Database-First**: Leverage existing deduplication mechanisms

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AutoProcessor                         │
│                  (Batch Coordinator)                     │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────┬───────────────┬──────────────┬──────────────┐
    ▼                 ▼               ▼              ▼              ▼
┌─────────┐    ┌──────────┐   ┌───────────┐   ┌─────────┐   ┌─────────────┐
│FeishuMsg│    │Message   │   │Database   │   │File     │   │Dingtalk     │
│Client   │───▶│Parser    │───▶│Repository│───▶│Processor│───▶│Notifier     │
└─────────┘    └──────────┘   └───────────┘   └─────────┘   └─────────────┘
```

## Core Responsibilities

### 1. Message Retrieval & Parsing
- Retrieve messages from Feishu using FeishuMessageClient
- Parse each message using MessageParser (regex pattern)
- Calculate message hash for deduplication

### 2. Duplicate Detection
- Check database for existing message hashes
- Skip already-processed messages
- Insert new messages with status 'pending'

### 3. File Processing
- Process new messages through FileProcessor
- Track processing results (success/failure)
- Update database status after processing

### 4. Notification & Reporting
- Generate comprehensive result summary
- Send DingTalk notification with standard detail level
- Return appropriate exit code for Task Scheduler

## Public Interface

### Class: AutoProcessor

```python
class AutoProcessor:
    """Automatic message processing coordinator for Windows Task Scheduler integration"""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize AutoProcessor with all required dependencies
        
        Args:
            settings: Configuration object, defaults to new Settings instance
        """
        
    def process_messages(self) -> int:
        """
        Main workflow orchestration method
        
        Returns:
            Exit code: 0 = success (even with partial failures), 
                      1 = critical system failure
        """
        
    def _is_duplicate_message(self, message_hash: str) -> bool:
        """
        Check if message was already processed
        
        Args:
            message_hash: MD5 hash of message content
            
        Returns:
            True if message exists in database, False otherwise
        """
        
    def _send_result_notification(self, results: List[ProcessResult]) -> bool:
        """
        Format and send notification to DingTalk
        
        Args:
            results: List of processing results
            
        Returns:
            True if notification sent successfully, False otherwise
        """
```

## Processing Workflow

### Step-by-Step Flow

```
1. Initialize Components
   ├─ FeishuMessageClient
   ├─ MessageParser  
   ├─ DatabaseRepository
   ├─ FileProcessor
   └─ DingtalkNotifier

2. Retrieve Messages
   └─ FeishuMessageClient.get_messages()
   └─ On failure: exit with code 1 (after retries)

3. Process Each Message
   For each message:
   ├─ Parse content (MessageParser)
   ├─ Calculate hash (MessageParser.calculate_message_hash())
   ├─ Check duplicate (DatabaseRepository.get_message_by_hash())
   ├─ If new: insert to database with status='pending'
   ├─ Update status to 'processing'
   ├─ Process via FileProcessor
   ├─ Update status to 'success'/'failed'/'critical_error'
   └─ Track result for notification

4. Generate Notification
   ├─ Count success/failure
   ├─ Format standard notification content
   └─ Send via DingtalkNotifier

5. Return Exit Code
   ├─ 0: Success (any messages processed successfully)
   └─ 1: Critical failure (config/retrieval errors)
```

## Data Structures

### ProcessResult (Internal)

```python
@dataclass
class ProcessResult:
    """Internal tracking for processing results"""
    folder_name: str
    share_link: str
    status: str  # 'success', 'failed', 'critical_error', 'skipped'
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
```

### Notification Format

**Title:** 百度网盘文件处理报告

**Content:**
```markdown
## 处理结果摘要

- 总计处理: X 条消息
- 成功: X 条
- 失败: X 条

## 成功处理

✅ {folder_name} - 文件传输成功

## 处理失败

❌ {folder_name} - {error_reason}

## 处理时间

开始时间: {start_time}
结束时间: {end_time}
总耗时: {total_time}
```

## Error Handling Strategy

### Critical Errors (Exit Code 1)
- Configuration validation failures
- Feishu message retrieval failures (after retries)
- Database connection failures
- Component initialization failures

### Message Processing Failures (Exit Code 0)
- FileProcessor failures (download/upload errors)
- Individual message parsing failures
- Duplicate messages (skipped, not failed)

### Error Recovery
- **Continue on Failure**: Always process remaining messages
- **Status Tracking**: Update database status for all messages
- **Logging**: Log all errors with appropriate detail level
- **Notification**: Include failures in final notification

## Database Status Flow

```
pending → processing → success/failed/critical_error
  ↓           ↓             ↓          ↓          ↓
(insert)   (update)      (update)   (update)   (update)
```

### Status Definitions

- **pending**: Message inserted, awaiting processing
- **processing**: Currently being processed by FileProcessor
- **success**: Processed successfully (all files transferred)
- **failed**: Processing failed (download/upload errors)
- **critical_error**: Unrecoverable system error

## Configuration Requirements

### Required Settings
- Feishu: app_id, app_secret, chat_id
- Database: host, port, user, password, database_name
- DingTalk: webhook_url
- Message: default_extraction_code
- BaiduPCS: executable_path, cookies_path, temp_dir

### Optional Settings
- feishu_hours_limit: Time window for processing (default: 24)
- max_retries: Retry attempts for failures (default: 3)
- log_level: Logging verbosity (default: INFO)

## Exit Codes for Windows Task Scheduler

| Code | Meaning | Task Scheduler Action |
|------|---------|----------------------|
| 0    | Success | Continue schedule |
| 1    | Critical Failure | Alert operators, retry manual |

## Testing Strategy

### Unit Tests (tests/unit/test_auto_processor.py)

**Test Coverage:**
1. **Initialization**: Component setup and validation
2. **Duplicate Detection**: Database lookup logic
3. **Message Processing**: Workflow orchestration
4. **Error Handling**: Various failure scenarios
5. **Notification**: Formatting and sending
6. **Exit Codes**: Correct code returned

**Test Structure:**
```python
class TestAutoProcessor:
    def test_init_with_valid_settings()
    def test_init_with_invalid_settings()
    def test_process_messages_with_new_messages()
    def test_process_messages_with_duplicate_messages()
    def test_process_messages_with_mixed_results()
    def test_process_messages_retrieval_failure()
    def test_is_duplicate_message_true()
    def test_is_duplicate_message_false()
    def test_send_result_notification_success()
    def test_send_result_notification_partial_failure()
    def test_exit_code_success_with_failures()
    def test_exit_code_critical_failure()
    def test_notification_formatting()
    def test_status_update_on_success()
    def test_status_update_on_failure()
    def test_status_update_on_critical_error()
```

### Integration Considerations
- Test with real Feishu API responses (mocked)
- Test with database operations
- Test FileProcessor integration
- Test DingTalk notification sending

## Implementation Phases

### Phase 1: Core Structure
1. Create AutoProcessor class with __init__
2. Implement component initialization
3. Add configuration validation

### Phase 2: Processing Workflow
1. Implement process_messages() main loop
2. Add message parsing and duplicate detection
3. Integrate FileProcessor for new messages
4. Add database status tracking

### Phase 3: Notification & Exit Codes
1. Implement _send_result_notification()
2. Add notification formatting
3. Implement exit code logic
4. Add comprehensive error handling

## Dependencies

### Internal Components
- `src.feishu.feishu_client.FeishuMessageClient`
- `src.feishu.message_parser.MessageParser`
- `src.database.repository.DatabaseRepository`
- `src.processor.file_processor.FileProcessor`
- `src.notification.dingtalk_notifier.DingtalkNotifier`
- `src.config.settings.Settings`
- `src.utils.logger.get_logger`

### External Libraries
- Standard Python libraries (typing, datetime, etc.)

## File Structure

```
src/
├── processor/
│   ├── __init__.py
│   ├── auto_processor.py       # NEW
│   └── file_processor.py       # EXISTING
```

## Success Criteria

1. **Functional**: Successfully processes new messages from Feishu
2. **Reliable**: Handles failures gracefully, continues processing
3. **Observable**: Clear exit codes and DingTalk notifications
4. **Maintainable**: Clean code, follows existing patterns
5. **Testable**: Comprehensive unit test coverage
6. **Deployable**: Ready for Windows Task Scheduler integration

## Future Considerations

### Potential Enhancements
- Add configuration for message processing order
- Support for multiple Feishu chats
- Detailed performance metrics
- Retry queue for failed messages
- Parallel processing of multiple messages

### Operational Considerations
- Monitoring for stuck processing
- Database cleanup for old logs
- Performance optimization for large message batches
- Rate limiting for Feishu API calls

## Appendix: Message Format

### Feishu Message Format
```
YYMMDD：https://pan.baidu.com/s/XXXX
```

Example:
```
260723：https://pan.baidu.com/s/1a2b3c4d5e6f
```

### Regex Pattern
```python
r'^(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)'
```

### Parsed Components
- **folder_name**: YYMMDD (6-digit date)
- **share_link**: Full Baidu netdisk URL
- **code**: Default extraction code from settings
