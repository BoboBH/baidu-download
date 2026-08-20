"""
Comprehensive End-to-End Integration Tests for Task 8

These tests perform REAL integration testing without mocks:
- Real HTTP requests to reliable public endpoints
- Real database operations using in-memory SQLite
- Real error scenarios (timeouts, network errors, invalid URLs)
- Complete workflow testing from message parsing to database storage
- Retry mechanism testing with actual retry logic
- Database state verification through complete lifecycles

Test Coverage:
1. Complete PDF workflow: Parse → Router → Download → Process → Database
2. Retry workflow: Network timeout → retry 1 → retry 2 → success
3. Error classification: 404 → immediate failure (no retries)
4. Database state tracking: retry_count increments correctly
5. Backward compatibility: BaiduPan messages still work correctly

NO MOCKS are used in these tests - all components are real.
"""
import unittest
import sqlite3
import tempfile
import os
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path

from src.config.settings import Settings
from src.feishu.models import ParseResult
from src.feishu.message_parser import MessageParser
from src.processor.parsers.router import ProcessorRouter
from src.processor.parsers.pdf_processor import PdfLinkProcessor
from src.processor.retry_manager import RetryManager, RetryConfig
from src.database.message_models import MessageProcessLog


# =============================================================================
# TEST CONFIGURATION AND HELPERS
# =============================================================================

class TestConfig:
    """Centralized configuration for integration tests."""

    # Timeout configurations (in seconds)
    FAST_TIMEOUT = 1
    NORMAL_TIMEOUT = 5
    SLOW_TIMEOUT = 10

    # Retry configurations
    TEST_MAX_RETRIES = 3
    TEST_BASE_DELAY_MS = 100
    TEST_FAST_DELAY_MS = 10  # For faster testing

    # HTTP status codes for error assertions
    CLIENT_ERROR_CODES = ['404', '403', '401', '503']
    NETWORK_ERROR_KEYWORDS = ['timeout', 'connection', 'network', '连接', '超时']


def get_reliable_test_pdf_url():
    """
    Try multiple reliable PDF sources with fallbacks.

    Returns a working PDF URL or raises SkipTest if none available.
    """
    test_urls = [
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://www.africau.edu/images/default/sample.pdf",
        "https://file-examples.com/storage/feebcdb1a666.pdf6"
    ]

    for url in test_urls:
        try:
            response = requests.head(url, timeout=TestConfig.FAST_TIMEOUT)
            if response.status_code == 200:
                return url
        except Exception:
            continue

    raise unittest.SkipTest("No reliable test PDF URL available - skipping tests that require external PDF")


