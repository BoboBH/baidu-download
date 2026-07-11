import pytest
from unittest.mock import Mock, patch, MagicMock
from src.uploader.sftp_client import SFTPClient
from src.config.settings import ConfigError
import paramiko

@pytest.fixture
def mock_settings():
    """模拟配置"""
    with patch('src.uploader.sftp_client.Settings') as mock:
        mock.return_value = Mock(
            sftp_host='192.168.0.122',
            sftp_port=22,
            sftp_username='sftp01',
            sftp_password='123456',
            sftp_remote_path='/upload'
        )
        yield mock

def test_sftp_client_init_validates_config(mock_settings):
    """测试客户端初始化时验证配置"""
    client = SFTPClient()

    assert client.host == '192.168.0.122'
    assert client.port == 22
    assert client.username == 'sftp01'

def test_connect_to_sftp(mock_settings):
    """测试连接SFTP服务器"""
    with patch('paramiko.Transport') as mock_transport, \
         patch('paramiko.SFTPClient.from_transport') as mock_sftp_from_transport:
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp_from_transport.return_value = mock_sftp

        client = SFTPClient()
        client.connect()

        assert client.sftp == mock_sftp
        assert mock_transport.called

def test_upload_file(mock_settings):
    """测试上传文件"""
    with patch('paramiko.Transport') as mock_transport, \
         patch('paramiko.SFTPClient.from_transport') as mock_sftp_from_transport, \
         patch('pathlib.Path.exists', return_value=True):
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp_from_transport.return_value = mock_sftp

        client = SFTPClient()
        client.connect()

        result = client.upload_file(
            local_path='./temp/test.pdf',
            remote_path='/upload/test.pdf'
        )

        assert result is True
        mock_sftp.put.assert_called_once()

def test_create_remote_directory(mock_settings):
    """测试创建远程目录"""
    with patch('paramiko.Transport') as mock_transport, \
         patch('paramiko.SFTPClient.from_transport') as mock_sftp_from_transport:
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp.stat.side_effect = IOError()  # Directory doesn't exist
        mock_sftp_from_transport.return_value = mock_sftp

        client = SFTPClient()
        client.connect()

        client.create_directory('/upload/folder')

        mock_sftp.mkdir.assert_called()

def test_disconnect(mock_settings):
    """测试断开连接"""
    with patch('paramiko.Transport') as mock_transport, \
         patch('paramiko.SFTPClient.from_transport') as mock_sftp_from_transport:
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp_from_transport.return_value = mock_sftp

        client = SFTPClient()
        client.connect()
        client.disconnect()

        mock_sftp.close.assert_called_once()
        mock_transport_instance.close.assert_called_once()
