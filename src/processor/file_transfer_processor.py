"""
文件传输处理器 - 专职处理待处理消息的文件传输
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import os
import shutil
from pathlib import Path
from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.processor.file_processor import FileProcessor
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger
from src.feishu.models import ParseResult

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """消息处理结果"""
    message_id: int
    folder_name: str
    share_link: str
    status: str  # 'success', 'failed', 'critical_error'
    message_type: Optional[str] = None  # 消息类型
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    total_files: Optional[int] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    total_size_mb: Optional[float] = None
    metadata: Optional[dict] = None  # 元数据（用于微信文章等信息）


@dataclass
class TransferResult:
    """文件传输总体结果"""
    total_messages: int
    success_messages: int
    failed_messages: int
    total_files: int
    total_success_files: int
    total_failed_files: int
    total_skipped_files: int
    total_size_mb: float
    processing_time_ms: int
    details: List[ProcessResult]


class FileTransferProcessor:
    """文件传输处理器 - 专职处理待处理消息的文件传输"""

    def __init__(self, settings: Optional[Settings] = None, force_reprocess=False):
        """
        Initialize FileTransferProcessor with required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance
            force_reprocess: Force reprocess all files regardless of history
        """
        self.settings = settings or Settings()
        self.force_reprocess = force_reprocess
        self.logger = logger

        # Initialize components
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.file_processor = FileProcessor(force_reprocess=self.force_reprocess)
        self.dingtalk_notifier = DingtalkNotifier(self.settings)

        # Initialize processor router for multi-message type support
        try:
            from src.processor.parsers.router import ProcessorRouter
            self.router = ProcessorRouter(self.settings)
            self.logger.info("ProcessorRouter initialized successfully")
        except ImportError as e:
            self.router = None
            self.logger.warning(f"Failed to initialize ProcessorRouter: {e}")

        self.logger.info("FileTransferProcessor initialized successfully")

    def get_pending_messages(self) -> List[MessageProcessLog]:
        """
        获取待处理的消息列表（包括pending和failed状态）

        Returns:
            待处理消息列表

        Filters:
            - Status must be 'pending' or 'failed'
            - For 'failed' status, retry_count must be less than max_message_retries
            - 'critical_error' messages are excluded (partial errors, no retry)
        """
        try:
            cursor = self.db_repo.connection.cursor()

            # Get max retries from settings, default to 10 if not available
            max_retries = self.settings.max_message_retries if hasattr(self.settings, 'max_message_retries') else 10

            # 查询pending和failed状态的消息，但对failed状态检查retry_count
            sql = """
            SELECT * FROM message_process_log
            WHERE process_status = 'pending'
               OR (process_status = 'failed' AND retry_count < %s)
            ORDER BY
                CASE
                    WHEN process_status = 'failed' THEN 1  # 优先重试失败的消息
                    ELSE 0
                END,
                created_at ASC
            LIMIT 10
            """

            cursor.execute(sql, (max_retries,))
            results = cursor.fetchall()

            messages = []
            for row in results:
                messages.append(MessageProcessLog(
                    id=row['id'],
                    message_hash=row['message_hash'],
                    original_message=row['original_message'],
                    share_link=row['share_link'],
                    folder_name=row['folder_name'],
                    extraction_code=row.get('extraction_code'),
                    source=row.get('source', 'feishu'),
                    message_type=row.get('message_type', 'baidupan'),  # 添加message_type字段
                    process_status=row['process_status'],
                    error_message=row['error_message'],
                    execution_summary_id=row.get('execution_summary_id'),
                    processing_time_ms=row.get('processing_time_ms'),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))

            cursor.close()

            # 统计各类消息数量
            pending_count = sum(1 for m in messages if m.process_status == 'pending')
            failed_count = sum(1 for m in messages if m.process_status == 'failed')
            self.logger.info(f"Found {len(messages)} messages total (pending: {pending_count}, failed: {failed_count})")
            return messages

        except Exception as e:
            self.logger.error(f"Failed to get pending messages: {e}")
            raise

    def process_pending_messages(self) -> TransferResult:
        """
        处理待处理消息的主要工作流程

        Returns:
            TransferResult: 传输结果统计
        """
        try:
            start_time = datetime.now()
            self.logger.info("Starting pending message processing")

            # 获取待处理消息
            pending_messages = self.get_pending_messages()

            if not pending_messages:
                self.logger.info("No pending messages to process")
                return TransferResult(
                    total_messages=0,
                    success_messages=0,
                    failed_messages=0,
                    total_files=0,
                    total_success_files=0,
                    total_failed_files=0,
                    total_skipped_files=0,
                    total_size_mb=0.0,
                    processing_time_ms=0,
                    details=[]
                )

            self.logger.info(f"Processing {len(pending_messages)} pending messages")

            results = []

            # 处理每条待处理消息
            for message in pending_messages:
                try:
                    message_start_time = datetime.now()
                    self.logger.info(f"Processing message: {message.folder_name} (ID: {message.id}, type: {message.message_type})")

                    # 更新状态为 processing
                    self.db_repo.update_message_status(message.message_hash, "processing")

                    # 根据消息类型选择处理方式
                    if message.message_type == 'baidupan' or not self.router:
                        # 百度网盘消息：使用 FileProcessor（完整流程：transfer->download->upload to SFTP）
                        self.logger.info(f"Using FileProcessor for baidupan message")

                        summary = self.file_processor.process_files(
                            share_link=message.share_link,
                            code=message.extraction_code or "",
                            folder_name=message.folder_name
                        )

                        # 计算处理时间
                        processing_time_ms = int((datetime.now() - message_start_time).total_seconds() * 1000)

                        # 根据处理结果更新状态
                        if summary and summary.success_count > 0:
                            status = "success"
                            error_message = None

                            # 插入执行摘要
                            if summary.total_files > 0:
                                summary_id = self.db_repo.insert_execution_summary(summary)
                                self.db_repo.update_message_status(
                                    message.message_hash,
                                    status,
                                    execution_summary_id=summary_id,
                                    processing_time_ms=processing_time_ms
                                )
                            else:
                                self.db_repo.update_message_status(
                                    message.message_hash,
                                    status,
                                    processing_time_ms=processing_time_ms
                                )
                        else:
                            status = "failed"
                            error_message = "File processing failed or no files transferred"
                            self.db_repo.update_message_status(
                                message.message_hash,
                                status,
                                error_message=error_message,
                                processing_time_ms=processing_time_ms
                            )

                        # 构建处理结果
                        process_result = ProcessResult(
                            message_id=message.id,
                            folder_name=message.folder_name,
                            share_link=message.share_link,
                            status=status,
                            message_type=message.message_type,  # 添加消息类型
                            error_message=error_message,
                            processing_time_ms=processing_time_ms,
                            total_files=summary.total_files if summary else 0,
                            success_count=summary.success_count if summary else 0,
                            failed_count=summary.failed_count if summary else 0,
                            skipped_count=summary.skipped_count if summary else 0,
                            total_size_mb=(summary.total_size / (1024 * 1024)) if summary and summary.total_size else 0.0
                        )

                        # 为百度网盘消息发送单条通知
                        self._send_single_message_notification(process_result)

                    else:
                        # 其他消息类型：使用 ProcessorRouter（钉钉文件/PDF链接只下载，不传输）
                        self.logger.info(f"Using ProcessorRouter for {message.message_type} message")

                        # 构造 ParseResult
                        parse_result = self._create_parse_result_from_message(message)

                        # 调用 Router 处理
                        router_result = self.router.process_message(parse_result)

                        # 计算处理时间
                        processing_time_ms = int((datetime.now() - message_start_time).total_seconds() * 1000)

                        # 根据 RouterResult 更新状态
                        if router_result.success:
                            status = "success"
                            error_message = None

                            # 🔥 关键修复：执行 SFTP 上传
                            success_count = 0
                            failed_count = 0
                            total_size = 0

                            if router_result.upload_files:
                                self.logger.info(f"Starting SFTP upload for {len(router_result.upload_files)} files")

                                # 🔥 关键修复：添加正确的SFTP基础路径
                                yyyymm = datetime.now().strftime('%Y%m')
                                sftp_base_path = f"{self.settings.sftp_remote_path}/random/{yyyymm}"

                                # 🔥 收集临时目录用于统一清理
                                temp_dirs_to_cleanup = set()

                                for upload_file in router_result.upload_files:
                                    try:
                                        local_path = upload_file.get('local_path')
                                        relative_path = upload_file.get('remote_path', '').lstrip('/')  # 移除前导斜杠
                                        file_size = upload_file.get('size', 0)

                                        if not local_path or not relative_path:
                                            self.logger.warning(f"Invalid upload file info: {upload_file}")
                                            failed_count += 1
                                            continue

                                        # 🔥 构建完整的SFTP路径
                                        remote_path = f"{sftp_base_path}/{relative_path}".replace('\\\\', '/')
                                        self.logger.info(f"Upload path: {local_path} -> {remote_path}")

                                        # 确保远程目录存在
                                        remote_dir = os.path.dirname(remote_path)
                                        if remote_dir and not self.file_processor.sftp_client.create_directory(remote_dir):
                                            self.logger.error(f"Failed to create remote directory: {remote_dir}")
                                            failed_count += 1
                                            continue

                                        # 执行 SFTP 上传
                                        if self.file_processor.sftp_client.upload_file(local_path, remote_path):
                                            success_count += 1
                                            total_size += file_size
                                            self.logger.info(f"✅ Uploaded: {local_path} -> {remote_path}")

                                            # 🔥 收集临时目录，不立即删除
                                            local_dir = str(Path(local_path).parent)
                                            if local_dir:
                                                temp_dirs_to_cleanup.add(local_dir)

                                        else:
                                            failed_count += 1
                                            self.logger.error(f"❌ Upload failed: {local_path}")

                                    except Exception as e:
                                        self.logger.error(f"Upload exception for {upload_file}: {e}")
                                        failed_count += 1

                                # 🔥 统一清理所有临时目录
                                self.logger.info(f"🗑️  Cleaning up {len(temp_dirs_to_cleanup)} temporary directories...")
                                for temp_dir in temp_dirs_to_cleanup:
                                    try:
                                        if os.path.exists(temp_dir):
                                            if os.path.isdir(temp_dir):
                                                shutil.rmtree(temp_dir)
                                                self.logger.info(f"🗑️  Cleaned up temp directory: {temp_dir}")
                                            elif os.path.isfile(temp_dir):
                                                os.remove(temp_dir)
                                                self.logger.info(f"🗑️  Cleaned up temp file: {temp_dir}")
                                    except Exception as cleanup_error:
                                        self.logger.warning(f"⚠️  Failed to cleanup {temp_dir}: {cleanup_error}")

                                self.logger.info(f"SFTP upload completed: {success_count} success, {failed_count} failed")

                            # 插入执行摘要（如果有处理结果）
                            if router_result.process_result and hasattr(router_result.process_result, 'total_files'):
                                from src.database.models import ExecutionSummary
                                summary = ExecutionSummary(
                                    share_link=message.share_link or "",
                                    folder_name=message.folder_name or "",
                                    total_files=router_result.process_result.total_files,
                                    success_count=success_count,  # 使用实际上传成功数
                                    failed_count=failed_count,
                                    skipped_count=router_result.process_result.skipped_count,
                                    start_time=message_start_time,
                                    end_time=datetime.now(),
                                    total_size=total_size
                                )
                                summary_id = self.db_repo.insert_execution_summary(summary)
                                self.db_repo.update_message_status(
                                    message.message_hash,
                                    status,
                                    execution_summary_id=summary_id,
                                    processing_time_ms=processing_time_ms
                                )
                            else:
                                self.db_repo.update_message_status(
                                    message.message_hash,
                                    status,
                                    processing_time_ms=processing_time_ms
                                )

                            # 构建处理结果
                            process_result = ProcessResult(
                                message_id=message.id,
                                folder_name=message.folder_name or "unknown",
                                share_link=message.share_link or "unknown",
                                status=status,
                                message_type=message.message_type,  # 添加消息类型
                                error_message=error_message,
                                processing_time_ms=processing_time_ms,
                                total_files=len(router_result.upload_files) if router_result.upload_files else 0,
                                success_count=success_count,
                                failed_count=failed_count,
                                skipped_count=0,
                                total_size_mb=total_size / (1024 * 1024) if total_size else 0.0,
                                metadata=router_result.metadata  # 传递元数据（用于微信文章等信息）
                            )
                        else:
                            status = "failed"
                            error_message = router_result.error or "Processing failed"
                            self.db_repo.update_message_status(
                                message.message_hash,
                                status,
                                error_message=error_message,
                                processing_time_ms=processing_time_ms
                            )

                            process_result = ProcessResult(
                                message_id=message.id,
                                folder_name=message.folder_name or "unknown",
                                share_link=message.share_link or "unknown",
                                status=status,
                                message_type=message.message_type,  # 添加消息类型
                                error_message=error_message,
                                processing_time_ms=processing_time_ms,
                                metadata=router_result.metadata  # 传递元数据（失败时也保留）
                            )

                    results.append(process_result)

                    # 为每个处理完成的消息发送通知
                    self._send_single_message_notification(process_result)

                    self.logger.info(f"✅ Message processing completed: {message.folder_name} - {status}")

                except Exception as e:
                    self.logger.error(f"Error processing message {message.message_hash}: {e}")
                    # 更新状态为 critical_error
                    self.db_repo.update_message_status(
                        message.message_hash,
                        "critical_error",
                        error_message=str(e)
                    )

                    results.append(ProcessResult(
                        message_id=message.id,
                        folder_name=message.folder_name or "unknown",
                        share_link=message.share_link or "unknown",
                        status="critical_error",
                        message_type=message.message_type,  # 添加消息类型
                        error_message=str(e)
                    ))
                    continue

            # 计算总处理时间
            total_processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 构建总体传输结果
            transfer_result = TransferResult(
                total_messages=len(results),
                success_messages=sum(1 for r in results if r.status == "success"),
                failed_messages=sum(1 for r in results if r.status in ["failed", "critical_error"]),
                total_files=sum(r.total_files or 0 for r in results),
                total_success_files=sum(r.success_count or 0 for r in results),
                total_failed_files=sum(r.failed_count or 0 for r in results),
                total_skipped_files=sum(r.skipped_count or 0 for r in results),
                total_size_mb=sum(r.total_size_mb or 0 for r in results),
                processing_time_ms=total_processing_time_ms,
                details=results
            )

            # 发送总体处理通知
            self._send_overall_notification(transfer_result)

            self.logger.info(f"File transfer processing completed in {total_processing_time_ms}ms")
            return transfer_result

        except Exception as e:
            self.logger.error(f"Critical failure during message processing: {e}")
            raise

    def _create_parse_result_from_message(self, message: MessageProcessLog) -> ParseResult:
        """
        从 MessageProcessLog 创建 ParseResult

        Args:
            message: 消息日志对象

        Returns:
            ParseResult 对象
        """
        message_type = message.message_type or 'baidupan'

        # 基础字段
        parse_result = ParseResult(
            message_type=message_type,
            unique_identifier=message.message_hash,
            source=message.source or 'feishu'
        )

        # 根据消息类型设置特定字段
        if message_type == 'baidupan':
            # 百度网盘消息
            parse_result.share_link = message.share_link
            parse_result.folder_name = message.folder_name
            parse_result.extraction_code = message.extraction_code

        elif message_type in ['dingtalk_pdf', 'dingtalk_zip']:
            # 钉钉文件消息
            parse_result.file_name = message.folder_name  # 文件名存储在 folder_name
            parse_result.download_code = message.extraction_code  # download_code 存储在 extraction_code

            # 解析 share_link 获取 file_id 和 space_id
            # 格式: dingtalk:file_id:space_id:download_code
            if message.share_link and message.share_link.startswith('dingtalk:'):
                parts = message.share_link.split(':')
                if len(parts) >= 3:
                    parse_result.file_id = parts[1]
                    parse_result.space_id = parts[2]

        elif message_type == 'pdf_link':
            # PDF链接消息
            parse_result.pdf_url = message.share_link
            parse_result.share_link = message.share_link  # 统一使用 share_link
            parse_result.folder_name = message.folder_name

        return parse_result

    def _create_parse_result_from_message(self, message: MessageProcessLog) -> ParseResult:
        """
        从 MessageProcessLog 创建 ParseResult

        Args:
            message: 消息日志对象

        Returns:
            ParseResult 对象
        """
        message_type = message.message_type or 'baidupan'

        # 基础字段
        parse_result = ParseResult(
            message_type=message_type,
            unique_identifier=message.message_hash,
            source=message.source or 'feishu'
        )

        # 根据消息类型设置特定字段
        if message_type == 'baidupan':
            # 百度网盘消息
            parse_result.share_link = message.share_link
            parse_result.folder_name = message.folder_name
            parse_result.extraction_code = message.extraction_code

        elif message_type in ['dingtalk_pdf', 'dingtalk_zip']:
            # 钉钉文件消息
            parse_result.file_name = message.folder_name  # 文件名存储在 folder_name
            parse_result.download_code = message.extraction_code  # download_code 存储在 extraction_code

            # 解析 share_link 获取 file_id 和 space_id
            # 格式: dingtalk:file_id:space_id:download_code
            if message.share_link and message.share_link.startswith('dingtalk:'):
                parts = message.share_link.split(':')
                if len(parts) >= 3:
                    parse_result.file_id = parts[1]
                    parse_result.space_id = parts[2]

        elif message_type == 'pdf_link':
            # PDF链接消息
            parse_result.pdf_url = message.share_link
            parse_result.share_link = message.share_link  # 统一使用 share_link
            parse_result.folder_name = message.folder_name

        return parse_result

    def _send_single_message_notification(self, result: ProcessResult) -> bool:
        """
        发送单个消息处理完成通知到钉钉

        Args:
            result: 单个消息处理结果

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # 构建通知内容（添加钉钉机器人关键词"Foundry"）
            content_lines = [
                "## 📢 Foundry：文件处理完成通知",
                "",
                "### 处理结果",
                ""
            ]

            # 根据消息类型定制显示内容
            if result.message_type == 'wxchat-article' and hasattr(result, 'metadata') and result.metadata:
                # 微信文章：显示文章标题和公众号名称
                article_title = result.metadata.get('article_title', '未知文章')
                account_name = result.metadata.get('account_name', '未知公众号')
                content_lines.extend([
                    f"**文章标题**: {article_title}",
                    f"**公众号**: {account_name}",
                    f"**类型**: 微信文章",
                    f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
                    ""
                ])
            else:
                # 其他消息类型：显示文件夹名称
                content_lines.extend([
                    f"**文件夹**: {result.folder_name}",
                    f"**类型**: {result.message_type or 'N/A'}",
                    f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
                    ""
                ])

            # 添加share_link信息（如果存在）
            if hasattr(result, 'share_link') and result.share_link:
                content_lines.extend([
                    f"**分享链接**: {result.share_link[:100]}{'...' if len(result.share_link) > 100 else ''}",
                    ""
                ])

            if result.status == "success":
                content_lines.extend([
                    "### 详细统计",
                    "",
                    f"- **总文件数**: {result.total_files}",
                    f"- **成功传输**: {result.success_count}",
                    f"- **传输失败**: {result.failed_count}",
                    f"- **总大小**: {result.total_size_mb:.2f} MB",
                    f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
                ])
            else:
                content_lines.extend([
                    "### 错误信息",
                    "",
                    f"❌ {result.error_message or '未知错误'}"
                ])

            # 添加时间戳
            content_lines.extend([
                "",
                f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])

            content = "\n".join(content_lines)

            # 发送通知
            title = f"文件处理完成 - {result.folder_name}"
            success = self.dingtalk_notifier.send_notification(title, content)

            if success:
                self.logger.info(f"Single message notification sent for {result.folder_name}")
            else:
                self.logger.warning(f"Failed to send notification for {result.folder_name}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending single message notification: {e}")
            return False

    def _send_overall_notification(self, result: TransferResult) -> bool:
        """
        发送总体处理结果通知到钉钉

        Args:
            result: 总体传输结果

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # 如果没有处理任何消息，不发送通知
            if result.total_messages == 0:
                self.logger.info("No messages processed, skipping overall notification")
                return True

            # 构建通知内容（添加钉钉机器人关键词"Foundry"）
            content_lines = [
                "## 📊 Foundry：文件传输总体报告",
                "",
                "### 总体统计",
                "",
                f"- **处理消息数**: {result.total_messages} 条",
                f"- **成功消息**: {result.success_messages} 条",
                f"- **失败消息**: {result.failed_messages} 条",
                f"- **总文件数**: {result.total_files} 个",
                f"- **成功文件**: {result.total_success_files} 个",
                f"- **失败文件**: {result.total_failed_files} 个",
                f"- **已处理跳过**: {result.total_skipped_files} 个",
                f"- **总大小**: {result.total_size_mb:.2f} MB",
                f"- **总耗时**: {result.processing_time_ms / 1000:.2f} 秒"
            ]

            # 添加时间戳
            content_lines.extend([
                "",
                f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])

            content = "\n".join(content_lines)

            # 发送通知
            title = "文件传输总体报告"
            success = self.dingtalk_notifier.send_notification(title, content)

            if success:
                self.logger.info("Overall notification sent successfully")
            else:
                self.logger.warning("Failed to send overall notification")

            return success

        except Exception as e:
            self.logger.error(f"Error sending overall notification: {e}")
            return False

    def close(self):
        """关闭资源"""
        if hasattr(self, 'db_repo'):
            self.db_repo.close()
            self.logger.info("FileTransferProcessor resources closed")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()