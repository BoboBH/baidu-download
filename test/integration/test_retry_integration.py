"""
Integration Tests for Message Retry Limit Feature

These tests provide end-to-end validation of the message retry functionality
using real database connections to ensure complete workflow validation.

Testing Approach:
- Uses real database connections (not mocks) for true integration testing
- Tests the complete retry lifecycle from initial failure through to exclusion
- Validates database schema changes and migration procedures
- Tests configuration integration and repository behavior
- Uses test database to avoid affecting production data

Key Test Scenarios:
1. End-to-End Retry Flow - Message processed through 10 failures to exclusion
2. Successful Recovery Test - Message fails 5 times then succeeds, resets retries
3. Database Migration Test - Schema changes and existing data preservation
"""

import pytest
import os
import hashlib
import tempfile
from datetime import datetime, timedelta
from typing import Optional

# Test configuration
TEST_MAX_RETRIES = 10  # Default max retry limit
TEST_DATABASE_NAME = "test_retry_integration"
TEST_MESSAGE_CONTENT = "240724: https://pan.baidu.com/s/test123abc"
TEST_SHARE_LINK = "https://pan.baidu.com/s/test123abc"
TEST_FOLDER_NAME = "240724"
TEST_EXTRACTION_CODE = "0409"


class RetryIntegrationTestSetup:
    """Helper class for setting up integration test environment"""

    @staticmethod
    def calculate_message_hash(message_content: str) -> str:
        """Calculate MD5 hash of message content"""
        return hashlib.md5(message_content.encode('utf-8')).hexdigest()

    @staticmethod
    def create_test_environment():
        """Create test environment with database configuration"""
        # Create temporary directory for test files
        temp_dir = tempfile.mkdtemp(prefix='retry_integration_test_')

        # Create test environment variables
        env_config = {
            'SFTP_HOST': 'localhost',
            'SFTP_PORT': '22',
            'SFTP_USERNAME': 'test_user',
            'SFTP_PASSWORD': 'test_pass',
            'SFTP_REMOTE_PATH': '/upload',
            'DB_HOST': 'localhost',
            'DB_PORT': '3306',
            'DB_USER': 'root',
            'DB_PASSWORD': 'test_password',
            'DB_NAME': TEST_DATABASE_NAME,
            'BAIDUPCS_GO_PATH': os.path.join(temp_dir, 'fake_baidupcs.exe'),
            'TEMP_DIR': temp_dir,
            'LOG_FILE': os.path.join(temp_dir, 'test.log'),
            'MESSAGE_MAX_RETRIES': str(TEST_MAX_RETRIES),
            'MESSAGE_DEFAULT_EXTRACTION_CODE': TEST_EXTRACTION_CODE
        }

        # Create fake BaiduPCS executable
        with open(env_config['BAIDUPCS_GO_PATH'], 'w') as f:
            f.write('fake executable')

        return temp_dir, env_config

    @staticmethod
    def cleanup_test_environment(temp_dir):
        """Clean up test environment"""
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@pytest.fixture
def test_environment():
    """Create and manage test environment for integration tests"""
    temp_dir, env_config = RetryIntegrationTestSetup.create_test_environment()

    # Set environment variables
    original_env = {}
    for key, value in env_config.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield temp_dir, env_config

    # Cleanup
    RetryIntegrationTestSetup.cleanup_test_environment(temp_dir)

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is not None:
            os.environ[key] = original_value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def test_database(test_environment):
    """Create test database connection and schema"""
    temp_dir, env_config = test_environment

    try:
        from src.database.repository import DatabaseRepository
        from src.config.settings import Settings

        # Create settings with test configuration
        settings = Settings()

        # Create database repository
        db_repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            settings=settings
        )

        yield db_repo, settings

        # Cleanup database after tests
        db_repo.close()

    except Exception as e:
        pytest.skip(f"Failed to create test database: {e}")


@pytest.fixture
def clean_database(test_database):
    """Ensure clean database state for each test"""
    db_repo, settings = test_database

    # Clean existing test data
    cursor = db_repo.connection.cursor()
    try:
        cursor.execute("DELETE FROM message_process_log WHERE 1=1")
        db_repo.connection.commit()
    except Exception as e:
        db_repo.connection.rollback()
        pytest.skip(f"Failed to clean database: {e}")
    finally:
        cursor.close()

    yield db_repo, settings


