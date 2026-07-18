"""
测试下载重试逻辑修复 - 确保失败/未上传的文件会被重新下载
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


def test_failed_file_gets_redownloaded(mock_dependencies):
    """测试之前失败的文件会被重新下载"""
    # 创建一个之前失败的文件日志
    failed_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='failed',
        START_TIME=datetime.now(),
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
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = failed_log

    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SUCCESS_COUNT == 1
    assert summary.FAILED_COUNT == 0

    # 验证下载被调用了（说明重新下载了）
    assert mock_dependencies['baidu'].download_file.called
    download_call_count = mock_dependencies['baidu'].download_file.call_count
    assert download_call_count >= 1, "Failed files should be re-downloaded"


def test_success_file_not_redownloaded(mock_dependencies):
    """测试之前成功的文件不会被重新下载"""
    # 创建一个之前成功的文件日志
    success_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='success',
        START_TIME=datetime.now(),
        DOWNLOAD_TIME=datetime.now(),
        UPLOAD_TIME=datetime.now(),
        FILE_SIZE=1024,
        ID=1
    )

    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['db'].insert_execution_summary.return_value = 1
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = success_log

    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SKIPPED_COUNT == 1
    assert summary.SUCCESS_COUNT == 0

    # 验证下载没有被调用（说明跳过了重新下载）
    assert not mock_dependencies['baidu'].download_file.called


def test_pending_file_gets_redownloaded(mock_dependencies):
    """测试之前pending状态的文件会被重新下载"""
    # 创建一个之前pending状态的文件日志
    pending_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='pending',
        START_TIME=datetime.now(),
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
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = pending_log

    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SUCCESS_COUNT == 1

    # 验证下载被调用了（说明重新下载了）
    assert mock_dependencies['baidu'].download_file.called


def test_downloading_file_gets_redownloaded(mock_dependencies):
    """测试之前downloading状态的文件会被重新下载"""
    # 创建一个之前downloading状态的文件日志
    downloading_log = FileTransferLog(
        SHARE_LINK='https://pan.baidu.com/s/test',
        EXTRACTION_CODE='1234',
        FOLDER_NAME='test-folder',
        FILE_NAME='test1.pdf',
        FILE_PATH='/folder/test1.pdf',
        TRANSFER_STATUS='downloading',
        START_TIME=datetime.now(),
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
    mock_dependencies['db'].get_file_log_by_name_and_link.return_value = downloading_log

    processor = FileProcessor(enable_sftp=True)

    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.SUCCESS_COUNT == 1

    # 验证下载被调用了（说明重新下载了）
    assert mock_dependencies['baidu'].download_file.called