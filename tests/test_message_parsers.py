"""
Comprehensive parser tests for multi-type message support.

Tests all message parsers independently and together:
- Baidu Pan link parsing
- PDF link parsing
- DingTalk PDF parsing
- DingTalk ZIP parsing
- Message priority routing
- File key calculation
- Unsupported file types
"""
import unittest
import hashlib
from src.feishu.models import ParseResult
from src.feishu.message_parser import MessageParser
from src.feishu.parsers.pdf_link_parser import PdfLinkParser
from src.feishu.parsers.dingtalk_file_parser import DingTalkFileParser


class TestParseResult(unittest.TestCase):
    """Test the unified ParseResult model."""

    def test_parse_result_creation(self):
        """Test creating ParseResult with all fields."""
        result = ParseResult(
            message_type='baidupan',
            unique_identifier='test_id',
            source='feishu',
            share_link='https://pan.baidu.com/s/test',
            extraction_code='abc123',
            folder_name='test_folder'
        )

        self.assertEqual(result.message_type, 'baidupan')
        self.assertEqual(result.unique_identifier, 'test_id')
        self.assertEqual(result.source, 'feishu')
        self.assertEqual(result.share_link, 'https://pan.baidu.com/s/test')

    def test_parse_result_type_checkers(self):
        """Test ParseResult type checker methods."""
        baidu_result = ParseResult(
            message_type='baidupan',
            unique_identifier='id',
            source='feishu',
            share_link='link'
        )
        self.assertTrue(baidu_result.is_baidupan())
        self.assertFalse(baidu_result.is_pdf_link())

        pdf_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='id',
            source='feishu',
            pdf_url='http://example.com/file.pdf'
        )
        self.assertTrue(pdf_result.is_pdf_link())
        self.assertFalse(pdf_result.is_baidupan())

    def test_parse_result_to_dict(self):
        """Test ParseResult to_dict conversion."""
        result = ParseResult(
            message_type='pdf_link',
            unique_identifier='id',
            source='dingtalk',
            pdf_url='http://example.com/file.pdf'
        )
        result_dict = result.to_dict()

        self.assertIn('message_type', result_dict)
        self.assertEqual(result_dict['message_type'], 'pdf_link')
        # None values should be removed
        self.assertNotIn('share_link', result_dict)


class TestPdfLinkParser(unittest.TestCase):
    """Test PDF link parser."""

    def setUp(self):
        """Set up test parser."""
        self.parser = PdfLinkParser()

    def test_parse_valid_pdf_link(self):
        """Test parsing valid PDF link."""
        content = "Please check this PDF: http://example.com/document.pdf"
        result = self.parser.parse(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'pdf_link')
        self.assertEqual(result.pdf_url, 'http://example.com/document.pdf')
        self.assertEqual(result.source, 'feishu')
        self.assertEqual(result.unique_identifier, 'http://example.com/document.pdf')

    def test_parse_https_pdf_link(self):
        """Test parsing HTTPS PDF link."""
        content = "Document: https://secure.example.com/file.pdf"
        result = self.parser.parse(content, 'dingtalk')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'pdf_link')
        self.assertEqual(result.pdf_url, 'https://secure.example.com/file.pdf')

    def test_parse_no_pdf_link(self):
        """Test parsing message without PDF link."""
        content = "This is just plain text without PDF"
        result = self.parser.parse(content, 'feishu')

        self.assertIsNone(result)

    def test_parse_invalid_pdf_url(self):
        """Test parsing invalid PDF URL."""
        content = "Fake PDF: http://example.com/file.txt"
        result = self.parser.parse(content, 'feishu')

        self.assertIsNone(result)

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        result = self.parser.parse('', 'feishu')
        self.assertIsNone(result)

    def test_can_process(self):
        """Test can_process method."""
        self.assertTrue(self.parser.can_process('pdf_link'))
        self.assertFalse(self.parser.can_process('baidupan'))
        self.assertFalse(self.parser.can_process('dingtalk_pdf'))


