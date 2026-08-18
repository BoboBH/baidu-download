# Message Retry Limit Manual Testing Guide

**Feature:** Message Retry Limit Configuration  
**Version:** 1.0  
**Date:** 2026-08-19  
**Purpose:** Comprehensive manual testing procedures for message retry limit feature

---

## 📋 Testing Prerequisites and Setup

### Required Tools and Access

**Database Access:**
- MySQL client access to test/production database
- Database credentials with SELECT, UPDATE, ALTER privileges
- Backup tool (mysqldump) available

**System Access:**
- Access to modify `.env` configuration file
- File system access to log files
- Ability to restart the application

**Test Environment:**
- Working database connection
- Application server access
- Sample test messages available

### Pre-Test Checklist

```bash
# 1. Verify database connectivity
mysql -u root -p -e "SELECT 1;"

# 2. Create database backup before testing
mysqldump -u root -p baidu_download > backup_before_retry_test_$(date +%Y%m%d).sql

# 3. Verify backup file created
ls -lh backup_before_retry_test_*.sql

# 4. Check current application status
ps aux | grep baidu-download  # Linux
tasklist | findstr baidu-download  # Windows
```

### Configuration File Location

```bash
# Main configuration file
.env

# Configuration template for reference
.env.example
```

**⚠️ IMPORTANT:** Always backup database and configuration files before testing!

---

## 🔧 Configuration Testing Procedures

### Test 1: Default Configuration Verification

**Objective:** Verify default MESSAGE_MAX_RETRIES configuration

**Steps:**
```bash
# 1. Check current configuration
grep MESSAGE_MAX_RETRIES .env

# Expected output: MESSAGE_MAX_RETRIES=10
```

**Expected Results:**
- Configuration value should be `10` (default)
- Application should start without errors
- Settings validation should pass

**Verification:**
```bash
# Start application and check logs
tail -f logs/transfer.log | grep -i "retry"

# Should see: Configuration loaded successfully
```

---

### Test 2: Configuration Range Testing

**Objective:** Test MESSAGE_MAX_RETRIES with different valid values

#### Test 2a: Minimum Value (1)

**Steps:**
```bash
# 1. Update .env file
sed -i 's/MESSAGE_MAX_RETRIES=10/MESSAGE_MAX_RETRIES=1/' .env

# 2. Verify change
grep MESSAGE_MAX_RETRIES .env

# 3. Restart application
# (Use your normal restart procedure)

# 4. Check logs for configuration load
tail -20 logs/transfer.log | grep -i "config\|retry"
```

**Expected Results:**
- Application starts successfully
- Configuration shows MESSAGE_MAX_RETRIES=1
- No validation errors in logs

#### Test 2b: Maximum Value (100)

**Steps:**
```bash
# 1. Update to maximum value
sed -i 's/MESSAGE_MAX_RETRIES=1/MESSAGE_MAX_RETRIES=100/' .env

# 2. Restart application
# 3. Verify configuration loaded
tail -20 logs/transfer.log | grep -i "config"
```

**Expected Results:**
- Application starts successfully
- Configuration shows MESSAGE_MAX_RETRIES=100
- No warnings about invalid configuration

#### Test 2c: Custom Value (3)

**Steps:**
```bash
# 1. Set to custom value for testing
sed -i 's/MESSAGE_MAX_RETRIES=100/MESSAGE_MAX_RETRIES=3/' .env

# 2. Restart application
```

**Expected Results:**
- Application accepts value 3
- Configuration validation passes
- Ready for message processing tests

---

### Test 3: Invalid Configuration Testing

**Objective:** Verify proper error handling for invalid values

#### Test 3a: Value Below Range (0)

**Steps:**
```bash
# 1. Set invalid value
sed -i 's/MESSAGE_MAX_RETRIES=3/MESSAGE_MAX_RETRIES=0/' .env

# 2. Try to start application
python main.py --auto
```

**Expected Results:**
- Application fails to start
- Clear error message about invalid configuration
- Error message includes valid range (1-100)

#### Test 3b: Value Above Range (101)

**Steps:**
```bash
# 1. Set another invalid value
sed -i 's/MESSAGE_MAX_RETRIES=0/MESSAGE_MAX_RETRIES=101/' .env

# 2. Try to start application
python main.py --auto
```

