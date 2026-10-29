"""WXCHAT_UPLOAD_TARGET 上传目标配置的单元测试

覆盖：
- Settings 加载 WXCHAT_UPLOAD_TARGET（默认both / external / 非法值报错）
- external 模式必须有完整外部SFTP配置
- WeChatArticleProcessor._upload_pdf 按模式分流：
  external=仅传外部SFTP（外部客户），both=主SFTP+外部SFTP（原有行为）
"""
import pytest
from unittest.mock import MagicMock

import src.wxchat.processor as proc_module
from src.config.settings import Settings, ConfigError
from src.wxchat.processor import WeChatArticleProcessor


# Settings 必填项的最小可用环境（BAIDUPCS_GO_PATH/TEMP_DIR 由 fixture 填入临时路径）
BASE_ENV = {
    'SFTP_HOST': '192.168.0.122',
    'SFTP_PORT': '22',
    'SFTP_USERNAME': 'sftp01',
    'SFTP_PASSWORD': '123456',
    'SFTP_REMOTE_PATH': '/sftp01/upload',
    'DB_HOST': '127.0.0.1',
    'DB_PORT': '3306',
    'DB_USER': 'user',
    'DB_PASSWORD': 'pwd',
    'DB_NAME': 'testdb',
    'WXCHAT_SFTP_REMOTE_PATH': '/sftp01/upload/wxchat',
    'WXCHAT_EXTERNAL_SFTP_HOST': '192.168.0.122',
    'WXCHAT_EXTERNAL_SFTP_PORT': '22',
    'WXCHAT_EXTERNAL_SFTP_USERNAME': 'sftp01',
    'WXCHAT_EXTERNAL_SFTP_PASSWORD': '123456',
    'WXCHAT_EXTERNAL_SFTP_FOLDER': '/sftp01/upload/cms',
    'WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS': '测试A,测试B',
}


def make_settings(tmp_path, monkeypatch, extra=None, remove=()):
    """用临时env文件构造Settings，隔离本机.env与已污染的os.environ"""
    env = dict(BASE_ENV)
    if extra:
        env.update(extra)
    for key in remove:
        env.pop(key, None)

    env['BAIDUPCS_GO_PATH'] = str(tmp_path / 'BaiduPCS-Go.exe')
    env['TEMP_DIR'] = str(tmp_path / 'temp')
    (tmp_path / 'BaiduPCS-Go.exe').write_text('dummy', encoding='utf-8')

    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for key in remove:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / 'test.env'
    env_file.write_text(
        '\n'.join(f'{k}={v}' for k, v in env.items()), encoding='utf-8'
    )
    return Settings(env_file=str(env_file))


def make_processor(settings):
    return WeChatArticleProcessor(settings, source='crawler')


def upload(processor):
    """调用_upload_pdf的统一入参：crawler源带account_name，避免wewe源查库"""
    return processor._upload_pdf(
        temp_pdf_path='/tmp/fake.pdf',
        publish_date='2026-10-15 10:00:00',
        account_id='mp_123',
        title='文章标题',
        article_id='art-1',
        article={'account_name': '测试号'},
    )


# ===== 配置加载 =====

def test_default_upload_target_is_both(tmp_path, monkeypatch):
    """未配置WXCHAT_UPLOAD_TARGET时默认both（主+外部，保持原有行为）"""
    settings = make_settings(tmp_path, monkeypatch, remove=('WXCHAT_UPLOAD_TARGET',))
    assert settings.wxchat_upload_target == 'both'


def test_external_upload_target_accepted(tmp_path, monkeypatch):
    settings = make_settings(tmp_path, monkeypatch, extra={'WXCHAT_UPLOAD_TARGET': 'external'})
    assert settings.wxchat_upload_target == 'external'


def test_invalid_upload_target_rejected(tmp_path, monkeypatch):
    with pytest.raises(ConfigError):
        make_settings(tmp_path, monkeypatch, extra={'WXCHAT_UPLOAD_TARGET': 'main'})