class TestDingTalkFileParser(unittest.TestCase):
    """Test DingTalk file parser."""

    def setUp(self):
        """Set up test parser."""
        self.parser = DingTalkFileParser()

    def test_parse_dingtalk_pdf(self):
        """Test parsing DingTalk PDF message."""
        message_data = {
            'fileName': 'test_document.pdf',
            'fileId': 'file123',
            'spaceId': 'space456',
            'downloadCode': 'code789'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'dingtalk_pdf')
        self.assertEqual(result.file_name, 'test_document.pdf')
        self.assertEqual(result.file_id, 'file123')
        self.assertEqual(result.space_id, 'space456')
        self.assertEqual(result.download_code, 'code789')
        self.assertEqual(result.unique_identifier, 'file123:space456')

    def test_parse_dingtalk_zip(self):
        """Test parsing DingTalk ZIP message."""
        message_data = {
            'fileName': 'archive.zip',
            'fileId': 'zip123',
            'spaceId': 'space789',
            'downloadCode': 'code000'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'dingtalk_zip')
        self.assertEqual(result.file_name, 'archive.zip')

    def test_parse_unsupported_file_type(self):
        """Test parsing unsupported file type."""
        message_data = {
            'fileName': 'document.docx',
            'fileId': 'doc123',
            'spaceId': 'space000',
            'downloadCode': 'code111'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNone(result)

    def test_parse_missing_file_id(self):
        """Test parsing message without file ID."""
        message_data = {
            'fileName': 'test.pdf',
            'spaceId': 'space123',
            'downloadCode': 'code456'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNone(result)

    def test_parse_missing_space_id(self):
        """Test parsing message without space ID."""
        message_data = {
            'fileName': 'test.pdf',
            'fileId': 'file789',
            'downloadCode': 'code012'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNone(result)

    def test_parse_alternative_field_names(self):
        """Test parsing with alternative field names."""
        message_data = {
            'file_name': 'test.pdf',
            'file_id': 'file999',
            'space_id': 'space888',
            'download_code': 'code777'
        }

        result = self.parser.parse(message_data, 'dingtalk')

        self.assertIsNotNone(result)
        self.assertEqual(result.file_name, 'test.pdf')
        self.assertEqual(result.file_id, 'file999')

    def test_can_process(self):
        """Test can_process method."""
        self.assertTrue(self.parser.can_process('dingtalk_pdf'))
        self.assertTrue(self.parser.can_process('dingtalk_zip'))
        self.assertFalse(self.parser.can_process('baidupan'))
        self.assertFalse(self.parser.can_process('pdf_link'))


class TestMessageParser(unittest.TestCase):
    """Test main message parser with priority routing."""

    def setUp(self):
        """Set up test parser."""
        self.parser = MessageParser()

    def test_parse_baidupan_link(self):
        """Test parsing Baidu Pan link (highest priority)."""
        content = "Please download: https://pan.baidu.com/s/abc123?pwd=xyz"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'baidupan')
        self.assertEqual(result.share_link, 'https://pan.baidu.com/s/abc123?pwd=xyz')
        self.assertEqual(result.extraction_code, 'xyz')

    def test_parse_baidupan_default_code(self):
        """Test parsing Baidu Pan link without extraction code."""
        content = "Link: https://pan.baidu.com/s/test456"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'baidupan')
        # Should use default extraction code from settings
        self.assertIsNotNone(result.extraction_code)

    def test_parse_pdf_link(self):
        """Test parsing PDF link."""
        content = "Check this PDF: http://example.com/document.pdf"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'pdf_link')
        self.assertEqual(result.pdf_url, 'http://example.com/document.pdf')

    def test_parse_dingtalk_pdf(self):
        """Test parsing DingTalk PDF message."""
        message_data = {
            'fileName': 'test.pdf',
            'fileId': 'file123',
            'spaceId': 'space456',
            'downloadCode': 'code789'
        }
        content = "DingTalk file"

        result = self.parser.parse_message(content, 'dingtalk', message_data)

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'dingtalk_pdf')
        self.assertEqual(result.file_name, 'test.pdf')

    def test_message_priority_baidu_over_pdf(self):
        """Test that Baidu links have priority over PDF links."""
        # Message contains both Baidu link and PDF link
        content = "Baidu: https://pan.baidu.com/s/abc123?pwd=xyz and PDF: http://example.com/file.pdf"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        # Should match Baidu link (higher priority)
        self.assertEqual(result.message_type, 'baidupan')
        self.assertNotEqual(result.message_type, 'pdf_link')

    def test_message_priority_pdf_over_dingtalk(self):
        """Test that PDF links have priority over DingTalk files."""
        content = "PDF link: http://example.com/document.pdf"
        message_data = {
            'fileName': 'dingtalk.pdf',
            'fileId': 'file123',
            'spaceId': 'space456',
            'downloadCode': 'code789'
        }

        result = self.parser.parse_message(content, 'dingtalk', message_data)

        self.assertIsNotNone(result)
        # Should match PDF link (higher priority than DingTalk)
        self.assertEqual(result.message_type, 'pdf_link')

    def test_parse_unsupported_message(self):
        """Test parsing unsupported message type."""
        content = "Just plain text without any links"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNone(result)

    def test_parse_json_formatted_message(self):
        """Test parsing JSON formatted message."""
        content = '{"text":"https://pan.baidu.com/s/json123?pwd=test"}'
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'baidupan')

    def test_extract_pwd_from_url(self):
        """Test pwd extraction from URL."""
        url = "https://pan.baidu.com/s/test?pwd=abc123"
        pwd = self.parser.extract_pwd_from_url(url)
        self.assertEqual(pwd, 'abc123')

        url_no_pwd = "https://pan.baidu.com/s/test"
        pwd_no = self.parser.extract_pwd_from_url(url_no_pwd)
        self.assertIsNone(pwd_no)


