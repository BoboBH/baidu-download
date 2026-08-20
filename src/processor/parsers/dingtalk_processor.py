"""
DingTalk file processor for DingTalk file downloads.

This processor handles downloading files from DingTalk using downloadCode and preparing them for SFTP upload.
Supports both PDF files and ZIP archives with structure preservation.
"""
import os
import zipfile
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from src.feishu.models import ParseResult
from src.utils.logger import get_logger


@dataclass
class DownloadResult:
    """
    Result of a DingTalk file download operation.

    Attributes:
        success: Whether the download was successful
        local_path: Path to the downloaded file
        file_size: Size of the downloaded file in bytes
        filename: Original filename from DingTalk
        error: Error message if download failed
        retryable: Whether the error is retryable (for failed downloads)
        temp_dir: Temporary directory for downloads
    """
    success: bool
    local_path: Optional[str] = None
    file_size: int = 0
    filename: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = False
    temp_dir: Optional[str] = None


@dataclass
class ProcessResult:
    """
    Result of DingTalk file processing operation.

    For PDF files, no processing is needed - they are ready for upload as-is.
    For ZIP files, extraction with structure preservation is performed.

    Attributes:
        success: Whether processing was successful
        processed_files: List of files ready for upload
        error: Error message if processing failed
        metadata: Additional processing metadata (extraction info, etc.)
    """
    success: bool
    processed_files: List[str]
    error: Optional[str] = None
    metadata: Optional[dict] = None


