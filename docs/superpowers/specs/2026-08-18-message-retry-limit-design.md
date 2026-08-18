# Message Retry Limit Feature Design Specification

**Date:** 2026-08-18  
**Author:** Design specification for message retry limit functionality  
**Status:** Approved for implementation

## Overview

Add a configurable retry limit feature to the message processing system that tracks the number of failed processing attempts per message and permanently excludes messages from retry processing after they reach a maximum retry threshold (default: 10 attempts).

### Problem Statement

The current message processing system will retry failed messages indefinitely. This can lead to:

1. **Resource waste** - Processing messages that consistently fail
2. **Log noise** - Repeated error messages for the same failures
3. **Operational overhead** - Manual intervention needed to stop retry loops
4. **System efficiency** - Resources diverted from potentially recoverable messages

### Success Criteria

- Messages stop being retried after configurable max retry limit
- Retry count resets on successful processing (giving messages "fresh attempts")
- Configuration is flexible via environment variables
- Database-level enforcement ensures consistency
- Existing messages are handled gracefully
- Silent exclusion of max-retry messages from future processing

## Architecture

### Approach: Database-Level Enforcement with Configuration

**Why this approach:**
- **Consistency:** Database constraints prevent retry limit bypass
- **Performance:** Single database query handles filtering
- **Reliability:** No application-level state synchronization issues
- **Observability:** Retry counts stored alongside message status
- **Flexibility:** Configuration allows operational tuning

**Architecture:**

```
┌─────────────────┐
│ Configuration   │
│ MESSAGE_MAX_RETRIES│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Message Processing System        │
│  ┌───────────────────────────────┐  │
│  │   Auto Processor               │  │
│  │  - Calls repository methods    │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│                  ▼                   │
│  ┌───────────────────────────────┐  │
│  │   Repository                  │  │
│  │  - update_message_status()    │  │
│  │  - get_recent_messages_to_retry()│
│  │  - Increment/reset retry_count│  │
│  └───────────────┬───────────────┘  │
└──────────────────┼──────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   Database       │
         │ message_process_log│
         │ - retry_count    │
         │ - process_status │
         └─────────────────┘
```

### Key Design Decisions

**1. Retry Count Semantics**
- **Increment** on status transition to `failed` or `critical_error`
- **Reset** to 0 on status transition to `success`
- **Rationale:** Gives messages "fresh attempts" after recovery, prevents accumulated retry penalties

**2. Maximum Retry Default**
- **Default:** 10 attempts (configurable via `MESSAGE_MAX_RETRIES`)
- **Range:** 1-100 (enforced in settings)
- **Rationale:** 10 attempts balance persistence with resource conservation

**3. Database Filtering**
- **Implementation:** Add `AND retry_count < {max_retries}` to retry queries
- **Index:** Create index on `retry_count` for efficient filtering
- **Rationale:** Database-level filtering is more reliable and performant

## Database Schema Changes

### Current Schema (message_process_log)

```sql
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error'),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
```

### New Schema

```sql
CREATE TABLE IF NOT EXISTS message_process_log (
    id INT AUTO_AUTO_INCREMENT PRIMARY KEY,
    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT '消息MD5哈希',
    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error'),
    retry_count INT DEFAULT 0 COMMENT '失败重试次数',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_retry_count (retry_count)
)
```

### Migration SQL

```sql
-- Phase 1: Add retry_count column
ALTER TABLE message_process_log 
ADD COLUMN retry_count INT DEFAULT 0 COMMENT '失败重试次数' 
AFTER error_message;

-- Phase 2: Add index for efficient filtering
CREATE INDEX idx_retry_count ON message_process_log(retry_count);

-- Verification: Check migration succeeded
SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;
-- Expected: 0 (all existing records get DEFAULT 0)
```

## Configuration Changes

### Environment Variable

```bash
# .env file configuration
MESSAGE_MAX_RETRIES=10
```

### Configuration Implementation

**File:** `src/config/settings.py`

```python
class Settings:
    def __init__(self):
        # Existing configuration...
        self.max_message_retries = self._get_int_env('MESSAGE_MAX_RETRIES', default=10)
        # Validate range
        if not 1 <= self.max_message_retries <= 100:
            raise ValueError(f"MESSAGE_MAX_RETRIES must be between 1 and 100, got: {self.max_message_retries}")
```

### Configuration Documentation

**File:** `.env.example`

```bash
# Message Retry Configuration
# Maximum number of retry attempts for failed messages before permanent exclusion
# Default: 10, Range: 1-100
MESSAGE_MAX_RETRIES=10
```

## Repository Modifications

### Update Method: `update_message_status()`

**Current Behavior:** Updates message status without retry tracking

**New Behavior:** Manages retry count based on status transitions

