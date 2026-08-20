"""
Tests for message receiver integration with unified router system.

Tests cover:
- Message receiver initialization with router
- Handling all message types through router
- Backwards compatibility with existing message flow
- Router integration for processing workflow
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.feishu.models import ParseResult
from src.config.settings import Settings


class TestMessageReceiverRouterIntegration(unittest.TestCase):
    """Test message receiver integration with unified router."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

    @patch('src.processor.message_receiver.DatabaseRepository')
    @patch('src.processor.message_receiver.FeishuMessageClient')
    @patch('src.processor.message_receiver.DingtalkNotifier')
    def test_message_receiver_initialization_with_router(self, mock_notifier, mock_client, mock_db):
        """Test message receiver can be initialized with router support."""
        from src.processor.message_receiver import MessageReceiver

        # Create receiver
        receiver = MessageReceiver(self.settings, source='feishu')

        # Verify initialization
        self.assertIsNotNone(receiver)
        self.assertEqual(receiver.source, 'feishu')
        self.assertIsNotNone(receiver.message_parser)

    @patch('src.processor.message_receiver.DatabaseRepository')
    @patch('src.processor.message_receiver.DingtalkNotifier')
    @patch('src.feishu.feishu_client.FeishuMessageClient')
    def test_receiver_handles_baidupan_messages(self, mock_client, mock_notifier, mock_db):
        """Test receiver handles BaiduPan messages correctly."""
        from src.processor.message_receiver import MessageReceiver

        receiver = MessageReceiver(self.settings, source='feishu')

        # Mock client to return BaiduPan message
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_messages.return_value = [
            {
                'message_id': 'msg_123',
                'body': {'content': '{"text":"https://pan.baidu.com/s/test?pwd=abc"}'}
            }
        ]

        # Mock database to return no existing message
        mock_db_instance = mock_db.return_value
        mock_db_instance.get_message_by_hash.return_value = None
        mock_db_instance.insert_message_log.return_value = 1

        # Receive messages
        result = receiver.receive_messages()

        # Verify structure
        self.assertIsNotNone(result)
        self.assertEqual(result.total_messages, 1)

    @patch('src.processor.message_receiver.DatabaseRepository')
    @patch('src.processor.message_receiver.DingtalkNotifier')
    @patch('src.processor.message_receiver.FeishuMessageClient')
    def test_receiver_handles_pdf_link_messages(self, mock_client, mock_notifier, mock_db):
        """Test receiver handles PDF link messages correctly."""
        from src.processor.message_receiver import MessageReceiver

        receiver = MessageReceiver(self.settings, source='feishu')

        # Mock client to return PDF link message
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_messages.return_value = [
            {
                'message_id': 'msg_456',
                'body': {'content': 'Please check: http://example.com/document.pdf'}
            }
        ]

        # Mock database
        mock_db_instance = mock_db.return_value
        mock_db_instance.get_message_by_hash.return_value = None
        mock_db_instance.insert_message_log.return_value = 2

        # Receive messages
        result = receiver.receive_messages()

        self.assertIsNotNone(result)
        self.assertEqual(result.total_messages, 1)

    @patch('src.processor.message_receiver.DatabaseRepository')
    @patch('src.processor.message_receiver.DingtalkNotifier')
    @patch('src.processor.message_receiver.FeishuMessageClient')
    def test_receiver_handles_mixed_message_types(self, mock_client, mock_notifier, mock_db):
        """Test receiver handles mixed message types in single batch."""
        from src.processor.message_receiver import MessageReceiver

        receiver = MessageReceiver(self.settings, source='feishu')

        # Mock client to return mixed messages
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_messages.return_value = [
            {
                'message_id': 'msg_1',
                'body': {'content': '{"text":"https://pan.baidu.com/s/test1?pwd=abc"}'}
            },
            {
                'message_id': 'msg_2',
                'body': {'content': 'PDF: http://example.com/doc1.pdf'}
            },
            {
                'message_id': 'msg_3',
                'body': {'content': 'Just text without links'}
            }
        ]

        # Mock database
        mock_db_instance = mock_db.return_value
        mock_db_instance.get_message_by_hash.return_value = None
        mock_db_instance.insert_message_log.return_value = 10

        # Receive messages
        result = receiver.receive_messages()

        # Should handle all messages
        self.assertIsNotNone(result)
        self.assertEqual(result.total_messages, 3)

    def test_parse_result_supports_all_message_types(self):
        """Test that ParseResult supports all message type fields."""
        # Test BaiduPan
        baidu_result = ParseResult(
            message_type='baidupan',
            unique_identifier='test_id',
            source='feishu',
            share_link='https://pan.baidu.com/s/test',
            extraction_code='abc123',
            folder_name='test_folder'
        )
        self.assertTrue(baidu_result.is_baidupan())

        # Test PDF link
        pdf_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='pdf_id',
            source='feishu',
            pdf_url='http://example.com/doc.pdf'
        )
        self.assertTrue(pdf_result.is_pdf_link())

        # Test DingTalk PDF
        dingtalk_pdf_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file:space',
            source='dingtalk',
            file_id='file123',
            space_id='space456',
            download_code='code789',
            file_name='report.pdf'
        )
        self.assertTrue(dingtalk_pdf_result.is_dingtalk_pdf())

        # Test DingTalk ZIP
        dingtalk_zip_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='zipfile:zipspace',
            source='dingtalk',
            file_id='zip123',
            space_id='zip456',
            download_code='zipcode',
            file_name='archive.zip'
        )
        self.assertTrue(dingtalk_zip_result.is_dingtalk_zip())

    def test_message_parser_handles_all_types(self):
        """Test that message parser handles all message types."""
        from src.feishu.message_parser import MessageParser

        parser = MessageParser()

        # Test BaiduPan parsing
        baidu_result = parser.parse_message("Link: https://pan.baidu.com/s/test?pwd=abc", 'feishu')
        self.assertIsNotNone(baidu_result)
        self.assertEqual(baidu_result.message_type, 'baidupan')

        # Test PDF link parsing
        pdf_result = parser.parse_message("PDF: http://example.com/doc.pdf", 'feishu')
        self.assertIsNotNone(pdf_result)
        self.assertEqual(pdf_result.message_type, 'pdf_link')

        # Test DingTalk file parsing
        dingtalk_data = {
            'fileName': 'test.pdf',
            'fileId': 'file123',
            'spaceId': 'space456',
            'downloadCode': 'code789'
        }
        dingtalk_result = parser.parse_message("", 'dingtalk', dingtalk_data)
        self.assertIsNotNone(dingtalk_result)
        self.assertEqual(dingtalk_result.message_type, 'dingtalk_pdf')

    def test_file_key_calculation_for_all_types(self):
        """Test file key calculation works for all message types."""
        from src.feishu.message_parser import MessageParser

        parser = MessageParser()

        # Test BaiduPan key
        baidu_key = parser.calculate_file_key('baidupan', 'https://pan.baidu.com/s/test')
        self.assertEqual(len(baidu_key), 32)  # MD5 hash

        # Test PDF link key
        pdf_key = parser.calculate_file_key('pdf_link', 'http://example.com/doc.pdf')
        self.assertEqual(len(pdf_key), 32)

        # Test DingTalk file key
        dingtalk_key = parser.calculate_file_key('dingtalk_pdf', 'file123:space456')
        self.assertEqual(len(dingtalk_key), 32)

        # All keys should be different
        self.assertNotEqual(baidu_key, pdf_key)
        self.assertNotEqual(baidu_key, dingtalk_key)
        self.assertNotEqual(pdf_key, dingtalk_key)


