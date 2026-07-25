import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.feishu.feishu_client import FeishuMessageClient


class TestFeishuMessageClient:
    """测试FeishuMessageClient类"""

    @pytest.fixture
    def mock_settings(self):
        """创建Mock配置对象"""
        settings = Mock()
        settings.feishu_app_id = "test_app_id"
        settings.feishu_app_secret = "test_app_secret"
        settings.feishu_chat_id = "test_chat_id"
        return settings

    @pytest.fixture
    def client(self, mock_settings):
        """创建FeishuMessageClient实例"""
        with patch('src.feishu.feishu_client.Settings', return_value=mock_settings):
            return FeishuMessageClient()

    def test_init_client(self, client, mock_settings):
        """测试客户端初始化"""
        assert client.app_id == "test_app_id"
        assert client.app_secret == "test_app_secret"
        assert client.chat_id == "test_chat_id"
        assert client.token is None
        assert client.max_retries == 5

    def test_get_tenant_access_token_success(self, client):
        """测试成功获取tenant_access_token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        with patch('requests.post', return_value=mock_response):
            token = client.get_tenant_access_token()
            assert token == "test_token"
            assert client.token == "test_token"

    def test_get_tenant_access_token_api_error(self, client):
        """测试API返回错误时的处理"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 9999,
            "msg": "Invalid app_id"
        }

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                client.get_tenant_access_token()
            assert "API error: Invalid app_id" in str(exc_info.value)

    def test_get_tenant_access_token_retry_on_500(self, client):
        """测试500错误时的重试机制"""
        mock_response_500 = Mock()
        mock_response_500.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        with patch('requests.post', side_effect=[mock_response_500, mock_response_success]):
            token = client.get_tenant_access_token()
            assert token == "test_token"

    def test_get_tenant_access_token_max_retries(self, client):
        """测试达到最大重试次数"""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                client.get_tenant_access_token()
            assert "Failed to get tenant_access_token" in str(exc_info.value)

    def test_get_tenant_access_token_exponential_backoff(self, client):
        """测试指数退避机制"""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch('requests.post', return_value=mock_response):
            with patch('time.sleep') as mock_sleep:
                try:
                    client.get_tenant_access_token()
                except Exception:
                    pass

                # 验证sleep调用次数和参数
                assert mock_sleep.call_count == 5
                sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
                expected_args = [1, 2, 4, 8, 16]
                assert sleep_args == expected_args

    def test_get_messages_success(self, client):
        """测试成功获取消息"""
        # Mock token
        client.token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "message_id": "msg1",
                        "content": '{"text":"测试消息1"}',
                        "create_time": "1690000000000"
                    },
                    {
                        "message_id": "msg2",
                        "content": '{"text":"测试消息2"}',
                        "create_time": "1690000001000"
                    }
                ],
                "has_more": False
            }
        }

        with patch('requests.get', return_value=mock_response):
            messages = client.get_messages(limit=50)
            assert len(messages) == 2
            assert messages[0]["message_id"] == "msg1"
            assert messages[1]["message_id"] == "msg2"

    def test_get_messages_without_token(self, client):
        """测试没有token时自动获取"""
        # Mock token获取
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock消息获取
        mock_messages_response = Mock()
        mock_messages_response.status_code = 200
        mock_messages_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "message_id": "msg1",
                        "content": '{"text":"测试消息"}',
                        "create_time": "1690000000000"
                    }
                ],
                "has_more": False
            }
        }

        with patch('requests.post', return_value=mock_token_response):
            with patch('requests.get', return_value=mock_messages_response):
                messages = client.get_messages(limit=50)
                assert len(messages) == 1
                assert client.token == "test_token"

    def test_get_messages_api_error(self, client):
        """测试消息API错误处理"""
        client.token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 9999,
            "msg": "Invalid chat_id"
        }

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                client.get_messages(limit=50)
            assert "API error: Invalid chat_id" in str(exc_info.value)

    def test_get_messages_retry_on_rate_limit(self, client):
        """测试限流时的重试"""
        client.token = "test_token"

        mock_rate_limit = Mock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.headers = {'Retry-After': '2'}

        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "code": 0,
            "data": {
                "items": [],
                "has_more": False
            }
        }

        with patch('requests.get', side_effect=[mock_rate_limit, mock_success]):
            messages = client.get_messages(limit=50)
            assert messages == []

    def test_get_messages_max_retries(self, client):
        """测试获取消息达到最大重试次数"""
        client.token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1'}

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                client.get_messages(limit=50)
            assert "Failed to get messages" in str(exc_info.value)

    def test_build_request_headers(self, client):
        """测试请求头构建"""
        client.token = "test_token"
        headers = client._build_request_headers()

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json; charset=utf-8"

    def test_is_rate_limit_error(self, client):
        """测试限流错误判断"""
        assert client._is_rate_limit_error(429) == True
        assert client._is_rate_limit_error(200) == False
        assert client._is_rate_limit_error(500) == False

    def test_should_retry_error(self, client):
        """测试错误是否应重试"""
        # 5xx错误应该重试
        assert client._should_retry_error(500) == True
        assert client._should_retry_error(502) == True
        assert client._should_retry_error(503) == True

        # 429限流应该重试
        assert client._should_retry_error(429) == True

        # 4xx其他错误不应重试
        assert client._should_retry_error(400) == False
        assert client._should_retry_error(401) == False
        assert client._should_retry_error(404) == False

    def test_wait_with_backoff(self, client):
        """测试退避等待"""
        with patch('time.sleep') as mock_sleep:
            client._wait_with_backoff(1)
            mock_sleep.assert_called_once_with(1)

    def test_extract_retry_after(self, client):
        """测试提取Retry-After头"""
        mock_response = Mock()
        mock_response.headers = {'Retry-After': '5'}

        retry_after = client._extract_retry_after(mock_response)
        assert retry_after == 5

    def test_extract_retry_after_default(self, client):
        """测试没有Retry-After头时的默认值"""
        mock_response = Mock()
        mock_response.headers = {}

        retry_after = client._extract_retry_after(mock_response)
        assert retry_after == 1

    def test_get_messages_with_default_limit(self, client):
        """测试使用默认limit参数"""
        client.token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [],
                "has_more": False
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
            client.get_messages()
            # 验证请求参数中的limit
            call_args = mock_get.call_args
            assert 'limit' in call_args[1]['params'] or 'limit' in str(call_args)

    def test_get_messages_with_custom_limit(self, client):
        """测试使用自定义limit参数"""
        client.token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [],
                "has_more": False
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
            client.get_messages(limit=100)
            # 验证请求参数中的limit
            call_args = mock_get.call_args
            assert 'limit' in str(call_args) or '100' in str(call_args)

    def test_empty_chat_id_handling(self, mock_settings):
        """测试空chat_id的处理"""
        mock_settings.feishu_chat_id = ""

        with patch('src.feishu.feishu_client.Settings', return_value=mock_settings):
            client = FeishuMessageClient()
            assert client.chat_id == ""

    def test_empty_credentials_handling(self, mock_settings):
        """测试空凭证的处理"""
        mock_settings.feishu_app_id = ""
        mock_settings.feishu_app_secret = ""
        mock_settings.feishu_chat_id = ""

        with patch('src.feishu.feishu_client.Settings', return_value=mock_settings):
            client = FeishuMessageClient()
            assert client.app_id == ""
            assert client.app_secret == ""
            assert client.chat_id == ""