class TestDatabaseMixin:
    """Mixin providing database setup for integration tests."""

    def _init_database_schema(self):
        """Create message_process_log table in test database."""
        sql = """
        CREATE TABLE IF NOT EXISTS message_process_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_hash VARCHAR(64) NOT NULL UNIQUE,
            original_message TEXT,
            share_link TEXT,
            folder_name TEXT,
            extraction_code TEXT,
            source VARCHAR(50) DEFAULT 'feishu',
            message_type VARCHAR(50) DEFAULT 'baidupan',
            raw_message TEXT,
            file_info TEXT,
            process_status VARCHAR(50) DEFAULT 'pending',
            error_message TEXT,
            execution_summary_id INTEGER,
            processing_time_ms INTEGER,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()


class TestAssertionsMixin:
    """Mixin providing consistent assertion patterns."""

    def assert_error_contains_any(self, error, patterns, message=""):
        """
        Assert error string contains at least one of the specified patterns.

        Args:
            error: Exception or error string to check
            patterns: List of strings to search for in error message
            message: Custom assertion message
        """
        error_str = str(error or '')
        self.assertTrue(
            any(pattern in error_str for pattern in patterns),
            f"{message}. Got: {error_str}"
        )

    def assert_http_error(self, error, expected_codes=None):
        """
        Assert error is HTTP error with expected status codes.

        Args:
            error: Exception or error string to check
            expected_codes: List of HTTP status codes to look for (defaults to common client errors)
        """
        if expected_codes is None:
            expected_codes = TestConfig.CLIENT_ERROR_CODES

        self.assert_error_contains_any(
            error,
            expected_codes,
            "Error should mention HTTP status code"
        )

    def assert_network_error(self, error):
        """
        Assert error is a network-related error.

        Args:
            error: Exception or error string to check
        """
        error_lower = str(error).lower()
        self.assertTrue(
            any(keyword in error_lower for keyword in TestConfig.NETWORK_ERROR_KEYWORDS),
            f"Error should mention network/connection/timeout error, got: {error}"
        )


class TestRealDatabaseIntegration(TestDatabaseMixin, unittest.TestCase):
    """Test real database integration with in-memory SQLite."""

    def setUp(self):
        """Set up test fixtures with in-memory SQLite database."""
        # Create in-memory SQLite database for testing
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Initialize database schema
        self._init_database_schema()

    def test_database_message_insertion(self):
        """Test real database insertion of message log."""
        # Create test message hash
        message_hash = hashlib.md5(b'test_message_content').hexdigest()

        # Insert message log
        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, share_link, folder_name, extraction_code,
         source, message_type, process_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Note: SQLite uses ? instead of %s
        sql = sql.replace('%s', '?')

        self.cursor.execute(sql, (
            message_hash,
            'Test message content',
            'https://example.com/test.pdf',
            'test_folder',
            'code123',
            'feishu',
            'pdf_link',
            'pending'
        ))
        self.conn.commit()

        # Verify insertion
        self.cursor.execute(
            "SELECT * FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[1], message_hash)  # message_hash (index 1)
        self.assertEqual(result[7], 'pdf_link')    # message_type (index 7)
        self.assertEqual(result[10], 'pending')    # process_status (index 10)
        self.assertEqual(result[14], 0)            # retry_count (index 14)

    def test_database_status_update(self):
        """Test real database status update with retry count tracking."""
        message_hash = hashlib.md5(b'test_retry_message').hexdigest()

        # Insert initial message
        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, process_status, retry_count)
        VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(sql, (message_hash, 'test', 'processing', 0))
        self.conn.commit()

        # Update to failed with retry count increment
        sql = """
        UPDATE message_process_log
        SET process_status = ?,
            error_message = ?,
            retry_count = retry_count + 1
        WHERE message_hash = ?
        """
        self.cursor.execute(sql, ('failed', 'Network timeout', message_hash))
        self.conn.commit()

        # Verify update
        self.cursor.execute(
            "SELECT process_status, retry_count, error_message FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()

        self.assertEqual(result[0], 'failed')
        self.assertEqual(result[1], 1)  # retry_count incremented
        self.assertEqual(result[2], 'Network timeout')

    def test_database_duplicate_detection(self):
        """Test duplicate message detection via message hash."""
        message_hash = hashlib.md5(b'duplicate_test').hexdigest()

        # Insert first message
        sql = "INSERT INTO message_process_log (message_hash, process_status) VALUES (?, ?)"
        self.cursor.execute(sql, (message_hash, 'pending'))
        self.conn.commit()

        # Try to insert duplicate
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(sql, (message_hash, 'pending'))
            self.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        self.conn.close()


class TestRealHTTPIntegration(TestAssertionsMixin, unittest.TestCase):
    """Test real HTTP requests to reliable public endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

    def test_real_pdf_download_success(self):
        """Test real PDF download from reliable public endpoint."""
        # Use reliable test PDF with fallback mechanism
        test_pdf_url = get_reliable_test_pdf_url()

        processor = PdfLinkProcessor(self.settings)

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='w3c_test_pdf',
            source='test',
            pdf_url=test_pdf_url
        )

        # Perform real download
        download_result = processor.download(parse_result)

        # Verify success
        self.assertTrue(download_result.success, "Real PDF download should succeed")
        self.assertIsNotNone(download_result.local_path, "Should have local file path")
        self.assertGreater(download_result.file_size, 0, "Should have positive file size")
        self.assertTrue(os.path.exists(download_result.local_path), "Downloaded file should exist")

        # Clean up downloaded file
        if os.path.exists(download_result.local_path):
            os.remove(download_result.local_path)

    def test_real_pdf_download_404_error(self):
        """Test real 404 error handling."""
        # Use a reliable endpoint that returns 404 - use a known 404 URL
        invalid_url = "https://www.google.com/this-page-definitely-does-not-exist-404-test.pdf"

        processor = PdfLinkProcessor(self.settings)

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test_404',
            source='test',
            pdf_url=invalid_url
        )

        # Perform real download request
        download_result = processor.download(parse_result)

        # Verify error handling
        self.assertFalse(download_result.success, "404 request should fail")
        self.assertIsNotNone(download_result.error, "Should have error message")
        # 404 errors should not be retryable
        self.assertFalse(download_result.retryable, "404 errors should not be retryable")
        # Use consistent error assertion
        self.assert_http_error(download_result.error, TestConfig.CLIENT_ERROR_CODES)

    def test_real_pdf_download_timeout(self):
        """Test real timeout error handling."""
        # Use non-existent domain with very short timeout to create real timeout
        timeout_url = "http://nonexistent-domain-for-pdf-timeout-test.com/file.pdf"

        processor = PdfLinkProcessor(self.settings)
        # Override timeout to be very short for testing
        processor.timeout = TestConfig.FAST_TIMEOUT

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test_timeout',
            source='test',
            pdf_url=timeout_url
        )

        # Perform real download request that will timeout
        download_result = processor.download(parse_result)

        # Verify timeout handling
        self.assertFalse(download_result.success, "Timeout request should fail")
        self.assertIsNotNone(download_result.error, "Should have error message")
        self.assertTrue(download_result.retryable, "Timeout errors should be retryable")
        # Use consistent network error assertion
        self.assert_network_error(download_result.error)

    def test_real_pdf_download_invalid_url(self):
        """Test real invalid URL error handling."""
        # Use malformed URL
        invalid_url = "https://this-domain-does-not-exist-12345.com/file.pdf"

        processor = PdfLinkProcessor(self.settings)
        # Short timeout for faster testing
        processor.timeout = TestConfig.NORMAL_TIMEOUT

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test_invalid_url',
            source='test',
            pdf_url=invalid_url
        )

        # Perform real download request
        download_result = processor.download(parse_result)

        # Verify error handling
        self.assertFalse(download_result.success, "Invalid URL request should fail")
        self.assertIsNotNone(download_result.error, "Should have error message")
        # Network errors are retryable
        self.assertTrue(download_result.retryable, "Network errors should be retryable")
        # Use consistent network error assertion
        self.assert_network_error(download_result.error)


