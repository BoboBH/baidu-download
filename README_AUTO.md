# 自动模式使用指南

## 📖 Overview

The **Automatic Mode** enables the Baidu PDF file transfer system to process Feishu messages automatically without manual intervention. When integrated with Windows Task Scheduler, it creates a completely automated workflow:

```
Feishu Messages → Message Parsing → File Processing → SFTP Upload → DingTalk Notification
```

### When to Use Automatic Mode

**Perfect for:**
- Regular file transfer operations from Feishu group messages
- Automated batch processing without manual intervention
- 24/7 unattended file transfer operations
- Scheduled processing of accumulated Feishu messages

**Key Benefits:**
- ✅ **Zero Manual Intervention** - Processes Feishu messages automatically
- ✅ **Duplicate Detection** - MD5 hash-based message deduplication
- ✅ **Comprehensive Logging** - Complete audit trail in MySQL database
- ✅ **Error Recovery** - Handles individual message failures gracefully
- ✅ **Status Notifications** - DingTalk integration for processing results
- ✅ **Windows Scheduler Ready** - Designed for scheduled task integration

### How It Works

1. **Message Retrieval**: Fetches recent messages from configured Feishu group
2. **Message Parsing**: Extracts folder name and Baidu share link using regex pattern
3. **Duplicate Check**: Calculates MD5 hash to prevent reprocessing
4. **File Processing**: Downloads PDFs from Baidu and uploads to SFTP
5. **Status Tracking**: Updates database with processing status and timing
6. **Notification**: Sends summary report to DingTalk

---

## 📋 Prerequisites

### System Requirements

#### Environment
- **Operating System**: Windows 11 or higher (for Task Scheduler integration)
- **Python**: 3.8+ (for Python version) OR Windows EXE version
- **MySQL**: 5.7+ with proper permissions
- **Network**: Stable internet connection for Feishu API, Baidu, and SFTP

#### Account Requirements
- **Feishu Developer Account** with:
  - App ID and App Secret
  - Access to target Feishu group
  - API permissions for message reading
  
- **DingTalk Robot** (optional but recommended):
  - Webhook URL for notification sending
  
- **Baidu NetDisk Account**:
  - Valid account with logged-in cookies
  - Access to shared files

#### Database Permissions
- MySQL user with permissions to:
  - Create database and tables
  - Insert, update, and query records
  - Create indexes

---

## 🔧 Configuration

### Configuration File Structure

The automatic mode requires specific configuration sections in your `.env` file. Copy the template and configure as needed:

```bash
copy .env.example .env
notepad .env
```

### Feishu Configuration (Required)

```ini
# ===== 飞书配置 (自动模式必需) =====
# 飞书应用凭证 (用于接收和处理飞书消息)
FEISHU_APP_ID=your_feishu_app_id_here
FEISHU_APP_SECRET=your_feishu_app_secret_here

# 飞书群组ID (用于接收下载通知)
FEISHU_CHAT_ID=your_feishu_chat_id_here

# 飞书消息时间范围 (小时)，默认24小时内
FEISHU_HOURS_LIMIT=24
```

**How to Get Feishu Credentials:**

1. **Access Feishu Open Platform**: Visit https://open.feishu.cn/
2. **Create Application**: 
   - Go to "App Management" → "Create App"
   - Choose "Self-built App" type
   - Copy App ID and App Secret from app details
3. **Configure Permissions**:
   - Enable "Message: Read Message" permission
   - Enable "API: Access tenant_access_token" permission
4. **Get Chat ID**:
   - Open target Feishu group
   - Right-click group name → "Group Settings"
   - Copy Group ID (looks like: oc_xxxxxxxxxxxxxxxx)

### DingTalk Configuration (Optional but Recommended)

```ini
# ===== 钉钉配置 (自动模式可选) =====
# 钉钉机器人Webhook地址 (用于发送下载通知)
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_dingtalk_token_here
```

**How to Get DingTalk Webhook:**

