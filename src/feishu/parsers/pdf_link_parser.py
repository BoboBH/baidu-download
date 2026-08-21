"""
PDF link parser for direct PDF file URLs.
"""
import re
from typing import Optional
from src.feishu.models import ParseResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PdfLinkParser:
    """
    Parser for direct PDF file links.

    Handles messages containing direct URLs to PDF files.
    """

    # Pattern to match PDF URLs
    # Matches http:// or https:// followed by any characters ending with .pdf
    PDF_PATTERN = re.compile(r'(https?://[^\s]+\.pdf)')

    def parse(self, content: str, source: str = 'feishu') -> Optional[ParseResult]:
        """
        Parse message content for PDF links.

        Args:
            content: Message content to parse
            source: Message source (feishu, dingtalk, etc.)

        Returns:
            ParseResult with message_type='pdf_link' if PDF link found
            None if no valid PDF link found
        """
        if not content:
            logger.warning("Empty message content for PDF link parsing")
            return None

        # Search for PDF URLs
        match = self.PDF_PATTERN.search(content)
        if not match:
            logger.debug(f"No PDF link found in message: {content[:50]}...")
            return None

        pdf_url = match.group(1).strip()

        # Validate the PDF URL
        if not self._is_valid_pdf_url(pdf_url):
            logger.warning(f"Invalid PDF URL: {pdf_url[:100]}...")
            return None

        logger.info(f"PDF link parsed successfully: {pdf_url[:100]}...")

        # Use the PDF URL as unique identifier for deduplication
        unique_identifier = pdf_url

        return ParseResult(
            message_type='pdf_link',
            unique_identifier=unique_identifier,
            source=source,
            pdf_url=pdf_url,
            share_link=pdf_url  # 设置share_link字段，统一使用share_link存储URL
        )

    def _is_valid_pdf_url(self, url: str) -> bool:
        """
        Validate if the URL is a valid PDF URL.

        Args:
            url: URL to validate

        Returns:
            True if valid PDF URL, False otherwise
        """
        if not url:
            return False

        # Basic validation: must start with http:// or https:// and end with .pdf
        if not (url.startswith('http://') or url.startswith('https://')):
            return False

        if not url.lower().endswith('.pdf'):
            return False

        # Additional validation: URL should not be too long
        if len(url) > 2000:
            logger.warning(f"PDF URL too long: {len(url)} characters")
            return False

        return True

    def can_process(self, message_type: str) -> bool:
        """
        Check if this parser can process the given message type.

        Args:
            message_type: Type of message to check

        Returns:
            True if this parser can process the message type
        """
        return message_type == 'pdf_link'