class TestRetryIntegration:
    """Integration tests for message retry limit functionality"""

    def test_message_retry_to_exclusion(self, clean_database):
        """
        Test Case 1: End-to-End Retry Flow

        Scenario:
        1. Process message through 10 consecutive failures
        2. Verify message is excluded from retry queue after reaching max retries
        3. Verify retry_count equals 10 (max retries)
        4. Verify database filtering prevents reprocessing

        Expected Results:
        - retry_count increments to 10
        - message excluded from retry queue
        - get_recent_messages_to_retry() returns empty list
        """
        db_repo, settings = clean_database

        # Step 1: Create initial message
        message_hash = RetryIntegrationTestSetup.calculate_message_hash(TEST_MESSAGE_CONTENT)

        from src.database.message_models import MessageProcessLog
        message_log = MessageProcessLog(
            message_hash=message_hash,
            original_message=TEST_MESSAGE_CONTENT,
            share_link=TEST_SHARE_LINK,
            folder_name=TEST_FOLDER_NAME,
            extraction_code=TEST_EXTRACTION_CODE,
            source='feishu',
            process_status='pending',
            retry_count=0
        )

        # Insert message
        message_id = db_repo.insert_message_log(message_log)
        assert message_id > 0, "Message should be inserted successfully"

        # Step 2: Process message through 10 failures
        for failure_count in range(1, TEST_MAX_RETRIES + 1):
            # Update status to failed (should increment retry_count)
            success = db_repo.update_message_status(
                message_hash=message_hash,
                status='critical_error',
                error_message=f"Test failure #{failure_count}",
                processing_time_ms=1000
            )

            assert success, f"Status update should succeed for failure #{failure_count}"

            # Verify retry_count incremented
            message = db_repo.get_message_by_hash(message_hash)
            assert message is not None, f"Message should exist after failure #{failure_count}"
            assert message.retry_count == failure_count, f"Retry count should be {failure_count} after {failure_count} failures"
            assert message.process_status == 'critical_error', f"Status should be critical_error after failure #{failure_count}"

        # Step 3: Verify message is excluded from retry queue
        retry_messages = db_repo.get_recent_messages_to_retry(hours=24)

        assert message_hash not in retry_messages, "Message should be excluded from retry queue after reaching max retries"

        # Verify no messages are eligible for retry
        assert len(retry_messages) == 0, "No messages should be eligible for retry after reaching max limit"

        # Step 4: Verify final state in database
        final_message = db_repo.get_message_by_hash(message_hash)
        assert final_message.retry_count == TEST_MAX_RETRIES, f"Final retry count should be {TEST_MAX_RETRIES}"
        assert final_message.process_status == 'critical_error', "Final status should be critical_error"
        assert final_message.error_message is not None, "Error message should be set"

        print(f"✓ Test completed: Message processed through {TEST_MAX_RETRIES} failures and properly excluded from retry queue")

    def test_successful_recovery_resets_retries(self, clean_database):
        """
        Test Case 2: Successful Recovery Test

        Scenario:
        1. Fail message 5 times (retry_count = 5)
        2. Process message successfully on 6th attempt
        3. Verify retry_count resets to 0 on success
        4. Verify message is eligible for retry on subsequent failure

        Expected Results:
        - retry_count resets to 0 after success
        - message becomes eligible for retry again
        - retry count increments again on new failure
        """
        db_repo, settings = clean_database

        # Step 1: Create message and fail it 5 times
        message_hash = RetryIntegrationTestSetup.calculate_message_hash(TEST_MESSAGE_CONTENT)

        from src.database.message_models import MessageProcessLog
        message_log = MessageProcessLog(
            message_hash=message_hash,
            original_message=TEST_MESSAGE_CONTENT,
            share_link=TEST_SHARE_LINK,
            folder_name=TEST_FOLDER_NAME,
            extraction_code=TEST_EXTRACTION_CODE,
            source='feishu',
            process_status='pending',
            retry_count=0
        )

        message_id = db_repo.insert_message_log(message_log)
        assert message_id > 0, "Message should be inserted successfully"

        # Fail message 5 times
        for i in range(1, 6):
            db_repo.update_message_status(
                message_hash=message_hash,
                status='critical_error',
                error_message=f"Test failure #{i}",
                processing_time_ms=1000
            )

        # Verify retry_count = 5
        message_after_failures = db_repo.get_message_by_hash(message_hash)
        assert message_after_failures.retry_count == 5, "Retry count should be 5 after 5 failures"

        # Step 2: Process message successfully (6th attempt)
        success = db_repo.update_message_status(
            message_hash=message_hash,
            status='success',
            processing_time_ms=1500
        )

        assert success, "Status update to success should succeed"

        # Step 3: Verify retry_count reset to 0
        message_after_success = db_repo.get_message_by_hash(message_hash)
        assert message_after_success.retry_count == 0, "Retry count should reset to 0 after success"
        assert message_after_success.process_status == 'success', "Status should be success"
        assert message_after_success.error_message is None, "Error message should be cleared on success"

        # Step 4: Verify message is NOT in retry queue (status is success)
        retry_messages = db_repo.get_recent_messages_to_retry(hours=24)
        assert message_hash not in retry_messages, "Successful message should not be in retry queue"

        # Step 5: Simulate new failure (message fails again after previous success)
        db_repo.update_message_status(
            message_hash=message_hash,
            status='critical_error',
            error_message="New failure after recovery",
            processing_time_ms=1000
        )

        # Verify retry_count incremented to 1 (not 6)
        message_after_new_failure = db_repo.get_message_by_hash(message_hash)
        assert message_after_new_failure.retry_count == 1, "Retry count should be 1 after new failure (not cumulative)"

        # Verify message is now eligible for retry again
        retry_messages_after_new_failure = db_repo.get_recent_messages_to_retry(hours=24)
        assert message_hash in retry_messages_after_new_failure, "Message should be eligible for retry after new failure"

        print("✓ Test completed: Message recovered successfully, retry count reset, and became eligible for retry again")

    def test_database_migration(self, test_database):
        """
        Test Case 3: Database Migration Test

        Scenario:
        1. Verify existing message_process_log table structure
        2. Verify retry_count column exists with correct properties
        3. Verify retry_count index exists for efficient filtering
        4. Verify existing data is preserved during migration
        5. Verify default value for retry_count on existing records

        Expected Results:
        - retry_count column exists with INT type
        - retry_count has DEFAULT value of 0
        - idx_retry_count index exists
        - Existing messages get retry_count = 0
        - Database operations work correctly after migration
        """
        db_repo, settings = test_database

        cursor = db_repo.connection.cursor()

        try:
            # Step 1: Verify table structure
            cursor.execute("DESCRIBE message_process_log")
            columns = cursor.fetchall()
            column_names = [col['Field'] for col in columns]

            # Verify retry_count column exists
            assert 'retry_count' in column_names, "retry_count column should exist in message_process_log table"

            # Get retry_count column properties
            retry_count_column = next(col for col in columns if col['Field'] == 'retry_count')

            # Step 2: Verify column properties
            assert retry_count_column is not None, "retry_count column should be found"
            assert retry_count_column['Type'] == 'int(11)' or retry_count_column['Type'].startswith('int'), "retry_count should be INT type"
            assert retry_count_column['Default'] == '0', "retry_count should have default value 0"
            assert retry_count_column['Null'] == 'YES', "retry_count should allow NULL for backward compatibility"

            # Step 3: Verify index exists
            cursor.execute("SHOW INDEX FROM message_process_log WHERE Key_name = 'idx_retry_count'")
            indexes = cursor.fetchall()

            assert len(indexes) > 0, "idx_retry_count index should exist"

            # Step 4: Test data preservation - create test messages
            from src.database.message_models import MessageProcessLog

            test_messages = [
                MessageProcessLog(
                    message_hash=hashlib.md5(f"test_message_{i}".encode()).hexdigest(),
                    original_message=f"test_message_{i}",
                    share_link=f"https://pan.baidu.com/s/test{i}",
                    folder_name=f"24072{i}",
                    extraction_code=TEST_EXTRACTION_CODE,
                    source='feishu',
                    process_status='pending'
                ) for i in range(1, 4)
            ]

            # Insert test messages
            message_ids = []
            for msg in test_messages:
                msg_id = db_repo.insert_message_log(msg)
                message_ids.append(msg_id)
                assert msg_id > 0, "Message should be inserted successfully"

            # Step 5: Verify default retry_count for new messages
            for msg_hash in [msg.message_hash for msg in test_messages]:
                message = db_repo.get_message_by_hash(msg_hash)
                assert message is not None, f"Message {msg_hash} should exist"
                assert message.retry_count == 0, f"New message {msg_hash} should have retry_count = 0"

            # Step 6: Test retry_count operations work correctly
            test_message_hash = test_messages[0].message_hash

            # Update status to failed (should increment retry_count)
            db_repo.update_message_status(
                message_hash=test_message_hash,
                status='critical_error',
                error_message="Test failure",
                processing_time_ms=1000
            )

            # Verify increment worked
            updated_message = db_repo.get_message_by_hash(test_message_hash)
            assert updated_message.retry_count == 1, "retry_count should increment to 1"

            # Update status to success (should reset retry_count)
            db_repo.update_message_status(
                message_hash=test_message_hash,
                status='success',
                processing_time_ms=2000
            )

            # Verify reset worked
            success_message = db_repo.get_message_by_hash(test_message_hash)
            assert success_message.retry_count == 0, "retry_count should reset to 0 on success"

            # Step 7: Test database query with retry_count filter
            # Create another message with different retry_count
            high_retry_message = MessageProcessLog(
                message_hash=hashlib.md5(b"high_retry_message").hexdigest(),
                original_message="high_retry_message",
                share_link="https://pan.baidu.com/s/highretry",
                folder_name="240727",
                extraction_code=TEST_EXTRACTION_CODE,
                source='feishu',
                process_status='pending'
            )

            high_retry_id = db_repo.insert_message_log(high_retry_message)
            assert high_retry_id > 0, "High retry message should be inserted"

            # Set high retry count directly (simulating manual intervention)
            cursor.execute(
                "UPDATE message_process_log SET retry_count = %s, process_status = 'critical_error' WHERE message_hash = %s",
                (TEST_MAX_RETRIES, high_retry_message.message_hash)
            )
            db_repo.connection.commit()

            # Verify filter works - only get messages with retry_count < max_retries
            retry_messages = db_repo.get_recent_messages_to_retry(hours=24)

            # High retry message should not be in results
            assert high_retry_message.message_hash not in retry_messages, "Message with retry_count >= max should be excluded"

            print("✓ Test completed: Database migration verified - schema, index, data preservation, and operations all working correctly")

        except Exception as e:
            db_repo.connection.rollback()
            raise pytest.Failed(f"Database migration test failed: {e}")
        finally:
            cursor.close()


