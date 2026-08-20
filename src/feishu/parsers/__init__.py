"""
Message parsers package for different message types.

This package provides specialized parsers for:
- PDF links: PdfLinkParser
- DingTalk files: DingTalkFileParser

Each parser implements a common interface:
- parse(content/message_data, source) -> Optional[ParseResult]
- can_process(message_type) -> bool
"""

from src.feishu.parsers.pdf_link_parser import PdfLinkParser
from src.feishu.parsers.dingtalk_file_parser import DingTalkFileParser

__all__ = [
    'PdfLinkParser',
    'DingTalkFileParser',
]
