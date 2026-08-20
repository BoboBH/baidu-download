import re
import hashlib
import json as json_module
from typing import Optional, Dict, Any
from src.config.settings import Settings
from src.utils.logger import get_logger
from src.feishu.models import ParseResult
from src.feishu.parsers.pdf_link_parser import PdfLinkParser
from src.feishu.parsers.dingtalk_file_parser import DingTalkFileParser

logger = get_logger(__name__)

class MessageParser:
    """
    Message parser with priority-based routing for multiple message types.

    Supported message types (in priority order):
    1. Baidu Pan links (baidupan) - highest priority
    2. PDF links (pdf_link)
    3. DingTalk files (dingtalk_pdf, dingtalk_zip)

    Priority ensures backwards compatibility - existing Baidu links are
    processed first before attempting other parsers.
    """

    # Simplified Baidu Pan link pattern
    # Matches:
    #   - https://pan.baidu.com/s/xxx?pwd=gqi4
    #   - https://pan.baidu.com/s/xxx
    #   - Any message containing Baidu Pan links
    BAIDU_LINK_PATTERN = re.compile(
        r'(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)'
    )

    def __init__(self):
        """Initialize parser with all sub-parsers."""
        self.settings = Settings()
        self.pdf_parser = PdfLinkParser()
        self.dingtalk_parser = DingTalkFileParser()

    def parse_message(self, content: str, source: str = 'feishu', message_data: Optional[Dict[str, Any]] = None) -> Optional[ParseResult]:
        """
        Parse message content with priority-based routing.

        Priority order:
        1. Baidu Pan links (highest priority) - backwards compatibility
        2. PDF links
        3. DingTalk files

        This ensures existing Baidu link functionality is preserved while
        adding support for new message types.

        Args:
            content: Message content (text)
            source: Message source ('feishu', 'dingtalk', etc.)
            message_data: Optional message data dictionary (for DingTalk files)

        Returns:
            ParseResult object for the first matching parser
            None if no parser matches the message
        """
        if not content and not message_data:
            logger.warning("Empty message content and no message data")
            return None

        # Normalize content
        content = content.strip()

        # Parse JSON format if present
        try:
            parsed_content = json_module.loads(content)
            if isinstance(parsed_content, dict) and 'text' in parsed_content:
                content = parsed_content['text']
                logger.debug(f"Parsed JSON message content: {content}")
        except (json_module.JSONDecodeError, TypeError):
            logger.debug("Using raw message content (not JSON)")

        # Priority 1: Try Baidu Pan parser first (backwards compatibility)
        baidu_result = self._parse_baidupan(content, source)
        if baidu_result:
            return baidu_result

        # Priority 2: Try PDF link parser
        pdf_result = self.pdf_parser.parse(content, source)
        if pdf_result:
            return pdf_result

        # Priority 3: Try DingTalk file parser (only if message_data provided)
        if message_data:
            dingtalk_result = self.dingtalk_parser.parse(message_data, source)
            if dingtalk_result:
                return dingtalk_result

        logger.debug(f"No parser matched message from {source}: {content[:50]}...")
        return None

    def _parse_baidupan(self, content: str, source: str) -> Optional[ParseResult]:
        """
        Parse Baidu Pan links with backwards compatibility.

        Args:
            content: Message content
            source: Message source

        Returns:
            ParseResult with message_type='baidupan' if Baidu link found
            None if no Baidu link found
        """
        # Search for Baidu Pan link
        link_match = self.BAIDU_LINK_PATTERN.search(content)
        if not link_match:
            return None

        share_link = link_match.group(1).strip()

        # Extract pwd parameter from URL
        extraction_code = self.extract_pwd_from_url(share_link)
        if not extraction_code:
            extraction_code = self.settings.message_default_extraction_code
            logger.info(f"No pwd in URL, using default extraction code: {extraction_code}")
        else:
            logger.info(f"Extracted pwd from URL: {extraction_code}")

        # Folder name will be determined by BaiduPCS-Go API
        folder_name = None

        # Generate unique identifier (share_link without pwd parameter)
        clean_link = share_link.split('?pwd=')[0]
        unique_identifier = clean_link

        logger.info(f"Baidu link parsed successfully: link={share_link[:50]}..., code={extraction_code}")

        return ParseResult(
            message_type='baidupan',
            unique_identifier=unique_identifier,
            source=source,
            share_link=share_link,
            extraction_code=extraction_code,
            folder_name=folder_name
        )

    def calculate_message_hash(self, content: str) -> str:
        """
        计算消息内容的MD5哈希值（已弃用，仅用于日志标识）

        Args:
            content: 消息内容

        Returns:
            MD5哈希值（32位小写十六进制）
        """
        if not content:
            return ""

        # 标准化消息内容（去除多余空格）
        normalized = re.sub(r'\s+', ' ', content.strip())

        # 计算MD5哈希
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def calculate_file_key(self, message_type: str, unique_identifier: str) -> str:
        """
        Calculate file unique key for deduplication using MD5 hash.

        The unique key is based on message type and unique identifier to ensure
        that different message types with the same identifier don't collide.

        Args:
            message_type: Type of message (baidupan, pdf_link, dingtalk_pdf, dingtalk_zip)
            unique_identifier: Unique identifier for the specific message

        Returns:
            MD5 hash (32-character lowercase hexadecimal string)
            Empty string if unique_identifier is not provided
        """
        if not unique_identifier:
            return ""

        # Normalize identifier (strip whitespace)
        clean_identifier = str(unique_identifier).strip()

        # Create composite key: message_type:unique_identifier
        composite_key = f"{message_type}:{clean_identifier}"

        # Calculate MD5 hash as unique key
        return hashlib.md5(composite_key.encode('utf-8')).hexdigest()

    def extract_pwd_from_url(self, url: str) -> Optional[str]:
        """
        从百度网盘URL中提取pwd参数作为提取码

        Args:
            url: 百度网盘分享链接

        Returns:
            提取码，如果URL中没有pwd参数则返回None
        """
        pwd_pattern = re.compile(r'[?&]pwd=([a-zA-Z0-9]+)')
        match = pwd_pattern.search(url)
        if match:
            return match.group(1)
        return None