1. **Add Robot to DingTalk Group**:
   - Open DingTalk group settings
   - Go to "Group Settings" → "Smart Group Assistant"
   - Add "Custom Robot"
2. **Configure Webhook**:
   - Choose "Custom" type
   - Copy webhook URL (looks like: https://oapi.dingtalk.com/robot/send?access_token=xxx)
3. **Security Settings** (recommended):
   - Add IP whitelist or keyword verification
   - Save and copy the final webhook URL

### Message Processing Configuration

```ini
# ===== 消息处理配置 (自动模式) =====
# 默认提取码 (4位数字，当飞书消息中未指定提取码时使用)
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
```

### Database Configuration

```ini
# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_db_password_here
DB_NAME=baidu_download
```

### Complete .env Example

```ini
# ===== 百度网盘配置 =====
BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
BAIDU_COOKIES_PATH=./baidu-cookies.txt
TEMP_DIR=./temp

# ===== SFTP服务器配置 =====
SFTP_HOST=192.168.0.122
SFTP_PORT=22
SFTP_USERNAME=sftp01
SFTP_PASSWORD=your_secure_password_here
SFTP_REMOTE_PATH=/sftp01/upload

# ===== MySQL数据库配置 =====
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_db_password_here
DB_NAME=baidu_download

# ===== 飞书配置 (自动模式必需) =====
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=your_secret_here
FEISHU_CHAT_ID=oc_xxxxxxxxxxxxxxxx
FEISHU_HOURS_LIMIT=24

# ===== 钉钉配置 (自动模式可选) =====
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your_token_here

# ===== 消息处理配置 (自动模式) =====
MESSAGE_DEFAULT_EXTRACTION_CODE=0409

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FILE=./logs/transfer.log

# ===== 性能配置 =====
MAX_RETRIES=3
CONCURRENT_UPLOADS=1
```

---

## 🚀 Installation

### Step 1: Deploy Application Files

#### Option A: EXE Version (Recommended)

```bash
# 1. Download and extract EXE version
unzip baidu-download-v1.1.5-exe.zip -d D:\baidu-auto\

# 2. Navigate to installation directory
cd D:\baidu-auto\

# 3. Verify files exist
dir
# Expected: baidu-download.exe, BaiduPCS-Go.exe, .env.example, etc.
```

#### Option B: Python Version

```bash
# 1. Extract source code
unzip baidu-download-v1.1.5.zip -d D:\baidu-auto\

# 2. Navigate to project directory
cd D:\baidu-auto\

# 3. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# 1. Copy configuration template
copy .env.example .env

# 2. Edit configuration
notepad .env

# 3. Fill in required credentials
# - Feishu App ID/Secret
# - Feishu Chat ID
# - DingTalk Webhook (optional)
# - Database credentials
# - SFTP credentials
```

### Step 3: Initialize Database

```bash
# 1. Access MySQL
mysql -u root -p

# 2. Run initialization script
source D:\\baidu-auto\\middle\\db_init.sql

# 3. Verify tables created
USE baidu_download;
SHOW TABLES;
# Expected: execution_summary, file_transfer_log, message_process_log
```

### Step 4: Test Configuration

```bash
# Test configuration validity
# EXE version:
baidu-download.exe --auto --dry-run

# Python version:
python main.py --auto --dry-run
```

Expected output:
```
[INFO] Configuration validation successful
[INFO] Feishu client initialized
[INFO] Database connection established
[INFO] AutoProcessor initialized successfully
[INFO] Automatic mode configuration test completed
```

### Step 5: Verify Endpoints

```bash
# Test Feishu API connection (requires manual Python test)
python -c "from src.feishu.feishu_client import FeishuMessageClient; from src.config.settings import Settings; client = FeishuMessageClient(Settings()); print(client.get_tenant_access_token())"

# Test database connection
mysql -u root -p -e "USE baidu_download; SELECT COUNT(*) FROM message_process_log;"

# Test SFTP connection
python test\diagnostic\diagnose_sftp.py
```

---

## ⏰ Windows Task Scheduler Setup

### Creating Scheduled Task

#### Method 1: Using Task Scheduler GUI (Recommended)

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Right-click "Task Scheduler Library" → "Create Basic Task"
   - Name: `Baidu Auto File Transfer`
   - Description: `Automatic Feishu message processing and file transfer`
   - Click "Next"

3. **Choose Trigger**:
   - Select "Daily" (or "When I log on" for testing)
   - Set start time (e.g., 09:00 AM)
   - Click "Next"

4. **Choose Action**:
   - Select "Start a program"
   - Click "Next"

5. **Configure Program**:
   - **EXE Version**:
     ```
     Program/script: D:\baidu-auto\baidu-download.exe
     Add arguments: --auto
     Start in: D:\baidu-auto\
     ```
   
   - **Python Version**:
     ```
     Program/script: C:\Python38\python.exe
     Add arguments: D:\baidu-auto\main.py --auto
     Start in: D:\baidu-auto\
     ```
   - Click "Next"

6. **Finish and Configure**:
   - Check "Open task properties" checkbox
   - Click "Finish"

7. **Advanced Settings** (recommended):
   - **General Tab**:
     - Select "Run whether user is logged on or not"
     - Check "Run with highest privileges"
     - Configure for: "Windows 10"
   
   - **Triggers Tab**:
     - Edit trigger → "Advanced settings"
     - Check "Repeat task every: 1 hour" (for frequent processing)
     - Duration: "Indefinitely"
   
   - **Conditions Tab**:
     - Uncheck "Start the task only if the computer is on AC power"
     - Check "Wake the computer to run this task" (if needed)
   
   - **Settings Tab**:
     - Check "Allow task to be run on demand"
     - Check "If the task fails, restart every 1 minute"
     - Attempt to restart up to: 3 times
     - Stop task if it runs longer than: 2 hours

8. **Test Task**:
   - Right-click task → "Run"
   - Check "Task Scheduler (Local)" → "Task Status" for execution status

#### Method 2: Using Command Line

```powershell
# Create scheduled task using PowerShell
$action = New-ScheduledTaskAction -Execute "D:\baidu-auto\baidu-download.exe" -Argument "--auto" -WorkingDirectory "D:\baidu-auto\"
$trigger = New-ScheduledTaskTrigger -Daily -At 09:00AM
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "Baidu Auto File Transfer" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Automatic Feishu message processing and file transfer"

# Verify creation
Get-ScheduledTask -TaskName "Baidu Auto File Transfer"
```

### Schedule Recommendations

**For Production Use:**
- **Frequency**: Every 1-2 hours
- **Duration**: 24/7 operation
- **Retry Logic**: Restart every 1 minute, up to 3 attempts
- **Priority**: Normal priority

**For Testing:**
- **Frequency**: Manual execution ("Run only when user is logged on")
- **Trigger**: "At task creation/modification" or manual execution
- **Priority**: Below normal

### Monitoring Scheduled Tasks

```powershell
# Check task status
Get-ScheduledTask -TaskName "Baidu Auto File Transfer" | Get-ScheduledTaskInfo

# View task history
Get-WinEvent -LogName "Microsoft-Windows-Task Scheduler/Operational" | Where-Object {$_.Message -like "*Baidu Auto*"} | Select-Object TimeCreated, Message | Format-Table -AutoSize

# Enable task history (if disabled)
wevtutil set-log "Microsoft-Windows-Task Scheduler/Operational" /e:true
```

---

## 📊 Usage

### Running Automatic Mode

#### Manual Execution

```bash
# EXE version - Basic automatic mode
baidu-download.exe --auto

# EXE version - With verbose logging
baidu-download.exe --auto --verbose

# Python version - Basic automatic mode  
python main.py --auto

# Python version - With verbose logging
python main.py --auto --verbose
```

#### Scheduled Execution

The system will run automatically based on your Windows Task Scheduler configuration. Monitor execution through:

1. **Task Scheduler**: Check "Task Status" in Task Scheduler GUI
2. **Log Files**: Review `logs/transfer.log` for detailed execution logs
3. **Database**: Query `message_process_log` table for processing records
4. **DingTalk**: Receive notification summaries (if configured)

### Expected Behavior

#### Successful Execution Flow

1. **Initialization** (5-10 seconds)
   - Load configuration from .env file
   - Initialize Feishu client and get tenant_access_token
   - Establish database connection
   - Verify message parser

2. **Message Retrieval** (5-15 seconds)
   - Fetch recent messages from Feishu group
   - Filter messages within configured time range
   - Parse message content using regex pattern

3. **Message Processing** (varies by file count/size)
   - Check for duplicates using MD5 hash
   - Insert new messages to database
   - Process each message: download → upload → update status

4. **Notification** (2-5 seconds)
   - Generate processing summary
   - Send markdown notification to DingTalk
   - Log final status and return exit code

#### Console Output Example

```
[2026-07-24 09:00:00] INFO     ============================================================
[2026-07-24 09:00:00] INFO     百度网盘PDF文件自动传输系统启动
[2026-07-24 09:00:00] INFO     ============================================================
[2026-07-24 09:00:01] INFO     验证配置...
[2026-07-24 09:00:01] INFO     配置验证通过
[2026-07-24 09:00:01] INFO     自动模式：开始自动处理飞书消息...
[2026-07-24 09:00:02] INFO     AutoProcessor initialized successfully
[2026-07-24 09:00:02] INFO     Starting automatic message processing
[2026-07-24 09:00:05] INFO     Retrieved 15 messages from Feishu
[2026-07-24 09:00:06] INFO     Message parsed successfully: 260723
[2026-07-24 09:00:06] INFO     Inserted new message: 260723
[2026-07-24 09:00:06] INFO     Processing files for folder: 260723
[2026-07-24 09:01:20] INFO     File processing summary: total=3, success=3, failed=0
[2026-07-24 09:01:21] INFO     DingTalk notification sent successfully
[2026-07-24 09:01:21] INFO     Processing completed in 79s
```

### Exit Codes

The system returns specific exit codes for monitoring:

| Exit Code | Meaning | Action Required |
|-----------|---------|-----------------|
| 0 | Success (no critical errors) | None - operation completed |
| 1 | Critical System Failure | Investigate logs, check configuration |
| 130 | User Interrupted (Ctrl+C) | None - user cancelled operation |

**Note**: Exit code 0 does not mean all files succeeded - it means the system functioned correctly even if individual file transfers failed. Check DingTalk notifications or database for detailed results.

#### Exit Code Examples

**Exit Code 0 Scenarios:**
- ✅ All messages processed successfully
- ✅ Some messages failed but system handled errors gracefully
- ✅ No critical system errors occurred
- ✅ Processing completed even if individual file transfers failed

**Example: Exit Code 0 with Partial Failures**
```bash
# Console output shows individual failures but system exits with 0
[INFO] Processing completed with 12 success, 2 failed, 1 skipped
[INFO] DingTalk notification sent successfully
# System returns exit code 0 because overall operation completed
```

**Exit Code 1 Scenarios:**
- ❌ Configuration validation failed (missing Feishu credentials)
- ❌ Database connection failure
- ❌ Critical API authentication errors (Feishu token cannot be obtained)
- ❌ System-level exceptions that prevent any message processing

**Example: Exit Code 1 with Critical Failure**
```bash
# Console output shows critical system failure
[ERROR] Configuration error: FEISHU_APP_ID is required
# System returns exit code 1 because operation cannot proceed
```

**Exit Code 130 Scenarios:**
- ⚠️ User pressed Ctrl+C to interrupt processing
- ⚠️ Manual cancellation during operation

**Example: Exit Code 130 with User Interruption**
```bash
# Console output shows user interruption
[INFO] Processing 15 messages...
^C[INFO] User interrupt received
[INFO] User interrupted operation
# System returns exit code 130 to indicate manual cancellation
```

---

## 📈 Monitoring

### Log Files

#### Transfer Log
```bash
# View recent logs
type logs\transfer.log

# View last 50 lines
powershell Get-Content logs\transfer.log -Tail 50

# Filter for errors
findstr /i "error" logs\transfer.log

# Filter for specific date
findstr /i "2026-07-24" logs\transfer.log
```

#### Log Levels
- **INFO**: Normal operations and progress updates
- **WARNING**: Non-critical issues (duplicate messages, API retries)
- **ERROR**: Processing failures (individual message or file failures)
- **DEBUG**: Detailed diagnostic information (use --verbose)

### Database Monitoring

#### Check Processing Status

```sql
-- View recent message processing
SELECT id, folder_name, status, processing_time, created_at 
FROM message_process_log 
ORDER BY created_at DESC 
LIMIT 20;

-- Check success rate
SELECT status, COUNT(*) as count, 
    AVG(processing_time) as avg_time_ms
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY status;

-- Find stuck messages
SELECT message_hash, folder_name, status, error_message, created_at
FROM message_process_log 
WHERE status = 'processing' 
AND created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);

-- View processing trends
SELECT DATE(created_at) as date, 
    status, 
    COUNT(*) as count
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(created_at), status
ORDER BY date DESC, status;
```

#### Performance Monitoring

```sql
-- Average processing time by status
SELECT status, 
    AVG(processing_time) as avg_ms,
    MIN(processing_time) as min_ms,
    MAX(processing_time) as max_ms,
    COUNT(*) as count
FROM message_process_log
WHERE processing_time IS NOT NULL
GROUP BY status;

-- Identify slow processing
SELECT folder_name, processing_time, status, created_at
FROM message_process_log
WHERE processing_time > 180000  -- > 3 minutes
ORDER BY processing_time DESC
LIMIT 10;
```

### DingTalk Notifications

When configured, the system sends detailed notifications including:

**Success Notification Format:**
```markdown
## 处理结果摘要

- 总计处理: 15 条消息
- 成功: 12 条
- 失败: 2 条  
- 跳过: 1 条

## 成功处理

✅ 260723 - 文件传输成功
✅ 260724 - 文件传输成功
✅ 260725 - 文件传输成功

## 处理失败

❌ 260726 - File processing failed or no files transferred
❌ 260727 - Download timeout

## 处理时间

完成时间: 2026-07-24 09:01:21
```

### Health Check Script

Create `health_check.bat` for automated monitoring:

```batch
@echo off
setlocal
set DB_PASSWORD=your_actual_password_here
set ERROR_COUNT=0

echo Checking log files...
findstr /C:"ERROR" logs\transfer.log | findstr /C:"Critical" > nul
if %errorlevel% equ 0 (
    echo [WARNING] Critical errors found in logs
    set /a ERROR_COUNT+=1
)

echo Checking database...
mysql -u root -p%DB_PASSWORD% -e "SELECT COUNT(*) FROM baidu_download.message_process_log WHERE status='critical_error' AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);" | findstr /C:"0" > nul
if %errorlevel% neq 0 (
    echo [WARNING] Recent critical errors in database
    set /a ERROR_COUNT+=1
)

echo Checking scheduled task...
schtasks /query /tn "Baidu Auto File Transfer" /fo LIST | findstr /C="Status: Ready" > nul
if %errorlevel% neq 0 (
    echo [WARNING] Scheduled task may not be running
    set /a ERROR_COUNT+=1
)

if %ERROR_COUNT% gtr 0 (
    echo [ALERT] System health check failed with %ERROR_COUNT% issues
    endlocal & exit /b 1
) else (
    echo [OK] All health checks passed
    endlocal & exit /b 0
)
```

**Note**: Replace `your_actual_password_here` with your actual MySQL password from the `.env` file. For better security in production, consider using Windows Credential Manager or reading credentials directly from the `.env` file using batch file parsing.

---

## 💬 Message Format

### Expected Feishu Message Format

The automatic mode expects Feishu messages in a specific format:

```
YYMMDD：https://pan.baidu.com/s/XXXX
```

**Pattern Breakdown:**
- **YYMMDD**: 6-digit date code (e.g., 260723 = July 23, 2026)
- **：**: Chinese colon (full-width) or regular colon
- **Space**: Optional whitespace separator
- **Share Link**: Baidu netdisk share link

**Examples of Valid Messages:**
```
260723：https://pan.baidu.com/s/1ABC123xyz
260724: https://pan.baidu.com/s/1DEF456abc
260725：https://pan.baidu.com/s/1GHI789def
```

**Invalid Messages (will be skipped):**
```
Hello, this is a regular message
Invalid format: https://pan.baidu.com/s/1ABC
260723 https://pan.baidu.com/s/1ABC  (missing colon)
```

### Message Processing Logic

1. **Pattern Matching**: Uses regex `^(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)`
2. **Extraction**: Folder name from date code, share link from URL
3. **Default Code**: Uses `MESSAGE_DEFAULT_EXTRACTION_CODE` (default: 0409)
4. **Hash Generation**: MD5 hash for duplicate detection
5. **Validation**: Ensures both folder name and share link are present

### Testing Message Format

```python
# Test message parser
from src.feishu.message_parser import MessageParser

parser = MessageParser()

# Test valid messages
test_messages = [
    "260723：https://pan.baidu.com/s/1ABC123xyz",
    "260724: https://pan.baidu.com/s/1DEF456abc",
]

for msg in test_messages:
    result = parser.parse_message(msg)
    if result:
        print(f"✅ Parsed: folder={result.folder_name}, link={result.share_link}")
        print(f"   Hash: {parser.calculate_message_hash(msg)}")
    else:
        print(f"❌ Failed to parse: {msg}")
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Configuration Errors

**Issue**: `ConfigError: FEISHU_APP_ID is required`
```
[ERROR] Configuration error: FEISHU_APP_ID is required
```

**Solution**:
```bash
# 1. Check .env file exists
dir .env

# 2. Verify required variables are set
type .env | findstr "FEISHU"

# 3. Add missing configuration
notepad .env
# Ensure FEISHU_APP_ID and FEISHU_APP_SECRET are set
```

#### 2. Feishu API Failures

**Issue**: `Failed to get tenant_access_token`
```
[ERROR] API returned error: app_id is invalid
[ERROR] Failed to get tenant_access_token after 5 attempts
```

**Solution**:
```bash
# 1. Verify Feishu credentials
# Test API access manually
curl -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}'