**Expected Results:**
- Application fails to start
- Clear error message about value exceeding maximum
- Application doesn't crash with unclear error

#### Test 3c: Non-Numeric Value

**Steps:**
```bash
# 1. Set invalid text value
sed -i 's/MESSAGE_MAX_RETRIES=101/MESSAGE_MAX_RETRIES=invalid/' .env

# 2. Try to start application
```

**Expected Results:**
- Application fails to start
- Error message about invalid format
- Clear indication of configuration parsing failure

---

### Test 4: Configuration Reset

**Steps:**
```bash
# 1. Reset to production-ready default
sed -i 's/MESSAGE_MAX_RETRIES=.*/MESSAGE_MAX_RETRIES=10/' .env

# 2. Verify reset
grep MESSAGE_MAX_RETRIES .env

# 3. Restart application with valid config
```

**Expected Results:**
- Configuration reset to default value
- Application starts successfully
- Ready for database and processing tests

---

## 🗄️ Database Verification Procedures

### Test 5: Schema Migration Verification

**Objective:** Verify database schema includes retry_count column and index

#### Test 5a: Check Column Existence

**SQL Query:**
```sql
-- Check if retry_count column exists
DESCRIBE message_process_log;

-- Expected result should show:
-- Field      Type             Null  Key  Default              Extra
-- ----------------------------------------------------------------
-- ...
-- retry_count int             YES        0                    
-- ...
```

**Expected Results:**
- `retry_count` column exists
- Type is `int`
- Default value is `0`
- Column positioned correctly (after processing_time_ms)

#### Test 5b: Check Index Existence

**SQL Query:**
```sql
-- Check if retry_count index exists
SHOW INDEX FROM message_process_log WHERE Key_name = 'idx_retry_count';

-- Expected result should show:
-- Table                Key_name          Seq_in_index    Column_name     Cardinality
-- -----------------------------------------------------------------------------------
-- message_process_log  idx_retry_count   1               retry_count     [some value]
```

**Expected Results:**
- Index `idx_retry_count` exists
- Index is on `retry_count` column
- Index is active and usable

#### Test 5c: Verify Existing Data Migration

**SQL Query:**
```sql
-- Check all existing records have retry_count set
SELECT COUNT(*) as null_count 
FROM message_process_log 
WHERE retry_count IS NULL;

-- Expected result: 0 (no NULL values)
```

**Expected Results:**
- 0 rows with NULL retry_count
- All existing records have default value of 0
- No data corruption from migration

---

### Test 6: Database Query Performance Testing

**Objective:** Verify retry filtering queries perform efficiently

#### Test 6a: Test Retry Query Performance

**SQL Query:**
```sql
-- Test the query used by get_recent_messages_to_retry()
EXPLAIN SELECT message_hash FROM message_process_log
WHERE process_status = 'critical_error'
AND retry_count < 10
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY created_at ASC;

-- Expected result:
-- - type: ref or range (good index usage)
-- - key: should show idx_retry_count or similar
-- - rows: reasonable number (not full table scan)
```

**Expected Results:**
- Query uses index (not full table scan)
- Execution time < 100ms for typical dataset
- No filesort or temporary tables in EXPLAIN output

#### Test 6b: Test Retry Count Distribution Query

**SQL Query:**
```sql
-- Test distribution query performance
EXPLAIN SELECT retry_count, COUNT(*) as count
FROM message_process_log
GROUP BY retry_count
ORDER BY retry_count;

-- Expected result:
-- Efficient query execution using index
```

**Expected Results:**
- Query completes in reasonable time
- Uses appropriate index for GROUP BY
- No performance warnings

---

## 🔄 Message Processing Scenarios

### Test 7: Normal Retry Flow Testing

**Objective:** Verify retry count increments on message failures

**Setup:**
```bash
# Ensure MESSAGE_MAX_RETRIES=3 for testing
grep MESSAGE_MAX_RETRIES .env
# Should show: MESSAGE_MAX_RETRIES=3
```

**Steps:**
```bash
# 1. Process a message that will fail (use known bad link)
# 2. Check retry count after first failure
# 3. Let message be reprocessed (should happen automatically)
# 4. Check retry count after second failure
# 5. Check retry count after third failure
```