class DingTalkFileProcessor:
    """
    Processor for DingTalk file downloads.

    Handles downloading files from DingTalk using downloadCode and preparing them for SFTP upload.
    Supports both PDF files and ZIP archives with structure preservation.

    Features:
    - DownloadCode-based file download from DingTalk API
    - Stream-based download for memory efficiency
    - File size validation (PDF: 200MB, ZIP: 500MB, single file: 50MB)
    - Timeout handling (300 seconds default)
    - Automatic filename conflict resolution
    - ZIP extraction with structure preservation
    - Clean temporary file management
    - Comprehensive error classification with retryable field
    """

    def __init__(self, settings):
        """
        Initialize DingTalk file processor.

        Args:
            settings: Application settings object
        """
        self.settings = settings
        self.max_pdf_size_mb = getattr(settings, 'max_pdf_size_mb', 200)
        self.max_zip_size_mb = getattr(settings, 'max_zip_size_mb', 500)
        self.max_single_file_size_mb = getattr(settings, 'max_single_file_size_mb', 50)
        self.timeout = getattr(settings, 'dingtalk_file_timeout', 300)  # 300 seconds default
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
        return message_type in ['dingtalk_pdf', 'dingtalk_zip']

    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        Download DingTalk file using downloadCode.

        Args:
            parse_result: ParseResult containing download_code and file_name

        Returns:
            DownloadResult with download status and file information
        """
        download_code = parse_result.download_code
        file_name = parse_result.file_name
        message_type = parse_result.message_type

        if not download_code or not file_name:
            return DownloadResult(
                success=False,
                error="Missing downloadCode or file_name in parse result"
            )

        self.logger.info(f"Starting DingTalk file download: {file_name} (type: {message_type})")

        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='dingtalk_download_')
            self.logger.debug(f"Created temp directory: {self.temp_dir}")

            # Build DingTalk download URL
            download_url = f"https://api.dingtalk.com/media/download?downloadCode={download_code}"
            self.logger.info(f"DingTalk download URL: {download_url[:60]}...")

            # Determine size limit based on message type
            if message_type == 'dingtalk_pdf':
                max_size = self.max_pdf_size_mb * 1024 * 1024
                size_limit_desc = f"{self.max_pdf_size_mb} MB"
            else:  # dingtalk_zip
                max_size = self.max_zip_size_mb * 1024 * 1024
                size_limit_desc = f"{self.max_zip_size_mb} MB"

            # Start download with stream
            response = requests.get(
                download_url,
                stream=True,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )

            # Check HTTP status manually (don't use raise_for_status to handle errors properly)
            status_code = response.status_code
            if status_code != 200:
                error_msg = f"DingTalk文件下载HTTP错误: {status_code}"
                self.logger.error(f"{error_msg} - file: {file_name}")

                # 根据HTTP状态码判断是否可重试
                if status_code in [404, 403, 401, 410]:  # Not Found, Forbidden, Unauthorized, Gone
                    return DownloadResult(
                        success=False,
                        error=error_msg,
                        retryable=False  # 这些错误不可重试
                    )
                elif status_code == 429:  # Rate Limited
                    return DownloadResult(
                        success=False,
                        error=error_msg,
                        retryable=True  # 429可重试
                    )
                elif 500 <= status_code < 600:  # 服务器错误可重试
                    return DownloadResult(
                        success=False,
                        error=error_msg,
                        retryable=True
                    )
                else:
                    return DownloadResult(
                        success=False,
                        error=error_msg,
                        retryable=False
                    )

            # Check content-length header if available
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                if file_size > max_size:
                    self.logger.warning(
                        f"File exceeds size limit: {file_size / (1024*1024):.2f} MB > {size_limit_desc}"
                    )
                    return DownloadResult(
                        success=False,
                        error=f"文件超过大小限制: {file_size / (1024*1024):.2f} MB > {size_limit_desc}",
                        retryable=False  # 超过大小限制不可重试
                    )

                self.logger.info(f"File size from header: {file_size / (1024*1024):.2f} MB")

            # Local file path
            local_path = os.path.join(self.temp_dir, file_name)

            # Download with streaming to handle large files
            downloaded_size = 0
            chunk_size = 8192  # 8KB chunks

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Check size limit during download
                        if downloaded_size > max_size:
                            self.logger.warning(
                                f"Downloaded size exceeds limit: {downloaded_size / (1024*1024):.2f} MB"
                            )
                            return DownloadResult(
                                success=False,
                                error=f"文件下载过程中超过大小限制: {downloaded_size / (1024*1024):.2f} MB > {size_limit_desc}",
                                retryable=False  # 超过大小限制不可重试
                            )

            # Verify file was downloaded
            if not os.path.exists(local_path):
                return DownloadResult(
                    success=False,
                    error="下载完成但文件不存在"
                )

            # Get actual file size
            actual_size = os.path.getsize(local_path)
            self.logger.info(f"DingTalk file download completed: {file_name} ({actual_size / (1024*1024):.2f} MB)")

            return DownloadResult(
                success=True,
                local_path=local_path,
                file_size=actual_size,
                filename=file_name,
                temp_dir=self.temp_dir
            )

        except requests.exceptions.Timeout:
            error_msg = f"DingTalk文件下载超时 (>{self.timeout}秒)"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                retryable=True  # 超时错误可重试
            )

        except requests.exceptions.HTTPError as e:
            # This should rarely be hit since we handle HTTP status codes above
            status_code = getattr(e.response, 'status_code', 'Unknown') if hasattr(e, 'response') and e.response else 'Unknown'
            error_msg = f"DingTalk文件下载HTTP错误: {status_code}"
            self.logger.error(f"{error_msg} - {str(e)}")

            # 根据HTTP状态码判断是否可重试
            if status_code in [404, 403, 401, 410]:
                retryable = False
            elif status_code == 429:
                retryable = True
            elif 500 <= status_code < 600:
                retryable = True
            else:
                retryable = False

            return DownloadResult(
                success=False,
                error=error_msg,
                retryable=retryable
            )

        except requests.exceptions.RequestException as e:
            # 网络连接错误通常可重试
            error_msg = f"DingTalk文件下载网络错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                retryable=True  # 网络错误可重试
            )

        except IOError as e:
            # IO错误通常不可重试
            error_msg = f"DingTalk文件下载IO错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                retryable=False  # IO错误不可重试
            )

        except Exception as e:
            # 未知错误保守处理
            error_msg = f"DingTalk文件下载未知错误: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(
                success=False,
                error=error_msg,
                retryable=False  # 未知错误保守处理为不可重试
            )

    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        Process downloaded DingTalk file.

        For PDF files, no processing is needed - they are ready for upload as-is.
        For ZIP files, extraction with structure preservation is performed.

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

        message_type = parse_result.message_type

        if message_type == 'dingtalk_pdf':
            # Verify file exists for PDF processing
            if not os.path.exists(download_result.local_path):
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error=f"下载的文件不存在: {download_result.local_path}"
                )
            # PDF files don't need processing, they're ready for upload as-is
            self.logger.info(f"DingTalk PDF processing completed (no processing needed): {download_result.local_path}")
            return ProcessResult(
                success=True,
                processed_files=[download_result.local_path],
                metadata={
                    'file_size': download_result.file_size,
                    'original_filename': download_result.filename,
                    'file_type': 'pdf'
                }
            )

        elif message_type == 'dingtalk_zip':
            # ZIP files need extraction
            self.logger.info("Starting DingTalk ZIP file extraction")
            return self._extract_zip(download_result, parse_result)

        else:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"不支持的消息类型: {message_type}"
            )

    def _extract_zip(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        Extract ZIP file with structure preservation.

        Args:
            download_result: Result from download operation
            parse_result: Original parse result

        Returns:
            ProcessResult with extracted files ready for upload
        """
        zip_file_path = download_result.local_path
        zip_name = Path(zip_file_path).stem  # Remove .zip extension

        # Create extraction directory
        temp_base_dir = download_result.temp_dir if download_result.temp_dir else self.temp_dir
        extract_dir = os.path.join(temp_base_dir, zip_name)
        os.makedirs(extract_dir, exist_ok=True)

        self.logger.info(f"Extracting ZIP file to: {extract_dir}")

        try:
            extracted_files = []
            total_size = 0
            skipped_large_files = 0
            max_single_size = self.max_single_file_size_mb * 1024 * 1024

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Get file list from ZIP
                file_list = zip_ref.namelist()
                self.logger.info(f"ZIP contains {len(file_list)} files")

                for file_info in file_list:
                    # Skip directories
                    if file_info.endswith('/'):
                        continue

                    try:
                        # Extract file
                        zip_ref.extract(file_info, extract_dir)

                        extracted_file_path = os.path.join(extract_dir, file_info)
                        file_size = os.path.getsize(extracted_file_path)
                        total_size += file_size

                        # Check single file size limit
                        if file_size > max_single_size:
                            self.logger.warning(f"Skipping oversized file: {file_info} ({file_size / (1024*1024):.2f} MB)")
                            os.remove(extracted_file_path)
                            skipped_large_files += 1
                        else:
                            extracted_files.append(extracted_file_path)
                            self.logger.debug(f"Extracted file: {file_info} ({file_size / 1024:.2f} KB)")

                    except Exception as e:
                        self.logger.warning(f"Failed to extract file {file_info}: {e}")
                        continue

            self.logger.info(f"ZIP extraction completed: {len(extracted_files)} files, total size: {total_size / (1024*1024):.2f} MB")
            if skipped_large_files > 0:
                self.logger.warning(f"Skipped {skipped_large_files} oversized files")

            if not extracted_files:
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="ZIP解压后无有效文件（可能所有文件都超过大小限制）"
                )

            return ProcessResult(
                success=True,
                processed_files=extracted_files,
                metadata={
                    'original_zip': download_result.filename,
                    'extracted_count': len(extracted_files),
                    'total_size': total_size,
                    'skipped_count': skipped_large_files,
                    'extract_dir': extract_dir,
                    'file_type': 'zip'
                }
            )

        except zipfile.BadZipFile:
            self.logger.error("ZIP file is corrupted")
            return ProcessResult(
                success=False,
                processed_files=[],
                error="ZIP文件损坏，无法解压"
            )
        except Exception as e:
            self.logger.error(f"ZIP extraction error: {e}")
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"ZIP解压异常: {str(e)}"
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
        message_type = parse_result.message_type

        if message_type == 'dingtalk_pdf':
            # PDF files upload directly
            for local_path in process_result.processed_files:
                remote_filename = self._generate_remote_filename(parse_result)
                remote_path = f"/{remote_filename}"
                upload_files.append({
                    'local_path': local_path,
                    'remote_path': remote_path
                })
                self.logger.info(f"Upload file prepared: {local_path} -> {remote_path}")

        elif message_type == 'dingtalk_zip':
            # ZIP extracted files, preserve directory structure
            extract_dir = process_result.metadata.get('extract_dir', '')
            original_zip = parse_result.file_name.replace('.zip', '')

            for local_path in process_result.processed_files:
                # Calculate relative path to preserve structure
                rel_path = Path(local_path).relative_to(extract_dir)

                # Remote path: original_zip/original_structure
                # Convert to forward slashes for cross-platform compatibility
                rel_path_str = str(rel_path).replace('\\', '/')
                remote_path = f"/{original_zip}/{rel_path_str}"

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

    def _generate_remote_filename(self, parse_result: ParseResult) -> str:
        """
        Generate remote filename with timestamp to avoid conflicts.

        Args:
            parse_result: Original parse result

        Returns:
            Remote filename with timestamp prefix
        """
        # Get original filename
        original_filename = parse_result.file_name if parse_result.file_name else 'file.pdf'

        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Combine timestamp with original filename
        name_without_ext, ext = os.path.splitext(original_filename)
        remote_filename = f"{name_without_ext}_{timestamp}{ext}"

        return remote_filename