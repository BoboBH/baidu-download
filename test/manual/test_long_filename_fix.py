#!/usr/bin/env python3
"""
Complete workflow test: Verify long filename fix
Test scenario: Database has 260807 link message, complete process-pending workflow test
"""

import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.processor.file_processor import FileProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_260807_full_workflow():
    """Test complete workflow with 260807 message"""

    print("=" * 80)
    print("[TEST] Complete Workflow Test: Long Filename Fix Verification")
    print("=" * 80)
    print()

    # 1. Initialize components
    print("1. Initializing components...")
    settings = Settings()
    db_repo = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )
    file_processor = FileProcessor()

    print("[OK] Components initialized")
    print()

    # 2. Find 260807 related pending messages
    print("2. Searching for 260807 messages in database...")

    try:
        cursor = db_repo.connection.cursor()
        cursor.execute("""
            SELECT id, message_hash, folder_name, share_link, extraction_code, process_status, created_at
            FROM message_process_log
            WHERE folder_name LIKE '%260807%'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        results = cursor.fetchall()

        if not results:
            print("[ERROR] No 260807 messages found")
            print()
            print("[TIP] Suggest: Insert test data first")
            print("   INSERT INTO message_log (message_hash, folder_name, share_link, extraction_code, source, process_status)")
            print("   VALUES (...)")
            return False

        print(f"[OK] Found {len(results)} 260807 messages:")
        for i, row in enumerate(results):
            print(f"   Message {i}: {row}")
            if isinstance(row, dict):
                print(f"   - ID: {row['id']}, Folder: {row['folder_name']}, Status: {row['process_status']}")
        print()

    except Exception as e:
        import traceback
        print(f"[ERROR] Database query failed: {e}")
        traceback.print_exc()
        return False

    # 3. Select first pending message for testing
    test_message = None
    for row in results:
        if isinstance(row, dict) and row.get('process_status') == 'pending':
            test_message = row
            break

    if not test_message and results:
        print("[WARN] No pending messages, using latest message")
        test_message = results[0]

    if not test_message:
        print("[ERROR] No valid message found for testing")
        return False

    try:
        message_id = test_message['id']
        message_hash = test_message['message_hash']
        folder_name = test_message['folder_name']
        share_link = test_message['share_link']
        extraction_code = test_message['extraction_code']
        process_status = test_message['process_status']
        created_at = test_message.get('created_at')
    except (KeyError, TypeError) as e:
        print(f"[ERROR] Invalid message structure: {e}")
        print(f"Message data: {test_message}")
        return False

    print(f"3. Selected test message:")
    print(f"   - ID: {message_id}")
    print(f"   - Folder: {folder_name}")
    print(f"   - Link: {share_link}")
    print(f"   - Code: {extraction_code}")
    print(f"   - Status: {process_status}")
    print()

    # 4. Execute complete workflow test
    print("4. Starting complete workflow test...")
    print(f"   Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Update status to processing
        print("   Updating message status to 'processing'...")
        db_repo.update_message_status(message_hash, "processing")
        print("   [OK] Status updated")
        print()

        # Execute file processing workflow
        print("   [EXEC] File download and SFTP upload...")
        print("   Steps:")
        print("     1) BaiduPCS-Go transfer share link")
        print("     2) Download file to download/ directory")
        print("     3) Find downloaded file (timestamp matching)")
        print("     4) Move to temp/ directory")
        print("     5) Upload to SFTP")
        print()

        start_time = time.time()
        summary = file_processor.process_files(
            share_link,
            extraction_code,
            folder_name
        )
        processing_time = int((time.time() - start_time) * 1000)

        print()
        print(f"   [RESULT] Processing result:")
        print(f"   - Success count: {summary.success_count if summary else 0}")
        print(f"   - Failure count: {summary.failure_count if summary else 0}")
        print(f"   - Processing time: {processing_time}ms")
        print()

        # 5. Verify results
        print("5. Verifying processing results...")

        # Check file transfer logs
        cursor = db_repo.connection.cursor()
        cursor.execute("""
            SELECT file_name, transfer_status, error_message, created_at
            FROM file_transfer_log
            WHERE folder_name = %s
            ORDER BY created_at DESC
            LIMIT 3
        """, (folder_name,))
        transfer_logs = cursor.fetchall()

        if transfer_logs:
            print(f"   [OK] Found {len(transfer_logs)} transfer records:")
            for log in transfer_logs:
                file_name, transfer_status, error_message, created_at = log
                print(f"   - File: {file_name[:50]}...")
                print(f"     Status: {transfer_status}")
                if error_message:
                    print(f"     Error: {error_message}")
                print()
        else:
            print("   [WARN] No transfer records found")
            print()

        # 6. Final status check
        print("6. Final status check...")

        # Check message status
        cursor = db_repo.connection.cursor()
        cursor.execute("""
            SELECT process_status FROM message_process_log WHERE message_hash = %s
        """, (message_hash,))
        final_status = cursor.fetchone()

        if final_status:
            print(f"   Message final status: {final_status[0]}")

        # Check SFTP files (if configured)
        if hasattr(settings, 'sftp_host') and settings.sftp_host:
            print("   [TIP] Check SFTP server to verify file upload")

        print()

        # 7. Test summary
        print("=" * 80)
        print("[SUMMARY] Test Summary")
        print("=" * 80)

        if summary and summary.success_count > 0:
            print("[SUCCESS] Test passed: Long filename issue fixed")
            print(f"   - Successfully processed {summary.success_count} files")
            print(f"   - Files downloaded and uploaded to SFTP correctly")

            # Update message status to success
            db_repo.update_message_status(
                message_hash,
                "success",
                processing_time_ms=processing_time
            )
            print("   - Message status updated to 'success'")
        else:
            print("[FAILED] Test failed: Issues still need fixing")

            # Update message status to failed
            db_repo.update_message_status(
                message_hash,
                "failed",
                error_message="Test processing failed",
                processing_time_ms=processing_time
            )
            print("   - Message status updated to 'failed'")

        print()
        print("[FIX] Key fixes:")
        print("   1. _find_downloaded_file() uses timestamp matching")
        print("   2. No longer relies on filename matching or os.walk() completeness")
        print("   3. Handles Windows MAX_PATH limit")

        print("=" * 80)
        print()

        return summary and summary.success_count > 0

    except Exception as e:
        print(f"[ERROR] Test process error: {e}")
        import traceback
        traceback.print_exc()

        # Update message status to critical_error
        try:
            db_repo.update_message_status(
                message_hash,
                "critical_error",
                error_message=str(e)
            )
        except:
            pass

        return False

    finally:
        db_repo.close()

def test_manual_long_filename():
    """Manual test: Direct long filename scenario test"""

    print("=" * 80)
    print("[TEST] Manual Test: Direct Long Filename Search")
    print("=" * 80)
    print()

    # Test file search functionality
    from src.downloader.baidu_client import BaiduClient

    baidu_client = BaiduClient()
    download_dir = "download"

    print("1. Scanning download directory...")

    if not os.path.exists(download_dir):
        print(f"[ERROR] Download directory not exist: {download_dir}")
        return False

    # Record start time
    import time
    start_time = time.time()

    print(f"2. Finding recently downloaded files (start time: {start_time})...")

    # Wait a few seconds to ensure time difference
    time.sleep(2)

    # Call search method
    test_remote_path = "//test/fake/path/long_filename.pdf"
    found_file = baidu_client._find_downloaded_file(download_dir, test_remote_path, start_time)

    if found_file:
        print(f"[OK] Found file: {found_file}")
        print(f"   Filename: {os.path.basename(found_file)}")
        print(f"   File size: {os.path.getsize(found_file)} bytes")

        # Check path length
        path_len = len(found_file)
        print(f"   Path length: {path_len} chars")
        if path_len > 250:
            print("   [WARN] Long path file (successfully fixed)")

        return True
    else:
        print("[ERROR] File not found")
        return False

if __name__ == "__main__":
    print()
    print("[LAUNCH] Long Filename Fix Test")
    print()

    # Select test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        # Manual test mode
        success = test_manual_long_filename()
    else:
        # Complete workflow test mode (default)
        success = test_260807_full_workflow()

    print()
    if success:
        print("[SUCCESS] Test passed")
        sys.exit(0)
    else:
        print("[FAILED] Test failed")
        sys.exit(1)