class TestWeChatArticleParser(unittest.TestCase):
    """Test WeChat article link parser."""

    def setUp(self):
        """Set up test parser."""
        self.parser = MessageParser()

    def test_parse_wxchat_article_link(self):
        """Test parsing standard WeChat article link."""
        content = "请看这篇文章：https://mp.weixin.qq.com/s/ABC123XYZ"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'wxchat-article')
        self.assertEqual(result.wxchat_article_url, 'https://mp.weixin.qq.com/s/ABC123XYZ')
        self.assertEqual(result.wxchat_article_id, 'ABC123XYZ')
        self.assertEqual(result.unique_identifier, 'ABC123XYZ')

    def test_parse_wxchat_article_link_with_additional_text(self):
        """Test parsing WeChat article link with additional text."""
        content = "帮我把这个文章转成PDF https://mp.weixin.qq.com/s/DEF456UVW"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'wxchat-article')
        self.assertEqual(result.wxchat_article_url, 'https://mp.weixin.qq.com/s/DEF456UVW')
        self.assertEqual(result.wxchat_article_id, 'DEF456UVW')

    def test_parse_wxchat_article_link_complex_id(self):
        """Test parsing WeChat article link with complex article ID."""
        content = "分享：https://mp.weixin.qq.com/s/abc123_xyz-456"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNotNone(result)
        self.assertEqual(result.message_type, 'wxchat-article')
        self.assertEqual(result.wxchat_article_id, 'abc123_xyz-456')

    def test_parse_no_wxchat_article_link(self):
        """Test parsing message without WeChat article link."""
        content = "This is just plain text without WeChat article"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNone(result)

    def test_parse_invalid_wechat_link(self):
        """Test parsing invalid WeChat link format."""
        content = "Invalid WeChat link: https://weixin.qq.com/test"
        result = self.parser.parse_message(content, 'feishu')

        self.assertIsNone(result)

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        result = self.parser.parse_message('', 'feishu')
        self.assertIsNone(result)

    def test_message_priority_wxchat_over_dingtalk(self):
        """Test that WeChat article links have priority over DingTalk files."""
        content = "WeChat article: https://mp.weixin.qq.com/s/TEST123"
        message_data = {
            'fileName': 'dingtalk.pdf',
            'fileId': 'file123',
            'spaceId': 'space456',
            'downloadCode': 'code789'
        }

        result = self.parser.parse_message(content, 'dingtalk', message_data)

        self.assertIsNotNone(result)
        # Should match WeChat article (higher priority than DingTalk)
        self.assertEqual(result.message_type, 'wxchat-article')

    def test_parse_result_type_checker_wxchat(self):
        """Test ParseResult type checker for WeChat article."""
        result = ParseResult(
            message_type='wxchat-article',
            unique_identifier='test_id',
            source='feishu',
            wxchat_article_url='https://mp.weixin.qq.com/s/TEST',
            wxchat_article_id='TEST'
        )

        self.assertTrue(result.is_wxchat_article())
        self.assertFalse(result.is_baidupan())
        self.assertFalse(result.is_pdf_link())
        self.assertFalse(result.is_dingtalk_file())


