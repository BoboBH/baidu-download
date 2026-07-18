"""
测试 --no-sftp 后启用 SFTP 的场景
确保先用 --no-sftp 执行，再启用 SFTP 时会重新上传
"""
import pytest
from unittest.mock import patch, MagicMock
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


def test_no_sftp_then_enable_sftp_should_reupload(mock_dependencies):
    """
    测试关键场景：
    1. 先用 --no-sftp 执行，文件状态为 success，upload_time = None
    2. 再去掉 --no-sftp（启用SFTP），应该重新下载并上传
    """
    # 模拟第一次 --no-sftp 执行后的状态：success 但 upload_time = None
    previous_no_sftp_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='success',  # 状态是 success
        START_TIME=datetime.now(),
        DOWNLOAD_TIME=datetime.now(),  # 有下载时间
        UPLOAD_TIME=None,  # ❌ 但没有上传时间（因为是 --no-sftp 模式）
        FILE_SIZE=1024,
        ID=1
    )

    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['sftp'].connect.return_value = True
    mock_dependencies['sftp'].upload_file.return_value = True
    mock_dependencies['sftp'].create_directory.return_value = True
    mock_dependencies['db'].insert_file_log.return_value = 2  # 新的日志ID
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = previous_no_sftp_log

    # 🔑 关键：这次启用 SFTP
    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    # ✅ 验证：应该重新上传，而不是跳过
    assert summary is not None
    assert summary.SUCCESS_COUNT == 1, "File should be uploaded to SFTP"
    assert summary.SKIPPED_COUNT == 0, "File should NOT be skipped"

    # ✅ 验证：下载和上传都被调用了（说明重新处理了）
    assert mock_dependencies['baidu'].download_file.called, "Should re-download the file"
    assert mock_dependencies['sftp'].upload_file.called, "Should upload to SFTP"

    # ✅ 验证：更新了状态并设置了 upload_time
    assert mock_dependencies['db'].update_file_status.called
    # 找到 success 状态的调用
    success_call = None
    for call in mock_dependencies['db'].update_file_status.call_args_list:
        if call[0][1] == 'success':
            success_call = call
            break

    assert success_call is not None, "Should have a success status update"
    assert 'upload_time' in success_call[1], "Should set upload_time this time"
    assert success_call[1]['upload_time'] is not None, "upload_time should not be None"


def test_enable_sftp_then_no_sftp_should_skip(mock_dependencies):
    """
    测试相反场景：
    1. 先启用 SFTP 执行，文件状态为 success，upload_time 有值
    2. 再用 --no-sftp 执行，应该跳过（因为已经成功处理过了）
    """
    # 模拟第一次启用SFTP执行后的状态：success 且 upload_time 有值
    previous_sftp_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='success',  # 状态是 success
        START_TIME=datetime.now(),
        DOWNLOAD_TIME=datetime.now(),  # 有下载时间
        UPLOAD_TIME=datetime.now(),  # ✅ 有上传时间（因为上传到了SFTP）
        FILE_SIZE=1024,
        ID=1
    )

    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = previous_sftp_log

    # 🔑 关键：这次禁用 SFTP
    processor = FileProcessor(enable_sftp=False)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    # ✅ 验证：应该跳过，不再重新处理
    assert summary is not None
    assert summary.SKIPPED_COUNT == 1, "File should be skipped"
    assert summary.SUCCESS_COUNT == 0, "File should NOT be processed again"

    # ✅ 验证：下载和上传都没有被调用（说明跳过了）
    assert not mock_dependencies['baidu'].download_file.called, "Should NOT re-download the file"
    assert not mock_dependencies['sftp'].upload_file.called, "Should NOT upload to SFTP"


def test_sftp_to_sftp_should_skip(mock_dependencies):
    """
    测试两次都启用 SFTP 的场景：
    1. 第一次启用 SFTP 执行，文件上传成功
    2. 第二次还是启用 SFTP，应该跳过（因为已经上传过了）
    """
    # 模拟第一次启用SFTP执行后的状态：success 且 upload_time 有值
    previous_sftp_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='success',
        START_TIME=datetime.now(),
        DOWNLOAD_TIME=datetime.now(),
        UPLOAD_TIME=datetime.now(),  # ✅ 有上传时间
        FILE_SIZE=1024,
        ID=1
    )

    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = previous_sftp_log

    # 🔑 关键：这次也启用 SFTP
    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    # ✅ 验证：应该跳过，不再重新处理
    assert summary is not None
    assert summary.SKIPPED_COUNT == 1, "File should be skipped"
    assert summary.SUCCESS_COUNT == 0, "File should NOT be processed again"

    # ✅ 验证：下载和上传都没有被调用（说明跳过了）
    assert not mock_dependencies['baidu'].download_file.called, "Should NOT re-download"
    assert not mock_dependencies['sftp'].upload_file.called, "Should NOT re-upload"