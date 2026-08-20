"""
Tests for retry manager - Task 7: 错误处理和重试机制完善

Following strict TDD: Write failing tests first
"""
import pytest
import time
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional
from src.processor.retry_manager import RetryManager, RetryConfig, RetryStatus
from src.config.settings import Settings


@dataclass
class MockDownloadResult:
    """Mock DownloadResult for testing"""
    success: bool
    error_message: Optional[str] = None
    retryable: bool = True
    error_type: Optional[str] = None


class TestRetryConfig:
    """Test retry configuration defaults and validation"""

    def test_default_config_values(self):
        """Test that default retry configuration has sensible values"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_ms == 1000
        assert config.max_delay_ms == 16000
        assert config.exponential_base == 2

    def test_custom_config_values(self):
        """Test that custom retry configuration can be set"""
        config = RetryConfig(
            max_retries=5,
            base_delay_ms=500,
            max_delay_ms=30000,
            exponential_base=3
        )
        assert config.max_retries == 5
        assert config.base_delay_ms == 500
        assert config.max_delay_ms == 30000
        assert config.exponential_base == 3

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(
            max_retries=3,
            base_delay_ms=1000,
            exponential_base=2
        )

        # Retry 1: 1000ms * 2^0 = 1000ms
        delay_1 = config.get_retry_delay(1)
        assert delay_1 == 1000

        # Retry 2: 1000ms * 2^1 = 2000ms
        delay_2 = config.get_retry_delay(2)
        assert delay_2 == 2000

        # Retry 3: 1000ms * 2^2 = 4000ms
        delay_3 = config.get_retry_delay(3)
        assert delay_3 == 4000

    def test_max_delay_capping(self):
        """Test that delays are capped at max_delay_ms"""
        config = RetryConfig(
            max_retries=10,
            base_delay_ms=1000,
            max_delay_ms=5000,
            exponential_base=2
        )

        # Calculate delay for retry 5: would be 16000ms but should cap at 5000ms
        delay_5 = config.get_retry_delay(5)
        assert delay_5 == 5000


class TestRetryManager:
    """Test retry manager functionality"""

    def test_manager_initialization(self):
        """Test that retry manager initializes correctly"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)
        assert manager.config.max_retries == 3
        assert manager.current_retry_count == 0

    def test_should_retry_with_retryable_error(self):
        """Test that retryable errors are retried"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True,
            error_type="timeout"
        )

        # Should retry on first failure
        assert manager.should_retry(result) is True
        # Record the retry attempt (increments counter)
        manager.record_retry_attempt()
        assert manager.current_retry_count == 1

    def test_should_not_retry_with_non_retryable_error(self):
        """Test that non-retryable errors are not retried"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="File not found",
            retryable=False,
            error_type="file_not_found"
        )

        # Should not retry non-retryable errors
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 0

    def test_should_not_retry_after_max_retries(self):
        """Test that retries stop after max_retries is reached"""
        config = RetryConfig(max_retries=2)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True,
            error_type="timeout"
        )

        # First retry
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()
        assert manager.current_retry_count == 1

        # Second retry
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()
        assert manager.current_retry_count == 2

        # Third attempt should not retry (max_retries=2)
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 2

    def test_should_not_retry_on_success(self):
        """Test that successful operations are not retried"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=True
        )

        # Should not retry successful operations
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 0

    def test_reset_clears_retry_count(self):
        """Test that reset clears retry counter"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True
        )

        # Perform a retry
        manager.should_retry(result)
        manager.record_retry_attempt()
        assert manager.current_retry_count == 1

        # Reset should clear counter
        manager.reset()
        assert manager.current_retry_count == 0

    def test_get_retry_status_pending(self):
        """Test retry status for pending (no retries yet)"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        status = manager.get_retry_status()
        assert status == RetryStatus.PENDING

    def test_get_retry_status_retrying(self):
        """Test retry status for retrying in progress"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True
        )

        # Perform a retry
        manager.should_retry(result)
        manager.record_retry_attempt()
        status = manager.get_retry_status()
        assert status == RetryStatus.RETRYING

    def test_get_retry_status_failed(self):
        """Test retry status when max retries exceeded"""
        config = RetryConfig(max_retries=1)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True
        )

        # Perform max retries
        manager.should_retry(result)
        manager.record_retry_attempt()
        assert manager.should_retry(result) is False

        status = manager.get_retry_status()
        assert status == RetryStatus.FAILED

    def test_calculate_delay_with_exponential_backoff(self):
        """Test that delay uses exponential backoff"""
        config = RetryConfig(
            max_retries=3,
            base_delay_ms=1000,
            exponential_base=2
        )
        manager = RetryManager(config)

        # First retry: 1000ms
        delay_1 = manager.calculate_delay()
        assert delay_1 == 1000

        # Simulate first retry
        manager.current_retry_count = 1

        # Second retry: 2000ms
        delay_2 = manager.calculate_delay()
        assert delay_2 == 2000

        # Simulate second retry
        manager.current_retry_count = 2

        # Third retry: 4000ms
        delay_3 = manager.calculate_delay()
        assert delay_3 == 4000

    def test_wait_with_backoff(self):
        """Test that wait uses exponential backoff timing"""
        config = RetryConfig(
            max_retries=3,
            base_delay_ms=100,  # Short delay for testing
            exponential_base=2
        )
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Network timeout",
            retryable=True
        )

        # First wait should be ~100ms
        start = time.time()
        manager.wait_if_needed(result)
        elapsed = time.time() - start
        assert elapsed >= 0.1  # At least 100ms

        # Record the retry attempt to increment counter for next retry
        manager.record_retry_attempt()

        # Second wait should be ~200ms
        start = time.time()
        manager.wait_if_needed(result)
        elapsed = time.time() - start
        assert elapsed >= 0.2  # At least 200ms