class TestFileKeyCalculation(unittest.TestCase):
    """Test file key calculation for deduplication."""

    def setUp(self):
        """Set up test parser."""
        self.parser = MessageParser()

    def test_calculate_file_key_baidupan(self):
        """Test file key calculation for Baidu Pan."""
        message_type = 'baidupan'
        unique_id = 'https://pan.baidu.com/s/test123'

        key = self.parser.calculate_file_key(message_type, unique_id)

        self.assertEqual(len(key), 32)  # MD5 hash length
        self.assertTrue(all(c in '0123456789abcdef' for c in key))

    def test_calculate_file_key_pdf_link(self):
        """Test file key calculation for PDF link."""
        message_type = 'pdf_link'
        unique_id = 'http://example.com/file.pdf'

        key = self.parser.calculate_file_key(message_type, unique_id)

        self.assertEqual(len(key), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in key))

    def test_calculate_file_key_dingtalk(self):
        """Test file key calculation for DingTalk file."""
        message_type = 'dingtalk_pdf'
        unique_id = 'file123:space456'

        key = self.parser.calculate_file_key(message_type, unique_id)

        self.assertEqual(len(key), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in key))

    def test_file_key_uniqueness(self):
        """Test that different message types produce different keys."""
        baidu_key = self.parser.calculate_file_key('baidupan', 'same_id')
        pdf_key = self.parser.calculate_file_key('pdf_link', 'same_id')
        dingtalk_key = self.parser.calculate_file_key('dingtalk_pdf', 'same_id')

        # All keys should be different (different message types)
        self.assertNotEqual(baidu_key, pdf_key)
        self.assertNotEqual(baidu_key, dingtalk_key)
        self.assertNotEqual(pdf_key, dingtalk_key)

    def test_file_key_consistency(self):
        """Test that same input produces same key."""
        message_type = 'baidupan'
        unique_id = 'https://pan.baidu.com/s/test'

        key1 = self.parser.calculate_file_key(message_type, unique_id)
        key2 = self.parser.calculate_file_key(message_type, unique_id)

        self.assertEqual(key1, key2)

    def test_file_key_empty_identifier(self):
        """Test file key with empty identifier."""
        key = self.parser.calculate_file_key('baidupan', '')
        self.assertEqual(key, '')

        key_none = self.parser.calculate_file_key('baidupan', None)
        self.assertEqual(key_none, '')

    def test_file_key_format(self):
        """Test file key format includes message type."""
        message_type = 'pdf_link'
        unique_id = 'http://example.com/file.pdf'

        key = self.parser.calculate_file_key(message_type, unique_id)

        # Verify it's a proper MD5 hash by manually computing
        composite = f"{message_type}:{unique_id}"
        expected_key = hashlib.md5(composite.encode('utf-8')).hexdigest()

        self.assertEqual(key, expected_key)


if __name__ == '__main__':
    unittest.main(verbosity=2)
