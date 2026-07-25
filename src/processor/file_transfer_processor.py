"""
文件传输处理器 - 专职处理待处理消息的文件传输
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.processor.file_processor import FileProcessor
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """消息处理结果"""
    message_id: int
    folder_name: str
    share_link: str
    status: str  # 'success', 'failed', 'critical_error'
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    total_files: Optional[int] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    total_size_mb: Optional[float] = None


@dataclass
class TransferResult:
    """文件传输总体结果"""
    total_messages: int
    success_messages: int
    failed_messages: int
    total_files: int
    total_success_files: int
    total_failed_files: int
    total_size_mb: float
    processing_time_ms: int
    details: List[ProcessResult]


class FileTransferProcessor:
    """文件传输处理器 - 专职处理待处理消息的文件传输"""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize FileTransferProcessor with required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance
        """
        self.settings = settings or Settings()
        self.logger = logger

        # Initialize components
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.file_processor = FileProcessor()
        self.dingtalk_notifier = DingtalkNotifier(self.settings)

        self.logger.info("FileTransferProcessor initialized successfully")

    def get_pending_messages(self) -> List[MessageProcessLog]:
        """
        获取待处理的消息列表

        Returns:
            待处理消息列表
        """
        try:
            cursor = self.db_repo.connection.cursor()

            sql = """
            SELECT * FROM message_process_log
            WHERE process_status = 'pending'
            ORDER BY created_at ASC
            LIMIT 10
            """

            cursor.execute(sql)
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
                    process_status=row['process_status'],
                    error_message=row['error_message'],
                    execution_summary_id=row.get('execution_summary_id'),
                    processing_time_ms=row.get('processing_time_ms'),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))

            cursor.close()
            self.logger.info(f"Found {len(messages)} pending messages")
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
                    self.logger.info(f"Processing message: {message.folder_name} (ID: {message.id})")

                    # 更新状态为 processing
                    self.db_repo.update_message_status(message.message_hash, "processing")

                    # 执行文件处理
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
                        error_message=error_message,
                        processing_time_ms=processing_time_ms,
                        total_files=summary.total_files if summary else 0,
                        success_count=summary.success_count if summary else 0,
                        failed_count=summary.failed_count if summary else 0,
                        total_size_mb=(summary.total_size / (1024 * 1024)) if summary and summary.total_size else 0.0
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

    def _send_single_message_notification(self, result: ProcessResult) -> bool:
        """
        发送单个消息处理完成通知到钉钉

        Args:
            result: 单个消息处理结果

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # 构建通知内容（添加钉钉机器人关键词"海外研报"）
            content_lines = [
                "## 📢 海外研报：文件处理完成通知",
                "",
                "### 处理结果",
                "",
                f"**文件夹**: {result.folder_name}",
                f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
                ""
            ]

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

            # 构建通知内容（添加钉钉机器人关键词"海外研报"）
            content_lines = [
                "## 📊 海外研报：文件传输总体报告",
                "",
                "### 总体统计",
                "",
                f"- **处理消息数**: {result.total_messages} 条",
                f"- **成功消息**: {result.success_messages} 条",
                f"- **失败消息**: {result.failed_messages} 条",
                f"- **总文件数**: {result.total_files} 个",
                f"- **成功文件**: {result.total_success_files} 个",
                f"- **失败文件**: {result.total_failed_files} 个",
                f"- **总大小**: {result.total_size_mb:.2f} MB",
                f"- **总耗时**: {result.processing_time_ms / 1000:.2f} 秒"
            ]

            # 添加成功处理详情
            success_results = [r for r in result.details if r.status == "success"]
            if success_results:
                content_lines.extend([
                    "",
                    "## ✅ 成功处理的消息",
                    ""
                ])
                for r in success_results:
                    content_lines.append(
                        f"📁 **{r.folder_name}** - {r.success_count}/{r.total_files} 文件, "
                        f"{r.total_size_mb:.2f} MB, {r.processing_time_ms / 1000:.1f}s"
                    )

            # 添加失败处理详情
            failed_results = [r for r in result.details if r.status in ["failed", "critical_error"]]
            if failed_results:
                content_lines.extend([
                    "",
                    "## ❌ 处理失败的消息",
                    ""
                ])
                for r in failed_results:
                    error_msg = r.error_message or "未知错误"
                    content_lines.append(f"📁 **{r.folder_name}** - {error_msg}")

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