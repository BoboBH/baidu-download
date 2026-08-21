"""
Unified models for message parsing across different message types.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ParseResult:
    """
    Unified message parsing result supporting multiple message types.

    Supported message types:
    - baidupan: Baidu Pan share links
    - pdf_link: Direct PDF file links
    - wxchat-article: WeChat article links
    - dingtalk_pdf: DingTalk PDF files
    - dingtalk_zip: DingTalk ZIP archives

    Attributes:
        message_type: Type of message (baidupan, pdf_link, dingtalk_pdf, dingtalk_zip)
        unique_identifier: Unique identifier for deduplication (message type specific)
        source: Message source (feishu, dingtalk, etc.)

        # Baidu Pan specific fields
        share_link: Baidu Pan share link (for baidupan type)
        extraction_code: Baidu Pan extraction code (for baidupan type)
        folder_name: Baidu Pan folder name (for baidupan type)

        # PDF link specific fields
        pdf_url: Direct PDF URL (for pdf_link type)

        # DingTalk file specific fields
        file_id: DingTalk file ID (for dingtalk_pdf/dingtalk_zip types)
        space_id: DingTalk space ID (for dingtalk_pdf/dingtalk_zip types)
        download_code: DingTalk download code (for dingtalk_pdf/dingtalk_zip types)
        file_name: DingTalk file name (for dingtalk_pdf/dingtalk_zip types)

        # WeChat article specific fields
        wxchat_article_url: WeChat article URL (for wxchat-article type)
        wxchat_article_id: WeChat article ID (for wxchat-article type)

        # Raw message data
        raw_message: Raw message data as dictionary (optional)
    """
    # Common fields for all message types
    message_type: str
    unique_identifier: str
    source: str

    # Baidu Pan specific fields
    share_link: Optional[str] = None
    extraction_code: Optional[str] = None
    folder_name: Optional[str] = None

    # PDF link specific fields
    pdf_url: Optional[str] = None

    # DingTalk file specific fields
    file_id: Optional[str] = None
    space_id: Optional[str] = None
    download_code: Optional[str] = None
    file_name: Optional[str] = None

    # WeChat article specific fields
    wxchat_article_url: Optional[str] = None
    wxchat_article_id: Optional[str] = None

    # Raw message data
    raw_message: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ParseResult to dictionary.

        Returns:
            Dictionary containing all non-None fields
        """
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}

    def is_baidupan(self) -> bool:
        """Check if this is a Baidu Pan message."""
        return self.message_type == 'baidupan'

    def is_pdf_link(self) -> bool:
        """Check if this is a PDF link message."""
        return self.message_type == 'pdf_link'

    def is_dingtalk_pdf(self) -> bool:
        """Check if this is a DingTalk PDF message."""
        return self.message_type == 'dingtalk_pdf'

    def is_dingtalk_zip(self) -> bool:
        """Check if this is a DingTalk ZIP message."""
        return self.message_type == 'dingtalk_zip'

    def is_dingtalk_file(self) -> bool:
        """Check if this is any DingTalk file message."""
        return self.message_type in ('dingtalk_pdf', 'dingtalk_zip')

    def is_wxchat_article(self) -> bool:
        """Check if this is a WeChat article message."""
        return self.message_type == 'wxchat-article'
