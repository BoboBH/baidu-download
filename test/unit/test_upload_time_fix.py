"""
测试上传时间修复 - 确保--no-sftp时不设置upload_time
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.processor.file_processor import FileProcessor
from src.database.models import FileTransferLog, ExecutionSummary


@pytest.fixture
def mock_dependencies():
    """模拟所有依赖"""
    with patch('src.processor.file_processor.BaiduClient') as mock_baidu, \
         patch('src.processor.file_processor.SFTPClient') as mock_sftp, \
         patch('src.processor.file_processor.DatabaseRepository') as mock_db, \
         patch('src.processor.file_processor.Settings') as mock_settings:

        mock_baidu_instance = MagicMock()
        mock_baidu.return_value = mock_baidu_instance

        mock_sftp_instance = MagicMock()
        mock_sftp.return_value = mock_sftp_instance
        mock_sftp_instance.remote_path = '/upload'

        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance

        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        mock_settings_instance.temp_dir = 'd:/git/baidu-download/temp'
        mock_settings_instance.max_retries = 3
        mock_settings_instance.db_host = 'localhost'
        mock_settings_instance.db_port = 3306
        mock_settings_instance.db_user = 'root'
        mock_settings_instance.db_password = 'password'
        mock_settings_instance.db_name = 'baidu_download'

        yield {
            'baidu': mock_baidu_instance,
            'sftp': mock_sftp_instance,
            'db': mock_db_instance,
            'settings': mock_settings_instance
        }


def test_no_sftp_does_not_set_upload_time(mock_dependencies):
    """测试--no-sftp时不设置upload_time"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = None

    # 创建禁用SFTP的处理器
    processor = FileProcessor(enable_sftp=False)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SUCCESS_COUNT == 1

    # 验证update_file_status被调用，且没有设置upload_time
    assert mock_dependencies['db'].update_file_status.called
    call_args = mock_dependencies['db'].update_file_status.call_args

    # 检查参数：update_file_status(log_id, 'success', download_time=download_time)
    # 但不包含upload_time参数
    assert call_args[0][1] == 'success'  # status is 'success'
    assert 'download_time' in call_args[1]  # download_time is set

    # 关键验证：upload_time不应该被设置
    # 在kwargs中检查upload_time
    if 'upload_time' in call_args[1]:
        assert call_args[1]['upload_time'] is None, "upload_time should not be set when --no-sftp is used"


def test_sftp_success_sets_upload_time(mock_dependencies):
    """测试SFTP成功时正确设置upload_time"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['sftp'].connect.return_value = True
    mock_dependencies['sftp'].upload_file.return_value = True
    mock_dependencies['sftp'].create_directory.return_value = True
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = None

    # 创建启用SFTP的处理器
    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SUCCESS_COUNT == 1

    # 验证update_file_status被调用，且设置了upload_time
    assert mock_dependencies['db'].update_file_status.called

    # 找到success状态的调用
    success_call = None
    for call in mock_dependencies['db'].update_file_status.call_args_list:
        if call[0][1] == 'success':  # status is 'success'
            success_call = call
            break

    assert success_call is not None, "Should have a success status call"
    assert 'upload_time' in success_call[1], "upload_time should be set when SFTP upload succeeds"
    assert success_call[1]['upload_time'] is not None, "upload_time should not be None when SFTP upload succeeds"


def test_sftp_failure_does_not_set_upload_time(mock_dependencies):
    """测试SFTP失败时不设置upload_time"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['sftp'].connect.return_value = True
    mock_dependencies['sftp'].upload_file.return_value = False  # 上传失败
    mock_dependencies['sftp'].create_directory.return_value = True
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = None

    # 创建启用SFTP的处理器
    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.FAILED_COUNT == 1

    # 验证update_file_status被调用为failed状态，且没有设置upload_time
    assert mock_dependencies['db'].update_file_status.called

    # 找到failed状态的调用
    failed_call = None
    for call in mock_dependencies['db'].update_file_status.call_args_list:
        if call[0][1] == 'failed':  # status is 'failed'
            failed_call = call
            break

    assert failed_call is not None, "Should have a failed status call"
    # 确保没有设置upload_time（或者检查它不是预期的参数）
    if 'upload_time' in failed_call[1]:
        assert failed_call[1]['upload_time'] is None, "upload_time should not be set when upload fails"