```python
def update_message_status(self, message_hash: str, status: str, error_message: str = None, processing_time_ms: int = None) -> bool:
    """
    Update message processing status and manage retry count.
    
    Args:
        message_hash: Unique message identifier
        status: New processing status
        error_message: Optional error details
        processing_time_ms: Optional processing duration
    
    Returns:
        bool: True if update successful
    
    Retry Count Logic:
        - Increment on status transition to 'failed' or 'critical_error'
        - Reset to 0 on status transition to 'success'
        - Unchanged for 'pending' and 'processing'
    """
    try:
        with self.connection.cursor() as cursor:
            if status in ['failed', 'critical_error']:
                # Increment retry count for failed statuses
                sql = """
                UPDATE message_process_log 
                SET process_status = %s, 
                    error_message = %s,
                    processing_time_ms = %s,
                    retry_count = retry_count + 1
                WHERE message_hash = %s
                """
                cursor.execute(sql, (status, error_message, processing_time_ms, message_hash))
            elif status == 'success':
                # Reset retry count on success
                sql = """
                UPDATE message_process_log 
                SET process_status = %s, 
                    error_message = NULL,
                    processing_time_ms = %s,
                    retry_count = 0
                WHERE message_hash = %s
                """
                cursor.execute(sql, (status, processing_time_ms, message_hash))
            else:
                # No retry count change for pending/processing
                sql = """
                UPDATE message_process_log 
                SET process_status = %s, 
                    error_message = %s,
                    processing_time_ms = %s
                WHERE message_hash = %s
                """
                cursor.execute(sql, (status, error_message, processing_time_ms, message_hash))
            
            self.connection.commit()
            return cursor.rowcount > 0
    except Exception as e:
        self.connection.rollback()
        logger.error(f"Failed to update message status: {e}")
        return False
```

### Query Method: `get_recent_messages_to_retry()`

**Current Behavior:** Returns all messages with `critical_error` status within time window

**New Behavior:** Filters out messages that have reached max retry limit

```python
def get_recent_messages_to_retry(self, hours: int = 24) -> List[str]:
    """
    Get messages eligible for retry processing.
    
    Args:
        hours: Time window in hours (default: 24)
    
    Returns:
        List of message hashes eligible for retry
    
    Filters:
        - Status must be 'critical_error'
        - Must be within time window
        - retry_count must be less than MESSAGE_MAX_RETRIES
    """
    max_retries = self.settings.max_message_retries
    
    sql = """
    SELECT message_hash FROM message_process_log
    WHERE process_status = 'critical_error'
    AND retry_count < %s
    AND created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
    ORDER BY created_at ASC
    """
    
    try:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, (max_retries, hours))
            results = cursor.fetchall()
            return [row[0] for row in results] if results else []
    except Exception as e:
        logger.error(f"Failed to get messages to retry: {e}")
        return []
```

## Error Handling and Logging

### Error Scenarios

**1. Database Migration Failure**
- **Detection:** Check for NULL retry_count values
- **Handling:** Rollback ALTER TABLE, investigate constraints
- **Logging:** Critical alert with schema validation details

**2. Configuration Invalid**
- **Detection:** MESSAGE_MAX_RETRIES outside 1-100 range
- **Handling:** Raise ValueError on startup, provide clear message
- **Logging:** Error with configuration details

**3. Retry Count Overflow**
- **Detection:** retry_count exceeds INT range (unlikely in practice)
- **Handling:** Database constraint will trigger error
- **Logging:** Warning with message hash and retry count

**4. Repository Update Failures**
- **Detection:** Exception in update_message_status()
- **Handling:** Return False, maintain atomic transaction
- **Logging:** Error with message hash and exception details

### Logging Strategy

```python
# Information level
logger.info(f"Message {message_hash} retry count updated to {retry_count}")
logger.info(f"Message {message_hash} excluded from retry (max retries reached: {max_retries})")

# Warning level
logger.warning(f"Message {message_hash} reached max retry count ({max_retries})")
logger.warning(f"Configuration: MESSAGE_MAX_RETRIES={max_retries}")

# Error level
logger.error(f"Failed to update retry count for message {message_hash}: {e}")
logger.error(f"Database migration failed: {e}")
```

## Testing Strategy

### Unit Tests

**Test Files:** `tests/database/test_repository_retry.py`

1. **Retry Count Increment Test**
   ```python
   def test_retry_count_increments_on_failure():
       # Create message, update status to failed twice
       # Assert retry_count == 2
   ```

2. **Retry Count Reset Test**
   ```python
   def test_retry_count_resets_on_success():
       # Create message, fail twice, then succeed
       # Assert retry_count == 0
   ```

3. **Max Retry Filtering Test**
   ```python
   def test_max_retry_messages_excluded():
       # Create messages with retry_count 10 and 11
       # Assert only retry_count < 10 returned
   ```

4. **Configuration Boundary Test**
   ```python
   def test_configuration_boundaries():
       # Test MESSAGE_MAX_RETRIES = 1, 10, 100
       # Test ValueError for 0 and 101
   ```

### Integration Tests

**Test Files:** `tests/integration/test_retry_integration.py`

1. **End-to-End Retry Flow**
   ```python
   def test_message_retry_to_exclusion():
       # Process message through 10 failures
       # Verify excluded from retry queue
       # Verify retry_count == 10
   ```

2. **Successful Recovery Test**
   ```python
   def test_successful_recovery_resets_retries():
       # Fail message 5 times, then succeed
       # Verify retry_count == 0
       # Verify eligible for retry on next failure
   ```

