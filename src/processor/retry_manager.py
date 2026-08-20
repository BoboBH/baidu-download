"""
Retry Manager - Task 7: 错误处理和重试机制完善

Implements intelligent retry logic with exponential backoff for error recovery
"""
from dataclasses import dataclass
from enum import Enum
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetryStatus(Enum):
    """Retry status enumeration"""
    PENDING = "pending"        # No retries attempted yet
    RETRYING = "retrying"      # Currently retrying
    FAILED = "failed"          # Max retries exceeded or non-retryable error
    COMPLETED = "completed"    # Operation completed successfully


@dataclass
class RetryConfig:
    """Retry configuration parameters"""
    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 16000
    exponential_base: int = 2

    def get_retry_delay(self, retry_count: int) -> int:
        """
        Calculate delay for given retry count using exponential backoff

        Args:
            retry_count: Current retry attempt number (1-indexed)

        Returns:
            Delay in milliseconds, capped at max_delay_ms
        """
        if retry_count <= 0:
            return 0

        # Exponential backoff: base_delay * exponential_base^(retry_count-1)
        delay = self.base_delay_ms * (self.exponential_base ** (retry_count - 1))

        # Cap at max_delay_ms
        return min(delay, self.max_delay_ms)


class RetryManager:
    """
    Manages retry logic with exponential backoff for error recovery

    Features:
    - Smart error classification (retryable vs non-retryable)
    - Exponential backoff delays
    - Retry status tracking
    - Configurable retry limits
    """

    def __init__(self, config: RetryConfig = None):
        """
        Initialize retry manager

        Args:
            config: Retry configuration, defaults to RetryConfig()
        """
        self.config = config if config is not None else RetryConfig()
        self.current_retry_count = 0
        self.operation_completed = False
        self.non_retryable_error = False
        self.max_retries_exceeded = False

    def should_retry(self, result) -> bool:
        """
        Determine if operation should be retried based on result (does NOT mutate state)

        Args:
            result: DownloadResult or similar object with:
                   - success: bool
                   - retryable: bool (optional)

        Returns:
            True if operation should be retried, False otherwise
        """
        # Don't retry successful operations
        if hasattr(result, 'success') and result.success:
            self.operation_completed = True
            logger.debug("Operation completed successfully - no retry needed")
            return False

        # Don't retry if max retries exceeded
        if self.current_retry_count >= self.config.max_retries:
            self.max_retries_exceeded = True
            logger.error(f"Max retries exceeded ({self.current_retry_count}/{self.config.max_retries}) - marking as failed")
            return False

        # Check if error is retryable
        if hasattr(result, 'retryable') and result.retryable is False:
            self.non_retryable_error = True
            error_msg = getattr(result, 'error_message', 'Unknown error') if hasattr(result, 'error_message') else 'Unknown error'
            logger.error(f"Non-retryable error encountered: {error_msg} - marking as failed")
            return False

        # Check if should retry (no mutation - state change happens in record_retry_attempt)
        should_retry = self.current_retry_count < self.config.max_retries
        if should_retry:
            logger.debug(f"Operation can be retried (attempt {self.current_retry_count + 1}/{self.config.max_retries})")
        return should_retry

    def record_retry_attempt(self):
        """
        Record that a retry attempt is being made (mutates state)

        This should be called AFTER should_retry() returns True and BEFORE
        the actual retry attempt is made.
        """
        self.current_retry_count += 1
        logger.info(f"Initiating retry attempt {self.current_retry_count}/{self.config.max_retries}")

    def is_retryable_error(self, result) -> bool:
        """
        Check if error type is retryable based on error classification

        Args:
            result: Result object with error_type field

        Returns:
            True if error is retryable, False otherwise
        """
        if not hasattr(result, 'retryable'):
            # Default to retryable if no retryable field
            return True

        return result.retryable

    def calculate_delay(self) -> int:
        """
        Calculate delay for next retry using exponential backoff

        Returns:
            Delay in milliseconds
        """
        # Use current_retry_count + 1 because we want delay for the NEXT retry
        # (current_retry_count is 0-indexed, but get_retry_delay expects 1-indexed)
        return self.config.get_retry_delay(self.current_retry_count + 1)

    def wait_if_needed(self, result):
        """
        Wait with exponential backoff before next retry if retry is needed

        Args:
            result: Operation result to check if retry is needed
        """
        if self.should_retry(result):
            delay_ms = self.calculate_delay()
            delay_sec = delay_ms / 1000.0
            logger.info(f"Waiting {delay_ms}ms ({delay_sec:.2f}s) before next retry")
            time.sleep(delay_sec)

    def reset(self):
        """Reset retry counter for new operation"""
        logger.debug(f"Resetting retry manager (previous attempts: {self.current_retry_count})")
        self.current_retry_count = 0
        self.operation_completed = False
        self.non_retryable_error = False
        self.max_retries_exceeded = False
        logger.debug("Retry manager reset complete")

    def get_retry_status(self) -> RetryStatus:
        """
        Get current retry status

        Returns:
            RetryStatus enum value
        """
        # Check if operation completed successfully
        if self.operation_completed:
            return RetryStatus.COMPLETED

        # Check if non-retryable error occurred
        if self.non_retryable_error:
            return RetryStatus.FAILED

        # Check if max retries exceeded
        if self.max_retries_exceeded:
            return RetryStatus.FAILED

        # Check if currently retrying
        if self.current_retry_count > 0:
            return RetryStatus.RETRYING

        # No retries yet
        return RetryStatus.PENDING