class TestErrorClassification:
    """Test error classification logic"""

    def test_classify_timeout_as_retryable(self):
        """Test that timeout errors are classified as retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Request timeout",
            retryable=True,
            error_type="timeout"
        )

        assert manager.is_retryable_error(result) is True

    def test_classify_network_error_as_retryable(self):
        """Test that network errors are classified as retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Connection refused",
            retryable=True,
            error_type="network_error"
        )

        assert manager.is_retryable_error(result) is True

    def test_classify_5xx_error_as_retryable(self):
        """Test that 5xx server errors are classified as retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Internal server error 500",
            retryable=True,
            error_type="server_error_500"
        )

        assert manager.is_retryable_error(result) is True

    def test_classify_429_error_as_retryable(self):
        """Test that 429 rate limit errors are classified as retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Rate limit exceeded 429",
            retryable=True,
            error_type="rate_limit"
        )

        assert manager.is_retryable_error(result) is True

    def test_classify_404_as_non_retryable(self):
        """Test that 404 not found errors are classified as non-retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="File not found 404",
            retryable=False,
            error_type="file_not_found"
        )

        assert manager.is_retryable_error(result) is False

    def test_classify_403_as_non_retryable(self):
        """Test that 403 forbidden errors are classified as non-retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Access forbidden 403",
            retryable=False,
            error_type="access_denied"
        )

        assert manager.is_retryable_error(result) is False

    def test_classify_401_as_non_retryable(self):
        """Test that 401 unauthorized errors are classified as non-retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Unauthorized 401",
            retryable=False,
            error_type="unauthorized"
        )

        assert manager.is_retryable_error(result) is False

    def test_classify_file_too_large_as_non_retryable(self):
        """Test that file too large errors are classified as non-retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="File size exceeds limit",
            retryable=False,
            error_type="file_too_large"
        )

        assert manager.is_retryable_error(result) is False

    def test_classify_io_error_as_non_retryable(self):
        """Test that IO errors are classified as non-retryable"""
        config = RetryConfig()
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="Disk write error",
            retryable=False,
            error_type="io_error"
        )

        assert manager.is_retryable_error(result) is False


class TestRetryIntegration:
    """Test retry manager integration scenarios"""

    def test_retry_workflow_success_after_retries(self):
        """Test successful retry workflow where operation succeeds after retries"""
        config = RetryConfig(max_retries=3, base_delay_ms=10)
        manager = RetryManager(config)

        # Simulate operation that fails twice then succeeds
        attempts = 0

        def mock_operation():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                return MockDownloadResult(
                    success=False,
                    error_message="Network timeout",
                    retryable=True
                )
            return MockDownloadResult(success=True)

        # First attempt fails
        result = mock_operation()
        assert manager.should_retry(result) is True
        manager.wait_if_needed(result)

        # Second attempt fails
        result = mock_operation()
        assert manager.should_retry(result) is True
        manager.wait_if_needed(result)

        # Third attempt succeeds
        result = mock_operation()
        assert manager.should_retry(result) is False

        assert attempts == 3
        assert manager.get_retry_status() == RetryStatus.COMPLETED

    def test_retry_workflow_max_retries_exceeded(self):
        """Test retry workflow where operation fails after max retries"""
        config = RetryConfig(max_retries=2, base_delay_ms=10)
        manager = RetryManager(config)

        attempts = 0

        def mock_operation():
            nonlocal attempts
            attempts += 1
            return MockDownloadResult(
                success=False,
                error_message="Network timeout",
                retryable=True
            )

        # First attempt fails, should retry
        result = mock_operation()
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()

        # Second attempt fails, should retry
        result = mock_operation()
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()

        # Third attempt fails, should NOT retry (max reached)
        result = mock_operation()
        assert manager.should_retry(result) is False

        assert attempts == 3
        assert manager.get_retry_status() == RetryStatus.FAILED

    def test_retry_workflow_non_retryable_error(self):
        """Test that non-retryable errors stop retries immediately"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        result = MockDownloadResult(
            success=False,
            error_message="File not found",
            retryable=False
        )

        # Should not retry non-retryable error
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 0
        assert manager.get_retry_status() == RetryStatus.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
