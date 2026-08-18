"""
Test script to verify retry count management in update_message_status()
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings

def test_retry_count_management():
    """Test retry count management logic"""
    print("Testing retry count management...")

    # Get database config
    config = Settings()

    # Create repository instance
    repo = DatabaseRepository(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database='baidu_download_test'
    )

    try:
        # Clean up any existing test data first
        print("0. Cleaning up existing test data...")
        import random
        test_hash = f"test_retry_{random.randint(10000, 99999)}"

        # Create test message with unique hash
        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test message for retry count",
            share_link="https://test.com/s/1",
            folder_name="test_folder",
            extraction_code="1234",
            source="feishu",  # Use valid source value
            process_status="pending",
            retry_count=0
        )

        # Insert test message
        print("1. Inserting test message with retry_count=0...")
        message_id = repo.insert_message_log(test_message)
        print(f"   Message inserted with ID: {message_id}")

        # Verify initial state
        msg = repo.get_message_by_hash(test_hash)
        print(f"   Initial retry_count: {msg.retry_count}")
        assert msg.retry_count == 0, "Initial retry_count should be 0"

        # Test 1: Update to 'pending' - retry_count should remain 0
        print("\n2. Updating status to 'pending' (retry_count should remain 0)...")
        result = repo.update_message_status(test_hash, "pending", processing_time_ms=100)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After 'pending': retry_count = {msg.retry_count}")
        assert msg.retry_count == 0, "retry_count should remain 0 for 'pending'"

        # Test 2: Update to 'processing' - retry_count should remain 0
        print("\n3. Updating status to 'processing' (retry_count should remain 0)...")
        result = repo.update_message_status(test_hash, "processing", processing_time_ms=100)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After 'processing': retry_count = {msg.retry_count}")
        assert msg.retry_count == 0, "retry_count should remain 0 for 'processing'"

        # Test 3: Update to 'failed' - retry_count should increment to 1
        print("\n4. Updating status to 'failed' (retry_count should increment to 1)...")
        result = repo.update_message_status(test_hash, "failed", error_message="Test error", processing_time_ms=200)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After first 'failed': retry_count = {msg.retry_count}")
        assert msg.retry_count == 1, "retry_count should be 1 after first failure"

        # Test 4: Update to 'critical_error' - retry_count should increment to 2
        print("\n5. Updating status to 'critical_error' (retry_count should increment to 2)...")
        result = repo.update_message_status(test_hash, "critical_error", error_message="Critical error", processing_time_ms=300)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After 'critical_error': retry_count = {msg.retry_count}")
        assert msg.retry_count == 2, "retry_count should be 2 after second failure"

        # Test 5: Update to 'success' - retry_count should reset to 0
        print("\n6. Updating status to 'success' (retry_count should reset to 0)...")
        result = repo.update_message_status(test_hash, "success", processing_time_ms=400)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After 'success': retry_count = {msg.retry_count}")
        assert msg.retry_count == 0, "retry_count should be reset to 0 after success"

        # Test 6: Another failure - retry_count should increment to 1 again
        print("\n7. Updating status to 'failed' again (retry_count should increment to 1)...")
        result = repo.update_message_status(test_hash, "failed", error_message="Another error", processing_time_ms=500)
        assert result, "Update should return True"
        msg = repo.get_message_by_hash(test_hash)
        print(f"   After another 'failed': retry_count = {msg.retry_count}")
        assert msg.retry_count == 1, "retry_count should be 1 after failure following success"

        # Test 7: Test invalid status value (should return False)
        print("\n8. Testing invalid status value (should return False)...")
        result = repo.update_message_status(test_hash, "invalid_status", processing_time_ms=100)
        assert result == False, "Invalid status should return False"
        print("   Invalid status correctly rejected")

        # Test 8: Test non-existent message_hash (should return False)
        print("\n9. Testing non-existent message_hash (should return False)...")
        result = repo.update_message_status("nonexistent_message", "processing", processing_time_ms=100)
        assert result == False, "Non-existent message should return False"
        print("   Non-existent message_hash correctly handled")

        # Test 9: Test error_message clearing behavior for pending/processing
        print("\n10. Testing error_message clearing for 'pending' status...")
        # First set a failed state with error
        repo.update_message_status(test_hash, "failed", error_message="Error before clearing", processing_time_ms=100)
        msg = repo.get_message_by_hash(test_hash)
        assert msg.error_message == "Error before clearing", "Error message should be set"
        # Now clear with pending
        repo.update_message_status(test_hash, "pending", processing_time_ms=100)
        msg = repo.get_message_by_hash(test_hash)
        assert msg.error_message is None, "Error message should be cleared for pending status"
        print("   Error message correctly cleared for 'pending'")

        # Test 10: Test error_message clearing for processing
        print("\n11. Testing error_message clearing for 'processing' status...")
        repo.update_message_status(test_hash, "failed", error_message="Another error", processing_time_ms=100)
        msg = repo.get_message_by_hash(test_hash)
        assert msg.error_message == "Another error", "Error message should be set"
        # Now clear with processing
        repo.update_message_status(test_hash, "processing", processing_time_ms=100)
        msg = repo.get_message_by_hash(test_hash)
        assert msg.error_message is None, "Error message should be cleared for processing status"
        print("   Error message correctly cleared for 'processing'")

        print("\n[PASS] All tests passed!")
        return True

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        repo.close()

if __name__ == "__main__":
    success = test_retry_count_management()
    sys.exit(0 if success else 1)
