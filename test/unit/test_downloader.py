import pytest
from unittest.mock import Mock, patch, call
from src.downloader.baidu_client import BaiduClient
from src.config.settings import ConfigError

@pytest.fixture
def mock_settings():
    """模拟配置"""
    with patch('src.downloader.baidu_client.Settings') as mock:
        mock.return_value = Mock(
            baidupcs_go_path='BaiduPCS-Go.exe',
            baidu_cookies_path='./test_cookies.txt',
            temp_dir='./temp'
        )
        yield mock

def test_baidu_client_init_validates_config(mock_settings):
    """测试客户端初始化时验证配置"""
    # Mock the file existence check
    with patch('pathlib.Path.exists', return_value=True):
        client = BaiduClient()

        assert client.baidupcs_path == 'BaiduPCS-Go.exe'
        assert client.temp_dir == './temp'

def test_login_with_cookies(mock_settings):
    """测试使用cookies登录"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='登录成功',
            stderr='',
            returncode=0
        )

        client = BaiduClient()
        result = client.login()

        assert result is True
        assert mock_run.called

def test_save_share_link(mock_settings):
    """测试转存分享链接"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='转存成功',
            stderr='',
            returncode=0
        )

        client = BaiduClient()
        result = client.save_share_link(
            share_link='https://pan.baidu.com/s/test',
            code='1234',
            folder_name='test-folder'
        )

        assert result is True

def test_list_pdf_files(mock_settings):
    """测试列出PDF文件"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='- /test.pdf 1048576\n- /test2.pdf 2048000',
            stderr='',
            returncode=0
        )

        client = BaiduClient()
        files = client.list_pdf_files('test-folder')

        assert len(files) == 2
        assert files[0]['name'] == '/test.pdf'
        assert files[0]['size'] == 1048576

def test_download_file(mock_settings):
    """测试下载文件"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run, \
         patch('os.makedirs'):
        mock_run.return_value = Mock(
            stdout='下载成功',
            stderr='',
            returncode=0
        )

        client = BaiduClient()
        result = client.download_file(
            remote_path='/test.pdf',
            local_path='./temp/test.pdf'
        )

        assert result is True

def test_delete_directory(mock_settings):
    """测试删除目录"""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='删除成功',
            stderr='',
            returncode=0
        )

        client = BaiduClient()
        result = client.delete_directory('test-folder')

        assert result is True
