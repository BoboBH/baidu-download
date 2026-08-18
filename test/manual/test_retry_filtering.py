"""
Comprehensive tests for message retry filtering functionality.

This test suite validates the retry limit filtering in get_recent_messages_to_retry()
method, ensuring that messages that have reached the maximum retry count are properly
excluded from retry processing.

Test Cases:
1. Messages with retry_count < max_retries are returned
2. Messages with retry_count >= max_retries are excluded
3. Different MESSAGE_MAX_RETRIES values are respected
4. Time window filtering still works correctly
5. Edge cases (empty results, mixed retry counts)
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings


class MockSettings:
    """Mock Settings object for testing"""
    def __init__(self, max_message_retries=10):
        self.max_message_retries = max_message_retries


def setup_test_data():
    """Setup test database with retry count test data"""
    print("Setting up test data...")

    try:
        settings = Settings()
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=settings
        )

        # Clean up existing test data
        print("Cleaning up existing test data...")
        with repo.connection.cursor() as cursor:
            # Clean up test messages
            cursor.execute("DELETE FROM message_process_log WHERE message_hash LIKE 'test_%' OR message_hash LIKE 'test_old_%'")
            repo.connection.commit()
            # Also clean up any execution summaries created by test messages
            cursor.execute("DELETE FROM execution_summary WHERE share_link = 'https://pan.baidu.com/s/test123'")
            repo.connection.commit()

        # Create test messages with different retry counts
        test_messages = [
            # Messages that should be returned (retry_count < max_retries)
            {"hash": "test_msg_001", "retry_count": 0, "should_return": True},
            {"hash": "test_msg_002", "retry_count": 3, "should_return": True},
            {"hash": "test_msg_003", "retry_count": 5, "should_return": True},
            {"hash": "test_msg_004", "retry_count": 9, "should_return": True},  # Below limit

            # Messages that should be filtered out (retry_count >= max_retries)
            {"hash": "test_msg_005", "retry_count": 10, "should_return": False},  # Exactly at limit
            {"hash": "test_msg_006", "retry_count": 11, "should_return": False},
            {"hash": "test_msg_007", "retry_count": 15, "should_return": False},
            {"hash": "test_msg_008", "retry_count": 20, "should_return": False},
        ]

        print("Creating test messages...")
        for msg in test_messages:
            log = MessageProcessLog(
                message_hash=msg["hash"],
                original_message=f"Test message {msg['hash']}",
                share_link="https://pan.baidu.com/s/test123",
                folder_name="test_folder",
                extraction_code="1234",
                source="feishu",
                process_status="critical_error",
                error_message="Test error",
                execution_summary_id=None,
                processing_time_ms=1000,
                retry_count=msg["retry_count"]
            )

            message_id = repo.insert_message_log(log)

            # Update the retry_count directly since insert sets it to 0
            with repo.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE message_process_log SET retry_count = %s WHERE id = %s",
                    (msg["retry_count"], message_id)
                )
                repo.connection.commit()

            print(f"  Created {msg['hash']} with retry_count={msg['retry_count']}")

        repo.close()
        print("Test data setup complete!\n")
        return True

    except Exception as e:
        print(f"Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retry_filtering_basic():
    """Test basic retry filtering - messages with retry_count < max_retries are returned"""
    print("=" * 60)
    print("TEST 1: Basic Retry Filtering")
    print("=" * 60)

    try:
        settings = Settings()
        mock_settings = MockSettings(max_message_retries=10)
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=mock_settings
        )

        messages = repo.get_recent_messages_to_retry(hours=24)

        print(f"Messages returned: {len(messages)}")
        print(f"Messages: {messages}")

        # Verify results
        expected_returned = ["test_msg_001", "test_msg_002", "test_msg_003", "test_msg_004"]
        expected_excluded = ["test_msg_005", "test_msg_006", "test_msg_007", "test_msg_008"]

        for msg_hash in expected_returned:
            if msg_hash in messages:
                print(f"[PASS] {msg_hash} correctly returned (retry_count < 10)")
            else:
                print(f"[FAIL] {msg_hash} should be returned but wasn't")
                return False

        for msg_hash in expected_excluded:
            if msg_hash not in messages:
                print(f"[PASS] {msg_hash} correctly excluded (retry_count >= 10)")
            else:
                print(f"[FAIL] {msg_hash} should be excluded but was returned")
                return False

        repo.close()
        print("\n[TEST 1 PASSED]\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_max_retries():
    """Test with different MESSAGE_MAX_RETRIES values"""
    print("=" * 60)
    print("TEST 2: Different Max Retries Values")
    print("=" * 60)

    try:
        settings = Settings()

        # Test with max_retries = 5
        print("Testing with max_retries = 5...")
        mock_settings = MockSettings(max_message_retries=5)
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=mock_settings
        )

        messages = repo.get_recent_messages_to_retry(hours=24)

        # Should only return messages with retry_count < 5
        expected_returned = ["test_msg_001", "test_msg_002"]
        expected_excluded = ["test_msg_003", "test_msg_004", "test_msg_005", "test_msg_006", "test_msg_007", "test_msg_008"]

        print(f"Messages returned: {len(messages)}")
        print(f"Messages: {messages}")

        for msg_hash in expected_returned:
            if msg_hash in messages:
                print(f"[PASS] {msg_hash} correctly returned")
            else:
                print(f"[FAIL] FAIL: {msg_hash} should be returned")
                repo.close()
                return False

        for msg_hash in expected_excluded:
            if msg_hash not in messages:
                print(f"[PASS] {msg_hash} correctly excluded")
            else:
                print(f"[FAIL] FAIL: {msg_hash} should be excluded")
                repo.close()
                return False

        repo.close()

        # Test with max_retries = 15
        print("\nTesting with max_retries = 15...")
        mock_settings = MockSettings(max_message_retries=15)
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=mock_settings
        )

        messages = repo.get_recent_messages_to_retry(hours=24)

        # Should return messages with retry_count < 15
        expected_returned = ["test_msg_001", "test_msg_002", "test_msg_003", "test_msg_004",
                           "test_msg_005", "test_msg_006"]
        expected_excluded = ["test_msg_007", "test_msg_008"]

        print(f"Messages returned: {len(messages)}")

        for msg_hash in expected_returned:
            if msg_hash in messages:
                print(f"[PASS] {msg_hash} correctly returned")
            else:
                print(f"[FAIL] FAIL: {msg_hash} should be returned")
                repo.close()
                return False

        for msg_hash in expected_excluded:
            if msg_hash not in messages:
                print(f"[PASS] {msg_hash} correctly excluded")
            else:
                print(f"[FAIL] FAIL: {msg_hash} should be excluded")
                repo.close()
                return False

        repo.close()
        print("\n[PASS] TEST 2 PASSED\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_settings():
    """Test behavior when settings is None (should use default)"""
    print("=" * 60)
    print("TEST 3: No Settings Provided (Default Behavior)")
    print("=" * 60)

    try:
        settings = Settings()
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=None  # No settings provided
        )

        messages = repo.get_recent_messages_to_retry(hours=24)

        # Should use default max_retries=10
        expected_returned = ["test_msg_001", "test_msg_002", "test_msg_003", "test_msg_004"]
        expected_excluded = ["test_msg_005", "test_msg_006", "test_msg_007", "test_msg_008"]

        print(f"Messages returned with default settings: {len(messages)}")

        for msg_hash in expected_returned:
            if msg_hash in messages:
                print(f"[PASS] {msg_hash} correctly returned")
            else:
                print(f"[FAIL] FAIL: {msg_hash} should be returned")
                repo.close()
                return False

        repo.close()
        print("\n[PASS] TEST 3 PASSED\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_time_window_filtering():
    """Test that time window filtering still works correctly"""
    print("=" * 60)
    print("TEST 4: Time Window Filtering")
    print("=" * 60)

    try:
        settings = Settings()
        mock_settings = MockSettings(max_message_retries=10)
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=mock_settings
        )

        # Create an old message that should be excluded by time window
        old_log = MessageProcessLog(
            message_hash="test_old_msg",
            original_message="Old test message",
            share_link="https://pan.baidu.com/s/test123",
            folder_name="test_folder",
            extraction_code="1234",
            source="feishu",
            process_status="critical_error",
            error_message="Test error",
            execution_summary_id=None,
            processing_time_ms=1000,
            retry_count=0
        )

        message_id = repo.insert_message_log(old_log)

        # Update created_at to be 25 hours ago
        with repo.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE message_process_log SET created_at = DATE_SUB(NOW(), INTERVAL 25 HOUR) WHERE id = %s",
                (message_id,)
            )
            repo.connection.commit()

        # Get messages from last 24 hours
        messages = repo.get_recent_messages_to_retry(hours=24)

        if "test_old_msg" not in messages:
            print("[PASS] Old message correctly excluded by time window")
        else:
            print("[FAIL] FAIL: Old message should be excluded by time window")
            repo.close()
            return False

        repo.close()
        print("\n[PASS] TEST 4 PASSED\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_result():
    """Test behavior when no messages match criteria"""
    print("=" * 60)
    print("TEST 5: Empty Result Edge Case")
    print("=" * 60)

    try:
        settings = Settings()
        mock_settings = MockSettings(max_message_retries=0)  # No messages should qualify
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=mock_settings
        )

        messages = repo.get_recent_messages_to_retry(hours=24)

        if len(messages) == 0:
            print("[PASS] Empty result correctly returned")
        else:
            print(f"[FAIL] FAIL: Expected 0 messages, got {len(messages)}")
            repo.close()
            return False

        repo.close()
        print("\n[PASS] TEST 5 PASSED\n")
        return True

    except Exception as e:
        print(f"[FAIL] TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    try:
        settings = Settings()
        repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )

        with repo.connection.cursor() as cursor:
            # Clean up all test messages including old test messages
            cursor.execute("DELETE FROM message_process_log WHERE message_hash LIKE 'test_%' OR message_hash LIKE 'test_old_%'")
            # Clean up any execution summaries created by test messages
            cursor.execute("DELETE FROM execution_summary WHERE share_link = 'https://pan.baidu.com/s/test123'")
            repo.connection.commit()

        repo.close()
        print("Test data cleaned up successfully\n")
        return True

    except Exception as e:
        print(f"Error cleaning up test data: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MESSAGE RETRY FILTERING TEST SUITE")
    print("=" * 60 + "\n")

    # Setup
    if not setup_test_data():
        print("Failed to setup test data. Exiting.")
        return False

    time.sleep(1)  # Give database time to settle

    # Run tests
    results = []
    results.append(("Basic Retry Filtering", test_retry_filtering_basic()))
    results.append(("Different Max Retries Values", test_different_max_retries()))
    results.append(("No Settings Provided", test_no_settings()))
    results.append(("Time Window Filtering", test_time_window_filtering()))
    results.append(("Empty Result Edge Case", test_empty_result()))

    # Cleanup
    cleanup_test_data()

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS] PASSED" if result else "[FAIL] FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[PASS] ALL TESTS PASSED!")
        return True
    else:
        print(f"\n[FAIL] {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
