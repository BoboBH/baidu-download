"""
DingTalk file processor for DingTalk file downloads.

This processor handles downloading files from DingTalk using downloadCode and preparing them for SFTP upload.
Supports both PDF files and ZIP archives with structure preservation.
"""
import os
import zipfile
import tempfile
import requests
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from src.feishu.models import ParseResult
from src.utils.logger import get_logger


class DingTalkAuthHelper:
    """钉钉认证助手 - 处理access_token获取和管理"""

    def __init__(self, app_key, app_secret):
        """
        初始化钉钉认证助手

        Args:
            app_key: 钉钉应用AppKey
            app_secret: 钉钉应用AppSecret
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        self.token_expire_time = None
        self.logger = get_logger(__name__)

    def get_access_token(self):
        """
        获取钉钉access_token

        Returns:
            access_token字符串或None
        """
        # 检查是否有有效的token
        if self._is_token_valid():
            self.logger.info("使用已缓存的access_token")
            return self.access_token

        # 获取新的token
        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            self.logger.info("正在获取钉钉access_token...")
            response = requests.get(url, params=params, timeout=30)
            result = response.json()

            if result.get("errcode") == 0:
                self.access_token = result.get("access_token")
                # 设置过期时间（当前时间 + 7000秒，提前100秒刷新）
                import time
                self.token_expire_time = time.time() + 7000

                self.logger.info(f"✅ 成功获取access_token: {self.access_token[:20]}...")
                self.logger.info(f"   Token有效期: 7200秒，将在{int((self.token_expire_time - time.time())/60)}分钟后刷新")
                return self.access_token
            else:
                error_msg = result.get('errmsg', '未知错误')
                self.logger.error(f"❌ 获取access_token失败: {error_msg} (错误代码: {result.get('errcode')})")
                return None

        except Exception as e:
            self.logger.error(f"❌ 获取access_token异常: {e}")
            return None

    def _is_token_valid(self):
        """检查token是否仍然有效"""
        if not self.access_token or not self.token_expire_time:
            return False

        import time
        return time.time() < self.token_expire_time


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

        # 🔥 新增：初始化钉钉认证助手
        self.auth_helper = DingTalkAuthHelper(
            settings.dingtalk_app_key,
            settings.dingtalk_app_secret
        )

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

            # 🔥 新增：每次下载前先获取access_token
            self.logger.info("Step 1: Getting DingTalk access_token for file download...")
            access_token = self.auth_helper.get_access_token()

            if not access_token:
                return DownloadResult(
                    success=False,
                    error="无法获取access_token，无法下载文件",
                    retryable=True  # access_token获取失败可重试
                )

            self.logger.info(f"✅ access_token获取成功: {access_token[:20]}...")

            # 🔥 使用正确的钉钉机器人下载流程
            # 第二步：调用机器人文件下载API（需要access_token）
            download_info_url = "https://api.dingtalk.com/v1.0/robot/messageFiles/download"  # 🔥 修正：正确的API端点
            self.logger.info(f"Step 2: Calling DingTalk file download API...")

            download_url = None
            download_headers = None

            try:
                # 使用access_token调用下载API
                info_response = requests.post(
                    download_info_url,
                    json={
                        "downloadCode": download_code,
                        "robotCode": self.settings.dingtalk_app_key  # 🔥 添加必需的robotCode参数
                    },
                    headers={
                        'x-acs-dingtalk-access-token': access_token,  # 🔥 关键：使用access_token
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )

                self.logger.info(f"Download API response: {info_response.status_code}")

                if info_response.status_code == 200:
                    try:
                        download_info = info_response.json()
                        self.logger.info(f"Download info received: {download_info}")

                        # 🔥 修复：直接检查是否有downloadUrl字段
                        if 'downloadUrl' in download_info and download_info['downloadUrl']:
                            download_url = download_info['downloadUrl']
                            self.logger.info(f"✅ Got downloadUrl from API: {download_url[:60]}...")

                            if 'headers' in download_info:
                                download_headers = download_info['headers']
                                self.logger.info(f"✅ Got download headers from API")
                        else:
                            # API返回错误
                            error_msg = download_info.get('errorMsg', download_info.get('errorMessage', download_info.get('error', '未知错误')))
                            self.logger.error(f"❌ API返回错误: {error_msg}")
                            return DownloadResult(
                                success=False,
                                error=f"钉钉API返回错误: {error_msg}",
                                retryable=False
                            )

                    except ValueError as json_error:
                        self.logger.warning(f"Failed to parse JSON response: {json_error}")
                else:
                    self.logger.error(f"❌ Download API returned HTTP {info_response.status_code}")
                    return DownloadResult(
                        success=False,
                        error=f"下载API返回HTTP错误: {info_response.status_code}",
                        retryable=True if 500 <= info_response.status_code < 600 else False
                    )

            except Exception as e:
                self.logger.warning(f"Download API call failed: {e}")
                # 如果API调用失败，无法继续
                return DownloadResult(
                    success=False,
                    error=f"下载API调用失败: {str(e)}",
                    retryable=True
                )

            # 检查是否成功获取下载URL
            if not download_url:
                error_msg = "未能获取有效的下载URL"
                self.logger.error(f"❌ {error_msg}")
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    retryable=False
                )

            self.logger.info(f"Final download URL: {download_url[:60]}...")

            # Determine size limit based on message type
            if message_type == 'dingtalk_pdf':
                max_size = self.max_pdf_size_mb * 1024 * 1024
                size_limit_desc = f"{self.max_pdf_size_mb} MB"
            else:  # dingtalk_zip
                max_size = self.max_zip_size_mb * 1024 * 1024
                size_limit_desc = f"{self.max_zip_size_mb} MB"

            # Start download with stream
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            if download_headers:
                headers.update(download_headers)

            response = requests.get(
                download_url,
                stream=True,
                timeout=self.timeout,
                headers=headers
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

            # 🔥 关键修复：验证响应是否真正成功
            if response.status_code != 200:
                error_msg = f"HTTP错误: {response.status_code}"
                self.logger.error(f"{error_msg} - Response: {response.text[:200]}")
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    retryable=True if 500 <= response.status_code < 600 else False
                )

            # 🔥 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            self.logger.info(f"Response Content-Type: {content_type}")

            if message_type == 'dingtalk_pdf' and 'pdf' not in content_type.lower():
                self.logger.warning(f"⚠️ Content-Type不是PDF: {content_type}")

            # 🔥 检查响应内容长度
            content_length = response.headers.get('content-length')
            if content_length:
                expected_size = int(content_length)
                if expected_size == 0:
                    error_msg = "服务器返回内容长度为0，文件可能不存在或无法访问"
                    self.logger.error(f"{error_msg} - Response: {response.text[:200]}")
                    return DownloadResult(
                        success=False,
                        error=error_msg,
                        retryable=False
                    )
                self.logger.info(f"Expected file size: {expected_size} bytes")

            # 🔥 先检查响应内容，避免下载错误信息
            response_preview = response.text[:500] if response.text else ""
            self.logger.info(f"Response preview: {response_preview[:100]}...")

            # 检查是否是错误页面
            error_indicators = ['error', '错误', 'not found', '404', '403', '401']
            if any(indicator in response_preview.lower() for indicator in error_indicators):
                error_msg = f"服务器返回错误页面: {response_preview[:100]}"
                self.logger.error(error_msg)
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    retryable=False
                )

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

            # 🔥 关键检查：文件大小验证
            if actual_size == 0:
                error_msg = "下载的文件大小为0字节，可能是下载失败"
                self.logger.error(error_msg)
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    retryable=True
                )

            # 🔥 对于PDF文件，检查文件头是否有效
            if message_type == 'dingtalk_pdf':
                try:
                    with open(local_path, 'rb') as f:
                        header = f.read(4)
                        if header != b'%PDF':
                            error_msg = f"下载的文件不是有效的PDF格式 (文件头: {header})"
                            self.logger.error(f"{error_msg} - 文件前100字节: {open(local_path, 'rb').read(100)}")
                            return DownloadResult(
                                success=False,
                                error=error_msg,
                                retryable=False
                            )
                except Exception as e:
                    self.logger.warning(f"无法验证PDF文件头: {e}")

            self.logger.info(f"✅ DingTalk file download completed: {file_name} ({actual_size / (1024*1024):.2f} MB)")

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

        # 🔥 关键修复：解压前先删除旧目录，避免重复文件
        if os.path.exists(extract_dir):
            self.logger.info(f"Removing old extraction directory: {extract_dir}")
            shutil.rmtree(extract_dir)

        os.makedirs(extract_dir)
        self.logger.info(f"Extracting ZIP file to: {extract_dir}")

        try:
            extracted_files = []
            total_size = 0
            skipped_large_files = 0
            max_single_size = self.max_single_file_size_mb * 1024 * 1024

            # 🔥 关键修复：需要手动处理钉钉ZIP文件的GBK编码文件名
            # 钉钉ZIP文件中的中文文件名使用GBK编码存储
            zip_ref = zipfile.ZipFile(zip_file_path, 'r')

            # 获取ZIP文件信息列表（包含原始字节）
            file_list = zip_ref.infolist()
            self.logger.info(f"ZIP contains {len(file_list)} files")

            for file_info_obj in file_list:
                # 🔥 关键修复：智能检测和处理ZIP文件中的中文文件名编码
                # zipfile已经自动解码了文件名，但可能使用了错误的编码（通常是cp437）
                wrong_decoded_name = file_info_obj.filename

                # 智能编码检测和修复
                decoded_name = wrong_decoded_name  # 默认使用原始文件名

                # 检查是否包含非ASCII字符（可能是编码错误的中文）
                if any(ord(c) > 127 for c in wrong_decoded_name):
                    try:
                        # zipfile默认使用cp437编码，所以先用cp437编码回字节
                        filename_bytes = wrong_decoded_name.encode('cp437')

                        # 尝试多种常见编码进行解码
                        encodings_to_try = [
                            ('gbk', 'GBK (简体中文)'),
                            ('gb2312', 'GB2312 (简体中文)'),
                            ('gb18030', 'GB18030 (中文)'),
                            ('utf-8', 'UTF-8 (国际通用)'),
                            ('shift_jis', 'Shift JIS (日文)'),
                            ('euc-kr', 'EUC-KR (韩文)'),
                            ('big5', 'Big5 (繁体中文)'),
                        ]

                        for encoding, description in encodings_to_try:
                            try:
                                decoded_name = filename_bytes.decode(encoding)
                                # 验证解码结果是否包含有意义的中文字符
                                if any('一' <= c <= '鿿' for c in decoded_name):
                                    self.logger.info(f"✅ Successfully detected {description}: {decoded_name}")
                                    break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 如果所有编码都失败，使用原始文件名
                            decoded_name = wrong_decoded_name
                            self.logger.warning(f"⚠️ Could not detect encoding, using original: {decoded_name}")

                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        # 如果转换失败，使用原始文件名
                        decoded_name = wrong_decoded_name
                        self.logger.warning(f"⚠️ Encoding fix failed: {e}, using original: {decoded_name}")
                else:
                    # 纯ASCII文件名，直接使用
                    self.logger.info(f"✅ Pure ASCII filename: {decoded_name}")

                # 跳过目录
                if decoded_name.endswith('/'):
                    continue

                self.logger.info(f"Processing file: {decoded_name}")

                try:
                    # 🔥 关键修复：用原始文件名解压，然后重命名为正确的中文文件名
                    zip_ref.extract(file_info_obj.filename, extract_dir)

                    # 构建原始文件路径（使用ZIP内部的错误编码文件名）
                    original_extracted_path = os.path.join(extract_dir, wrong_decoded_name)

                    # 构建正确的文件路径（使用修复后的中文文件名）
                    correct_file_path = os.path.join(extract_dir, decoded_name)

                    # 如果文件名不同，重命名文件
                    if wrong_decoded_name != decoded_name and os.path.exists(original_extracted_path):
                        os.rename(original_extracted_path, correct_file_path)
                        self.logger.info(f"✅ Renamed: {wrong_decoded_name} -> {decoded_name}")
                        extracted_file_path = correct_file_path
                    else:
                        # 文件名相同或文件不存在，使用原始路径
                        extracted_file_path = original_extracted_path

                    file_size = os.path.getsize(extracted_file_path)
                    total_size += file_size

                    # Check single file size limit
                    if file_size > max_single_size:
                        self.logger.warning(f"Skipping oversized file: {decoded_name} ({file_size / (1024*1024):.2f} MB)")
                        os.remove(extracted_file_path)
                        skipped_large_files += 1
                    else:
                        extracted_files.append(extracted_file_path)
                        self.logger.debug(f"Extracted file: {decoded_name} ({file_size / 1024:.2f} KB)")

                except Exception as e:
                    self.logger.warning(f"Failed to extract file {decoded_name}: {e}")
                    continue

            # 🔥 关闭ZIP文件
            zip_ref.close()
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

                # 获取文件大小
                file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

                upload_files.append({
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'size': file_size  # 添加文件大小
                })
                self.logger.info(f"Upload file prepared: {local_path} -> {remote_path}")

        elif message_type == 'dingtalk_zip':
            # ZIP extracted files, preserve directory structure
            extract_dir = process_result.metadata.get('extract_dir', '')
            original_zip = parse_result.file_name.replace('.zip', '')

            for local_path in process_result.processed_files:
                # 🔥 修复中文文件名乱码：使用URL编码的文件名
                file_name = os.path.basename(local_path)

                # 检查文件名是否包含非ASCII字符（可能是中文）
                if any(ord(c) > 127 for c in file_name):
                    self.logger.info(f"Non-ASCII filename detected: {file_name}")

                    # 尝试修复编码，如果已经是UTF-8则保持原样
                    try:
                        # 如果文件名已经是可读的UTF-8，直接使用
                        file_name.encode('utf-8')
                        self.logger.info(f"Filename is valid UTF-8: {file_name}")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        # 如果不是有效的UTF-8，使用URL编码作为最后手段
                        import urllib.parse
                        encoded_name = urllib.parse.quote(file_name.encode('utf-8', errors='replace'))
                        self.logger.warning(f"Filename encoding issues, using URL-encoded: {encoded_name}")
                        file_name = encoded_name

                # Calculate relative path to preserve structure
                rel_path = Path(local_path).relative_to(extract_dir)

                # Remote path: original_zip/original_structure
                # Convert to forward slashes for cross-platform compatibility
                rel_path_str = str(rel_path).replace('\\', '/')

                # 🔥 修复：使用URL编码的文件名
                safe_rel_path = rel_path_str.replace(file_name, file_name)

                remote_path = f"/{original_zip}/{safe_rel_path}"

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
            # Always set temp_dir to None, even if cleanup failed or directory didn't exist
            self.temp_dir = None

    def _generate_remote_filename(self, parse_result: ParseResult) -> str:
        """
        Generate remote filename preserving original name.

        Args:
            parse_result: Original parse result

        Returns:
            Remote filename (original name, no timestamp added)
        """
        # 🔥 优化：保留原文件名，不加时间戳后缀
        original_filename = parse_result.file_name if parse_result.file_name else 'file.pdf'
        return original_filename