# 2. Check app permissions in Feishu open platform
# 3. Verify chat_id is correct
# 4. Ensure IP whitelist allows access (if configured)
```

#### 3. Database Connection Issues

**Issue**: `Database connection failed`
```
[ERROR] Database connection failed: Access denied for user 'root'@'localhost'
```

**Solution**:
```bash
# 1. Test MySQL connection
mysql -u root -p -e "SELECT 1;"

# 2. Check database exists
mysql -u root -p -e "SHOW DATABASES LIKE 'baidu_download';"

# 3. Verify credentials in .env
type .env | findstr "DB_"

# 4. Grant permissions if needed
mysql -u root -p -e "GRANT ALL PRIVILEGES ON baidu_download.* TO 'root'@'localhost'; FLUSH PRIVILEGES;"
```

#### 4. Message Parsing Failures

**Issue**: Messages not being parsed
```
[WARNING] Failed to parse message: Hello everyone
[INFO] Retrieved 15 messages from Feishu
[INFO] Parsed 0 messages successfully
```

**Solution**:
```bash
# 1. Check message format matches expected pattern
# Valid: 260723：https://pan.baidu.com/s/1ABC
# Invalid: 260723 https://pan.baidu.com/s/1ABC (missing colon)

# 2. Enable verbose logging
baidu-download.exe --auto --verbose