class TestBackwardsCompatibility(unittest.TestCase):
    """Test backwards compatibility with existing message flow."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
        except Exception as e:
            self.skipTest(f"Settings not available: {e}")

    def test_baidupan_messages_still_work(self):
        """Test that BaiduPan message flow still works correctly."""
        from src.feishu.message_parser import MessageParser

        parser = MessageParser()

        # Parse BaiduPan message
        content = "Please download: https://pan.baidu.com/s/test123?pwd=xyz"
        result = parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'baidupan')
        self.assertEqual(result.share_link, 'https://pan.baidu.com/s/test123?pwd=xyz')
        self.assertEqual(result.extraction_code, 'xyz')

    def test_message_priority_maintained(self):
        """Test that message type priority is maintained."""
        from src.feishu.message_parser import MessageParser

        parser = MessageParser()

        # Message with both Baidu and PDF links
        content = "Baidu: https://pan.baidu.com/s/abc?pwd=123 and PDF: http://example.com/file.pdf"
        result = parser.parse_message(content, 'feishu')

        # Baidu should have priority
        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'baidupan')

    def test_source_field_preserved(self):
        """Test that message source field is preserved."""
        from src.feishu.message_parser import MessageParser

        parser = MessageParser()

        # Test different sources
        feishu_result = parser.parse_message("https://pan.baidu.com/s/test", 'feishu')
        self.assertEqual(feishu_result.source, 'feishu')

        dingtalk_result = parser.parse_message("https://pan.baidu.com/s/test", 'dingtalk')
        self.assertEqual(dingtalk_result.source, 'dingtalk')


class TestRouterAvailability(unittest.TestCase):
    """Test that router is available and functional."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            self.settings = Settings()
            from src.processor.parsers.router import ProcessorRouter
            from src.feishu.message_parser import MessageParser
            self.router = ProcessorRouter(self.settings)
            self.parser = MessageParser()
        except Exception as e:
            self.skipTest(f"Router components not available: {e}")

    def test_router_available(self):
        """Test that router is available."""
        self.assertIsNotNone(self.router)
        self.assertTrue(hasattr(self.router, 'process_message'))

    def test_router_handles_all_message_types(self):
        """Test that router can handle all message types."""
        supported_types = ['baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip']

        for message_type in supported_types:
            with self.subTest(message_type=message_type):
                self.assertTrue(self.router.can_process(message_type),
                               f"Router should handle {message_type}")

    def test_router_get_processor_for_all_types(self):
        """Test that router returns valid processors for all types."""
        supported_types = ['baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip']

        for message_type in supported_types:
            with self.subTest(message_type=message_type):
                processor = self.router.get_processor(message_type)
                self.assertIsNotNone(processor,
                                    f"Router should return processor for {message_type}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
