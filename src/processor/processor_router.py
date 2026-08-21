"""
统一的文件处理器路由器 - 根据消息类型自动选择合适的处理器

支持的消息类型：
- baidupan: 百度网盘链接 -> FileProcessor
- dingtalk_pdf, dingtalk_zip: 钉钉文件 -> DingTalkFileProcessor
- pdf_link: 外部PDF链接 -> 直接下载上传
"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.processor.file_processor import FileProcessor
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
from src.processor.parsers.wxchat_article_processor import WxchatArticleProcessor
from src.uploader.sftp_client import SFTPClient
from src.database.models import ExecutionSummary
from src.feishu.models import ParseResult
from src.utils.logger import get_logger
import tempfile
import os
import requests

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """统一的处理结果"""
    success: bool
    message_type: str
    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    metadata: Optional[dict] = None


class ProcessorRouter:
    """
    统一的文件处理器路由器

    根据消息类型自动选择合适的处理器，避免手动写死逻辑
    """

    def __init__(self, settings: Optional[Settings] = None, enable_sftp=True):
        """
        初始化处理器路由器

        Args:
            settings: 配置对象
            enable_sftp: 是否启用SFTP上传
        """
        self.settings = settings or Settings()
        self.enable_sftp = enable_sftp

        # 初始化各个处理器
        self.baidu_processor = FileProcessor(enable_sftp=enable_sftp)
        self.dingtalk_processor = DingTalkFileProcessor(self.settings)
        self.wxchat_article_processor = WxchatArticleProcessor(self.settings)
        self.sftp_client = SFTPClient()

        if enable_sftp:
            self.sftp_client.connect()

        logger.info("ProcessorRouter initialized successfully")

    def process_message(self, parse_result: ParseResult) -> ProcessResult:
        """
        根据消息类型路由到合适的处理器

        Args:
            parse_result: 解析结果

        Returns:
            ProcessResult: 处理结果
        """
        start_time = datetime.now()
        message_type = parse_result.message_type

        logger.info(f"Processing message with type: {message_type}")

        try:
            # 路由到合适的处理器
            if message_type == 'baidupan':
                return self._process_baidupan(parse_result, start_time)
            elif message_type in ['dingtalk_pdf', 'dingtalk_zip']:
                return self._process_dingtalk_file(parse_result, start_time)
            elif message_type == 'pdf_link':
                return self._process_pdf_link(parse_result, start_time)
            elif message_type == 'wxchat-article':
                return self._process_wxchat_article(parse_result, start_time)
            else:
                return ProcessResult(
                    success=False,
                    message_type=message_type,
                    error_message=f"不支持的消息类型: {message_type}"
                )

        except Exception as e:
            logger.error(f"Error processing message type {message_type}: {e}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ProcessResult(
                success=False,
                message_type=message_type,
                error_message=str(e),
                processing_time_ms=processing_time
            )

    def _process_baidupan(self, parse_result: ParseResult, start_time: datetime) -> ProcessResult:
        """处理百度网盘链接"""
        logger.info("Routing to BaiduPan processor...")

        summary = self.baidu_processor.process_files(
            share_link=parse_result.share_link,
            code=parse_result.extraction_code,
            folder_name=parse_result.folder_name
        )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        if summary and summary.success_count > 0:
            return ProcessResult(
                success=True,
                message_type='baidupan',
                total_files=summary.total_files,
                success_count=summary.success_count,
                failed_count=summary.failed_count,
                skipped_count=summary.skipped_count,
                processing_time_ms=processing_time,
                metadata={'total_size_mb': summary.total_size / (1024*1024) if summary.total_size else 0}
            )
        else:
            return ProcessResult(
                success=False,
                message_type='baidupan',
                error_message="百度网盘文件处理失败",
                processing_time_ms=processing_time
            )

    def _process_dingtalk_file(self, parse_result: ParseResult, start_time: datetime) -> ProcessResult:
        """处理钉钉文件（PDF或ZIP）"""
        logger.info("Routing to DingTalk file processor...")

        # 下载文件
        download_result = self.dingtalk_processor.download(parse_result)

        if not download_result.success:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ProcessResult(
                success=False,
                message_type=parse_result.message_type,
                error_message=download_result.error,
                processing_time_ms=processing_time
            )

        logger.info(f"DingTalk file downloaded: {download_result.filename} ({download_result.file_size / (1024*1024):.2f} MB)")

        # 处理文件（PDF直接使用，ZIP需要解压）
        process_result = self.dingtalk_processor.process(download_result, parse_result)

        if not process_result.success:
            self.dingtalk_processor.cleanup()
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ProcessResult(
                success=False,
                message_type=parse_result.message_type,
                error_message=process_result.error,
                processing_time_ms=processing_time
            )

        # 生成上传文件列表
        upload_files = self.dingtalk_processor.get_upload_files(process_result, parse_result)
        logger.info(f"Generated {len(upload_files)} upload files")

        # 上传到SFTP
        success_count = 0
        failed_count = 0

        if self.enable_sftp:
            # 🔥 生成钉钉文件的上传路径：/sftp_remote_path/random/{yyyymm}/{file_name}
            yyyymm = datetime.now().strftime('%Y%m')
            dingtalk_base_path = f"{self.settings.sftp_remote_path}/random/{yyyymm}"

            for upload_file in upload_files:
                local_path = upload_file['local_path']

                # 对于钉钉文件，使用新的路径结构
                if parse_result.message_type == 'dingtalk_pdf':
                    # PDF文件：/sftp_remote_path/random/{yyyymm}/{file_name}
                    remote_filename = os.path.basename(upload_file['remote_path'])
                    remote_path = f"{dingtalk_base_path}/{remote_filename}".replace('\\\\', '/')
                elif parse_result.message_type == 'dingtalk_zip':
                    # ZIP文件：/sftp_remote_path/random/{yyyymm}/{zip_name}/内部文件
                    # 保持原有的相对路径结构
                    relative_path = upload_file['remote_path'].lstrip('/')
                    remote_path = f"{dingtalk_base_path}/{relative_path}".replace('\\\\', '/')
                else:
                    # 其他类型使用原有路径
                    remote_path = f"{self.settings.sftp_remote_path}{upload_file['remote_path']}".replace('\\\\', '/')

                logger.info(f"Uploading: {local_path} -> {remote_path}")

                # 确保远程目录存在
                remote_dir = os.path.dirname(remote_path)
                if not self.sftp_client.create_directory(remote_dir):
                    logger.error(f"Failed to create remote directory: {remote_dir}")
                    failed_count += 1
                    continue

                # 上传文件
                if self.sftp_client.upload_file(local_path, remote_path):
                    logger.info(f"Upload successful: {remote_path}")
                    success_count += 1
                else:
                    logger.error(f"Upload failed: {remote_path}")
                    failed_count += 1

        # 清理临时文件
        self.dingtalk_processor.cleanup()

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return ProcessResult(
            success=success_count > 0,
            message_type=parse_result.message_type,
            total_files=len(upload_files),
            success_count=success_count,
            failed_count=failed_count,
            processing_time_ms=processing_time,
            metadata=process_result.metadata
        )

    def _process_pdf_link(self, parse_result: ParseResult, start_time: datetime) -> ProcessResult:
        """处理外部PDF链接"""
        logger.info("Routing to PDF link processor...")

        pdf_url = parse_result.pdf_url
        if not pdf_url:
            return ProcessResult(
                success=False,
                message_type='pdf_link',
                error_message="PDF URL为空"
            )

        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix='pdf_link_download_')

            # 生成文件名
            filename = os.path.basename(pdf_url)
            if not filename.endswith('.pdf'):
                filename = f"{filename if filename else 'downloaded'}.pdf"

            # 添加时间戳避免冲突
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name_without_ext, ext = os.path.splitext(filename)
            filename = f"{name_without_ext}_{timestamp}{ext}"

            local_path = os.path.join(temp_dir, filename)

            logger.info(f"Downloading PDF from: {pdf_url[:80]}...")
            logger.info(f"Local path: {local_path}")

            # 下载PDF文件
            response = requests.get(pdf_url, stream=True, timeout=300)

            if response.status_code != 200:
                return ProcessResult(
                    success=False,
                    message_type='pdf_link',
                    error_message=f"下载失败: HTTP {response.status_code}"
                )

            # 保存文件
            downloaded_size = 0
            chunk_size = 8192
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

            file_size_mb = downloaded_size / (1024 * 1024)
            logger.info(f"PDF downloaded: {file_size_mb:.2f} MB")

            # 上传到SFTP
            success_count = 0
            failed_count = 0

            if self.enable_sftp:
                # 生成SFTP远程路径
                sftp_folder = f"pdf_links_{datetime.now().strftime('%Y%m%d')}"
                remote_path = f"{self.settings.sftp_remote_path}/{sftp_folder}/{filename}".replace('\\\\', '/')

                logger.info(f"Uploading to SFTP: {remote_path}")

                # 确保目录存在
                remote_dir = os.path.dirname(remote_path)
                if not self.sftp_client.create_directory(remote_dir):
                    logger.error(f"Failed to create remote directory: {remote_dir}")
                    failed_count = 1
                else:
                    # 上传文件
                    if self.sftp_client.upload_file(local_path, remote_path):
                        logger.info(f"Upload successful: {remote_path}")
                        success_count = 1
                    else:
                        logger.error(f"Upload failed: {remote_path}")
                        failed_count = 1

            # 清理临时文件
            try:
                os.remove(local_path)
                os.rmdir(temp_dir)
                logger.info("Temporary files cleaned up")
            except Exception as e:
                logger.warning(f"Failed to clean up temp files: {e}")

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProcessResult(
                success=success_count > 0,
                message_type='pdf_link',
                total_files=1,
                success_count=success_count,
                failed_count=failed_count,
                processing_time_ms=processing_time,
                metadata={
                    'file_size_mb': file_size_mb,
                    'pdf_url': pdf_url[:80] + '...' if len(pdf_url) > 80 else pdf_url
                }
            )

        except Exception as e:
            logger.error(f"Error processing PDF link: {e}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ProcessResult(
                success=False,
                message_type='pdf_link',
                error_message=str(e),
                processing_time_ms=processing_time
            )

    def _process_wxchat_article(self, parse_result: ParseResult, start_time: datetime) -> ProcessResult:
        """处理微信文章链接 - 简化版：直接使用share_link生成PDF"""
        logger.info("Processing WeChat article link directly...")

        try:
            # 使用share_link（微信文章URL）直接处理
            article_url = parse_result.share_link
            article_id = parse_result.wxchat_article_id or article_url.split('/')[-1]

            logger.info(f"Processing WeChat article: {article_url[:80]}...")

            # 1. 提取文章元数据（标题、公众号名）
            download_result = self.wxchat_article_processor.download(parse_result)

            if not download_result.success:
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return ProcessResult(
                    success=False,
                    message_type='wxchat-article',
                    error_message=download_result.error,
                    retryable=download_result.retryable,
                    processing_time_ms=processing_time
                )

            logger.info(f"Article metadata extracted: {download_result.article_title}")

            # 2. 生成PDF
            process_result = self.wxchat_article_processor.process(download_result, parse_result)

            if not process_result.success:
                self.wxchat_article_processor.cleanup()
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return ProcessResult(
                    success=False,
                    message_type='wxchat-article',
                    error_message=process_result.error,
                    retryable=process_result.retryable,
                    processing_time_ms=processing_time
                )

            # 3. 生成上传文件列表
            upload_files = self.wxchat_article_processor.get_upload_files(process_result, parse_result)
            logger.info(f"Generated {len(upload_files)} upload files")

            # 4. 上传到SFTP
            success_count = 0
            failed_count = 0

            if self.enable_sftp:
                for upload_file in upload_files:
                    local_path = upload_file['local_path']
                    remote_path = upload_file['remote_path']

                    logger.info(f"Uploading: {local_path} -> {remote_path}")

                    try:
                        # 确保远程目录存在
                        remote_dir = os.path.dirname(remote_path)
                        if not self.sftp_client.create_directory(remote_dir):
                            logger.error(f"Failed to create remote directory: {remote_dir}")
                            failed_count += 1
                            continue

                        # 上传文件
                        if self.sftp_client.upload_file(local_path, remote_path):
                            logger.info(f"Upload successful: {remote_path}")
                            success_count += 1
                        else:
                            logger.error(f"Upload failed: {remote_path}")
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Upload error for {remote_path}: {e}")
                        failed_count += 1

            # 5. 清理临时文件
            self.wxchat_article_processor.cleanup()

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProcessResult(
                success=success_count > 0,
                message_type='wxchat-article',
                total_files=len(upload_files),
                success_count=success_count,
                failed_count=failed_count,
                processing_time_ms=processing_time,
                metadata={
                    'article_title': process_result.article_title,
                    'account_name': process_result.account_name,
                    'article_id': article_id,
                    'article_url': article_url
                }
            )

        except Exception as e:
            logger.error(f"Error processing WeChat article: {e}")
            self.wxchat_article_processor.cleanup()

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_message = str(e)

            # 判断是否为可重试错误
            if "timeout" in error_message.lower() or "连接" in error_message.lower():
                retryable = True
            elif "database" in error_message.lower() or "db_" in error_message.lower():
                retryable = False  # 数据库错误通常不可重试
            else:
                retryable = False  # 默认不可重试

            return ProcessResult(
                success=False,
                message_type='wxchat-article',
                error_message=error_message,
                retryable=retryable,
                processing_time_ms=processing_time
            )

    def close(self):
        """关闭所有连接"""
        try:
            self.baidu_processor.close()
            self.sftp_client.disconnect()

            # 确保处理器清理完成
            if hasattr(self, 'wxchat_article_processor'):
                self.wxchat_article_processor.cleanup()

            logger.info("ProcessorRouter connections closed")
        except Exception as e:
            logger.error(f"Error closing ProcessorRouter: {e}")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()