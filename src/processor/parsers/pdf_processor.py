"""
PDF link processor for direct PDF file downloads.

This processor handles downloading PDF files from HTTP URLs and preparing them for SFTP upload.
"""
import os
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse
from src.feishu.models import ParseResult
from src.utils.logger import get_logger


@dataclass
class DownloadResult:
    """
    Result of a PDF download operation.

    Attributes:
        success: Whether the download was successful
        local_path: Path to the downloaded file
        file_size: Size of the downloaded file in bytes
        filename: Original filename from the URL
        error: Error message if download failed
    """
    success: bool
    local_path: Optional[str] = None
    file_size: int = 0
    filename: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ProcessResult:
    """
    Result of PDF processing operation.

    For PDF files, no processing is needed - they are ready for upload as-is.

    Attributes:
        success: Whether processing was successful
        processed_files: List of files ready for upload
        error: Error message if processing failed
    """
    success: bool
    processed_files: List[str]
    error: Optional[str] = None


class PdfLinkProcessor:
    """
    Processor for PDF link downloads.

    Handles downloading PDF files from HTTP URLs and preparing them for SFTP upload.

    Features:
    - Stream-based download for memory efficiency
    - File size validation (200MB default limit)
    - Timeout handling (300 seconds default)
    - Automatic filename conflict resolution
    - Clean temporary file management
    """

    def __init__(self, settings):
        """
        Initialize PDF processor.

        Args:
            settings: Application settings object with max_pdf_size_mb attribute
        """
        self.settings = settings
        self.max_pdf_size_mb = getattr(settings, 'max_pdf_size_mb', 200)
        self.timeout = getattr(settings, 'wxchat_pdf_timeout', 300)  # 300 seconds default
        self.temp_dir = None
        self.logger = get_logger(__name__)

    def can_process(self, message_type: str) -> bool:
        """
        Check if this processor can handle the given message type.

        Args:
            message_type: Type of message to check

        Returns:
            True if this processor can process the message type
        """
        return message_type == 'pdf_link'

    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        Download PDF file from URL.

        Args:
            parse_result: ParseResult containing pdf_url

        Returns:
            DownloadResult with download status and file information
        """
        if not parse_result.pdf_url:
            return DownloadResult(
                success=False,
                error="No PDF URL in parse result"
            )

        pdf_url = parse_result.pdf_url
        self.logger.info(f"Starting PDF download: {pdf_url[:100]}...")

        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='pdf_download_')
            self.logger.debug(f"Created temp directory: {self.temp_dir}")

            # Extract filename from URL
            original_filename = self._extract_filename_from_url(pdf_url)
            if not original_filename:
                original_filename = 'downloaded.pdf'

            # Local file path
            local_path = os.path.join(self.temp_dir, original_filename)

            # Start download with stream
            response = requests.get(
                pdf_url,
                stream=True,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )

            # Check HTTP status
            response.raise_for_status()

            # Check content-length header if available
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                max_size = self.max_pdf_size_mb * 1024 * 1024
                if file_size > max_size:
                    self.logger.warning(
                        f"PDF file exceeds size limit: {file_size / (1024*1024):.2f} MB > {self.max_pdf_size_mb} MB"
                    )
                    return DownloadResult(
                        success=False,
                        error=f"PDF文件超过大小限制: {file_size / (1024*1024):.2f} MB > {self.max_pdf_size_mb} MB"
                    )

                self.logger.info(f"PDF file size from header: {file_size / (1024*1024):.2f} MB")

            # Download with streaming to handle large files
            downloaded_size = 0
            chunk_size = 8192  # 8KB chunks

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Check size limit during download
                        max_size = self.max_pdf_size_mb * 1024 * 1024
                        if downloaded_size > max_size:
                            self.logger.warning(
                                f"Downloaded size exceeds limit: {downloaded_size / (1024*1024):.2f} MB"
                            )
                            return DownloadResult(
                                success=False,
                                error=f"PDF文件下载过程中超过大小限制: {downloaded_size / (1024*1024):.2f} MB > {self.max_pdf_size_mb} MB"
                            )

            # Verify file was downloaded
            if not os.path.exists(local_path):
                return DownloadResult(
                    success=False,
                    error="下载完成但文件不存在"
                )

            # Get actual file size
            actual_size = os.path.getsize(local_path)
            self.logger.info(f"PDF download completed: {actual_size / (1024*1024):.2f} MB")

            return DownloadResult(
                success=True,
                local_path=local_path,
                file_size=actual_size,
                filename=original_filename
            )

        except requests.exceptions.Timeout:
            error_msg = f"PDF下载超时 (>{self.timeout}秒)"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg
            )

        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, 'status_code', 'Unknown') if hasattr(e, 'response') and e.response else 'Unknown'
            error_msg = f"PDF下载HTTP错误: {status_code}"
            self.logger.error(f"{error_msg} - {str(e)}")
            return DownloadResult(
                success=False,
                error=error_msg
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"PDF下载网络错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg
            )

        except IOError as e:
            error_msg = f"PDF下载文件IO错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg
            )

        except Exception as e:
            error_msg = f"PDF下载未知错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg
            )

    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        Process downloaded PDF file.

        For PDF files, no processing is needed - they are ready for upload as-is.

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

        if not download_result.local_path:
            return ProcessResult(
                success=False,
                processed_files=[],
                error="下载结果中没有本地文件路径"
            )

        # Verify file exists
        if not os.path.exists(download_result.local_path):
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"下载的文件不存在: {download_result.local_path}"
            )

        self.logger.info(f"PDF processing completed (no processing needed): {download_result.local_path}")

        # PDF files don't need processing, they're ready for upload as-is
        return ProcessResult(
            success=True,
            processed_files=[download_result.local_path]
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
        for local_path in process_result.processed_files:
            # Generate remote filename with timestamp to avoid conflicts
            remote_filename = self._generate_remote_filename(parse_result)
            remote_path = f"/{remote_filename}"

            upload_files.append({
                'local_path': local_path,
                'remote_path': remote_path
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
            # Always set temp_dir to None, even if cleanup failed or directory didn't exist
            self.temp_dir = None

    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """
        Extract filename from PDF URL.

        Args:
            url: PDF URL to extract filename from

        Returns:
            Filename if found, None otherwise
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            path = parsed.path

            # Extract filename from path
            if path:
                filename = os.path.basename(path)
                if filename and filename.lower().endswith('.pdf'):
                    return filename

            return None

        except Exception as e:
            self.logger.warning(f"Failed to extract filename from URL: {url[:100]}, error: {e}")
            return None

    def _generate_remote_filename(self, parse_result: ParseResult) -> str:
        """
        Generate remote filename with timestamp to avoid conflicts.

        Args:
            parse_result: Original parse result

        Returns:
            Remote filename with timestamp prefix
        """
        # Get original filename
        original_filename = 'file.pdf'
        if parse_result.pdf_url:
            extracted = self._extract_filename_from_url(parse_result.pdf_url)
            if extracted:
                original_filename = extracted

        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Combine timestamp with original filename
        remote_filename = f"{timestamp}_{original_filename}"

        return remote_filename