# 3. Test message parser manually
python -c "from src.feishu.message_parser import MessageParser; p = MessageParser(); print(p.parse_message('260723：https://pan.baidu.com/s/1ABC'))"
```

#### 5. Duplicate Message Detection

**Issue**: Valid messages being skipped
```
[INFO] Skipping duplicate message: 260723
```

**Solution**:
```sql
-- Check if message was already processed
SELECT message_hash, folder_name, status, created_at
FROM message_process_log
WHERE folder_name = '260723';

-- If status is 'failed', can manually update to retry
UPDATE message_process_log
SET status = 'pending'
WHERE folder_name = '260723' AND status = 'failed';
```

#### 6. File Processing Failures

**Issue**: Files not transferring successfully
```
[ERROR] File processing failed: Download timeout
[INFO] Processing completed with failures
```

**Solution**:
```bash
# 1. Check Baidu netdisk cookies are valid
type baidu-cookies.txt

# 2. Test BaiduPCS-Go manually
BaiduPCS-Go.exe download https://pan.baidu.com/s/1ABC

# 3. Check SFTP connectivity
python test\diagnostic\diagnose_sftp.py

# 4. Verify sufficient disk space
dir

# 5. Check individual file status in database
mysql -u root -p baidu_download -e "SELECT file_name, transfer_status, error_message FROM file_transfer_log WHERE transfer_status='failed' ORDER BY created_at DESC LIMIT 10;"
```

#### 7. Windows Task Scheduler Issues

**Issue**: Scheduled task not running
```
Task Scheduler: The task failed to start
```

**Solution**:
```powershell
# 1. Check task status
Get-ScheduledTask -TaskName "Baidu Auto File Transfer" | Get-ScheduledTaskInfo