**Database Verification:**
```sql
-- After each failure, check retry count
SELECT message_hash, retry_count, process_status, error_message
FROM message_process_log
WHERE message_hash = '[your_test_message_hash]'
ORDER BY updated_at DESC;

-- Expected results:
-- After 1st failure: retry_count = 1
-- After 2nd failure: retry_count = 2  
-- After 3rd failure: retry_count = 3
-- After 4th failure: retry_count = 3 (should not increment further)
```

**Expected Results:**
- retry_count increments with each failure
- retry_count never exceeds MESSAGE_MAX_RETRIES
- Message stops being processed after reaching limit

---

### Test 8: Maximum Retry Exclusion Testing

**Objective:** Verify messages are permanently excluded after reaching max retries

**Steps:**
```bash
# 1. Find or create a message at retry limit
# 2. Verify it's excluded from retry queue
# 3. Wait for next retry processing cycle
# 4. Confirm message is not processed again
```

**Database Verification:**
```sql
-- 1. Find messages at retry limit
SELECT message_hash, retry_count, process_status, created_at
FROM message_process_log
WHERE retry_count >= 3
ORDER BY retry_count DESC, updated_at DESC
LIMIT 10;

-- 2. Check if excluded messages appear in retry query
SELECT message_hash FROM message_process_log
WHERE process_status = 'critical_error'
AND retry_count < 3
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- Expected: Messages with retry_count >= 3 should NOT appear
```

**Expected Results:**
- Messages at retry limit are excluded from query results
- No additional processing attempts for excluded messages
- Log shows exclusion messages

**Log Verification:**
```bash
# Check logs for exclusion messages
grep "excluded from retry" logs/transfer.log

# Should see messages like:
# "Message [hash] excluded from retry (max retries reached: 3)"
```

---

### Test 9: Successful Recovery Testing

**Objective:** Verify retry count resets to 0 on successful processing

**Steps:**
```bash
# 1. Find a message with high retry_count
# 2. Fix the underlying issue (e.g., bad link, missing file)
# 3. Allow message to be processed successfully
# 4. Verify retry_count reset to 0
```

**Database Verification:**
```sql
-- Before success: Find message with retries
SELECT message_hash, retry_count, process_status
FROM message_process_log
WHERE retry_count > 0
LIMIT 1;

-- After success: Verify reset
SELECT message_hash, retry_count, process_status
FROM message_process_log
WHERE message_hash = '[the_same_hash]';
-- Expected: retry_count = 0, process_status = 'success'
```

**Expected Results:**
- retry_count resets to 0 on successful processing
- Message becomes eligible for retry on future failures
- No accumulated retry penalties after recovery

---

### Test 10: Concurrent Message Processing

**Objective:** Verify retry count handling under concurrent processing

**Steps:**
```bash
# 1. Process multiple messages simultaneously
# 2. Monitor retry count updates in real-time
# 3. Check for race conditions or duplicate increments
```

**Database Verification:**
```sql
-- Check for unusual retry_count values
SELECT message_hash, retry_count, process_status
FROM message_process_log
WHERE retry_count > 100  -- Unusually high values
OR retry_count < 0;      -- Negative values

-- Expected: 0 rows (no abnormal values)
```

**Expected Results:**
- No retry_count values exceed MESSAGE_MAX_RETRIES
- No negative retry_count values
- Consistent retry_count updates without race conditions

---

## 📊 Log Analysis Procedures

### Test 11: Log Pattern Verification

**Objective:** Verify proper logging of retry operations

#### Test 11a: Retry Count Increment Logs

**Log File Location:**
```bash
# Main log file
./logs/transfer.log

# Check recent logs
tail -f logs/transfer.log
```

**Expected Log Patterns:**
```bash
# Look for retry count increment messages
grep "retry count" logs/transfer.log | tail -10

# Should see patterns like:
# "Message abc123 retry count updated to 1"
# "Message abc123 retry count updated to 2"
# "Message def456 retry count updated to 3"
```

**Expected Results:**
- Clear log messages for each retry count update
- Message hash included in log entry
- Current retry_count value visible

#### Test 11b: Maximum Retry Exclusion Logs

