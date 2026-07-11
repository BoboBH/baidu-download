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

def test_processor_process_files_successfully(mock_dependencies):
    """测试成功处理文件"""
    # 设置模拟返回值
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024},
        {'name': '/folder/test2.pdf', 'size': 2048}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['sftp'].connect.return_value = True
    mock_dependencies['sftp'].upload_file.return_value = True
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1

    processor = FileProcessor()
    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary is not None
    assert summary.total_files == 2
    assert summary.success_count == 2
    assert summary.failed_count == 0

def test_processor_handles_download_failure(mock_dependencies):
    """测试处理下载失败"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = False  # 下载失败
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1

    processor = FileProcessor()
    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary.failed_count == 1
    assert summary.success_count == 0

def test_processor_handles_upload_failure(mock_dependencies):
    """测试处理上传失败"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = [
        {'name': '/folder/test1.pdf', 'size': 1024}
    ]
    mock_dependencies['baidu'].download_file.return_value = True
    mock_dependencies['sftp'].upload_file.return_value = False  # 上传失败
    mock_dependencies['db'].insert_file_log.return_value = 1
    mock_dependencies['db'].insert_execution_summary.return_value = 1

    processor = FileProcessor()
    summary = processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    assert summary.failed_count == 1
    assert summary.success_count == 0

def test_processor_deletes_existing_folder(mock_dependencies):
    """测试删除已存在的文件夹"""
    mock_dependencies['baidu'].login.return_value = True
    mock_dependencies['baidu'].delete_directory.return_value = True
    mock_dependencies['baidu'].save_share_link.return_value = True
    mock_dependencies['baidu'].list_pdf_files.return_value = []
    mock_dependencies['db'].insert_execution_summary.return_value = 1

    processor = FileProcessor()
    processor.process_files(
        share_link='https://pan.baidu.com/s/test',
        code='1234',
        folder_name='test-folder'
    )

    # 验证删除了旧目录
    mock_dependencies['baidu'].delete_directory.assert_called_once_with('test-folder')
