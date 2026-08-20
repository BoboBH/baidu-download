"""
Comprehensive tests for PDF link processor.

Tests cover:
- can_process method
- Successful PDF download (mocked)
- File size limit enforcement
- Timeout handling
- Process method (PDF needs no processing)
- get_upload_files method
- File cleanup
"""
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.processor.parsers.pdf_processor import PdfLinkProcessor, DownloadResult, ProcessResult
from src.feishu.models import ParseResult
from src.config.settings import Settings


class TestPdfLinkProcessor(unittest.TestCase):
    """Test cases for PdfLinkProcessor"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock settings
        self.settings = Mock(spec=Settings)
        self.settings.max_pdf_size_mb = 200  # 200MB default
        self.settings.wxchat_pdf_timeout = 300  # 300 seconds default
        self.settings.temp_dir = tempfile.gettempdir()

        # Create processor instance
        self.processor = PdfLinkProcessor(self.settings)

        # Create test parse result
        self.parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            source='feishu',
            pdf_url='https://example.com/test.pdf'
        )

    def tearDown(self):
        """Clean up after tests"""
        # Clean up any temporary files created during tests
        if self.processor.temp_dir and os.path.exists(self.processor.temp_dir):
            import shutil
            shutil.rmtree(self.processor.temp_dir)

    def test_can_process_with_pdf_link(self):
        """Test can_process returns True for pdf_link message type"""
        self.assertTrue(self.processor.can_process('pdf_link'))

    def test_can_process_with_other_types(self):
        """Test can_process returns False for other message types"""
        self.assertFalse(self.processor.can_process('baidupan'))
        self.assertFalse(self.processor.can_process('dingtalk_pdf'))
        self.assertFalse(self.processor.can_process('dingtalk_zip'))
        self.assertFalse(self.processor.can_process('unknown'))

    @patch('src.processor.parsers.pdf_processor.requests.get')
    def test_successful_pdf_download(self, mock_get):
        """Test successful PDF download with mocked HTTP response"""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1024'}  # 1KB file
        mock_response.raise_for_status = Mock()

        # Create mock content iterator
        mock_content = b'PDF content data' * 100  # ~1.5KB of data
        mock_response.iter_content = Mock(return_value=iter([mock_content]))

        mock_get.return_value = mock_response

        # Perform download
        result = self.processor.download(self.parse_result)

        # Verify result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.local_path)
        self.assertGreater(result.file_size, 0)
        self.assertEqual(result.filename, 'test.pdf')
        self.assertIsNone(result.error)

        # Verify file exists
        self.assertTrue(os.path.exists(result.local_path))

        # Verify mock was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], 'https://example.com/test.pdf')
        self.assertTrue(call_args[1]['stream'])  # stream=True
        self.assertEqual(call_args[1]['timeout'], 300)

    @patch('src.processor.parsers.pdf_processor.requests.get')
    def test_file_size_limit_from_header(self, mock_get):
        """Test file size limit enforcement from content-length header"""
        # Create mock response with large file size
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(300 * 1024 * 1024)}  # 300MB
        mock_response.raise_for_status = Mock()

        mock_get.return_value = mock_response

        # Perform download
        result = self.processor.download(self.parse_result)

        # Verify size limit was enforced
        self.assertFalse(result.success)
        self.assertIn("超过大小限制", result.error)
        self.assertIn("300", result.error)  # Should mention the file size

    @patch('src.processor.parsers.pdf_processor.requests.get')
    def test_file_size_limit_during_download(self, mock_get):
        """Test file size limit enforcement during download"""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No content-length header

        # Create content that exceeds limit during download
        # Mock returns large chunks that will exceed 200MB
        large_chunk = b'X' * (10 * 1024 * 1024)  # 10MB chunks
        chunk_count = 25  # 25 chunks = 250MB total (exceeds 200MB limit)

        def content_iterator(chunk_size):
            """Iterator that yields chunks until size limit is exceeded"""
            for _ in range(chunk_count):
                yield large_chunk

        mock_response.iter_content = Mock(side_effect=content_iterator)
        mock_response.raise_for_status = Mock()

        mock_get.return_value = mock_response

        # Perform download
        result = self.processor.download(self.parse_result)

        # Verify size limit was enforced during download
        self.assertFalse(result.success)
        self.assertIn("下载过程中超过大小限制", result.error)

    @patch('src.processor.parsers.pdf_processor.requests.get')
    def test_download_timeout(self, mock_get):
        """Test timeout handling"""
        # Create mock that raises timeout exception
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        # Perform download
        result = self.processor.download(self.parse_result)

        # Verify timeout was handled
        self.assertFalse(result.success)
        self.assertIn("超时", result.error)
        self.assertIn("300", result.error)  # Should mention the timeout value

    @patch('src.processor.parsers.pdf_processor.requests.get')
    def test_http_error_handling(self, mock_get):
        """Test HTTP error handling"""
        # Create mock response with 404 error
        import requests
        mock_response = Mock()
        mock_response.status_code = 404

        # Create HTTPError with response
        http_error = requests.exceptions.HTTPError("Not Found")
        http_error.response = mock_response
        mock_response.raise_for_status = Mock(side_effect=http_error)

        mock_get.return_value = mock_response

        # Perform download
        result = self.processor.download(self.parse_result)

        # Verify HTTP error was handled
        self.assertFalse(result.success)
        self.assertIn("HTTP错误", result.error)
        self.assertIn("404", result.error)

    def test_process_with_successful_download(self):
        """Test process method with successful download"""
        # Create temporary file to simulate downloaded file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(b'PDF content')
        temp_file.close()

        try:
            # Create download result
            download_result = DownloadResult(
                success=True,
                local_path=temp_file.name,
                file_size=1024,
                filename='test.pdf'
            )

            # Process the downloaded file
            result = self.processor.process(download_result, self.parse_result)

            # Verify result - PDF files need no processing
            self.assertTrue(result.success)
            self.assertEqual(len(result.processed_files), 1)
            self.assertEqual(result.processed_files[0], temp_file.name)
            self.assertIsNone(result.error)
        finally:
            # Clean up
            os.unlink(temp_file.name)

    def test_process_with_failed_download(self):
        """Test process method with failed download"""
        # Create failed download result
        download_result = DownloadResult(
            success=False,
            error="Download failed"
        )

        # Process the failed download
        result = self.processor.process(download_result, self.parse_result)

        # Verify result
        self.assertFalse(result.success)
        self.assertEqual(len(result.processed_files), 0)
        self.assertEqual(result.error, "Download failed")

    def test_process_with_missing_file(self):
        """Test process method when downloaded file is missing"""
        # Create download result with non-existent file
        download_result = DownloadResult(
            success=True,
            local_path='/nonexistent/file.pdf',
            file_size=1024,
            filename='test.pdf'
        )

        # Process the download
        result = self.processor.process(download_result, self.parse_result)

        # Verify error handling
        self.assertFalse(result.success)
        self.assertEqual(len(result.processed_files), 0)
        self.assertIn("不存在", result.error)

    def test_get_upload_files(self):
        """Test get_upload_files method"""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(b'PDF content')
        temp_file.close()

        try:
            # Create process result
            process_result = ProcessResult(
                success=True,
                processed_files=[temp_file.name]
            )

            # Get upload files
            upload_files = self.processor.get_upload_files(process_result, self.parse_result)

            # Verify result
            self.assertEqual(len(upload_files), 1)
            self.assertEqual(upload_files[0]['local_path'], temp_file.name)

            # Verify remote path format (timestamp_filename.pdf)
            remote_path = upload_files[0]['remote_path']
            self.assertTrue(remote_path.startswith('/'))
            self.assertTrue(remote_path.endswith('.pdf'))

            # Extract timestamp and filename
            parts = remote_path[1:].rsplit('_', 1)  # Remove leading / and split at last _
            self.assertEqual(len(parts), 2)
            timestamp, filename = parts
            self.assertEqual(filename, 'test.pdf')

            # Verify timestamp format (YYYYMMDD_HHMMSS)
            import re
            timestamp_pattern = r'\d{8}_\d{6}'
            self.assertIsNotNone(re.match(timestamp_pattern, timestamp))

        finally:
            # Clean up
            os.unlink(temp_file.name)

    def test_get_upload_files_with_failed_process(self):
        """Test get_upload_files with failed process result"""
        # Create failed process result
        process_result = ProcessResult(
            success=False,
            processed_files=[],
            error="Processing failed"
        )

        # Get upload files
        upload_files = self.processor.get_upload_files(process_result, self.parse_result)

        # Verify empty result
        self.assertEqual(len(upload_files), 0)

    def test_cleanup(self):
        """Test cleanup method removes temporary directory"""
        # Create a temporary directory manually
        temp_dir = tempfile.mkdtemp(prefix='pdf_test_')
        self.processor.temp_dir = temp_dir

        # Create a file in the temp directory
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')

        # Verify directory exists
        self.assertTrue(os.path.exists(temp_dir))

        # Perform cleanup
        self.processor.cleanup()

        # Verify directory was removed
        self.assertFalse(os.path.exists(temp_dir))
        self.assertIsNone(self.processor.temp_dir)

    def test_cleanup_with_nonexistent_directory(self):
        """Test cleanup with non-existent directory"""
        # Set temp_dir to non-existent path
        self.processor.temp_dir = '/nonexistent/directory'

        # Should not raise exception
        self.processor.cleanup()

        # Temp dir should be set to None
        self.assertIsNone(self.processor.temp_dir)

    def test_extract_filename_from_url(self):
        """Test filename extraction from URL"""
        test_cases = [
            ('https://example.com/test.pdf', 'test.pdf'),
            ('https://example.com/path/to/document.pdf', 'document.pdf'),
            ('https://example.com/path/file.pdf?param=value', 'file.pdf'),
            ('https://example.com/FILE.PDF', 'FILE.PDF'),  # Case insensitive
            ('https://example.com/file.txt', None),  # Not a PDF
            ('https://example.com/', None),  # No filename
        ]

        for url, expected_filename in test_cases:
            result = self.processor._extract_filename_from_url(url)
            self.assertEqual(result, expected_filename, f"Failed for URL: {url}")

    def test_generate_remote_filename(self):
        """Test remote filename generation with timestamp"""
        # Generate remote filename
        remote_filename = self.processor._generate_remote_filename(self.parse_result)

        # Verify format: YYYYMMDD_HHMMSS_test.pdf
        import re
        pattern = r'^\d{8}_\d{6}_test\.pdf$'
        self.assertIsNotNone(re.match(pattern, remote_filename))

        # Extract timestamp
        parts = remote_filename.split('_')
        timestamp = f"{parts[0]}_{parts[1]}"
        filename = '_'.join(parts[2:])  # In case original filename has underscores

        self.assertEqual(filename, 'test.pdf')

    def test_download_with_no_pdf_url(self):
        """Test download when parse result has no PDF URL"""
        # Create parse result without PDF URL
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test',
            source='feishu'
        )

        # Attempt download
        result = self.processor.download(parse_result)

        # Verify error handling
        self.assertFalse(result.success)
        self.assertIn("No PDF URL", result.error)

    def test_download_with_invalid_url(self):
        """Test download with invalid URL (network error)"""
        import requests

        # Mock get to raise connection error
        with patch('src.processor.parsers.pdf_processor.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            result = self.processor.download(self.parse_result)

            # Verify error handling
            self.assertFalse(result.success)
            self.assertIn("网络错误", result.error)

    def test_download_creates_temp_directory(self):
        """Test that download creates temporary directory"""
        with patch('src.processor.parsers.pdf_processor.requests.get') as mock_get:
            # Create mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-length': '1024'}
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = Mock(return_value=iter([b'PDF content']))

            mock_get.return_value = mock_response

            # Ensure temp_dir is None before download
            self.assertIsNone(self.processor.temp_dir)

            # Perform download
            result = self.processor.download(self.parse_result)

            # Verify temp directory was created
            self.assertTrue(result.success)
            self.assertIsNotNone(self.processor.temp_dir)
            self.assertTrue(os.path.exists(self.processor.temp_dir))
            # Check that the directory name (not full path) starts with prefix
            dir_name = os.path.basename(self.processor.temp_dir)
            self.assertTrue(dir_name.startswith('pdf_download_'))

    def test_download_file_size_within_limit(self):
        """Test download with file size exactly at the limit"""
        with patch('src.processor.parsers.pdf_processor.requests.get') as mock_get:
            # Create mock response with file size exactly at limit (200MB)
            file_size = 200 * 1024 * 1024  # Exactly 200MB
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-length': str(file_size)}
            mock_response.raise_for_status = Mock()

            # Mock content that will be downloaded
            mock_response.iter_content = Mock(return_value=iter([b'PDF content']))
            mock_get.return_value = mock_response

            result = self.processor.download(self.parse_result)

            # Should succeed (at limit is acceptable)
            self.assertTrue(result.success)
            self.assertIsNone(result.error)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()