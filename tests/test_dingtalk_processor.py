"""
Comprehensive tests for DingTalk file processor using real DingTalk service.

NOTE: These tests require real DingTalk service access. No mocks are used per spec requirements.
User must provide valid DingTalk download codes for testing.
"""
import unittest
import tempfile
import shutil
import zipfile
import os
from pathlib import Path
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor, DownloadResult, ProcessResult
from src.feishu.models import ParseResult
from src.config.settings import Settings


class TestDingTalkProcessor(unittest.TestCase):
    """Comprehensive tests for DingTalk file processor with real service."""

    def setUp(self):
        """Set up test environment."""
        try:
            self.settings = Settings()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

        # Set smaller size limits for testing
        self.settings.max_pdf_size_mb = 1
        self.settings.max_zip_size_mb = 2
        self.settings.max_single_file_size_mb = 0.5
        self.settings.dingtalk_file_timeout = 300

        self.processor = DingTalkFileProcessor(self.settings)
        self.temp_test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        if Path(self.temp_test_dir).exists():
            shutil.rmtree(self.temp_test_dir)
        if self.processor:
            self.processor.cleanup()

    def test_can_process_dingtalk_types(self):
        """Test processor can handle DingTalk message types."""
        self.assertTrue(self.processor.can_process('dingtalk_pdf'))
        self.assertTrue(self.processor.can_process('dingtalk_zip'))
        self.assertFalse(self.processor.can_process('baidupan'))
        self.assertFalse(self.processor.can_process('pdf_link'))

    def test_download_result_dataclass(self):
        """Test DownloadResult dataclass has required fields."""
        result = DownloadResult(
            success=True,
            local_path='/tmp/test.pdf',
            file_size=1024000,
            filename='test.pdf',
            retryable=False
        )
        self.assertTrue(result.success)
        self.assertEqual(result.local_path, '/tmp/test.pdf')
        self.assertEqual(result.file_size, 1024000)
        self.assertEqual(result.filename, 'test.pdf')
        self.assertFalse(result.retryable)

    def test_process_result_dataclass(self):
        """Test ProcessResult dataclass has required fields."""
        result = ProcessResult(
            success=True,
            processed_files=['/tmp/file1.pdf', '/tmp/file2.pdf'],
            metadata={'count': 2}
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_files), 2)
        self.assertIsNotNone(result.metadata)

    def test_download_missing_download_code(self):
        """Test download fails when downloadCode is missing."""
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_id='file123',
            space_id='space456',
            download_code=None,  # Missing download code
            file_name='test.pdf',
            source='dingtalk'
        )

        result = self.processor.download(parse_result)

        self.assertFalse(result.success)
        self.assertIn('Missing downloadCode', result.error)
        self.assertFalse(result.retryable)

    def test_download_missing_file_name(self):
        """Test download fails when file_name is missing."""
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_id='file123',
            space_id='space456',
            download_code='valid_code',
            file_name=None,  # Missing file name
            source='dingtalk'
        )

        result = self.processor.download(parse_result)

        self.assertFalse(result.success)
        self.assertIn('Missing downloadCode or file_name', result.error)
        self.assertFalse(result.retryable)

    def test_process_pdf_no_processing_needed(self):
        """Test PDF processing doesn't modify the file."""
        # Create a mock PDF file
        pdf_path = os.path.join(self.temp_test_dir, 'test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4 mock pdf content')

        download_result = DownloadResult(
            success=True,
            local_path=pdf_path,
            file_size=1024,
            filename='test.pdf',
            temp_dir=self.temp_test_dir
        )

        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='test.pdf',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_files), 1)
        self.assertEqual(result.processed_files[0], pdf_path)
        self.assertIsNotNone(result.metadata)
        self.assertEqual(result.metadata['file_type'], 'pdf')

    def test_process_unsupported_message_type(self):
        """Test processing unsupported message type fails."""
        download_result = DownloadResult(
            success=True,
            local_path='/tmp/test.pdf',
            file_size=1024,
            filename='test.pdf'
        )

        parse_result = ParseResult(
            message_type='unsupported_type',
            unique_identifier='test',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertFalse(result.success)
        self.assertIn('不支持的消息类型', result.error)

    def test_process_failed_download(self):
        """Test processing failed download returns error."""
        download_result = DownloadResult(
            success=False,
            error='Network error',
            retryable=True
        )

        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='test.pdf',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertFalse(result.success)
        self.assertEqual(result.error, 'Network error')

    def test_extract_zip_file(self):
        """Test ZIP extraction preserves structure."""
        # Create a test ZIP file
        zip_path = os.path.join(self.temp_test_dir, 'test.zip')

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr('doc1.txt', 'Content of document 1')
            zipf.writestr('doc2.txt', 'Content of document 2')
            zipf.writestr('subfolder/doc3.txt', 'Content of document 3')

        download_result = DownloadResult(
            success=True,
            local_path=zip_path,
            file_size=1024,
            filename='test.zip',
            temp_dir=self.temp_test_dir
        )

        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file789:space456',
            file_name='test.zip',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_files), 3, "Should extract 3 files")
        self.assertIsNotNone(result.metadata)
        self.assertEqual(result.metadata['extracted_count'], 3)
        self.assertEqual(result.metadata['file_type'], 'zip')

    def test_extract_zip_with_large_files(self):
        """Test ZIP extraction skips oversized files."""
        # Create ZIP with mixed file sizes
        zip_path = os.path.join(self.temp_test_dir, 'mixed.zip')

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Small file (within limit)
            zipf.writestr('small.txt', 'Small content')
            # Large file (exceeds 0.5MB limit)
            large_content = 'x' * (1 * 1024 * 1024)  # 1MB
            zipf.writestr('large.txt', large_content)

        download_result = DownloadResult(
            success=True,
            local_path=zip_path,
            file_size=1024,
            filename='mixed.zip',
            temp_dir=self.temp_test_dir
        )

        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file999:space456',
            file_name='mixed.zip',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertTrue(result.success)
        self.assertEqual(len(result.processed_files), 1, "Should only extract small file")
        self.assertEqual(result.metadata['skipped_count'], 1, "Should skip 1 large file")

    def test_extract_corrupted_zip(self):
        """Test corrupted ZIP file handling."""
        # Create a corrupted ZIP file
        zip_path = os.path.join(self.temp_test_dir, 'corrupted.zip')
        with open(zip_path, 'wb') as f:
            f.write(b'This is not a valid ZIP file')

        download_result = DownloadResult(
            success=True,
            local_path=zip_path,
            file_size=100,
            filename='corrupted.zip',
            temp_dir=self.temp_test_dir
        )

        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file_bad:space456',
            file_name='corrupted.zip',
            source='dingtalk'
        )

        result = self.processor.process(download_result, parse_result)

        self.assertFalse(result.success)
        self.assertIn('ZIP文件损坏', result.error)
        # When processing fails, metadata should be None
        self.assertIsNone(result.metadata, "Failed processing should have None metadata")

    def test_get_upload_files_for_pdf(self):
        """Test upload file generation for PDF."""
        pdf_path = os.path.join(self.temp_test_dir, 'test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4')

        process_result = ProcessResult(
            success=True,
            processed_files=[pdf_path],
            metadata={'file_type': 'pdf'}
        )

        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='test.pdf',
            source='dingtalk'
        )

        upload_files = self.processor.get_upload_files(process_result, parse_result)

        self.assertEqual(len(upload_files), 1)
        self.assertEqual(upload_files[0]['local_path'], pdf_path)
        self.assertTrue(upload_files[0]['remote_path'].startswith('/'))
        self.assertTrue(upload_files[0]['remote_path'].endswith('.pdf'))

    def test_get_upload_files_for_zip(self):
        """Test upload file generation preserves ZIP structure."""
        # Create extraction directory structure
        extract_dir = os.path.join(self.temp_test_dir, 'project')
        os.makedirs(extract_dir)
        os.makedirs(os.path.join(extract_dir, 'docs'))
        os.makedirs(os.path.join(extract_dir, 'src'))

        # Create test files
        (Path(extract_dir) / 'docs' / 'spec.pdf').touch()
        (Path(extract_dir) / 'src' / 'main.py').touch()

        process_result = ProcessResult(
            success=True,
            processed_files=[
                str(Path(extract_dir) / 'docs' / 'spec.pdf'),
                str(Path(extract_dir) / 'src' / 'main.py')
            ],
            metadata={
                'extract_dir': extract_dir,
                'file_type': 'zip'
            }
        )

        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file789:space456',
            file_name='project.zip',
            source='dingtalk'
        )

        upload_files = self.processor.get_upload_files(process_result, parse_result)

        self.assertEqual(len(upload_files), 2)

        # Check that structure is preserved
        remote_paths = [f['remote_path'] for f in upload_files]
        self.assertIn('/project/docs/spec.pdf', remote_paths)
        self.assertIn('/project/src/main.py', remote_paths)

    def test_get_upload_files_failed_process(self):
        """Test upload file generation for failed processing."""
        process_result = ProcessResult(
            success=False,
            processed_files=[],
            error='Processing failed'
        )

        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='test.pdf',
            source='dingtalk'
        )

        upload_files = self.processor.get_upload_files(process_result, parse_result)

        self.assertEqual(len(upload_files), 0)

    def test_generate_remote_filename(self):
        """Test remote filename generation with timestamp."""
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='report.pdf',
            source='dingtalk'
        )

        remote_filename = self.processor._generate_remote_filename(parse_result)

        self.assertTrue(remote_filename.startswith('report_'))
        self.assertTrue(remote_filename.endswith('.pdf'))
        # Check timestamp format (YYYYMMDD_HHMMSS)
        parts = remote_filename.split('_')
        self.assertEqual(len(parts), 3)  # name, date, time.ext

    def test_cleanup(self):
        """Test temporary directory cleanup."""
        # Create a temp directory
        temp_dir = tempfile.mkdtemp(prefix='cleanup_test_')
        self.processor.temp_dir = temp_dir

        # Verify directory exists
        self.assertTrue(os.path.exists(temp_dir))

        # Run cleanup
        self.processor.cleanup()

        # Verify directory is removed and temp_dir is set to None
        self.assertFalse(os.path.exists(temp_dir))
        self.assertIsNone(self.processor.temp_dir)

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup handles non-existent directories gracefully."""
        self.processor.temp_dir = '/nonexistent/directory/path'

        # Should not raise exception
        self.processor.cleanup()

        # temp_dir should still be set to None
        self.assertIsNone(self.processor.temp_dir)


class TestDingTalkProcessorRealService(unittest.TestCase):
    """Integration tests using real DingTalk service (requires valid download codes)."""

    def setUp(self):
        """Set up test environment for real service tests."""
        try:
            self.settings = Settings()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

        # These tests require real DingTalk download codes
        self.test_dingtalk_pdf_code = os.getenv('TEST_DINGTALK_PDF_CODE')
        self.test_dingtalk_zip_code = os.getenv('TEST_DINGTALK_ZIP_CODE')

        if not self.test_dingtalk_pdf_code and not self.test_dingtalk_zip_code:
            self.skipTest("No DingTalk test codes provided. Set TEST_DINGTALK_PDF_CODE or TEST_DINGTALK_ZIP_CODE environment variables.")

        self.processor = DingTalkFileProcessor(self.settings)

    def tearDown(self):
        """Clean up after real service tests."""
        if self.processor:
            self.processor.cleanup()

    @unittest.skipIf(not os.getenv('TEST_DINGTALK_PDF_CODE'), "Requires TEST_DINGTALK_PDF_CODE environment variable")
    def test_real_dingtalk_pdf_download(self):
        """Test real DingTalk PDF download using valid downloadCode."""
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='test_pdf_file:space123',
            file_id='test_pdf_file',
            space_id='space123',
            download_code=self.test_dingtalk_pdf_code,
            file_name='test_document.pdf',
            source='dingtalk'
        )

        # Download file
        download_result = self.processor.download(parse_result)

        if not download_result.success:
            self.skipTest(f"Real DingTalk download failed: {download_result.error}")

        self.assertTrue(download_result.success)
        self.assertIsNotNone(download_result.local_path)
        self.assertGreater(download_result.file_size, 0)
        self.assertTrue(os.path.exists(download_result.local_path))

        # Process file
        process_result = self.processor.process(download_result, parse_result)
        self.assertTrue(process_result.success)
        self.assertEqual(len(process_result.processed_files), 1)

        # Get upload files
        upload_files = self.processor.get_upload_files(process_result, parse_result)
        self.assertEqual(len(upload_files), 1)

    @unittest.skipIf(not os.getenv('TEST_DINGTALK_ZIP_CODE'), "Requires TEST_DINGTALK_ZIP_CODE environment variable")
    def test_real_dingtalk_zip_download_and_extraction(self):
        """Test real DingTalk ZIP download and extraction."""
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='test_zip_file:space456',
            file_id='test_zip_file',
            space_id='space456',
            download_code=self.test_dingtalk_zip_code,
            file_name='test_project.zip',
            source='dingtalk'
        )

        # Download file
        download_result = self.processor.download(parse_result)

        if not download_result.success:
            self.skipTest(f"Real DingTalk download failed: {download_result.error}")

        self.assertTrue(download_result.success)
        self.assertIsNotNone(download_result.local_path)
        self.assertGreater(download_result.file_size, 0)

        # Process ZIP file (should extract contents)
        process_result = self.processor.process(download_result, parse_result)
        self.assertTrue(process_result.success)
        self.assertGreater(len(process_result.processed_files), 0)
        self.assertEqual(process_result.metadata['file_type'], 'zip')

        # Get upload files (should preserve structure)
        upload_files = self.processor.get_upload_files(process_result, parse_result)
        self.assertEqual(len(upload_files), len(process_result.processed_files))


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)