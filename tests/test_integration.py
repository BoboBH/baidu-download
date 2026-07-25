"""
集成测试：验证完整流程
"""

import pytest
from src.processor.message_receiver import MessageReceiver
from src.config.settings import Settings
from unittest.mock import Mock, patch, MagicMock


class TestMessageReceiverIntegration:
    """集成测试：消息接收完整流程"""

    def test_feishu_message_receiving_still_works(self):
        """测试飞书消息接收仍然正常工作"""
        settings = Mock()
        settings.db_host = 'localhost'
        settings.db_port = 3306
        settings.db_user = 'test_user'
        settings.db_password = 'test_pass'
        settings.db_name = 'test_db'
        settings.feishu_app_id = 'test_app_id'
        settings.feishu_app_secret = 'test_app_secret'
        settings.feishu_chat_id = 'test_chat_id'
        settings.dingtalk_webhook = 'test_webhook'
        settings.sftp_host = 'test_host'
        settings.sftp_port = 22
        settings.sftp_username = 'test_user'
        settings.sftp_password = 'test_pass'
        settings.sftp_remote_path = '/test'
        settings.baidupcs_go_path = 'test_path'
        settings.baidu_cookies_path = 'test_cookies'
        settings.temp_dir = 'test_temp'
        settings.log_level = 'INFO'
        settings.log_file = 'test.log'
        settings.max_retries = 3
        settings.concurrent_uploads = 1

        with patch('src.processor.message_receiver.FeishuMessageClient'):
            with patch('src.processor.message_receiver.DatabaseRepository'):
                with patch('src.notification.dingtalk_notifier.DingtalkNotifier'):
                    receiver = MessageReceiver(settings, source='feishu')
                    assert receiver.source == 'feishu'

    def test_dingtalk_message_receiving_initialization(self):
        """测试钉钉消息接收器初始化"""
        settings = Mock()
        settings.db_host = 'localhost'
        settings.db_port = 3306
        settings.db_user = 'test_user'
        settings.db_password = 'test_pass'
        settings.db_name = 'test_db'
        settings.dingtalk_app_key = 'test_app_key'
        settings.dingtalk_app_secret = 'test_app_secret'
        settings.dingtalk_chat_id = 'test_chat_id'
        settings.dingtalk_webhook = 'test_webhook'
        settings.sftp_host = 'test_host'
        settings.sftp_port = 22
        settings.sftp_username = 'test_user'
        settings.sftp_password = 'test_pass'
        settings.sftp_remote_path = '/test'
        settings.baidupcs_go_path = 'test_path'
        settings.baidu_cookies_path = 'test_cookies'
        settings.temp_dir = 'test_temp'
        settings.log_level = 'INFO'
        settings.log_file = 'test.log'
        settings.max_retries = 3
        settings.concurrent_uploads = 1

        with patch('src.feishu.dingtalk_client.DingtalkMessageClient'):
            with patch('src.processor.message_receiver.DatabaseRepository'):
                with patch('src.notification.dingtalk_notifier.DingtalkNotifier'):
                    receiver = MessageReceiver(settings, source='dingtalk')
                    assert receiver.source == 'dingtalk'