def test_external_target_requires_external_sftp_config(tmp_path, monkeypatch):
    """external模式下缺外部SFTP配置应启动即报错，否则文章会无处上传"""
    with pytest.raises(ConfigError):
        make_settings(
            tmp_path, monkeypatch,
            extra={'WXCHAT_UPLOAD_TARGET': 'external'},
            remove=('WXCHAT_EXTERNAL_SFTP_HOST',),
        )


# ===== _upload_pdf 按模式分流 =====

def test_external_mode_skips_main_sftp(tmp_path, monkeypatch):
    """external模式：不连主SFTP，只调外部上传，pdf_url记外部路径"""
    settings = make_settings(tmp_path, monkeypatch, extra={'WXCHAT_UPLOAD_TARGET': 'external'})
    processor = make_processor(settings)

    mock_sftp_cls = MagicMock()
    monkeypatch.setattr(proc_module, 'SFTPClient', mock_sftp_cls)
    mock_external = MagicMock(return_value=True)
    monkeypatch.setattr(processor, '_upload_to_external_sftp', mock_external)

    pdf_url, error_message = upload(processor)

    mock_sftp_cls.assert_not_called()  # 主SFTP全程不连接
    mock_external.assert_called_once_with('/tmp/fake.pdf', '测试号', '文章标题', '202610', '测试号')
    assert error_message is None
    assert pdf_url == '/sftp01/upload/cms/202610/测试号_文章标题.pdf'


def test_external_mode_upload_failure(tmp_path, monkeypatch):
    """external模式：外部上传失败应标记文章失败"""
    settings = make_settings(tmp_path, monkeypatch, extra={'WXCHAT_UPLOAD_TARGET': 'external'})
    processor = make_processor(settings)

    mock_sftp_cls = MagicMock()
    monkeypatch.setattr(proc_module, 'SFTPClient', mock_sftp_cls)
    monkeypatch.setattr(processor, '_upload_to_external_sftp', MagicMock(return_value=False))

    pdf_url, error_message = upload(processor)

    mock_sftp_cls.assert_not_called()
    assert pdf_url is None
    assert error_message == '外部SFTP上传失败'


def test_both_mode_uploads_main_then_external(tmp_path, monkeypatch):
    """both模式（默认）：保持原行为——主SFTP成功后再传外部，pdf_url记主路径"""
    settings = make_settings(tmp_path, monkeypatch, remove=('WXCHAT_UPLOAD_TARGET',))
    processor = make_processor(settings)

    mock_sftp_cls = MagicMock()
    # with SFTPClient() as sftp 走 __enter__，实际操作发生在 __enter__ 的返回值上
    mock_sftp_instance = mock_sftp_cls.return_value.__enter__.return_value
    mock_sftp_instance.upload_file.return_value = True
    monkeypatch.setattr(proc_module, 'SFTPClient', mock_sftp_cls)
    mock_external = MagicMock(return_value=True)
    monkeypatch.setattr(processor, '_upload_to_external_sftp', mock_external)

    pdf_url, error_message = upload(processor)

    mock_sftp_cls.assert_called_once_with()  # 主SFTP用默认配置连接
    mock_sftp_instance.upload_file.assert_called_once_with(
        '/tmp/fake.pdf', '/sftp01/upload/wxchat/202610/测试号_文章标题.pdf'
    )
    mock_external.assert_called_once_with('/tmp/fake.pdf', '测试号', '文章标题', '202610', '测试号')
    assert error_message is None
    assert pdf_url == '/sftp01/upload/wxchat/202610/测试号_文章标题.pdf'


def test_both_mode_main_failure_skips_external(tmp_path, monkeypatch):
    """both模式：主SFTP失败时不尝试外部，保持原有嵌套语义"""
    settings = make_settings(tmp_path, monkeypatch, remove=('WXCHAT_UPLOAD_TARGET',))
    processor = make_processor(settings)

    mock_sftp_cls = MagicMock()
    mock_sftp_cls.return_value.__enter__.return_value.upload_file.return_value = False
    monkeypatch.setattr(proc_module, 'SFTPClient', mock_sftp_cls)
    mock_external = MagicMock()
    monkeypatch.setattr(processor, '_upload_to_external_sftp', mock_external)

    pdf_url, error_message = upload(processor)

    mock_external.assert_not_called()
    assert pdf_url is None
    assert error_message == '主SFTP上传失败'