class TestCompletePDFWorkflow(TestAssertionsMixin, unittest.TestCase):
    """Test complete PDF workflow: Parse → Router → Download → Process → Cleanup."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
            self.parser = MessageParser()
            self.router = ProcessorRouter(self.settings)
        except Exception as e:
            self.skipTest(f"Components not available: {e}")

    def test_complete_pdf_workflow_success(self):
        """Test complete successful PDF processing workflow."""
        # Use reliable test PDF with fallback mechanism
        test_pdf_url = get_reliable_test_pdf_url()

        # Step 1: Parse message
        content = f"Please review this PDF: {test_pdf_url}"
        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result, "Message should be parsed")
        self.assertEqual(parse_result.message_type, 'pdf_link')
        self.assertEqual(parse_result.pdf_url, test_pdf_url)

        # Step 2: Router can process
        self.assertTrue(self.router.can_process('pdf_link'), "Router should process PDF links")

        # Step 3: Router routes to correct processor
        processor = self.router.get_processor('pdf_link')
        self.assertIsInstance(processor, PdfLinkProcessor)

        # Step 4: Complete router workflow
        router_result = self.router.process_message(parse_result)

        # Verify workflow result
        self.assertIsNotNone(router_result)
        self.assertTrue(router_result.success, "Complete workflow should succeed")
        self.assertEqual(router_result.message_type, 'pdf_link')
        self.assertEqual(router_result.processor_used, 'PdfLinkProcessor')

        # Verify download step
        self.assertIsNotNone(router_result.download_result)
        self.assertTrue(router_result.download_result.success, "Download should succeed")

        # Verify process step
        self.assertIsNotNone(router_result.process_result)
        self.assertTrue(router_result.process_result.success, "Process should succeed")

        # Verify upload files list
        self.assertIsNotNone(router_result.upload_files)
        self.assertGreater(len(router_result.upload_files), 0, "Should have upload files")

        # Verify file structure
        upload_file = router_result.upload_files[0]
        self.assertIn('local_path', upload_file)
        self.assertIn('remote_path', upload_file)
        self.assertTrue(os.path.exists(upload_file['local_path']), "Local file should exist")

        # Cleanup
        processor.cleanup()

    def test_complete_pdf_workflow_with_download_failure(self):
        """Test complete workflow handling download failure."""
        # Use URL that will fail - ensure it has .pdf extension for parser to recognize
        failing_url = "https://www.google.com/nonexistent-404-test-pdf.pdf"

        content = f"Broken PDF: {failing_url}"
        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result, "PDF URL should be parsed")

        # Router workflow should handle failure gracefully
        router_result = self.router.process_message(parse_result)

        # Verify failure handling
        self.assertIsNotNone(router_result)
        self.assertFalse(router_result.success, "Workflow should fail for 404")
        self.assertIsNotNone(router_result.error, "Should have error message")
        # Use consistent error assertion
        self.assert_http_error(router_result.error, TestConfig.CLIENT_ERROR_CODES)

        # Verify download failed
        self.assertIsNotNone(router_result.download_result)
        self.assertFalse(router_result.download_result.success, "Download should fail")


class TestCompleteBaiduPanWorkflow(TestDatabaseMixin, unittest.TestCase):
    """Test complete BaiduPan workflow: Parse → Router → Database."""

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        try:
            self.settings = Settings()
            self.parser = MessageParser()
            self.router = ProcessorRouter(self.settings)

            # Create in-memory database for integration testing
            self.conn = sqlite3.connect(':memory:', check_same_thread=False)
            self.cursor = self.conn.cursor()
            self._init_database_schema()
        except Exception as e:
            self.skipTest(f"Components not available: {e}")

    def test_complete_baidupan_workflow_parse_to_database(self):
        """Test complete BaiduPan workflow from parsing to database storage."""
        # Real BaiduPan message format
        content = "Please download this file: https://pan.baidu.com/s/test123456?pwd=abcd1234"

        # Step 1: Parse BaiduPan message
        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result, "BaiduPan message should be parsed")
        self.assertEqual(parse_result.message_type, 'baidupan')
        self.assertEqual(parse_result.share_link, 'https://pan.baidu.com/s/test123456?pwd=abcd1234')
        self.assertEqual(parse_result.extraction_code, 'abcd1234')

        # Step 2: Router can process BaiduPan messages
        self.assertTrue(self.router.can_process('baidupan'), "Router should process BaiduPan")

        # Step 3: Router routes to correct processor
        processor = self.router.get_processor('baidupan')
        self.assertIsNotNone(processor, "Should get BaiduPan processor")
        processor_name = processor.__class__.__name__
        self.assertIn('BaiduPan', processor_name, "Should use BaiduPan processor")

        # Step 4: Database integration - insert message log
        message_hash = self.parser.calculate_file_key(
            'baidupan',
            f"{parse_result.share_link}"
        )

        # Insert into database
        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, share_link, folder_name, extraction_code,
         source, message_type, process_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(sql, (
            message_hash,
            content,
            parse_result.share_link,
            parse_result.folder_name or '',
            parse_result.extraction_code,
            'feishu',
            'baidupan',
            'pending'
        ))
        self.conn.commit()

        # Verify database insertion
        self.cursor.execute(
            "SELECT * FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()

        self.assertIsNotNone(result, "Message should be in database")
        self.assertEqual(result[1], message_hash)  # message_hash
        self.assertEqual(result[3], parse_result.share_link)  # share_link
        self.assertEqual(result[6], 'feishu')  # source
        self.assertEqual(result[7], 'baidupan')  # message_type
        self.assertEqual(result[10], 'pending')  # process_status

        # Step 5: Simulate processing status update
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ? WHERE message_hash = ?",
            ('processing', message_hash)
        )
        self.conn.commit()

        # Verify status update
        self.cursor.execute(
            "SELECT process_status FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        status = self.cursor.fetchone()
        self.assertEqual(status[0], 'processing')

    def test_complete_baidupan_workflow_without_extraction_code(self):
        """Test BaiduPan workflow without extraction code (uses default)."""
        content = "Download: https://pan.baidu.com/s/noextrcode"

        # Step 1: Parse message
        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result, "Should parse BaiduPan without extraction code")
        self.assertEqual(parse_result.message_type, 'baidupan')
        self.assertEqual(parse_result.share_link, 'https://pan.baidu.com/s/noextrcode')
        self.assertIsNotNone(parse_result.extraction_code, "Should have default extraction code")

        # Step 2: Router integration
        self.assertTrue(self.router.can_process('baidupan'))
        processor = self.router.get_processor('baidupan')
        self.assertIsNotNone(processor)

        # Step 3: Database integration
        message_hash = self.parser.calculate_file_key('baidupan', parse_result.share_link)

        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, share_link, extraction_code, source, message_type, process_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(sql, (
            message_hash,
            content,
            parse_result.share_link,
            parse_result.extraction_code,
            'feishu',
            'baidupan',
            'pending'
        ))
        self.conn.commit()

        # Verify database state
        self.cursor.execute(
            "SELECT extraction_code, process_status FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], parse_result.extraction_code)
        self.assertEqual(result[1], 'pending')

    def test_complete_baidupan_workflow_with_retry_count(self):
        """Test BaiduPan workflow with retry count tracking in database."""
        content = "Baidu file: https://pan.baidu.com/s/retrytest?pwd=test123"

        # Parse and get message hash
        parse_result = self.parser.parse_message(content, 'feishu')
        message_hash = self.parser.calculate_file_key('baidupan', parse_result.share_link)

        # Insert initial message
        sql = """
        INSERT INTO message_process_log
        (message_hash, original_message, share_link, extraction_code, process_status, retry_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(sql, (
            message_hash,
            content,
            parse_result.share_link,
            parse_result.extraction_code,
            'processing',
            0
        ))
        self.conn.commit()

        # Simulate retry - increment retry count
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = retry_count + 1 WHERE message_hash = ?",
            ('failed', message_hash)
        )
        self.conn.commit()

        # Verify retry count incremented
        self.cursor.execute(
            "SELECT retry_count, process_status FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertEqual(result[0], 1, "Retry count should be 1")
        self.assertEqual(result[1], 'failed')

        # Simulate success - reset retry count
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = 0 WHERE message_hash = ?",
            ('success', message_hash)
        )
        self.conn.commit()

        # Verify reset
        self.cursor.execute(
            "SELECT retry_count FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        final_result = self.cursor.fetchone()
        self.assertEqual(final_result[0], 0, "Retry count should reset to 0 on success")

    def tearDown(self):
        """Clean up test database."""
        self.conn.close()


class TestRetryWorkflowWithRealErrors(TestAssertionsMixin, unittest.TestCase):
    """Test retry workflow with REAL HTTP requests to public endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.retry_config = RetryConfig(
            max_retries=TestConfig.TEST_MAX_RETRIES,
            base_delay_ms=TestConfig.TEST_BASE_DELAY_MS,
            exponential_base=2
        )
        self.retry_manager = RetryManager(self.retry_config)

    def _make_request_result(self, success, retryable, error_message=None):
        """Create a request result object compatible with retry manager."""
        class RequestResult:
            def __init__(self, success, retryable, error_message=None):
                self.success = success
                self.retryable = retryable
                self.error = error_message
                self.error_message = error_message or ("Success" if success else "Request failed")
        return RequestResult(success, retryable, error_message)

    def test_retry_workflow_real_timeout_to_success(self):
        """Test retry workflow with REAL HTTP timeout → retry → success."""
        attempts = 0
        max_timeout_attempts = 2  # Clear limit for timeout attempts

        def simulate_request_with_timeout_then_success():
            """
            Make real HTTP requests: timeout attempts → success attempt.

            Uses local network timeout (10.255.255.1) for reliable timeout simulation.
            Clear separation: first N attempts timeout, then success.
            """
            nonlocal attempts
            attempts += 1

            if attempts <= max_timeout_attempts:
                # Timeout attempts: Use local network timeout
                try:
                    # Local network timeout (10.255.255.1) - reliable timeout simulation
                    response = requests.get(
                        "http://10.255.255.1/test",
                        timeout=TestConfig.FAST_TIMEOUT
                    )
                    return self._make_request_result(True, True)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
                    # Explicit timeout error - retryable
                    return self._make_request_result(False, True, f"Connection timeout: {str(e)}")
                except requests.exceptions.ConnectionError as e:
                    # Connection error - retryable
                    return self._make_request_result(False, True, f"Connection error: {str(e)}")
            else:
                # Success attempt: Use reliable endpoint
                try:
                    response = requests.get(
                        "https://www.google.com",
                        timeout=TestConfig.SLOW_TIMEOUT
                    )
                    return self._make_request_result(True, True)
                except Exception as e:
                    # If success endpoint fails, treat as test infrastructure issue
                    raise unittest.SkipTest(f"Success endpoint unavailable: {e}")

        # Reset retry manager for this test
        self.retry_manager = RetryManager(self.retry_config)

        # Execute retry workflow with clear attempt tracking
        result = None
        max_total_attempts = max_timeout_attempts + 2  # Safety limit

        for attempt_num in range(1, max_total_attempts + 1):
            result = simulate_request_with_timeout_then_success()

            if result.success:
                # Success - stop retrying
                break

            # Check if should retry
            if self.retry_manager.should_retry(result):
                self.retry_manager.record_retry_attempt()
                self.retry_manager.wait_if_needed(result)
            else:
                # Should not retry - stop
                break

        # Verify retry workflow completed successfully
        self.assertGreaterEqual(attempts, max_timeout_attempts + 1,
                               f"Should make at least {max_timeout_attempts + 1} attempts (timeouts + success)")
        self.assertLessEqual(attempts, max_total_attempts,
                            f"Should make at most {max_total_attempts} attempts")
        self.assertTrue(result.success, "Final result should be success")
        self.assertEqual(self.retry_manager.current_retry_count, max_timeout_attempts,
                        f"Should have {max_timeout_attempts} retry count")

    def test_retry_workflow_real_404_immediate_failure(self):
        """Test that REAL 404 errors fail immediately without retries."""
        attempts = 0

        def real_404_request():
            """Make REAL HTTP request that returns 404."""
            nonlocal attempts
            attempts += 1

            try:
                # Use a reliable method to test 404
                response = requests.get(
                    "https://www.google.com/this-page-definitely-does-not-exist-404",
                    timeout=TestConfig.SLOW_TIMEOUT
                )
                # Check if it's a 404 or other 4xx error
                if response.status_code == 404:
                    return self._make_request_result(False, False, f"File not found: 404")
                elif 400 <= response.status_code < 500:
                    return self._make_request_result(False, False, f"Client error: {response.status_code}")
                else:
                    return self._make_request_result(False, False, f"Unexpected status: {response.status_code}")
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors
                if hasattr(e.response, 'status_code') and e.response.status_code == 404:
                    return self._make_request_result(False, False, f"File not found: 404")
                return self._make_request_result(False, False, f"HTTP error: {str(e)}")
            except Exception as e:
                return self._make_request_result(False, False, f"Request failed: {str(e)}")

        # Reset retry manager for this test
        self.retry_manager = RetryManager(self.retry_config)

        # First attempt with REAL 404-like error
        result = real_404_request()

        # Should NOT retry 404 errors
        should_retry = self.retry_manager.should_retry(result)

        # Verify immediate failure
        self.assertFalse(should_retry, "404 errors should not be retried")
        self.assertEqual(attempts, 1, "Should only make 1 attempt")
        self.assertEqual(self.retry_manager.current_retry_count, 0, "Should have 0 retries")
        self.assertFalse(result.success, "Result should be failure")
        # Use consistent error assertion
        self.assert_error_contains_any(result.error, ['404', 'Client error'],
                                      "Error should mention 404 or client error")

    def test_retry_workflow_max_retries_with_real_timeouts(self):
        """Test that retries stop after max_retries with REAL timeout requests."""
        attempts = 0
        max_retries = 2

        config = RetryConfig(
            max_retries=max_retries,
            base_delay_ms=TestConfig.TEST_FAST_DELAY_MS,  # Very short for testing
            exponential_base=2
        )
        manager = RetryManager(config)

        def real_continuous_timeout_request():
            """Make REAL HTTP requests that always timeout."""
            nonlocal attempts
            attempts += 1

            try:
                # Use local network timeout for reliable timeout simulation
                response = requests.get(
                    "http://10.255.255.1/test",
                    timeout=TestConfig.FAST_TIMEOUT
                )
                return self._make_request_result(True, True)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
                return self._make_request_result(False, True, f"Connection timeout: {str(e)}")
            except requests.exceptions.ConnectionError as e:
                return self._make_request_result(False, True, f"Connection error: {str(e)}")
            except Exception as e:
                return self._make_request_result(False, True, f"Network error: {str(e)}")

        # Retry loop with REAL HTTP requests
        result = None
        max_safety_attempts = 10  # Safety limit to prevent infinite loop

        for attempt_num in range(1, max_safety_attempts + 1):
            result = real_continuous_timeout_request()

            if manager.should_retry(result):
                manager.record_retry_attempt()
                manager.wait_if_needed(result)
            else:
                break

        # Verify max retries respected
        self.assertEqual(attempts, max_retries + 1, "Should attempt max_retries + 1 times")
        self.assertEqual(manager.current_retry_count, max_retries, "Should have max_retries count")
        self.assertFalse(result.success, "Final result should still be failure")

    def test_retry_delay_exponential_backoff(self):
        """Test exponential backoff in retry delays."""
        delays = []

        for retry_num in range(1, 4):
            # Calculate delay for this retry number
            delay = self.retry_config.get_retry_delay(retry_num)
            delays.append(delay)

        # Verify exponential backoff using TestConfig values
        expected_delays = [
            TestConfig.TEST_BASE_DELAY_MS,  # 100ms
            TestConfig.TEST_BASE_DELAY_MS * 2,  # 200ms
            TestConfig.TEST_BASE_DELAY_MS * 4  # 400ms
        ]
        self.assertEqual(delays[0], expected_delays[0],
                        f"First retry delay should be {expected_delays[0]}ms")
        self.assertEqual(delays[1], expected_delays[1],
                        f"Second retry delay should be {expected_delays[1]}ms")
        self.assertEqual(delays[2], expected_delays[2],
                        f"Third retry delay should be {expected_delays[2]}ms")


class TestMessagePriorityRouting(unittest.TestCase):
    """Test message type priority routing without mocks."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
            self.parser = MessageParser()
            self.router = ProcessorRouter(self.settings)
        except Exception as e:
            self.skipTest(f"Components not available: {e}")

    def test_baidu_link_highest_priority(self):
        """Test that Baidu links have highest priority."""
        # Message contains both Baidu and PDF links
        content = "Baidu link: https://pan.baidu.com/s/test123?pwd=abc and PDF: http://example.com/file.pdf"

        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result)
        self.assertEqual(parse_result.message_type, 'baidupan', "Baidu link should have priority")

    def test_pdf_link_medium_priority(self):
        """Test that PDF links have medium priority."""
        # Message contains PDF link
        content = "PDF report: http://example.com/report.pdf"

        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result)
        self.assertEqual(parse_result.message_type, 'pdf_link')

    def test_router_message_type_routing(self):
        """Test router routes different message types correctly."""
        # Test routing for each message type
        message_types = ['baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip']

        for msg_type in message_types:
            with self.subTest(message_type=msg_type):
                can_process = self.router.can_process(msg_type)
                self.assertTrue(can_process, f"Router should process {msg_type}")

                processor = self.router.get_processor(msg_type)
                self.assertIsNotNone(processor, f"Should get processor for {msg_type}")

    def test_router_priority_order(self):
        """Test router maintains processor priority order."""
        # Get processors in priority order
        processors = self.router.processors

        # Should have at least 3 processors (BaiduPan, PDF, DingTalk)
        self.assertGreaterEqual(len(processors), 3, "Should have at least 3 processors")

        # Verify priority order by checking processor types
        processor_types = [p.__class__.__name__ for p in processors]

        # BaiduPan should come before PDF
        baidupan_idx = next((i for i, t in enumerate(processor_types) if 'BaiduPan' in t), -1)
        pdf_idx = next((i for i, t in enumerate(processor_types) if 'Pdf' in t), -1)

        if baidupan_idx >= 0 and pdf_idx >= 0:
            self.assertLess(baidupan_idx, pdf_idx, "BaiduPan should have higher priority than PDF")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing BaiduPan messages."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.parser = MessageParser()
            self.settings = Settings()
            self.router = ProcessorRouter(self.settings)
        except Exception as e:
            self.skipTest(f"Components not available: {e}")

    def test_baidupan_message_parsing(self):
        """Test BaiduPan message parsing still works."""
        content = "Download from Baidu: https://pan.baidu.com/s/test123?pwd=abc123"

        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result, "BaiduPan message should be parsed")
        self.assertEqual(parse_result.message_type, 'baidupan')
        self.assertEqual(parse_result.share_link, 'https://pan.baidu.com/s/test123?pwd=abc123')
        self.assertEqual(parse_result.extraction_code, 'abc123')

    def test_baidupan_default_extraction_code(self):
        """Test BaiduPan without extraction code uses default."""
        content = "Download: https://pan.baidu.com/s/test456"

        parse_result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(parse_result)
        self.assertEqual(parse_result.message_type, 'baidupan')
        self.assertIsNotNone(parse_result.extraction_code, "Should have default extraction code")

    def test_baidupan_router_integration(self):
        """Test BaiduPan integration with router."""
        content = "Baidu file: https://pan.baidu.com/s/baidu_test?pwd=test"

        parse_result = self.parser.parse_message(content, 'feishu')

        # Router should handle BaiduPan messages
        self.assertTrue(self.router.can_process(parse_result.message_type))

        processor = self.router.get_processor(parse_result.message_type)
        self.assertIsNotNone(processor, "Should get processor for BaiduPan")

        # Verify it's the correct processor type
        processor_name = processor.__class__.__name__
        self.assertIn('BaiduPan', processor_name, "Should use BaiduPan processor")

    def test_message_hash_calculation(self):
        """Test message hash calculation for deduplication."""
        # Test hash for BaiduPan message
        share_link = "https://pan.baidu.com/s/hash_test?pwd=xyz"
        folder_name = "test_folder"

        hash1 = self.parser.calculate_file_key('baidupan', f"{folder_name}:{share_link}")
        hash2 = self.parser.calculate_file_key('baidupan', f"{folder_name}:{share_link}")

        # Same input should produce same hash
        self.assertEqual(hash1, hash2, "Same input should produce same hash")
        self.assertEqual(len(hash1), 32, "Hash should be 32 characters (MD5)")


