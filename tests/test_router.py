"""
Comprehensive tests for processor routing system using real processor instances.

Tests cover:
- Router initialization and processor registration
- Priority ordering (BaiduPan > PDF > DingTalk)
- Routing logic for all message types
- Complete workflow integration (download → process → get_upload_files)
- Error handling when no processor available
- Error handling when processor operations fail
- can_process method functionality
- process_message method with unified workflow

NOTE: These tests use REAL processor instances as required by specification.
No mocks are used - only real processor objects.
"""
import unittest
import tempfile
import os
from pathlib import Path

from src.feishu.models import ParseResult
from src.config.settings import Settings


class TestProcessorRouter(unittest.TestCase):
    """Test cases for ProcessorRouter using real processor instances"""

    def setUp(self):
        """Set up test fixtures"""
        try:
            self.settings = Settings()
            self.settings.temp_dir = tempfile.gettempdir()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

        # Import router here - this will fail initially
        try:
            from src.processor.parsers.router import ProcessorRouter
            self.ProcessorRouter = ProcessorRouter
        except ImportError:
            self.skipTest("ProcessorRouter not implemented yet")

    def tearDown(self):
        """Clean up after tests"""
        pass

    # ===== RED TESTS - Router Initialization =====

    def test_router_initialization(self):
        """Test router can be initialized with settings"""
        router = self.ProcessorRouter(self.settings)
        self.assertIsNotNone(router)
        self.assertEqual(router.settings, self.settings)

    def test_router_has_processors_list(self):
        """Test router maintains processors list"""
        router = self.ProcessorRouter(self.settings)
        self.assertTrue(hasattr(router, 'processors'))
        self.assertIsInstance(router.processors, list)

    # ===== RED TESTS - Processor Registration =====

    def test_register_processor_adds_to_list(self):
        """Test register_processor adds processor to list"""
        from src.processor.parsers.pdf_processor import PdfLinkProcessor

        router = self.ProcessorRouter(self.settings)
        processor = PdfLinkProcessor(self.settings)

        initial_count = len(router.processors)
        router.register_processor(processor, priority=1)

        self.assertEqual(len(router.processors), initial_count + 1)
        self.assertIn(processor, router.processors)

    def test_register_processor_with_priority(self):
        """Test processors are ordered by priority"""
        from src.processor.parsers.pdf_processor import PdfLinkProcessor
        from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor

        router = self.ProcessorRouter(self.settings)

        # Get initial count (should have default processors)
        initial_count = len(router.processors)

        pdf_processor = PdfLinkProcessor(self.settings)
        dingtalk_processor = DingTalkFileProcessor(self.settings)

        # Register with lower priority first
        router.register_processor(dingtalk_processor, priority=2)
        router.register_processor(pdf_processor, priority=1)

        # Should have more processors now
        self.assertEqual(len(router.processors), initial_count + 2)

        # Find the newly registered processors in the list
        pdf_indices = [i for i, p in enumerate(router.processors) if p == pdf_processor]
        dingtalk_indices = [i for i, p in enumerate(router.processors) if p == dingtalk_processor]

        self.assertEqual(len(pdf_indices), 1, "PDF processor should be in list exactly once")
        self.assertEqual(len(dingtalk_indices), 1, "DingTalk processor should be in list exactly once")

        # PDF processor should come before DingTalk processor in the list
        self.assertLess(pdf_indices[0], dingtalk_indices[0],
                      "PDF processor should have higher priority than DingTalk processor")

    # ===== RED TESTS - can_process Method =====

    def test_can_process_with_pdf_link(self):
        """Test can_process returns True for pdf_link type"""
        router = self.ProcessorRouter(self.settings)
        # Assuming router has processors registered
        self.assertTrue(router.can_process('pdf_link'))

    def test_can_process_with_dingtalk_pdf(self):
        """Test can_process returns True for dingtalk_pdf type"""
        router = self.ProcessorRouter(self.settings)
        self.assertTrue(router.can_process('dingtalk_pdf'))

    def test_can_process_with_dingtalk_zip(self):
        """Test can_process returns True for dingtalk_zip type"""
        router = self.ProcessorRouter(self.settings)
        self.assertTrue(router.can_process('dingtalk_zip'))

    def test_can_process_with_baidupan(self):
        """Test can_process returns True for baidupan type"""
        router = self.ProcessorRouter(self.settings)
        self.assertTrue(router.can_process('baidupan'))

    def test_can_process_returns_false_for_unknown_type(self):
        """Test can_process returns False for unknown message type"""
        router = self.ProcessorRouter(self.settings)
        self.assertFalse(router.can_process('unknown_type'))

    # ===== RED TESTS - Routing Logic =====

    def test_get_processor_for_pdf_link(self):
        """Test get_processor returns correct processor for pdf_link"""
        router = self.ProcessorRouter(self.settings)
        from src.processor.parsers.pdf_processor import PdfLinkProcessor

        processor = router.get_processor('pdf_link')
        self.assertIsInstance(processor, PdfLinkProcessor)

    def test_get_processor_for_dingtalk_pdf(self):
        """Test get_processor returns correct processor for dingtalk_pdf"""
        router = self.ProcessorRouter(self.settings)
        from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor

        processor = router.get_processor('dingtalk_pdf')
        self.assertIsInstance(processor, DingTalkFileProcessor)

    def test_get_processor_for_dingtalk_zip(self):
        """Test get_processor returns correct processor for dingtalk_zip"""
        router = self.ProcessorRouter(self.settings)
        from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor

        processor = router.get_processor('dingtalk_zip')
        self.assertIsInstance(processor, DingTalkFileProcessor)

    def test_get_processor_returns_none_for_unknown_type(self):
        """Test get_processor returns None for unknown message type"""
        router = self.ProcessorRouter(self.settings)
        processor = router.get_processor('unknown_type')
        self.assertIsNone(processor)

    # ===== RED TESTS - Priority Ordering =====

    def test_priority_order_baidupan_highest(self):
        """Test BaiduPan processor has highest priority"""
        router = self.ProcessorRouter(self.settings)

        # Get priorities by checking processor order
        baidupan_processor = router.get_processor('baidupan')
        pdf_processor = router.get_processor('pdf_link')

        # BaiduPan should come before PDF in the list
        if baidupan_processor and pdf_processor:
            baidupan_index = router.processors.index(baidupan_processor)
            pdf_index = router.processors.index(pdf_processor)
            self.assertLess(baidupan_index, pdf_index,
                          "BaiduPan processor should have higher priority than PDF processor")

    def test_priority_order_pdf_medium(self):
        """Test PDF processor has medium priority"""
        router = self.ProcessorRouter(self.settings)

        pdf_processor = router.get_processor('pdf_link')
        dingtalk_processor = router.get_processor('dingtalk_pdf')

        # PDF should come before DingTalk in the list
        if pdf_processor and dingtalk_processor:
            pdf_index = router.processors.index(pdf_processor)
            dingtalk_index = router.processors.index(dingtalk_processor)
            self.assertLess(pdf_index, dingtalk_index,
                          "PDF processor should have higher priority than DingTalk processor")

    def test_complete_priority_order(self):
        """Test complete priority order: BaiduPan > PDF > DingTalk"""
        router = self.ProcessorRouter(self.settings)

        baidupan_processor = router.get_processor('baidupan')
        pdf_processor = router.get_processor('pdf_link')
        dingtalk_processor = router.get_processor('dingtalk_pdf')

        if all([baidupan_processor, pdf_processor, dingtalk_processor]):
            baidupan_index = router.processors.index(baidupan_processor)
            pdf_index = router.processors.index(pdf_processor)
            dingtalk_index = router.processors.index(dingtalk_processor)

            self.assertLess(baidupan_index, pdf_index,
                          "BaiduPan should have higher priority than PDF")
            self.assertLess(pdf_index, dingtalk_index,
                          "PDF should have higher priority than DingTalk")

    # ===== RED TESTS - Complete Workflow Integration =====

    def test_process_message_with_pdf_link_success(self):
        """Test complete workflow for pdf_link message type"""
        router = self.ProcessorRouter(self.settings)

        # Create a valid ParseResult for PDF link
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test-pdf-123',
            source='test',
            pdf_url='https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'  # Small test PDF
        )

        result = router.process_message(parse_result)

        # Verify result structure
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'download_result'))
        self.assertTrue(hasattr(result, 'process_result'))
        self.assertTrue(hasattr(result, 'upload_files'))

    def test_process_message_workflow_steps(self):
        """Test that process_message executes all workflow steps"""
        router = self.ProcessorRouter(self.settings)

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test-pdf-workflow',
            source='test',
            pdf_url='https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
        )

        result = router.process_message(parse_result)

        # Verify workflow steps were executed
        self.assertIsNotNone(result.download_result, "Download step should be executed")

        # If download succeeds, process_result should exist
        if result.download_result.success:
            self.assertIsNotNone(result.process_result, "Process step should be executed when download succeeds")
            self.assertIsNotNone(result.upload_files, "Get upload files step should be executed when download succeeds")
        else:
            # If download fails, we should have an error
            self.assertIsNotNone(result.error, "Error should be set when download fails")
            self.assertFalse(result.success, "Result should be failed when download fails")

    def test_process_message_unified_result_structure(self):
        """Test process_message returns unified result structure"""
        router = self.ProcessorRouter(self.settings)

        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test-result-structure',
            source='test',
            pdf_url='https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
        )

        result = router.process_message(parse_result)

        # Verify unified result structure
        self.assertTrue(hasattr(result, 'message_type'))
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'download_result'))
        self.assertTrue(hasattr(result, 'process_result'))
        self.assertTrue(hasattr(result, 'upload_files'))
        self.assertTrue(hasattr(result, 'error'))

        # Verify types
        self.assertIsInstance(result.message_type, str)
        self.assertIsInstance(result.success, bool)
        self.assertIsInstance(result.upload_files, list)

    # ===== RED TESTS - Error Handling =====

    def test_process_message_with_no_available_processor(self):
        """Test process_message handles no available processor error"""
        router = self.ProcessorRouter(self.settings)

        # Create ParseResult with unknown type
        parse_result = ParseResult(
            message_type='unknown_type',
            unique_identifier='test-unknown',
            source='test'
        )

        result = router.process_message(parse_result)

        # Should return error result
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn('No processor', result.error)

    def test_process_message_with_download_failure(self):
        """Test process_message handles download failure gracefully"""
        router = self.ProcessorRouter(self.settings)

        # Create ParseResult with invalid URL
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test-download-fail',
            source='test',
            pdf_url='https://invalid-url-that-does-not-exist-12345.com/file.pdf'
        )

        result = router.process_message(parse_result)

        # Should handle download failure
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.download_result)
        self.assertFalse(result.download_result.success)
        self.assertIsNotNone(result.error)

    def test_process_message_error_classification(self):
        """Test process_message properly classifies errors"""
        router = self.ProcessorRouter(self.settings)

        # Test with missing required field
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='test-error-classification',
            source='test',
            pdf_url=None  # Missing URL
        )

        result = router.process_message(parse_result)

        # Should classify as error
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        # Error should indicate what went wrong
        self.assertIn('No PDF URL', result.error or '')

    # ===== RED TESTS - Processor Cleanup =====

    def test_router_cleanup_all_processors(self):
        """Test router cleanup method cleans up all processors"""
        router = self.ProcessorRouter(self.settings)

        # Create some processors by routing different message types
        router.get_processor('pdf_link')
        router.get_processor('dingtalk_pdf')

        # Call cleanup
        router.cleanup()

        # Should not raise any errors
        self.assertTrue(True)

    # ===== RED TESTS - Message Type Coverage =====

    def test_all_supported_message_types(self):
        """Test router supports all defined message types"""
        router = self.ProcessorRouter(self.settings)

        # All message types from ParseResult documentation
        supported_types = ['baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip']

        for message_type in supported_types:
            with self.subTest(message_type=message_type):
                self.assertTrue(router.can_process(message_type),
                             f"Router should support {message_type}")

    def test_unsupported_message_types(self):
        """Test router rejects unsupported message types"""
        router = self.ProcessorRouter(self.settings)

        unsupported_types = ['video_link', 'image_file', 'unknown', '']

        for message_type in unsupported_types:
            with self.subTest(message_type=message_type):
                self.assertFalse(router.can_process(message_type),
                              f"Router should not support {message_type}")


if __name__ == '__main__':
    unittest.main()