# 2. Check task history
Get-WinEvent -LogName "Microsoft-Windows-Task Scheduler/Operational" | Where-Object {$_.Message -like "*Baidu Auto*"} | Select-Object TimeCreated, Message

# 3. Test task manually
Start-ScheduledTask -TaskName "Baidu Auto File Transfer"

# 4. Verify user permissions
# Ensure task runs with account that has necessary permissions

# 5. Check working directory
# Ensure "Start in" field points to correct directory
```

#### 8. DingTalk Notification Failures

**Issue**: Notifications not being sent
```
[WARNING] Failed to send DingTalk notification
```

**Solution**:
```bash
# 1. Test webhook manually
curl -X POST "YOUR_DINGTALK_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"Test message"}}'

# 2. Check webhook URL is correct
type .env | findstr "DINGTALK"

# 3. Verify robot is not disabled in DingTalk group
# 4. Check security settings (IP whitelist, keywords)
```

### Diagnostic Commands

**Note**: The following diagnostic scripts are included in the project:
- `diagnose_mysql.py` - Available in project root for MySQL database diagnostics
- `diagnose_sftp.py` - Available in `test/diagnostic/` directory for SFTP connectivity testing

```bash
# Full system diagnostic
python diagnose_mysql.py
python test/diagnostic/diagnose_sftp.py

