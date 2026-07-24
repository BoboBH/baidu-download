import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from src.notification.dingtalk_notifier import DingtalkNotifier


class TestDingtalkNotifier:
    """测试DingtalkNotifier类"""

    @pytest.fixture
    def mock_settings(self):
        """创建Mock配置对象"""
        settings = Mock()
        settings.dingtalk_webhook = "https://oapi.dingtalk.com/robot/send?access_token=test_token"
        return settings

    @pytest.fixture
    def client(self, mock_settings):
        """创建DingtalkNotifier实例"""
        with patch('src.notification.dingtalk_notifier.Settings', return_value=mock_settings):
            return DingtalkNotifier()

    @pytest.fixture
    def client_no_webhook(self):
        """创建没有webhook的客户端实例"""
        settings = Mock()
        settings.dingtalk_webhook = ""
        with patch('src.notification.dingtalk_notifier.Settings', return_value=settings):
            return DingtalkNotifier()

    def test_init_client(self, client, mock_settings):
        """测试客户端初始化"""
        assert client.webhook == "https://oapi.dingtalk.com/robot/send?access_token=test_token"

    def test_init_client_no_webhook(self, client_no_webhook):
        """测试没有webhook时的初始化"""
        assert client_no_webhook.webhook == ""

    def test_send_notification_success(self, client):
        """测试成功发送通知"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        with patch('requests.post', return_value=mock_response):
            result = client.send_notification("测试标题", "测试内容")
            assert result is True

    def test_send_notification_with_markdown_formatting(self, client):
        """测试带markdown格式的通知发送"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        markdown_content = """
# 标题1
## 标题2
*粗体*
- 列表项1
- 列表项2
[链接文字](https://example.com)
"""

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = client.send_notification("测试标题", markdown_content)
            assert result is True

            # 验证请求格式
            call_args = mock_post.call_args
            sent_data = call_args[1]['json']
            assert sent_data['msgtype'] == 'markdown'
            assert sent_data['markdown']['title'] == "测试标题"
            assert markdown_content.strip() in sent_data['markdown']['text']

    def test_send_notification_api_error(self, client):
        """测试API返回错误时的处理"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 300001,
            "errmsg": "keyword is not in content"
        }

        with patch('requests.post', return_value=mock_response):
            result = client.send_notification("测试标题", "测试内容")
            assert result is False

    def test_send_notification_http_error(self, client):
        """测试HTTP错误处理"""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch('requests.post', return_value=mock_response):
            result = client.send_notification("测试标题", "测试内容")
            assert result is False

    def test_send_notification_network_error(self, client):
        """测试网络错误处理"""
        with patch('requests.post', side_effect=requests.exceptions.RequestException("Network error")):
            result = client.send_notification("测试标题", "测试内容")
            assert result is False

    def test_send_notification_no_webhook(self, client_no_webhook):
        """测试没有webhook时的发送"""
        result = client_no_webhook.send_notification("测试标题", "测试内容")
        assert result is False

    def test_send_notification_request_format(self, client):
        """测试请求格式正确性"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            client.send_notification("标题", "内容")

            # 验证请求URL
            call_args = mock_post.call_args
            assert call_args[0][0] == client.webhook

            # 验证请求头
            headers = call_args[1]['headers']
            assert headers['Content-Type'] == 'application/json'

            # 验证请求体
            sent_data = call_args[1]['json']
            assert sent_data['msgtype'] == 'markdown'
            assert 'markdown' in sent_data
            assert 'title' in sent_data['markdown']
            assert 'text' in sent_data['markdown']

    def test_send_notification_empty_content(self, client):
        """测试空内容处理"""
        # 空内容应该被拒绝
        result = client.send_notification("标题", "")
        assert result is False

        # 空标题应该被拒绝
        result = client.send_notification("", "内容")
        assert result is False

    def test_send_notification_timeout(self, client):
        """测试超时处理"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            client.send_notification("标题", "内容")

            # 验证设置了超时
            call_args = mock_post.call_args
            assert 'timeout' in call_args[1]

    def test_send_notification_complex_markdown(self, client):
        """测试复杂markdown格式"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        complex_markdown = """
### 文件传输通知
**文件名**: test.pdf
**大小**: 10.5MB
**状态**: 传输成功

- 服务器: test-server.com
- 路径: /uploads/test.pdf
- 时间: 2024-01-01 12:00:00

[查看详情](https://example.com/details)
"""

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = client.send_notification("文件传输", complex_markdown)
            assert result is True

            # 验证markdown内容被正确传递
            call_args = mock_post.call_args
            sent_data = call_args[1]['json']
            assert "文件传输通知" in sent_data['markdown']['text']
            assert "**文件名**: test.pdf" in sent_data['markdown']['text']
            assert "[查看详情](https://example.com/details)" in sent_data['markdown']['text']

    def test_send_notification_with_newlines(self, client):
        """测试包含换行符的内容"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }

        content_with_newlines = "第一行\n第二行\n第三行"

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = client.send_notification("多行测试", content_with_newlines)
            assert result is True

            call_args = mock_post.call_args
            sent_data = call_args[1]['json']
            assert "第一行" in sent_data['markdown']['text']
            assert "第二行" in sent_data['markdown']['text']
            assert "第三行" in sent_data['markdown']['text']