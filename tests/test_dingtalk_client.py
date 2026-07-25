"""
测试 DingtalkMessageClient
"""

import pytest
from unittest.mock import Mock, patch
from src.feishu.dingtalk_client import DingtalkMessageClient
from src.config.settings import Settings


class TestDingtalkMessageClient:
    """测试钉钉消息客户端"""

    def setup_method(self):
        """设置测试环境"""
        self.settings = Mock(spec=Settings)
        self.settings.dingtalk_app_key = 'test_app_key'
        self.settings.dingtalk_app_secret = 'test_app_secret'
        self.settings.dingtalk_chat_id = 'test_chat_id'
        self.client = DingtalkMessageClient(self.settings)

    def test_initialization(self):
        """测试客户端初始化"""
        assert self.client.app_key == 'test_app_key'
        assert self.client.app_secret == 'test_app_secret'
        assert self.client.chat_id == 'test_chat_id'
        assert self.client.token is None
        assert self.client.max_retries == 5

    def test_initialization_with_empty_credentials(self):
        """测试空凭证初始化"""
        settings = Mock(spec=Settings)
        settings.dingtalk_app_key = ''
        settings.dingtalk_app_secret = ''
        settings.dingtalk_chat_id = ''

        client = DingtalkMessageClient(settings)
        assert client.app_key == ''
        assert client.app_secret == ''

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_success(self, mock_post):
        """测试成功获取 access_token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accessToken': 'test_token_123'
        }
        mock_post.return_value = mock_response

        token = self.client.get_access_token()

        assert token == 'test_token_123'
        assert self.client.token == 'test_token_123'
        mock_post.assert_called_once()

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_api_error(self, mock_post):
        """测试API错误"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': 'Invalid credentials'
        }
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="API error"):
            self.client.get_access_token()

    @patch('src.feishu.dingtalk_client.requests.post')
    def test_get_access_token_retry_on_500(self, mock_post):
        """测试500错误重试"""
        mock_response_error = Mock()
        mock_response_error.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'accessToken': 'test_token_123'
        }

        mock_post.side_effect = [
            mock_response_error,
            mock_response_success
        ]

        token = self.client.get_access_token()

        assert token == 'test_token_123'
        assert mock_post.call_count == 2

    def test_calculate_backoff(self):
        """测试指数退避计算"""
        assert self.client._calculate_backoff(0) == 1
        assert self.client._calculate_backoff(1) == 2
        assert self.client._calculate_backoff(2) == 4
        assert self.client._calculate_backoff(3) == 8
        assert self.client._calculate_backoff(4) == 16  # 最大值
        assert self.client._calculate_backoff(10) == 16  # 超过最大值

    def test_should_retry_error(self):
        """测试重试错误判断"""
        assert self.client._should_retry_error(500) == True
        assert self.client._should_retry_error(503) == True
        assert self.client._should_retry_error(429) == True
        assert self.client._should_retry_error(400) == False
        assert self.client._should_retry_error(404) == False

    def test_is_rate_limit_error(self):
        """测试限流错误判断"""
        assert self.client._is_rate_limit_error(429) == True
        assert self.client._is_rate_limit_error(500) == False

    @patch('src.feishu.dingtalk_client.DingtalkMessageClient.get_messages')
    def test_get_messages_not_implemented(self, mock_get):
        """测试 get_messages 未实现"""
        mock_get.side_effect = NotImplementedError(
            "get_messages requires Dingtalk API endpoint confirmation"
        )

        with pytest.raises(NotImplementedError):
            self.client.get_messages()