**Expected Log Patterns:**
```bash
# Look for exclusion messages
grep "excluded from retry\|max retries" logs/transfer.log | tail -10

# Should see patterns like:
# "Message xyz789 excluded from retry (max retries reached: 3)"
# "Configuration: MESSAGE_MAX_RETRIES=3"
```

**Expected Results:**
- Clear warning when message reaches max retries
- Configuration value logged for reference
- Message hash included in exclusion notice

#### Test 11c: Configuration Change Logs

**Expected Log Patterns:**
```bash
# Look for configuration load messages
grep "MESSAGE_MAX_RETRIES\|Configuration" logs/transfer.log | tail -10

# Should see patterns like:
# "Configuration loaded: MESSAGE_MAX_RETRIES=10"
# "Configuration: MESSAGE_MAX_RETRIES=3"
```

**Expected Results:**
- Configuration logged at startup
- Changes to configuration visible in logs
- Clear indication of active retry limit

---

### Test 12: Log Error Analysis

**Objective:** Verify error handling and error logging

#### Test 12a: Database Error Logs

**Expected Log Patterns:**
```bash
# Look for database errors related to retry_count
grep -i "error.*retry\|failed.*update.*retry" logs/transfer.log

# If found, check details:
grep -i -A 5 -B 5 "error.*retry" logs/transfer.log | tail -20
```

**Expected Results:**
- No database errors during retry_count updates
- Any errors should include detailed context
- Error messages should be actionable

#### Test 12b: Configuration Error Logs

**Expected Log Patterns:**
```bash
# Look for configuration errors
grep -i "error.*config\|invalid.*retry" logs/transfer.log

# If invalid configuration was tested:
# Should see clear error messages about validation failure
```

**Expected Results:**
- Invalid configuration values logged with clear errors
- Valid range mentioned in error messages
- No silent failures or ambiguous errors

---

### Test 13: Log Integrity and Performance

**Objective:** Verify logging doesn't impact system performance

**Steps:**
```bash
# 1. Check log file size
ls -lh logs/transfer.log

# 2. Check for excessive logging
wc -l logs/transfer.log

# 3. Look for repetitive log entries
# (Should not see same message logged hundreds of times)
```

**Expected Results:**
- Log file size is reasonable (< 100MB for typical operation)
- No excessive duplicate log entries
- Log rotation working if configured

---

## ✅ Expected Results Checklist

### Configuration Validation

- [ ] MESSAGE_MAX_RETRIES accepts value 1 (minimum)
- [ ] MESSAGE_MAX_RETRIES accepts value 10 (default)
- [ ] MESSAGE_MAX_RETRIES accepts value 100 (maximum)
- [ ] MESSAGE_MAX_RETRIES rejects value 0 (below minimum)
- [ ] MESSAGE_MAX_RETRIES rejects value 101 (above maximum)
- [ ] MESSAGE_MAX_RETRIES rejects non-numeric values
- [ ] Configuration changes require application restart
- [ ] Configuration value logged at startup

### Database Schema

- [ ] retry_count column exists in message_process_log table
- [ ] retry_count column type is INT
- [ ] retry_count default value is 0
- [ ] retry_count allows NULL values (for backward compatibility)
- [ ] idx_retry_count index exists
- [ ] Index is on retry_count column only
- [ ] All existing records have retry_count = 0
- [ ] No NULL retry_count values in existing data

### Database Queries

- [ ] Retry filtering query uses index efficiently
- [ ] Messages at retry limit excluded from results
- [ ] Query performance is acceptable (< 100ms typical)
- [ ] No full table scans in retry filtering
- [ ] Retry distribution query performs well

### Message Processing

- [ ] retry_count increments on each failure
- [ ] retry_count increments only once per processing attempt
- [ ] retry_count resets to 0 on successful processing
- [ ] Messages stop processing after reaching max retries
- [ ] No messages exceed MESSAGE_MAX_RETRIES
- [ ] No negative retry_count values
- [ ] Exclusion happens silently (no repeated attempts)

### Log Analysis

- [ ] Retry count increments are logged
- [ ] Message exclusions are logged
- [ ] Configuration changes are logged
- [ ] Error messages include context (message hash, retry count)
- [ ] No database errors in logs during normal operation
- [ ] Configuration errors are clear and actionable
- [ ] Log file size remains reasonable

---

## 🚨 Troubleshooting Common Issues