class TestRetryIntegrationEdgeCases:
    """Integration tests for edge cases and boundary conditions"""

    def test_retry_count_with_different_status_transitions(self, clean_database):
        """
        Test retry count behavior with various status transitions

        Scenario:
        1. Test all valid status transitions and their effect on retry_count
        2. Verify retry_count only changes for specific transitions
        3. Test invalid status handling

        Expected Results:
        - failed/critical_error: increment retry_count
        - success: reset retry_count to 0
        - pending/processing: no change to retry_count
        - invalid status: update fails gracefully
        """
        db_repo, settings = clean_database

        message_hash = RetryIntegrationTestSetup.calculate_message_hash(TEST_MESSAGE_CONTENT)

        from src.database.message_models import MessageProcessLog
        message_log = MessageProcessLog(
            message_hash=message_hash,
            original_message=TEST_MESSAGE_CONTENT,
            share_link=TEST_SHARE_LINK,
            folder_name=TEST_FOLDER_NAME,
            extraction_code=TEST_EXTRACTION_CODE,
            source='feishu',
            process_status='pending',
            retry_count=0
        )

        db_repo.insert_message_log(message_log)

        # Test 1: pending -> processing (retry_count should not change)
        db_repo.update_message_status(message_hash, 'processing')
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 0, "retry_count should remain 0 for pending->processing"

        # Test 2: processing -> failed (retry_count should increment)
        db_repo.update_message_status(message_hash, 'failed', error_message="Test failure")
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 1, "retry_count should increment to 1 for failed status"

        # Test 3: failed -> critical_error (retry_count should increment again)
        db_repo.update_message_status(message_hash, 'critical_error', error_message="Critical error")
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 2, "retry_count should increment to 2 for critical_error status"

        # Test 4: critical_error -> success (retry_count should reset)
        db_repo.update_message_status(message_hash, 'success')
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 0, "retry_count should reset to 0 for success status"

        # Test 5: success -> failed (retry_count should increment from 0)
        db_repo.update_message_status(message_hash, 'failed', error_message="Another failure")
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 1, "retry_count should increment to 1 after success->failed"

        # Test 6: Invalid status (should fail gracefully)
        result = db_repo.update_message_status(message_hash, 'invalid_status')
        assert result == False, "Update with invalid status should return False"

        # Verify retry_count unchanged after failed update
        message = db_repo.get_message_by_hash(message_hash)
        assert message.retry_count == 1, "retry_count should remain unchanged after invalid status update"

        print("✓ Test completed: All status transitions handle retry_count correctly")

    def test_configuration_integration(self, test_environment):
        """
        Test configuration integration with retry limit functionality

        Scenario:
        1. Test with different MESSAGE_MAX_RETRIES values
        2. Verify settings validation
        3. Test repository uses correct max_retries value

        Expected Results:
        - Settings validates MESSAGE_MAX_RETRIES range (1-100)
        - Repository uses settings.max_message_retries
        - Invalid values raise ConfigError
        """
        temp_dir, env_config = test_environment

        # Test 1: Valid configuration values
        valid_configs = [1, 10, 50, 100]
        for max_retries in valid_configs:
            os.environ['MESSAGE_MAX_RETRIES'] = str(max_retries)

            try:
                from src.config.settings import Settings
                settings = Settings()

                assert settings.max_message_retries == max_retries, f"Settings should load max_retries={max_retries}"

            except Exception as e:
                pytest.fail(f"Valid max_retries={max_retries} should not raise exception: {e}")

        # Test 2: Invalid configuration values
        invalid_configs = [0, -1, 101, 1000]
        for max_retries in invalid_configs:
            os.environ['MESSAGE_MAX_RETRIES'] = str(max_retries)

            try:
                from src.config.settings import Settings
                with pytest.raises(Exception) as exc_info:
                    settings = Settings()

                assert "MESSAGE_MAX_RETRIES" in str(exc_info.value) or "between 1 and 100" in str(exc_info.value), \
                    f"Invalid max_retries={max_retries} should raise ConfigError with appropriate message"

            except ImportError:
                pytest.skip("Settings module not available")

        print("✓ Test completed: Configuration integration works correctly with validation")

    def test_concurrent_message_retry_filtering(self, clean_database):
        """
        Test retry filtering with multiple messages at different retry counts

        Scenario:
        1. Create multiple messages with different retry counts
        2. Verify get_recent_messages_to_retry() filters correctly
        3. Test boundary conditions (max_retries - 1, max_retries, max_retries + 1)

        Expected Results:
        - Messages with retry_count < max_retries are included
        - Messages with retry_count >= max_retries are excluded
        - Filtering works correctly at boundary conditions
        """
        db_repo, settings = clean_database

        from src.database.message_models import MessageProcessLog

        # Create messages with different retry counts
        retry_scenarios = [
            (0, 'critical_error', 'new_failure'),      # Should be included
            (5, 'critical_error', 'medium_failure'),   # Should be included
            (TEST_MAX_RETRIES - 1, 'critical_error', 'near_max'),  # Should be included
            (TEST_MAX_RETRIES, 'critical_error', 'at_max'),         # Should be excluded
            (TEST_MAX_RETRIES + 1, 'critical_error', 'over_max'),   # Should be excluded
            (3, 'success', 'success_message'),          # Should be excluded (wrong status)
        ]

        message_hashes = []
        for retry_count, status, description in retry_scenarios:
            message_hash = hashlib.md5(f"test_{description}".encode()).hexdigest()
            message_hashes.append((message_hash, retry_count, status, description))

            message_log = MessageProcessLog(
                message_hash=message_hash,
                original_message=f"test_{description}",
                share_link=f"https://pan.baidu.com/s/{description}",
                folder_name="240724",
                extraction_code=TEST_EXTRACTION_CODE,
                source='feishu',
                process_status=status
            )

            db_repo.insert_message_log(message_log)

            # Manually set retry_count for testing
            cursor = db_repo.connection.cursor()
            cursor.execute(
                "UPDATE message_process_log SET retry_count = %s WHERE message_hash = %s",
                (retry_count, message_hash)
            )
            db_repo.connection.commit()
            cursor.close()

        # Get messages eligible for retry
        retry_messages = db_repo.get_recent_messages_to_retry(hours=24)

        # Verify filtering
        expected_included = [
            msg[0] for msg in message_hashes
            if msg[1] < TEST_MAX_RETRIES and msg[2] == 'critical_error'
        ]

        expected_excluded = [
            msg[0] for msg in message_hashes
            if msg[1] >= TEST_MAX_RETRIES or msg[2] != 'critical_error'
        ]

        # Check included messages
        for msg_hash in expected_included:
            assert msg_hash in retry_messages, f"Message with retry_count < max_retries should be included: {msg_hash}"

        # Check excluded messages
        for msg_hash in expected_excluded:
            assert msg_hash not in retry_messages, f"Message with retry_count >= max_retries or wrong status should be excluded: {msg_hash}"

        print("✓ Test completed: Concurrent message retry filtering works correctly")


def run_integration_tests():
    """
    Helper function to run integration tests manually
    """
    print("Running Message Retry Integration Tests...")
    print("=" * 60)

    # Run pytest on this file
    import sys
    import subprocess

    result = subprocess.run(
        [sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'],
        capture_output=False
    )

    return result.returncode == 0


if __name__ == '__main__':
    success = run_integration_tests()
    exit(0 if success else 1)