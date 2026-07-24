from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.database.repository import DatabaseRepository
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

            # Process messages logic will be added in next tasks
            return 0

        except Exception as e:
            self.logger.error(f"Critical failure during message processing: {e}")
            return 1
