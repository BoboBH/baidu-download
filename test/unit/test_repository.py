import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.database.repository import DatabaseRepository
from src.database.models import FileTransferLog, ExecutionSummary

@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    with patch('pymysql.connect') as mock_connect:
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        yield mock_connection, mock_cursor

def test_repository_init_creates_tables(mock_db_connection):
    """测试仓库初始化时创建表"""
    mock_connection, mock_cursor = mock_db_connection
    
    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )
    
    assert mock_cursor.execute.called
    assert repo.connection == mock_connection

def test_insert_file_log(mock_db_connection):
    """测试插入文件日志"""
    mock_connection, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 1
    
    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )
    
    log = FileTransferLog(
        share_link='https://pan.baidu.com/s/test',
        extraction_code='1234',
        folder_name='test',
        file_name='test.pdf'
    )
    
    log_id = repo.insert_file_log(log)
    
    assert log_id == 1
    assert mock_cursor.execute.called

def test_update_file_status(mock_db_connection):
    """测试更新文件状态"""
    mock_connection, mock_cursor = mock_db_connection

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    repo.update_file_status(
        file_id=1,
        status='downloading',
        error_message=None
    )

    assert mock_cursor.execute.called

def test_get_file_logs_by_link(mock_db_connection):
    """测试根据分享链接获取文件日志"""
    mock_connection, mock_cursor = mock_db_connection

    # Mock query results
    mock_cursor.fetchall.return_value = [
        {
            'id': 1,
            'share_link': 'https://pan.baidu.com/s/test',
            'extraction_code': '1234',
            'folder_name': 'test',
            'file_name': 'test.pdf',
            'file_path': '/test.pdf',
            'transfer_status': 'success',
            'error_message': None,
            'start_time': datetime(2026, 7, 11, 14, 30, 0),
            'download_time': datetime(2026, 7, 11, 14, 31, 0),
            'upload_time': datetime(2026, 7, 11, 14, 32, 0),
            'file_size': 1024,
            'created_at': datetime(2026, 7, 11, 14, 30, 0),
            'updated_at': datetime(2026, 7, 11, 14, 32, 0)
        }
    ]

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    logs = repo.get_file_logs_by_link('https://pan.baidu.com/s/test')

    assert len(logs) == 1
    assert logs[0].file_name == 'test.pdf'
    assert mock_cursor.execute.called
