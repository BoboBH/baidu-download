"""
集成测试:测试完整的文件传输流程
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.processor.file_processor import FileProcessor
from src.database.models import FileTransferLog, ExecutionSummary

@pytest.fixture
def temp_env():
    """创建临时环境"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建临时目录
        temp_subdir = os.path.join(temp_dir, 'temp')
        os.makedirs(temp_subdir, exist_ok=True)

        # 创建临时配置文件
        env_file = os.path.join(temp_dir, '.env')
        with open(env_file, 'w') as f:
            f.write(f"""
SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=test
SFTP_PASSWORD=test
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=test
DB_NAME=test_db
TEMP_DIR={temp_subdir}
LOG_FILE={temp_dir}/test.log
""")

        # 设置环境变量
        os.environ['SFTP_HOST'] = 'localhost'
        os.environ['SFTP_PORT'] = '22'
        os.environ['SFTP_USERNAME'] = 'test'
        os.environ['SFTP_PASSWORD'] = 'test'
        os.environ['SFTP_REMOTE_PATH'] = '/upload'
        os.environ['DB_HOST'] = 'localhost'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'root'
        os.environ['DB_PASSWORD'] = 'test'
        os.environ['DB_NAME'] = 'test_db'
        os.environ['TEMP_DIR'] = temp_subdir
        os.environ['LOG_FILE'] = f'{temp_dir}/test.log'

        yield temp_dir

def test_full_integration_flow(temp_env):
    """测试完整的集成流程"""

    # 模拟所有外部依赖
    with patch('src.processor.file_processor.BaiduClient') as mock_baidu, \
         patch('src.processor.file_processor.SFTPClient') as mock_sftp, \
         patch('src.processor.file_processor.DatabaseRepository') as mock_db:

        # 设置模拟行为
        mock_baidu_instance = MagicMock()
        mock_baidu.return_value = mock_baidu_instance
        mock_baidu_instance.login.return_value = True
        mock_baidu_instance.delete_directory.return_value = True
        mock_baidu_instance.save_share_link.return_value = True
        mock_baidu_instance.list_pdf_files.return_value = [
            {'name': '/test/file1.pdf', 'size': 1024},
            {'name': '/test/file2.pdf', 'size': 2048}
        ]
        mock_baidu_instance.download_file.return_value = True

        mock_sftp_instance = MagicMock()
        mock_sftp.return_value = mock_sftp_instance
        mock_sftp_instance.connect.return_value = True
        mock_sftp_instance.upload_file.return_value = True

        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.insert_file_log.return_value = 1
        mock_db_instance.insert_execution_summary.return_value = 1

        # 创建临时文件来模拟BaiduPCS-Go
        fake_exe = os.path.join(temp_env, 'BaiduPCS-Go.exe')
        with open(fake_exe, 'w') as f:
            f.write('fake')
        os.environ['BAIDUPCS_GO_PATH'] = fake_exe

        processor = FileProcessor()
        summary = processor.process_files(
            share_link='https://pan.baidu.com/s/test',
            code='1234',
            folder_name='test-folder'
        )

        # 验证结果
        assert summary is not None
        assert summary.total_files == 2
        assert summary.success_count == 2
        assert summary.failed_count == 0

        # 验证调用顺序
        assert mock_baidu_instance.login.called
        assert mock_baidu_instance.delete_directory.called
        assert mock_baidu_instance.save_share_link.called
        assert mock_baidu_instance.list_pdf_files.called
        assert mock_baidu_instance.download_file.call_count == 2
        assert mock_sftp_instance.upload_file.call_count == 2

def test_error_recovery_in_integration(temp_env):
    """测试集成过程中的错误恢复"""

    with patch('src.processor.file_processor.BaiduClient') as mock_baidu, \
         patch('src.processor.file_processor.SFTPClient') as mock_sftp, \
         patch('src.processor.file_processor.DatabaseRepository') as mock_db:

        # 设置第一个文件成功,第二个文件失败
        mock_baidu_instance = MagicMock()
        mock_baidu.return_value = mock_baidu_instance
        mock_baidu_instance.login.return_value = True
        mock_baidu_instance.delete_directory.return_value = True
        mock_baidu_instance.save_share_link.return_value = True
        mock_baidu_instance.list_pdf_files.return_value = [
            {'name': '/test/file1.pdf', 'size': 1024},
            {'name': '/test/file2.pdf', 'size': 2048}
        ]

        # 第一个文件下载成功,第二个失败(所有重试都失败)
        mock_baidu_instance.download_file.side_effect = [True, False, False, False]

        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.insert_file_log.return_value = 1
        mock_db_instance.insert_execution_summary.return_value = 1

        # 创建临时文件来模拟BaiduPCS-Go
        fake_exe = os.path.join(temp_env, 'BaiduPCS-Go.exe')
        with open(fake_exe, 'w') as f:
            f.write('fake')
        os.environ['BAIDUPCS_GO_PATH'] = fake_exe

        processor = FileProcessor()
        summary = processor.process_files(
            share_link='https://pan.baidu.com/s/test',
            code='1234',
            folder_name='test-folder'
        )

        # 验证结果:应该有1个成功,1个失败
        assert summary.total_files == 2
        assert summary.success_count == 1
        assert summary.failed_count == 1
