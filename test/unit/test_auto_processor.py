import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.processor.auto_processor import AutoProcessor, ProcessResult
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

    @patch('src.processor.auto_processor.ProcessResult')
    def test_process_messages_parses_valid_message(self, mock_result_class, auto_processor):
        """Test process_messages parses valid Feishu messages"""
        # Mock Feishu messages
        mock_messages = [
            {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
            {"message_id": "msg2", "content": '{"text":"invalid message"}'},
        ]
        auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)

        # Mock message parser
        mock_parse_result = Mock()
        mock_parse_result.folder_name = "260723"
        mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
        mock_parse_result.code = "0409"
        auto_processor.message_parser.parse_message = Mock(side_effect=[mock_parse_result, None])

        # Mock duplicate check - no duplicates
        auto_processor._is_duplicate_message = Mock(return_value=False)

        # Mock database insertion
        auto_processor.db_repo.insert_message_log = Mock(return_value=1)

        exit_code = auto_processor.process_messages()

        assert exit_code == 0
        assert auto_processor.message_parser.parse_message.call_count == 2
        auto_processor.db_repo.insert_message_log.assert_called_once()

    def test_process_messages_skips_duplicate_messages(self, auto_processor):
        """Test process_messages skips duplicate messages"""
        mock_messages = [
            {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
        ]
        auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)

        mock_parse_result = Mock()
        mock_parse_result.folder_name = "260723"
        mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
        mock_parse_result.code = "0409"
        auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)

        # Mock duplicate check - message is duplicate
        auto_processor._is_duplicate_message = Mock(return_value=True)

        # Should NOT insert duplicate message
        auto_processor.db_repo.insert_message_log = Mock()

        exit_code = auto_processor.process_messages()

        assert exit_code == 0
        auto_processor.db_repo.insert_message_log.assert_not_called()

    @patch('src.processor.auto_processor.ProcessResult')
    def test_process_messages_calls_file_processor(self, mock_result_class, auto_processor):
        """Test process_messages processes new messages via FileProcessor"""
        mock_messages = [
            {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
        ]
        auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)

        mock_parse_result = Mock()
        mock_parse_result.folder_name = "260723"
        mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
        mock_parse_result.code = "0409"
        auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
        auto_processor.message_parser.calculate_message_hash = Mock(return_value="hash123")
        auto_processor._is_duplicate_message = Mock(return_value=False)
        auto_processor.db_repo.insert_message_log = Mock(return_value=1)

        # Mock FileProcessor success
        mock_summary = Mock(spec=ExecutionSummary)
        mock_summary.SUCCESS_COUNT = 5
        mock_summary.FAILED_COUNT = 0
        auto_processor.file_processor.process_files = Mock(return_value=mock_summary)

        exit_code = auto_processor.process_messages()

        assert exit_code == 0
        auto_processor.file_processor.process_files.assert_called_once_with(
            "https://pan.baidu.com/s/abc123",
            "0409",
            "260723"
        )

    def test_process_messages_handles_file_processor_failure(self, auto_processor):
        """Test process_messages handles FileProcessor failures gracefully"""
        mock_messages = [
            {"message_id": "msg1", "content": '{"text":"260723：https://pan.baidu.com/s/abc123"}'},
        ]
        auto_processor.feishu_client.get_messages = Mock(return_value=mock_messages)

        mock_parse_result = Mock()
        mock_parse_result.folder_name = "260723"
        mock_parse_result.share_link = "https://pan.baidu.com/s/abc123"
        mock_parse_result.code = "0409"
        auto_processor.message_parser.parse_message = Mock(return_value=mock_parse_result)
        auto_processor.message_parser.calculate_message_hash = Mock(return_value="hash123")
        auto_processor._is_duplicate_message = Mock(return_value=False)
        auto_processor.db_repo.insert_message_log = Mock(return_value=1)

        # Mock FileProcessor failure
        auto_processor.file_processor.process_files = Mock(return_value=None)

        exit_code = auto_processor.process_messages()

        # Should still return 0 (success with partial failures)
        assert exit_code == 0

    def test_send_result_notification_success(self, auto_processor):
        """Test notification formatting for successful processing"""
        results = [
            ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
            ProcessResult(folder_name="260724", share_link="https://pan.baidu.com/s/abc2", status="success"),
        ]

        auto_processor.dingtalk_notifier.send_notification = Mock(return_value=True)

        result = auto_processor._send_result_notification(results)

        assert result is True
        auto_processor.dingtalk_notifier.send_notification.assert_called_once()

        # Verify notification content
        call_args = auto_processor.dingtalk_notifier.send_notification.call_args
        title = call_args[0][0]
        content = call_args[0][1]

        assert "成功" in title or "处理报告" in title
        assert "2 条消息" in content or "2" in content
        assert "260723" in content
        assert "260724" in content

    def test_send_result_notification_with_failures(self, auto_processor):
        """Test notification formatting includes failures"""
        results = [
            ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
            ProcessResult(folder_name="260724", share_link="https://pan.baidu.com/s/abc2", status="failed", error_message="Download timeout"),
        ]

        auto_processor.dingtalk_notifier.send_notification = Mock(return_value=True)

        result = auto_processor._send_result_notification(results)

        assert result is True

        # Verify error messages included
        call_args = auto_processor.dingtalk_notifier.send_notification.call_args
        content = call_args[0][1]

        assert "失败" in content
        assert "Download timeout" in content or "timeout" in content.lower()

    def test_send_result_notification_failure_handling(self, auto_processor):
        """Test notification failure is handled gracefully"""
        results = [
            ProcessResult(folder_name="260723", share_link="https://pan.baidu.com/s/abc1", status="success"),
        ]

        auto_processor.dingtalk_notifier.send_notification = Mock(return_value=False)

        result = auto_processor._send_result_notification(results)

        # Should return False but not raise exception
        assert result is False
