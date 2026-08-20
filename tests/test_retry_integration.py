"""
Integration tests for retry manager - Task 7: 错误处理和重试机制完善

Tests real-world scenarios without mocks to ensure retry mechanism works correctly
"""
import pytest
import time
from unittest.mock import Mock
from src.processor.retry_manager import RetryManager, RetryConfig, RetryStatus
from src.config.settings import Settings
from src.processor.auto_processor import AutoProcessor


class TestAutoProcessorRetryIntegration:
    """Test retry manager integration with AutoProcessor"""

    def test_auto_processor_retry_manager_initialization(self):
        """Test that AutoProcessor initializes retry manager correctly"""
        settings = Settings()
        processor = AutoProcessor(settings=settings)

        # Verify retry manager is initialized
        assert processor.retry_manager is not None
        assert processor.retry_manager.config.max_retries == settings.retry_max_attempts
        assert processor.retry_manager.config.base_delay_ms == settings.retry_base_delay_ms
        assert processor.retry_manager.config.max_delay_ms == settings.retry_max_delay_ms

    def test_auto_processor_exception_classification(self):
        """Test that AutoProcessor correctly classifies exceptions as retryable/non-retryable"""
        settings = Settings()
        processor = AutoProcessor(settings=settings)

        # Test retryable exceptions
        retryable_exceptions = [
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("500 Internal Server Error"),
            Exception("429 Rate limit exceeded"),
            Exception("Temporarily unavailable"),
        ]

        for exc in retryable_exceptions:
            assert processor._is_exception_retryable(exc) is True, f"Should be retryable: {exc}"

        # Test non-retryable exceptions
        non_retryable_exceptions = [
            Exception("404 Not Found"),
            Exception("403 Forbidden"),
            Exception("401 Unauthorized"),
            Exception("File too large"),
            Exception("Invalid parameter"),
            Exception("Permission denied"),
        ]

        for exc in non_retryable_exceptions:
            assert processor._is_exception_retryable(exc) is False, f"Should not be retryable: {exc}"

    def test_auto_processor_default_retryable(self):
        """Test that unknown exceptions default to retryable"""
        settings = Settings()
        processor = AutoProcessor(settings=settings)

        # Unknown exception should default to retryable
        unknown_exception = Exception("Unknown error occurred")
        assert processor._is_exception_retryable(unknown_exception) is True