### Issue 1: Configuration Not Taking Effect

**Symptoms:**
- Changes to .env don't affect retry behavior
- Application uses old configuration values

**Troubleshooting Steps:**
```bash
# 1. Verify .env file is being read
grep MESSAGE_MAX_RETRIES .env

# 2. Check for cached configuration
find . -name "*.pyc" -delete

# 3. Restart application completely
# (not just soft reload)

# 4. Check logs for configuration load
tail -50 logs/transfer.log | grep -i "config"

# 5. Verify configuration file location
# (Should be in application root directory)
```

**Solution:**
- Ensure .env file is in correct location
- Restart application after configuration changes
- Check for multiple .env files in different directories

---

### Issue 2: Retry Count Not Incrementing

**Symptoms:**
- Messages fail repeatedly but retry_count stays at 0
- No retry count increment logs

**Troubleshooting Steps:**
```sql
-- 1. Check if retry_count column is writable
UPDATE message_process_log 
SET retry_count = 1 
WHERE message_hash = 'test_hash';

-- 2. Check application logs for errors
grep -i "error.*retry\|failed.*update" logs/transfer.log

-- 3. Verify database user permissions
SHOW GRANTS FOR CURRENT_USER();

-- 4. Check for triggers preventing updates
SHOW TRIGGERS LIKE 'message_process_log';
```

**Solution:**
- Verify database user has UPDATE privileges
- Check for application-level errors in logs
- Ensure no database triggers interfere with updates

---

### Issue 3: Messages Not Being Excluded

**Symptoms:**
- Messages exceed MESSAGE_MAX_RETRIES but still get processed
- retry_count values exceed configuration maximum

**Troubleshooting Steps:**
```sql
-- 1. Check actual retry_count values
SELECT message_hash, retry_count, process_status
FROM message_process_log
WHERE retry_count > (SELECT @max_retries FROM (SELECT 10 AS max_retries) AS tmp)
ORDER BY retry_count DESC;

-- 2. Verify index is being used
EXPLAIN SELECT message_hash FROM message_process_log
WHERE process_status = 'critical_error'
AND retry_count < 10;

-- 3. Check for application-level filtering issues
grep -i "max.*retry\|excluded" logs/transfer.log | tail -20
```

**Solution:**
- Verify application code uses retry filtering query
- Check for cached query results in application
- Ensure configuration value is correctly read
- Restart application to clear any caches

---

### Issue 4: Database Migration Failures

**Symptoms:**
- Cannot add retry_count column
- Migration SQL fails with errors

**Troubleshooting Steps:**
```sql
-- 1. Check if column already exists
DESCRIBE message_process_log;

-- 2. Check for conflicting constraints
SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_NAME = 'message_process_log';

-- 3. Verify table engine
SHOW TABLE STATUS LIKE 'message_process_log';

-- 4. Test migration on backup database first
```

**Solution:**
- Use rollback-safe migration approach
- Test migration on staging database first
- Check for existing columns or constraints
- Ensure sufficient database permissions

---

### Issue 5: Performance Degradation

**Symptoms:**
- Slow message processing after feature deployment
- Database queries take longer than expected

**Troubleshooting Steps:**
```sql
-- 1. Check query execution plan
EXPLAIN SELECT message_hash FROM message_process_log
WHERE process_status = 'critical_error'
AND retry_count < 10
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- 2. Check index usage
SHOW INDEX FROM message_process_log;

-- 3. Analyze table statistics
ANALYZE TABLE message_process_log;

-- 4. Check for table locks
SHOW OPEN TABLES WHERE In_use > 0;
```

**Solution:**
- Verify idx_retry_count index exists and is active
- Run ANALYZE TABLE to update statistics
- Check for missing or corrupted indexes
- Consider database maintenance if dataset is large

---

## ⚡ Performance Considerations

### Query Performance Monitoring

**Key Queries to Monitor:**

```sql
-- 1. Retry filtering query (most frequent)
SELECT message_hash FROM message_process_log
WHERE process_status = 'critical_error'
AND retry_count < 10
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- Performance target: < 100ms for typical dataset

-- 2. Retry distribution query (reporting)
SELECT retry_count, COUNT(*) as count
FROM message_process_log
GROUP BY retry_count
ORDER BY retry_count;

-- Performance target: < 500ms

-- 3. Update query (message status update)
UPDATE message_process_log 
SET process_status = 'failed', 
    retry_count = retry_count + 1
WHERE message_hash = 'abc123';

-- Performance target: < 50ms per update
```

