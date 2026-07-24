import os
import pytest
from src.config.settings import Settings, ConfigError

@pytest.fixture
def cleanup_env():
    """Fixture to ensure environment variables are cleaned up after each test"""
    original_env = os.environ.copy()
    yield
    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def required_config(cleanup_env):
    """Fixture to set required configuration for Settings initialization"""
    required_vars = {
        'SFTP_HOST': 'test_host',
        'SFTP_USERNAME': 'test_user',
        'SFTP_PASSWORD': 'test_pass',
        'SFTP_REMOTE_PATH': '/test/path',
        'DB_HOST': 'localhost',
        'DB_USER': 'root',
        'DB_PASSWORD': 'password',
        'DB_NAME': 'test_db'
    }
    for key, value in required_vars.items():
        os.environ[key] = value
    yield required_vars


def test_feishu_config_loading(required_config):
    """测试飞书配置加载"""
    # 设置飞书配置环境变量
    os.environ['FEISHU_APP_ID'] = 'cli_a1b2c3d4e5f6g7h8'
    os.environ['FEISHU_APP_SECRET'] = 'secret_app_secret_value_here'
    os.environ['FEISHU_CHAT_ID'] = 'oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    os.environ['FEISHU_HOURS_LIMIT'] = '48'
    os.environ['DINGTALK_WEBHOOK'] = 'https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    os.environ['MESSAGE_DEFAULT_EXTRACTION_CODE'] = '0410'

    settings = Settings()

    assert settings.feishu_app_id == 'cli_a1b2c3d4e5f6g7h8'
    assert settings.feishu_app_secret == 'secret_app_secret_value_here'
    assert settings.feishu_chat_id == 'oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    assert settings.feishu_hours_limit == 48
    assert settings.dingtalk_webhook == 'https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    assert settings.message_default_extraction_code == '0410'


def test_feishu_config_defaults(required_config):
    """测试飞书配置默认值"""
    settings = Settings()

    assert settings.feishu_app_id == ''
    assert settings.feishu_app_secret == ''
    assert settings.feishu_chat_id == ''
    assert settings.feishu_hours_limit == 24  # 24 hours default
    assert settings.dingtalk_webhook == ''
    assert settings.message_default_extraction_code == '0409'


def test_feishu_validation_app_id_without_secret(required_config):
    """测试飞书配置验证：只有APP_ID没有APP_SECRET应该报错"""
    os.environ['FEISHU_APP_ID'] = 'cli_a1b2c3d4e5f6g7h8'

    with pytest.raises(ConfigError, match="FEISHU_APP_ID provided but FEISHU_APP_SECRET missing"):
        Settings()


def test_feishu_validation_secret_without_app_id(required_config):
    """测试飞书配置验证：只有APP_SECRET没有APP_ID应该报错"""
    os.environ['FEISHU_APP_SECRET'] = 'secret_app_secret_value_here'

    with pytest.raises(ConfigError, match="FEISHU_APP_SECRET provided but FEISHU_APP_ID missing"):
        Settings()


def test_feishu_validation_chat_id_without_credentials(required_config):
    """测试飞书配置验证：只有CHAT_ID没有凭据应该报错"""
    os.environ['FEISHU_CHAT_ID'] = 'oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

    with pytest.raises(ConfigError, match="FEISHU_CHAT_ID provided but FEISHU_APP_ID or FEISHU_APP_SECRET missing"):
        Settings()


def test_feishu_validation_complete_config(required_config):
    """测试飞书配置验证：完整的配置应该通过验证"""
    os.environ['FEISHU_APP_ID'] = 'cli_a1b2c3d4e5f6g7h8'
    os.environ['FEISHU_APP_SECRET'] = 'secret_app_secret_value_here'
    os.environ['FEISHU_CHAT_ID'] = 'oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

    # Should not raise any exception
    settings = Settings()
    assert settings.feishu_app_id == 'cli_a1b2c3d4e5f6g7h8'
    assert settings.feishu_app_secret == 'secret_app_secret_value_here'
    assert settings.feishu_chat_id == 'oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'


def test_feishu_validation_partial_config_ok(required_config):
    """测试飞书配置验证：部分配置（没有CHAT_ID）应该通过"""
    os.environ['FEISHU_APP_ID'] = 'cli_a1b2c3d4e5f6g7h8'
    os.environ['FEISHU_APP_SECRET'] = 'secret_app_secret_value_here'

    # Should not raise any exception (CHAT_ID is optional)
    settings = Settings()
    assert settings.feishu_app_id == 'cli_a1b2c3d4e5f6g7h8'
    assert settings.feishu_app_secret == 'secret_app_secret_value_here'
    assert settings.feishu_chat_id == ''


def test_dingtalk_webhook_invalid_format(required_config):
    """测试钉钉webhook URL格式验证：无效的URL应该报错"""
    os.environ['DINGTALK_WEBHOOK'] = 'not-a-valid-url'

    with pytest.raises(ConfigError, match="Invalid DINGTALK_WEBHOOK URL format"):
        Settings()


def test_dingtalk_webhook_valid_format(required_config):
    """测试钉钉webhook URL格式验证：有效的URL应该通过"""
    os.environ['DINGTALK_WEBHOOK'] = 'https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxx'

    # Should not raise any exception
    settings = Settings()
    assert settings.dingtalk_webhook == 'https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxx'


def test_extraction_code_invalid_format(required_config):
    """测试提取码格式验证：非4位数字应该报错"""
    os.environ['MESSAGE_DEFAULT_EXTRACTION_CODE'] = 'abc123'

    with pytest.raises(ConfigError, match="Invalid MESSAGE_DEFAULT_EXTRACTION_CODE format"):
        Settings()


def test_extraction_code_valid_format(required_config):
    """测试提取码格式验证：4位数字应该通过"""
    os.environ['MESSAGE_DEFAULT_EXTRACTION_CODE'] = '0410'

    # Should not raise any exception
    settings = Settings()
    assert settings.message_default_extraction_code == '0410'


def test_extraction_code_default_format(required_config):
    """测试提取码格式验证：默认值'0409'应该通过"""
    # Don't set MESSAGE_DEFAULT_EXTRACTION_CODE, use default
    settings = Settings()
    assert settings.message_default_extraction_code == '0409'  # Default value is valid
