import pytest
import os
from src.config.settings import Settings, ConfigError

def test_load_config_from_env():
    """测试从环境变量加载配置"""
    os.environ['SFTP_HOST'] = '192.168.1.1'
    os.environ['SFTP_PORT'] = '22'
    os.environ['SFTP_USERNAME'] = 'testuser'
    os.environ['SFTP_PASSWORD'] = 'testpass'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_USER'] = 'root'
    os.environ['DB_PASSWORD'] = 'password'
    os.environ['DB_NAME'] = 'test_db'
    os.environ['SFTP_REMOTE_PATH'] = '/upload'
    os.environ['BAIDUPCS_GO_PATH'] = './fake/BaiduPCS-Go.exe'
    os.environ['TEMP_DIR'] = './temp'

    # Create fake BaiduPCS-Go file
    os.makedirs('./fake', exist_ok=True)
    with open('./fake/BaiduPCS-Go.exe', 'w') as f:
        f.write('fake')

    settings = Settings()

    assert settings.sftp_host == '192.168.1.1'
    assert settings.sftp_port == 22
    assert settings.sftp_username == 'testuser'

def test_missing_required_config_raises_error():
    """测试缺失必需配置时抛出异常"""
    # Clear all relevant environment variables
    for key in list(os.environ.keys()):
        if key.startswith(('SFTP_', 'DB_', 'BAIDU')):
            del os.environ[key]

    with pytest.raises(ConfigError):
        Settings()

def test_invalid_port_number_raises_error():
    """测试无效端口号时抛出异常"""
    # Set valid base config
    os.environ['SFTP_HOST'] = 'localhost'
    os.environ['SFTP_USERNAME'] = 'test'
    os.environ['SFTP_PASSWORD'] = 'test'
    os.environ['SFTP_REMOTE_PATH'] = '/upload'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_USER'] = 'root'
    os.environ['DB_PASSWORD'] = 'test'
    os.environ['DB_NAME'] = 'test'
    os.environ['BAIDUPCS_GO_PATH'] = './fake/BaiduPCS-Go.exe'
    os.environ['TEMP_DIR'] = './temp'

    os.environ['SFTP_PORT'] = 'invalid'

    with pytest.raises(ConfigError):
        Settings()
