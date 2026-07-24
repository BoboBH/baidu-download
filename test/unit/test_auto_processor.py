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
            with patch('src.processor.auto_processor.DatabaseRepository'):
                with patch('src.processor.auto_processor.FeishuMessageClient'):
                    with patch('src.processor.auto_processor.MessageParser'):
                        with patch('src.processor.auto_processor.FileProcessor'):
                            with patch('src.processor.auto_processor.DingtalkNotifier'):
                                return AutoProcessor()

    def test_auto_processor_init(self, auto_processor):
        """Test AutoProcessor initialization"""
        assert auto_processor.settings is not None
        assert auto_processor.feishu_client is not None
        assert auto_processor.message_parser is not None
        assert auto_processor.db_repo is not None
        assert auto_processor.file_processor is not None
        assert auto_processor.dingtalk_notifier is not None

    def test_is_duplicate_message_true(self, auto_processor):
        """Test duplicate message detection returns True for existing message"""
        mock_message_log = Mock(spec=MessageProcessLog)
        mock_message_log.message_hash = "abc123"
        auto_processor.db_repo.get_message_by_hash = Mock(return_value=mock_message_log)

        result = auto_processor._is_duplicate_message("abc123")
        assert result is True
        auto_processor.db_repo.get_message_by_hash.assert_called_once_with("abc123")

    def test_is_duplicate_message_false(self, auto_processor):
        """Test duplicate message detection returns False for new message"""
        auto_processor.db_repo.get_message_by_hash = Mock(return_value=None)

        result = auto_processor._is_duplicate_message("new_message")
        assert result is False
        auto_processor.db_repo.get_message_by_hash.assert_called_once_with("new_message")

    def test_process_messages_returns_exit_code(self, auto_processor):
        """Test process_messages returns integer exit code"""
        with patch.object(auto_processor, 'feishu_client') as mock_feishu:
            mock_feishu.get_messages.return_value = []

            exit_code = auto_processor.process_messages()
            assert isinstance(exit_code, int)
            assert exit_code in [0, 1]
