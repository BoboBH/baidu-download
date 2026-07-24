from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.processor.file_processor import FileProcessor
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessResult:
    """Internal tracking for processing results"""
    folder_name: str
    share_link: str
    status: str  # 'success', 'failed', 'critical_error', 'skipped'
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


class AutoProcessor:
    """Automatic message processing coordinator for Windows Task Scheduler integration"""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize AutoProcessor with all required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance
        """
        self.settings = settings or Settings()
        self.logger = logger

        # Initialize components
        self.feishu_client = FeishuMessageClient(self.settings)
        self.message_parser = MessageParser()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.file_processor = FileProcessor()
        self.dingtalk_notifier = DingtalkNotifier(self.settings)

        self.logger.info("AutoProcessor initialized successfully")

    def _is_duplicate_message(self, message_hash: str) -> bool:
        """
        Check if message was already processed

        Args:
            message_hash: MD5 hash of message content

        Returns:
            True if message exists in database, False otherwise
        """
        existing_message = self.db_repo.get_message_by_hash(message_hash)
        return existing_message is not None

    def process_messages(self) -> int:
        """
        Main workflow orchestration method

        Returns:
            Exit code: 0 = success (even with partial failures),
                  1 = critical system failure
        """
        try:
            self.logger.info("Starting automatic message processing")

            # Retrieve messages from Feishu
            messages = self.feishu_client.get_messages()
            self.logger.info(f"Retrieved {len(messages)} messages from Feishu")

            results = []

            for message in messages:
                try:
                    # Extract message content from JSON
                    content = message.get("content", "")
                    if not content:
                        self.logger.warning(f"Empty message content for message_id: {message.get('message_id')}")
                        continue

                    # Parse message content
                    parse_result = self.message_parser.parse_message(content)
                    if not parse_result:
                        self.logger.debug(f"Failed to parse message: {content[:50]}...")
                        continue

                    # Calculate message hash
                    message_hash = self.message_parser.calculate_message_hash(content)

                    # Check for duplicates
                    if self._is_duplicate_message(message_hash):
                        self.logger.info(f"Skipping duplicate message: {parse_result.folder_name}")
                        results.append(ProcessResult(
                            folder_name=parse_result.folder_name,
                            share_link=parse_result.share_link,
                            status="skipped"
                        ))
                        continue

                    # Insert new message to database
                    message_log = MessageProcessLog(
                        message_hash=message_hash,
                        original_message=content,
                        share_link=parse_result.share_link,
                        folder_name=parse_result.folder_name,
                        status="pending"
                    )
                    message_id = self.db_repo.insert_message_log(message_log)
                    self.logger.info(f"Inserted new message: {parse_result.folder_name}")

                    # Update status to processing
                    self.db_repo.update_message_status(message_hash, "processing")

                    # Process via FileProcessor
                    start_time = datetime.now()
                    summary = self.file_processor.process_files(
                        parse_result.share_link,
                        parse_result.code,
                        parse_result.folder_name
                    )
                    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                    # Update database status based on result
                    if summary and summary.SUCCESS_COUNT > 0:
                        status = "success"
                        error_message = None
                    else:
                        status = "failed"
                        error_message = "File processing failed or no files transferred"

                    self.db_repo.update_message_status(
                        message_hash,
                        status,
                        error_message=error_message,
                        processing_time=processing_time
                    )

                    results.append(ProcessResult(
                        folder_name=parse_result.folder_name,
                        share_link=parse_result.share_link,
                        status=status,
                        error_message=error_message,
                        processing_time_ms=processing_time
                    ))

                except Exception as e:
                    self.logger.error(f"Error processing individual message: {e}")
                    # Update status to critical_error for this message
                    if 'message_hash' in locals():
                        self.db_repo.update_message_status(
                            message_hash,
                            "critical_error",
                            error_message=str(e)
                        )
                    continue

            return 0

        except Exception as e:
            self.logger.error(f"Critical failure during message processing: {e}")
            return 1

    def _send_result_notification(self, results: List[ProcessResult]) -> bool:
        """
        Format and send notification to DingTalk

        Args:
            results: List of processing results

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Count results by status
            success_count = sum(1 for r in results if r.status == "success")
            failed_count = sum(1 for r in results if r.status == "failed")
            skipped_count = sum(1 for r in results if r.status == "skipped")
            total_count = len(results)

            # Build notification content
            content_lines = [
                "## 处理结果摘要",
                "",
                f"- 总计处理: {total_count} 条消息",
                f"- 成功: {success_count} 条",
                f"- 失败: {failed_count} 条",
                f"- 跳过: {skipped_count} 条",
            ]

            # Add successful processing details
            success_results = [r for r in results if r.status == "success"]
            if success_results:
                content_lines.extend([
                    "",
                    "## 成功处理",
                    ""
                ])
                for result in success_results:
                    content_lines.append(f"✅ {result.folder_name} - 文件传输成功")

            # Add failed processing details
            failed_results = [r for r in results if r.status == "failed"]
            if failed_results:
                content_lines.extend([
                    "",
                    "## 处理失败",
                    ""
                ])
                for result in failed_results:
                    error_msg = result.error_message or "未知错误"
                    content_lines.append(f"❌ {result.folder_name} - {error_msg}")

            # Add timestamp
            content_lines.extend([
                "",
                f"## 处理时间",
                "",
                f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])

            content = "\n".join(content_lines)

            # Send notification
            title = "百度网盘文件处理报告"
            success = self.dingtalk_notifier.send_notification(title, content)

            if success:
                self.logger.info("DingTalk notification sent successfully")
            else:
                self.logger.warning("Failed to send DingTalk notification")

            return success

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False

            return 0

        except Exception as e:
            self.logger.error(f"Critical failure during message processing: {e}")
            return 1