# Check all log levels
findstr /i "INFO\|WARNING\|ERROR" logs\transfer.log

# Test configuration validity
baidu-download.exe --auto --dry-run --verbose

# Verify database integrity
mysql -u root -p baidu_download -e "SELECT COUNT(*) as total FROM message_process_log; SELECT COUNT(*) as pending FROM message_process_log WHERE status='pending';"

# Check recent activity
mysql -u root -p baidu_download -e "SELECT status, COUNT(*) FROM message_process_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) GROUP BY status;"
```

### Getting Help

When all troubleshooting steps fail:

1. **Enable verbose logging**: Run with `--verbose` flag
2. **Collect diagnostic information**:
   - Last 100 lines of transfer log
   - Database query results
   - Task Scheduler export
   - Configuration file (with sensitive data removed)

3. **Check documentation**:
   - Main README.md
   - Deployment guide (DEPLOYMENT.md)
   - API documentation if available

4. **Contact support** with collected diagnostic information

---

## 📚 Database Schema

### message_process_log Table

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key, auto-increment |
| message_hash | VARCHAR(64) | MD5 hash of message content (unique) |
| original_message | TEXT | Original Feishu message content |
| share_link | VARCHAR(500) | Extracted Baidu share link |
| folder_name | VARCHAR(255) | Extracted folder name (date code) |
| status | ENUM | pending, processing, success, failed, critical_error |
| error_message | TEXT | Error details if processing failed |
| execution_summary_id | INT | Foreign key to execution_summary table |
| processing_time | INT | Processing duration in milliseconds |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### Status Workflow

```
pending → processing → success
                 ↘ failed
                 ↘ critical_error