### Index Effectiveness

**Verification Steps:**
```sql
-- 1. Check index cardinality
SHOW INDEX FROM message_process_log;

-- Cardinality for idx_retry_count should be > 0
-- (Higher cardinality = better selectivity)

-- 2. Check index usage
EXPLAIN SELECT message_hash FROM message_process_log
WHERE retry_count < 10;

-- Should show "Using index" or "Using where" with idx_retry_count
```

### Large Dataset Handling

**Considerations:**
- Index becomes more important as dataset grows
- Consider partitioning if message_process_log > 1M rows
- Monitor query execution time trends
- Archive old messages to maintain performance

---

## 📝 Sign-off Checklist

### Pre-Deployment Verification

- [ ] Database migration tested on staging environment
- [ ] Configuration validation tested with all boundary values
- [ ] Manual testing completed for all scenarios
- [ ] Log analysis procedures verified
- [ ] Performance benchmarks established
- [ ] Rollback procedure tested
- [ ] Operations team trained on new feature
- [ ] Monitoring and alerting configured

### Post-Deployment Validation

- [ ] Database schema verified in production
- [ ] Configuration correctly deployed
- [ ] Application starts without errors
- [ ] Sample messages processed successfully
- [ ] Retry counts increment correctly
- [ ] Message exclusions working as expected
- [ ] Logs show expected patterns
- [ ] Performance within acceptable ranges
- [ ] No database errors in logs
- [ ] Alerting configured and tested

### Rollback Preparation

- [ ] Database backup created pre-deployment
- [ ] Rollback SQL script prepared and tested
- [ ] Configuration backup created
- [ ] Application code version controlled
- [ ] Rollback procedure documented
- [ ] Team trained on rollback process

---

## 📞 Support and Contact

**For issues or questions about this testing guide:**

1. **Database Issues:** Check database administrator
2. **Configuration Issues:** Review .env.example and settings.py
3. **Application Issues:** Check application logs and error messages
4. **Performance Issues:** Run query performance analysis

**Additional Resources:**
- Design Specification: `docs/superpowers/specs/2026-08-18-message-retry-limit-design.md`
- Implementation Plan: `docs/superpowers/plans/2026-08-18-message-retry-limit.md`
- Configuration Template: `.env.example`

---

## 📋 Test Execution Log

Use this section to track test execution:

| Test # | Test Name | Executed By | Date | Results | Notes |
|-------|-----------|-------------|------|---------|-------|
| 1 | Default Config | | | ☐ Pass ☐ Fail | |
| 2a | Min Value (1) | | | ☐ Pass ☐ Fail | |
| 2b | Max Value (100) | | | ☐ Pass ☐ Fail | |
| 2c | Custom Value (3) | | | ☐ Pass ☐ Fail | |
| 3a | Invalid: 0 | | | ☐ Pass ☐ Fail | |
| 3b | Invalid: 101 | | | ☐ Pass ☐ Fail | |
| 3c | Invalid: text | | | ☐ Pass ☐ Fail | |
| 5a | Column Check | | | ☐ Pass ☐ Fail | |
| 5b | Index Check | | | ☐ Pass ☐ Fail | |
| 5c | Data Migration | | | ☐ Pass ☐ Fail | |
| 6a | Query Performance | | | ☐ Pass ☐ Fail | |
| 7 | Normal Retry Flow | | | ☐ Pass ☐ Fail | |
| 8 | Max Exclusion | | | ☐ Pass ☐ Fail | |
| 9 | Recovery Reset | | | ☐ Pass ☐ Fail | |
| 10 | Concurrent Processing | | | ☐ Pass ☐ Fail | |
| 11a | Increment Logs | | | ☐ Pass ☐ Fail | |
| 11b | Exclusion Logs | | | ☐ Pass ☐ Fail | |
| 11c | Config Logs | | | ☐ Pass ☐ Fail | |

**Overall Test Result:** ☐ Pass ☐ Fail

**Signed Off By:** _________________ **Date:** _______________

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-19  
**Next Review Date:** Post-implementation validation