"""
BaiduPan processor for Baidu Pan share link downloads.

This processor handles downloading files from Baidu Pan share links and preparing them for SFTP upload.
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from src.feishu.models import ParseResult
from src.utils.logger import get_logger


@dataclass
class DownloadResult:
    """
    Result of a BaiduPan download operation.

    Attributes:
        success: Whether the download was successful
        local_paths: Paths to the downloaded files (BaiduPan may download multiple files)
        file_sizes: Sizes of the downloaded files in bytes
        error: Error message if download failed
        retryable: Whether the error is retryable (for failed downloads)
    """
    success: bool
    local_paths: List[str] = None
    file_sizes: List[int] = None
    error: Optional[str] = None
    retryable: bool = False

    def __post_init__(self):
        if self.local_paths is None:
            self.local_paths = []
        if self.file_sizes is None:
            self.file_sizes = []


@dataclass
class ProcessResult:
    """
    Result of BaiduPan processing operation.

    For BaiduPan files, processing means identifying PDF files that are ready for upload.

    Attributes:
        success: Whether processing was successful
        processed_files: List of files ready for upload
        error: Error message if processing failed
    """
    success: bool
    processed_files: List[str]
    error: Optional[str] = None


class BaiduPanProcessor:
    """
    Processor for BaiduPan share link downloads.

    Handles downloading files from Baidu Pan share links and preparing them for SFTP upload.

    Features:
    - BaiduPCS-Go integration for download
    - Automatic PDF file detection
    - Multiple file handling
    - Clean temporary file management
    """

    def __init__(self, settings):
        """
        Initialize BaiduPan processor.

        Args:
            settings: Application settings object
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.temp_dir = None

    def can_process(self, message_type: str) -> bool:
        """
        Check if this processor can handle the given message type.

        Args:
            message_type: Type of message to check

        Returns:
            True if this processor can process the message type
        """
        return message_type == 'baidupan'

    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        Download files from BaiduPan share link.

        This is a placeholder implementation. The actual BaiduPan download functionality
        is implemented in the existing FileProcessor class.

        Args:
            parse_result: ParseResult containing share_link, extraction_code, folder_name

        Returns:
            DownloadResult with download status and file information
        """
        # Placeholder implementation
        # The actual BaiduPan download uses BaiduPCS-Go and is handled by FileProcessor
        self.logger.info("BaiduPan download placeholder - implemented in FileProcessor")

        return DownloadResult(
            success=False,
            error="BaiduPan download not implemented in processor layer"
        )

    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        Process downloaded BaiduPan files.

        For BaiduPan files, processing means identifying PDF files ready for upload.

        Args:
            download_result: Result from download operation
            parse_result: Original parse result

        Returns:
            ProcessResult with processed files ready for upload
        """
        if not download_result.success:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=download_result.error
            )

        # Filter for PDF files (BaiduPan may have multiple files)
        pdf_files = []
        for local_path in download_result.local_paths:
            if local_path.lower().endswith('.pdf') and os.path.exists(local_path):
                pdf_files.append(local_path)

        if not pdf_files:
            return ProcessResult(
                success=False,
                processed_files=[],
                error="No PDF files found in downloaded content"
            )

        self.logger.info(f"BaiduPan processing completed: {len(pdf_files)} PDF files")

        return ProcessResult(
            success=True,
            processed_files=pdf_files
        )

    def get_upload_files(self, process_result: ProcessResult, parse_result: ParseResult) -> List[dict]:
        """
        Generate upload file list from process result.

        Args:
            process_result: Result from process operation
            parse_result: Original parse result

        Returns:
            List of dictionaries with upload file information:
            [{'local_path': str, 'remote_path': str}]
        """
        if not process_result.success:
            return []

        upload_files = []
        folder_name = parse_result.folder_name if parse_result.folder_name else 'baidupan'

        for local_path in process_result.processed_files:
            # Extract filename from local path
            filename = os.path.basename(local_path)

            # Remote path: folder_name/filename
            remote_path = f"/{folder_name}/{filename}"

            # 获取文件大小
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            upload_files.append({
                'local_path': local_path,
                'remote_path': remote_path,
                'size': file_size  # 添加文件大小
            })

            self.logger.info(f"Upload file prepared: {local_path} -> {remote_path}")

        return upload_files

    def cleanup(self):
        """
        Clean up temporary files and directories.

        Removes the temporary download directory and all its contents.
        """
        if self.temp_dir:
            if os.path.exists(self.temp_dir):
                try:
                    import shutil
                    shutil.rmtree(self.temp_dir)
                    self.logger.info(f"Cleaned up temp directory: {self.temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp directory: {self.temp_dir}, error: {e}")
            self.temp_dir = None