```

---

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AUTOMATIC MODE WORKFLOW                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────┐
        │   Windows Task Scheduler Trigger      │
        │   (Daily / Hourly / On Demand)        │
        └───────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────┐
        │   Load Configuration (.env)           │
        │   - Feishu credentials                │
        │   - Database settings                 │
        │   - SFTP configuration                │
        └───────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────┐
        │   Initialize Components              │
        │   - Feishu client (get token)         │
        │   - Database connection               │
        │   - Message parser                     │
        │   - File processor                     │
        │   - DingTalk notifier                 │
        └───────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────┐
        │   Retrieve Feishu Messages            │
        │   - Get recent messages                │
        │   - Filter by time range               │
        └───────────────────────────────────────┘
                              │
                              ▼
        ┌───────────────────────────────────────┐
        │   Process Each Message                │
        │   - Parse content (regex)              │
        │   - Calculate MD5 hash                 │
        │   - Check for duplicates               │
        │   - Insert to database                 │
        └───────────────────────────────────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                │
              ▼                                ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ New Message     │            │ Duplicate        │
    │ Process:        │            │ Skip & Log       │
    │ - Update status │            └──────────────────┘
    │   to processing │                      
    │ - Download from │                      
    │   Baidu         │                      
    │ - Upload to SFTP│                      
    │ - Update DB     │                      
    └──────────────────┘                      
              │                                
              ▼                                
    ┌──────────────────┐                      
    │ Update Result     │                      
    │ - status: success │                      
    │   or failed      │                      
    │ - Save timing    │                      
    └──────────────────┘                      
              │                                
              ▼                                
    ┌──────────────────┐                      
    │ Send Summary     │                      
    │ - Count results  │                      
    │ - Format markdown│                      
    │ - DingTalk notify│                      
    └──────────────────┘                      
              │                                
              ▼                                
    ┌──────────────────┐                      
    │ Return Exit Code  │                      
    │ - 0 = success     │                      
    │ - 1 = critical    │                      
    └──────────────────┘                      
```

