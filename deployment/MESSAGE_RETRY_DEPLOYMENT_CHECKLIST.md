# Message Retry Limit Feature - Production Deployment Checklist

**Feature Version:** 1.0  
**Deployment Target:** Production Environment  
**Risk Level:** Medium (Database Schema Changes)  
**Estimated Downtime:** 0-5 minutes (Database Migration Phase)

---

## 📋 Pre-Deployment Checklist

### Phase 1: Planning and Preparation ⏰ T-7 Days

#### 1.1 Stakeholder Communication
- [ ] **Notify stakeholders** of upcoming deployment 7 days in advance
  - [ ] Operations team notified
  - [ ] Development team notified  
  - [ ] Business stakeholders notified
  - [ ] Support team briefed on changes

- [ ] **Schedule deployment window** confirmed
  - [ ] Deployment date: _____________
  - [ ] Deployment time: _____________ to _____________
  - [ ] Backup personnel assigned: _____________

#### 1.2 Environment Preparation
- [ ] **Test environment validation** completed
  - [ ] All migration scripts tested in staging
  - [ ] Configuration validation successful
  - [ ] Performance benchmarks established
  - [ ] Rollback procedures tested

- [ ] **Production environment preparation**
  - [ ] Production database backup completed (within 24 hours)
  - [ ] Configuration files backed up
  - [ ] Application files backed up
  - [ ] Rollback access credentials verified

### Phase 2: Pre-Deployment Verification ⏰ T-1 Day

#### 2.1 Database Readiness
- [ ] **Database backup verification**
  - [ ] Full database backup completed
  - [ ] Backup integrity verified
  - [ ] Backup restoration tested
  - [ ] Backup stored in secure location

- [ ] **Database schema validation**
  - [ ] Current schema documented
  - [ ] Migration scripts reviewed
  - [ ] Rollback scripts prepared
  - [ ] Schema changes approved by DBA

#### 2.2 Configuration Validation
- [ ] **Configuration file preparation**
  - [ ] `.env` file updated with MESSAGE_MAX_RETRIES
  - [ ] Configuration validated for correct values (1-100)
  - [ ] Configuration tested in staging environment
  - [ ] Configuration backup created

```bash
# Configuration validation command
MESSAGE_MAX_RETRIES=10 # Must be between 1-100
```

#### 2.3 Application Readiness
- [ ] **Application version validation**
  - [ ] Version v1.4.6+ confirmed
  - [ ] All previous migrations applied
  - [ ] Application tested with new feature
  - [ ] Performance baseline established

- [ ] **Deployment package preparation**
  - [ ] Production deployment package created
  - [ ] Package integrity verified
  - [ ] Deployment scripts prepared
  - [ ] Rollback scripts tested

---

## 🚀 Deployment Procedures

### Phase 3: Deployment Execution ⏰ T-0 (Deployment Window)

#### Step 1: Pre-Deployment Checks (5 minutes)

```bash
# 1.1 Verify database connectivity
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "USE $DB_NAME; SELECT 1;"

# 1.2 Verify current schema
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "DESCRIBE message_process_log;"

# 1.3 Verify application is running
ps aux | grep baidu-download || tasklist | findstr baidu-download

# 1.4 Check current retry_count column status
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) as count FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '$DB_NAME' AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';"
```

