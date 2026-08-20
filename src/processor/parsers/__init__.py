"""
Processors package for different message types.

This package provides specialized processors for:
- PDF links: PdfLinkProcessor for direct PDF file downloads
- DingTalk files: DingTalkFileProcessor for DingTalk file downloads

Each processor implements a common interface:
- can_process(message_type) -> bool
- download(parse_result) -> DownloadResult
- process(download_result, parse_result) -> ProcessResult
- get_upload_files(process_result, parse_result) -> List[dict]
- cleanup() -> None
"""

from src.processor.parsers.pdf_processor import PdfLinkProcessor

__all__ = [
    'PdfLinkProcessor',
]