3. **Database Migration Test**
   ```python
   def test_database_migration():
       # Run migration SQL
       # Verify schema changes
       # Verify existing data preserved
   ```

### Manual Testing

**Test Scenarios:**

1. **Configuration Testing**
   - Set MESSAGE_MAX_RETRIES=3 in .env
   - Process messages, verify exclusion after 3 failures
   - Verify retry_count in database matches expectations

2. **Database Verification**
   ```sql
   -- Check messages at retry limit
   SELECT message_hash, retry_count, process_status 
   FROM message_process_log 
   WHERE retry_count >= (SELECT @max_retries);
   
   -- Verify retry distribution
   SELECT retry_count, COUNT(*) as count
   FROM message_process_log
   GROUP BY retry_count
   ORDER BY retry_count;
   ```

3. **Log Analysis**
   - Check for retry count increment logs
   - Verify max retry exclusion warnings
   - Confirm no database errors during updates

## Migration Plan

### Phase 1: Database Schema (Rollback Safe)

```bash
# 1. Backup database
mysqldump -u user -p database > backup_before_retry_limit.sql

# 2. Apply migration
mysql -u user -p database < database/migrations/add_retry_count.sql

# 3. Verify migration
mysql -u user -p database -e "SELECT COUNT(*) FROM message_process_log WHERE retry_count IS NULL;"
# Expected: 0

# 4. Test rollback capability
mysql -u user -p database -e "ALTER TABLE message_process_log DROP COLUMN retry_count;"
```

### Phase 2: Application Deployment

1. **Add configuration** to `.env` file
2. **Deploy code changes** to repository and settings
3. **Monitor logs** for retry count operations
4. **Verify database** retry_count increments

### Rollback Plan

**If issues detected:**

1. **Immediate:** Remove retry filter from repository query (quick fix)
2. **Investigate:** Check logs for error patterns
3. **Decision:** 
   - **Keep column** if rollback is temporary (harmless)
   - **Drop column** if rollback is permanent: `ALTER TABLE message_process_log DROP COLUMN retry_count;`
4. **Revert code** to previous version

## Implementation Checklist

### Database
- [ ] Add `retry_count` column to `message_process_log` table
- [ ] Create `idx_retry_count` index
- [ ] Test migration on staging database
- [ ] Verify existing data gets `retry_count = 0`

### Configuration
- [ ] Add `MESSAGE_MAX_RETRIES` to settings validation
- [ ] Update `.env.example` with new variable
- [ ] Test configuration boundaries (1, 10, 100, invalid values)

### Repository
- [ ] Modify `update_message_status()` to manage retry_count
- [ ] Modify `get_recent_messages_to_retry()` to filter by max_retries
- [ ] Add logging for retry count operations
- [ ] Add error handling for retry count updates

### Testing
- [ ] Write unit tests for retry count logic
- [ ] Write integration tests for end-to-end retry flow
- [ ] Write manual test scenarios
- [ ] Test database migration and rollback
- [ ] Verify configuration validation

### Documentation
- [ ] Update `.env.example` with MESSAGE_MAX_RETRIES
- [ ] Add inline code comments explaining retry logic
- [ ] Document migration steps in deployment guide
- [ ] Update operational runbooks with retry limit monitoring

## Monitoring and Observability

### Key Metrics

1. **Retry Count Distribution**
   ```sql
   SELECT retry_count, COUNT(*) as message_count
   FROM message_process_log
   WHERE process_status IN ('failed', 'critical_error')
   GROUP BY retry_count
   ORDER BY retry_count DESC;
   ```

2. **Excluded Messages**
   ```sql
   SELECT COUNT(*) as excluded_messages
   FROM message_process_log
   WHERE retry_count >= (SELECT @max_retries);
   ```

3. **Retry Recovery Rate**
   ```sql
   SELECT 
     COUNT(CASE WHEN retry_count > 0 AND process_status = 'success' THEN 1 END) as recovered_messages,
     COUNT(CASE WHEN process_status = 'success' THEN 1 END) as total_success
   FROM message_process_log;
   ```

### Alerting

**Warnings:**
- High percentage of messages reaching retry limit (> 20%)
- Sudden spikes in retry_count increments
- Database errors during retry count updates

**Information:**
- Message successfully recovered after multiple retries
- Configuration changes to MESSAGE_MAX_RETRIES

## Future Enhancements

### Potential Improvements

1. **Exponential Backoff:** Increase delay between retries based on retry_count
2. **Per-Message Type Limits:** Different max_retries for different message types
3. **Retry Policy Configuration:** More sophisticated retry strategies (circuit breakers, time-based exclusion)
4. **Metrics Dashboard:** Visual monitoring of retry patterns and system health
5. **Manual Reset:** Administrative interface to reset retry counts for specific messages

## Success Metrics

- **Operational:** 100% reduction in infinite retry loops
- **Performance:** Reduced processing time by excluding hopeless messages
- **Reliability:** No increase in message processing failures
- **Observability:** Clear visibility into retry patterns via database queries
- **Flexibility:** Easy configuration adjustment without code changes