- [ ] Database connectivity confirmed
- [ ] Current schema validated
- [ ] Application status verified
- [ ] retry_count column status confirmed (0 = doesn't exist, 1 = exists)

#### Step 2: Application Shutdown (2 minutes)

```bash
# 2.1 Stop application gracefully
python main.py --stop || systemctl stop baidu-download

# 2.2 Verify application stopped
ps aux | grep baidu-download || tasklist | findstr baidu-download

# 2.3 Check no pending database transactions
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SHOW PROCESSLIST;"
```

- [ ] Application stopped successfully
- [ ] No active processes remaining
- [ ] No pending database transactions

#### Step 3: Database Migration (10 minutes)

```bash
# 3.1 Create database backup (if not done recently)
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME > backup_before_retry_migration_$(date +%Y%m%d_%H%M%S).sql

# 3.2 Verify backup created successfully
ls -lh backup_before_retry_migration_*.sql

# 3.3 Execute migration script
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < database/migrations/add_retry_count.sql

# 3.4 Verify migration success
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = '$DB_NAME' AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';
"

# 3.5 Verify index created
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "
SHOW INDEX FROM message_process_log WHERE Key_name = 'idx_retry_count';
"

# 3.6 Verify data integrity
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "
SELECT COUNT(*) as total_messages, 
       SUM(CASE WHEN retry_count = 0 THEN 1 ELSE 0 END) as zero_retry_count,
       SUM(CASE WHEN retry_count > 0 THEN 1 ELSE 0 END) as positive_retry_count
FROM message_process_log;
"
```

- [ ] Database backup created successfully
- [ ] Migration script executed without errors
- [ ] retry_count column verified
- [ ] idx_retry_count index verified
- [ ] Data integrity confirmed (all existing records have retry_count = 0)

#### Step 4: Configuration Update (3 minutes)

```bash
# 4.1 Backup current configuration
cp .env .env.backup_before_retry_$(date +%Y%m%d_%H%M%S)

# 4.2 Add MESSAGE_MAX_RETRIES configuration
echo "MESSAGE_MAX_RETRIES=10" >> .env

# 4.3 Verify configuration added
grep MESSAGE_MAX_RETRIES .env

# 4.4 Validate configuration loads correctly
python -c "from src.config.settings import Settings; s = Settings(); print(f'Max retries: {s.max_message_retries}')"
```

- [ ] Configuration backed up
- [ ] MESSAGE_MAX_RETRIES added to .env
- [ ] Configuration validated successfully
- [ ] Value within valid range (1-100)

#### Step 5: Application Deployment (5 minutes)

```bash
# 5.1 Update application code (if needed)
# git pull origin main || deploy new version

# 5.2 Install dependencies (if updated)
# pip install -r requirements.txt

# 5.3 Start application
python main.py --auto --verbose || systemctl start baidu-download

# 5.4 Verify application started
ps aux | grep baidu-download || tasklist | findstr baidu-download

# 5.5 Check application logs for errors
tail -f logs/transfer.log
```

- [ ] Application code updated (if needed)
- [ ] Dependencies installed (if updated)
- [ ] Application started successfully
- [ ] No startup errors in logs

#### Step 6: Post-Deployment Verification (10 minutes)

```bash
# 6.1 Test retry limit functionality
python -c "
from src.config.settings import Settings;
from src.database.repository import DatabaseRepository;

settings = Settings()
print(f'Max retries configured: {settings.max_message_retries}')

db_repo = DatabaseRepository(
    host=settings.db_host,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    database=settings.db_name
)

# Test retry filtering
retry_messages = db_repo.get_recent_messages_to_retry(hours=24)
print(f'Retry messages filtered successfully: {len(retry_messages)} messages eligible for retry')
"

# 6.2 Test retry count increment
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "
-- Test retry count increment simulation
UPDATE message_process_log SET retry_count = retry_count + 1 WHERE process_status = 'failed' LIMIT 1;
SELECT message_hash, retry_count, process_status FROM message_process_log WHERE retry_count > 0 ORDER BY retry_count DESC LIMIT 5;
"

# 6.3 Monitor application behavior
tail -f logs/transfer.log | grep -i retry
```

- [ ] Configuration loaded correctly
- [ ] Retry filtering functionality working
- [ ] Retry count increment verified
- [ ] No unexpected behavior in logs
- [ ] Application processing messages normally

---

## ✅ Post-Deployment Validation

### Phase 4: Post-Deployment Testing (30 minutes)

#### 4.1 Functional Testing

- [ ] **Message retry limit functionality**
  - [ ] Test message retry counting
  - [ ] Test retry exclusion at limit
  - [ ] Test successful retry resets counter
  - [ ] Verify retry filtering works correctly

```bash
# Run functional tests
python deployment/scripts/test_retry_functionality.py
```

#### 4.2 Performance Testing

- [ ] **Performance validation**
  - [ ] Database query performance verified
  - [ ] Application response time normal
  - [ ] No performance degradation observed
  - [ ] Resource utilization within limits

```sql
-- Check query performance
EXPLAIN SELECT * FROM message_process_log WHERE retry_count < 10 AND process_status IN ('failed', 'critical_error');
```

#### 4.3 Monitoring Verification

- [ ] **Monitoring and alerting**
  - [ ] Application metrics collecting
  - [ ] Database metrics monitoring active
  - [ ] Error rates within normal range
  - [ ] No new alert patterns

#### 4.4 Data Integrity

- [ ] **Data validation**
  - [ ] All messages have retry_count set
  - [ ] No NULL retry_count values
  - [ ] Historical data preserved correctly
  - [ ] Index performance verified

```sql
-- Data integrity verification
SELECT COUNT(*) as null_retry_count FROM message_process_log WHERE retry_count IS NULL;
-- Expected: 0

SELECT COUNT(*) as total_messages, MIN(retry_count) as min_retry, MAX(retry_count) as max_retry FROM message_process_log;
-- Expected: all values >= 0
```

---

## 🔄 Rollback Procedures

### Emergency Rollback Triggers

**Immediate rollback required if:**
- Application crashes repeatedly after deployment
- Database corruption detected
- Performance degradation > 50%
- Data integrity issues discovered
- Security vulnerabilities identified

### Rollback Procedure (15 minutes)

#### Step 1: Application Shutdown (2 minutes)
```bash
# Stop application
python main.py --stop || systemctl stop baidu-download
```

- [ ] Application stopped

#### Step 2: Database Rollback (5 minutes)
```bash
# 2.1 Restore database from backup
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < backup_before_retry_migration_YYYYMMDD_HHMMSS.sql

# 2.2 Verify rollback successful
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "DESCRIBE message_process_log;"

# 2.3 Verify retry_count column removed
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "
SELECT COUNT(*) as count FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '$DB_NAME' AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count';
"
# Expected: 0 (column should not exist)
```

- [ ] Database restored successfully
- [ ] retry_count column removed
- [ ] Index removed
- [ ] Data integrity verified

#### Step 3: Configuration Rollback (2 minutes)
```bash
# 3.1 Restore previous configuration
cp .env.backup_before_retry_YYYYMMDD_HHMMSS .env

# 3.2 Verify configuration restored
grep -v MESSAGE_MAX_RETRIES .env
```

- [ ] Configuration restored
- [ ] MESSAGE_MAX_RETRIES removed

#### Step 4: Application Restart (3 minutes)
```bash
# 4.1 Start previous application version
python main.py --auto --verbose || systemctl start baidu-download

# 4.2 Verify application started
ps aux | grep baidu-download || tasklist | findstr baidu-download

# 4.3 Check logs for errors
tail -f logs/transfer.log
```

- [ ] Application started successfully
- [ ] No startup errors
- [ ] Normal operation resumed

#### Step 5: Validation (3 minutes)
- [ ] Application functioning normally
- [ ] No database errors
- [ ] Message processing resumed
- [ ] Performance baseline restored

---

## 📊 Deployment Sign-Off

### Pre-Deployment Sign-Off

**Technical Lead:** _______________________ **Date:** ________  
**Operations Lead:** _______________________ **Date:** ________  
**Database Administrator:** _______________________ **Date:** ________  

### Deployment Execution Sign-Off

**Deployment Engineer:** _______________________ **Time:** ________  
**Monitoring Engineer:** _______________________ **Time:** ________  

### Post-Deployment Validation Sign-Off

**Quality Assurance:** _______________________ **Time:** ________  
**Operations Manager:** _______________________ **Time:** ________  

---

## 📝 Deployment Notes

### Issues Encountered:
___________________________________________________________________________
___________________________________________________________________________

### Deviations from Plan:
___________________________________________________________________________
___________________________________________________________________________

### Additional Observations:
___________________________________________________________________________
___________________________________________________________________________

---

## 🆘 Emergency Contacts

| Role | Name | Contact | Availability |
|------|------|---------|---------------|
| Deployment Lead | _____________ | _____________ | _____________ |
| Database Admin | _____________ | _____________ | _____________ |
| Operations Lead | _____________ | _____________ | _____________ |
| Development Lead | _____________ | _____________ | _____________ |

---

## 📈 Success Criteria

**Deployment is considered successful when:**
- [ ] All pre-deployment checks completed without issues
- [ ] Database migration completed successfully
- [ ] Application restarted without errors
- [ ] All post-deployment validations passed
- [ ] Performance within 10% of baseline
- [ ] No data integrity issues
- [ ] Monitoring systems functioning normally
- [ ] All stakeholders notified of successful deployment

---

**Checklist Version:** 1.0  
**Last Updated:** 2026-08-19  
**Next Review Date:** Post-Deployment + 7 days

---

⚠️ **IMPORTANT:** This checklist must be followed exactly. Any deviations must be documented and approved by the deployment lead before proceeding.