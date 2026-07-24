import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.processor.auto_processor import AutoProcessor
from src.database.message_models import MessageProcessLog
from src.database.models import ExecutionSummary


class TestAutoProcessor:
    """Test suite for AutoProcessor coordinator class"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock configuration"""
        settings = Mock()
        settings.feishu_app_id = "test_app_id"
        settings.feishu_app_secret = "test_secret"
        settings.feishu_chat_id = "test_chat_id"
        settings.feishu_hours_limit = 24
        settings.dingtalk_webhook = "https://oapi.dingtalk.com/robot/send?access_token=test"
        settings.message_default_extraction_code = "0409"
        settings.db_host = "localhost"
        settings.db_port = 3306
        settings.db_user = "test_user"
        settings.db_password = "test_pass"
        settings.db_name = "test_db"
        return settings

    @pytest.fixture
    def auto_processor(self, mock_settings):
        """Create AutoProcessor instance with mocked dependencies"""
        with patch('src.processor.auto_processor.Settings', return_value=mock_settings):
            return AutoProcessor()