class TestRetryManagerRealScenarios:
    """Test retry manager with real-world scenarios"""

    def test_network_timeout_scenario(self):
        """Test retry behavior for network timeout scenario"""
        config = RetryConfig(
            max_retries=3,
            base_delay_ms=100,  # Short delay for testing
            exponential_base=2
        )
        manager = RetryManager(config)

        # Simulate network timeout result
        class NetworkTimeoutResult:
            success = False
            retryable = True
            error_message = "Network timeout after 30s"

        result = NetworkTimeoutResult()

        # Should retry first timeout
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()
        assert manager.current_retry_count == 1

        # Should retry second timeout
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()
        assert manager.current_retry_count == 2

        # Should retry third timeout
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()
        assert manager.current_retry_count == 3

        # Should NOT retry fourth timeout (max reached)
        assert manager.should_retry(result) is False
        assert manager.get_retry_status() == RetryStatus.FAILED

    def test_file_not_found_scenario(self):
        """Test that file not found errors are not retried"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        # Simulate file not found result
        class FileNotFoundError:
            success = False
            retryable = False
            error_message = "File not found: report.pdf"

        result = FileNotFoundError()

        # Should NOT retry file not found
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 0
        assert manager.get_retry_status() == RetryStatus.FAILED

    def test_rate_limit_scenario(self):
        """Test retry behavior for rate limiting scenario"""
        config = RetryConfig(
            max_retries=2,
            base_delay_ms=50,  # Short delay for testing
            exponential_base=2
        )
        manager = RetryManager(config)

        # Simulate rate limit result
        class RateLimitResult:
            success = False
            retryable = True
            error_message = "429 Too Many Requests"

        result = RateLimitResult()

        # First rate limit should retry
        assert manager.should_retry(result) is True
        manager.record_retry_attempt()

        # Calculate and verify delay (should be 100ms for second retry since counter is now 1)
        delay = manager.calculate_delay()
        assert delay == 100  # 50ms * 2^(1) = 100ms (since current_retry_count is 1)

        # Simulate wait
        start = time.time()
        manager.wait_if_needed(result)
        elapsed = time.time() - start
        assert elapsed >= 0.1  # At least 100ms

    def test_success_after_retries_scenario(self):
        """Test successful operation after retries"""
        config = RetryConfig(
            max_retries=3,
            base_delay_ms=10,  # Very short delay for testing
            exponential_base=2
        )
        manager = RetryManager(config)

        attempts = 0

        def simulate_operation():
            nonlocal attempts
            attempts += 1

            if attempts < 3:
                # Fail first two attempts
                class TimeoutResult:
                    success = False
                    retryable = True
                    error_message = "Request timeout"
                return TimeoutResult()
            else:
                # Succeed on third attempt
                class SuccessResult:
                    success = True
                return SuccessResult()

        # First attempt fails, should retry
        result = simulate_operation()
        assert manager.should_retry(result) is True

        # Second attempt fails, should retry
        result = simulate_operation()
        assert manager.should_retry(result) is True

        # Third attempt succeeds, should NOT retry
        result = simulate_operation()
        assert manager.should_retry(result) is False

        assert attempts == 3
        assert manager.get_retry_status() == RetryStatus.COMPLETED

    def test_immediate_failure_scenario(self):
        """Test that non-retryable errors fail immediately"""
        config = RetryConfig(max_retries=5)  # Even with many retries allowed
        manager = RetryManager(config)

        # Simulate access denied error
        class AccessDeniedResult:
            success = False
            retryable = False
            error_message = "403 Access Forbidden"

        result = AccessDeniedResult()

        # Should fail immediately without retries
        assert manager.should_retry(result) is False
        assert manager.current_retry_count == 0
        assert manager.get_retry_status() == RetryStatus.FAILED


class TestRetryConfiguration:
    """Test retry configuration integration"""

    def test_settings_retry_configuration(self):
        """Test that Settings has retry configuration"""
        settings = Settings()

        # Verify retry configuration exists
        assert hasattr(settings, 'retry_max_attempts')
        assert hasattr(settings, 'retry_base_delay_ms')
        assert hasattr(settings, 'retry_max_delay_ms')
        assert hasattr(settings, 'retry_exponential_base')

        # Verify default values
        assert settings.retry_max_attempts == 3
        assert settings.retry_base_delay_ms == 1000
        assert settings.retry_max_delay_ms == 16000
        assert settings.retry_exponential_base == 2

    def test_retry_config_from_settings(self):
        """Test creating RetryConfig from Settings values"""
        settings = Settings()
        config = RetryConfig(
            max_retries=settings.retry_max_attempts,
            base_delay_ms=settings.retry_base_delay_ms,
            max_delay_ms=settings.retry_max_delay_ms,
            exponential_base=settings.retry_exponential_base
        )

        assert config.max_retries == 3
        assert config.base_delay_ms == 1000
        assert config.max_delay_ms == 16000
        assert config.exponential_base == 2


class TestRetryStatusTracking:
    """Test retry status tracking through lifecycle"""

    def test_status_pending_to_retrying_to_completed(self):
        """Test status progression: pending -> retrying -> completed"""
        config = RetryConfig(max_retries=2)
        manager = RetryManager(config)

        # Initial status should be pending
        assert manager.get_retry_status() == RetryStatus.PENDING

        # After first retry, should be retrying
        class FailResult:
            success = False
            retryable = True

        manager.should_retry(FailResult())
        manager.record_retry_attempt()
        assert manager.get_retry_status() == RetryStatus.RETRYING

        # After success, should be completed
        class SuccessResult:
            success = True

        manager.should_retry(SuccessResult())
        assert manager.get_retry_status() == RetryStatus.COMPLETED

    def test_status_pending_to_failed(self):
        """Test status progression: pending -> failed (non-retryable error)"""
        config = RetryConfig(max_retries=3)
        manager = RetryManager(config)

        # Initial status should be pending
        assert manager.get_retry_status() == RetryStatus.PENDING

        # Non-retryable error should go directly to failed
        class NonRetryableResult:
            success = False
            retryable = False

        manager.should_retry(NonRetryableResult())
        assert manager.get_retry_status() == RetryStatus.FAILED

    def test_status_pending_to_retrying_to_failed_max_retries(self):
        """Test status progression: pending -> retrying -> failed (max retries)"""
        config = RetryConfig(max_retries=2)
        manager = RetryManager(config)

        # Initial status should be pending
        assert manager.get_retry_status() == RetryStatus.PENDING

        class FailResult:
            success = False
            retryable = True

        # First retry
        manager.should_retry(FailResult())
        manager.record_retry_attempt()
        assert manager.get_retry_status() == RetryStatus.RETRYING

        # Second retry
        manager.should_retry(FailResult())
        manager.record_retry_attempt()
        assert manager.get_retry_status() == RetryStatus.RETRYING

        # Third attempt should fail (max retries = 2)
        manager.should_retry(FailResult())
        assert manager.get_retry_status() == RetryStatus.FAILED

    def test_reset_clears_all_state(self):
        """Test that reset clears all tracking state"""
        config = RetryConfig(max_retries=2)
        manager = RetryManager(config)

        # Perform some retries
        class FailResult:
            success = False
            retryable = True

        manager.should_retry(FailResult())
        manager.record_retry_attempt()
        assert manager.current_retry_count == 1
        assert manager.get_retry_status() == RetryStatus.RETRYING

        # Reset should clear all state
        manager.reset()
        assert manager.current_retry_count == 0
        assert manager.get_retry_status() == RetryStatus.PENDING
        assert manager.operation_completed is False
        assert manager.non_retryable_error is False
        assert manager.max_retries_exceeded is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