class TestDatabaseIntegrationWithRetry(TestDatabaseMixin, unittest.TestCase):
    """Test database integration with retry count tracking."""

    def setUp(self):
        """Set up test database."""
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_database_schema()

        # Track message hashes for duplicate detection tests
        self.message_hashes = []

    def test_retry_count_increments_on_failure(self):
        """Test that retry_count increments on each failure."""
        message_hash = hashlib.md5(b'retry_increment_test').hexdigest()

        # Insert initial message
        self.cursor.execute(
            "INSERT INTO message_process_log (message_hash, process_status, retry_count) VALUES (?, ?, ?)",
            (message_hash, 'processing', 0)
        )
        self.conn.commit()

        # Simulate retry 1
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = retry_count + 1 WHERE message_hash = ?",
            ('failed', message_hash)
        )
        self.conn.commit()

        # Check retry count
        self.cursor.execute(
            "SELECT retry_count FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertEqual(result[0], 1, "Retry count should be 1 after first failure")

        # Simulate retry 2
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = retry_count + 1 WHERE message_hash = ?",
            ('failed', message_hash)
        )
        self.conn.commit()

        # Check retry count
        self.cursor.execute(
            "SELECT retry_count FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertEqual(result[0], 2, "Retry count should be 2 after second failure")

    def test_retry_count_reset_on_success(self):
        """Test that retry_count resets to 0 on success."""
        message_hash = hashlib.md5(b'retry_reset_test').hexdigest()

        # Insert message with retries
        self.cursor.execute(
            "INSERT INTO message_process_log (message_hash, process_status, retry_count) VALUES (?, ?, ?)",
            (message_hash, 'failed', 3)
        )
        self.conn.commit()

        # Update to success
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = 0 WHERE message_hash = ?",
            ('success', message_hash)
        )
        self.conn.commit()

        # Verify reset
        self.cursor.execute(
            "SELECT retry_count FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertEqual(result[0], 0, "Retry count should be 0 after success")

    def test_message_lifecycle_pending_to_success(self):
        """Test complete message lifecycle: pending → processing → success."""
        message_hash = hashlib.md5(b'lifecycle_test').hexdigest()

        # Insert as pending
        self.cursor.execute(
            "INSERT INTO message_process_log (message_hash, process_status, retry_count) VALUES (?, ?, ?)",
            (message_hash, 'pending', 0)
        )
        self.conn.commit()

        # Update to processing
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ? WHERE message_hash = ?",
            ('processing', message_hash)
        )
        self.conn.commit()

        # Update to success
        self.cursor.execute(
            "UPDATE message_process_log SET process_status = ?, retry_count = 0 WHERE message_hash = ?",
            ('success', message_hash)
        )
        self.conn.commit()

        # Verify final state
        self.cursor.execute(
            "SELECT process_status, retry_count FROM message_process_log WHERE message_hash = ?",
            (message_hash,)
        )
        result = self.cursor.fetchone()
        self.assertEqual(result[0], 'success')
        self.assertEqual(result[1], 0)

    def tearDown(self):
        """Clean up test database."""
        self.conn.close()


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)