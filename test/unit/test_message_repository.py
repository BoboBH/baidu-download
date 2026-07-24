import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog

@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    with patch('pymysql.connect') as mock_connect:
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        yield mock_connection, mock_cursor

def test_insert_message_log(mock_db_connection):
    """测试插入消息日志"""
    mock_connection, mock_cursor = mock_db_connection
    mock_cursor.lastrowid = 1

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    log = MessageProcessLog(
        message_hash='test_hash_123',
        original_message='260723：https://pan.baidu.com/s/xxx',
        share_link='https://pan.baidu.com/s/xxx',
        folder_name='260723',
        status='pending'
    )

    log_id = repo.insert_message_log(log)

    assert log_id == 1
    assert mock_cursor.execute.called

def test_get_message_by_hash(mock_db_connection):
    """测试根据哈希获取消息"""
    mock_connection, mock_cursor = mock_db_connection

    # Mock query results
    mock_cursor.fetchone.return_value = {
        'id': 1,
        'message_hash': 'test_hash_456',
        'original_message': 'test message',
        'share_link': 'https://pan.baidu.com/s/yyy',
        'folder_name': '260724',
        'status': 'success',
        'error_message': None,
        'execution_summary_id': None,
        'processing_time': None,
        'created_at': datetime(2026, 7, 11, 14, 30, 0),
        'updated_at': datetime(2026, 7, 11, 14, 30, 0)
    }

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    retrieved_log = repo.get_message_by_hash('test_hash_456')

    assert retrieved_log is not None
    assert retrieved_log.message_hash == 'test_hash_456'
    assert retrieved_log.status == 'success'
    assert mock_cursor.execute.called

def test_update_message_status(mock_db_connection):
    """测试更新消息状态"""
    mock_connection, mock_cursor = mock_db_connection

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    repo.update_message_status(
        'test_hash_789',
        'success',
        execution_summary_id=999,
        processing_time=3000
    )

    assert mock_cursor.execute.called

def test_get_nonexistent_message(mock_db_connection):
    """测试获取不存在的消息"""
    mock_connection, mock_cursor = mock_db_connection

    # Mock no results
    mock_cursor.fetchone.return_value = None

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    log = repo.get_message_by_hash('nonexistent_hash')

    assert log is None
    assert mock_cursor.execute.called

def test_get_recent_messages_to_retry(mock_db_connection):
    """测试获取需要重试的消息"""
    mock_connection, mock_cursor = mock_db_connection

    # Mock query results
    mock_cursor.fetchall.return_value = [
        {'message_hash': 'hash1'},
        {'message_hash': 'hash2'}
    ]

    repo = DatabaseRepository(
        host='localhost',
        port=3306,
        user='root',
        password='password',
        database='test_db'
    )

    messages = repo.get_recent_messages_to_retry(hours=24)

    assert len(messages) == 2
    assert 'hash1' in messages
    assert 'hash2' in messages
    assert mock_cursor.execute.called