---

## 🎯 Best Practices

### Configuration Management
- **Use Environment Variables**: Store sensitive data in `.env`, never commit to version control
- **Regular Credential Updates**: Rotate Feishu app secrets and API tokens periodically
- **Backup Configuration**: Keep copy of working `.env` file for disaster recovery

### Monitoring and Alerting
- **Daily Health Checks**: Run `health_check.bat` or similar monitoring script
- **Log Rotation**: Implement log file rotation to prevent disk space issues
- **Database Maintenance**: Regular cleanup of old records (>90 days)

### Security Considerations
- **Principle of Least Privilege**: Use dedicated database users with minimal permissions
- **Network Security**: Configure firewall rules for Feishu API and SFTP endpoints
- **Credential Storage**: Consider using Windows Credential Manager for production deployments

### Performance Optimization
- **Schedule Frequency**: Adjust based on message volume (hourly for high volume, daily for low)
- **Concurrent Processing**: Monitor and adjust `CONCURRENT_UPLOADS` setting
- **Database Indexing**: Ensure proper indexes on frequently queried columns

### Error Handling Strategy
- **Graceful Degradation**: System continues processing even if individual messages fail
- **Retry Logic**: Leverage built-in exponential backoff for API calls
- **Manual Intervention**: Maintain procedure for handling `critical_error` status messages

---

## 🔗 Related Documentation

- **[README.md](README.md)** - Main project documentation
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Detailed deployment guide
- **[QUICK_START.md](docs/QUICK_START.md)** - Quick start guide
- **[.env.example](.env.example)** - Configuration template

---

**Automatic mode provides a hands-free, production-ready solution for automated Feishu message processing and file transfer operations.** 🚀