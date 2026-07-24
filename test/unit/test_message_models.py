from datetime import datetime
from src.database.models import MessageProcessLog

def test_message_process_log_creation():
    """测试MessageProcessLog模型创建"""
    log = MessageProcessLog(
        message_hash='abc123',
        original_message='260723：https://pan.baidu.com/s/xxx',
        share_link='https://pan.baidu.com/s/xxx',
        folder_name='260723',
        status='pending'
    )

    assert log.message_hash == 'abc123'
    assert log.original_message == '260723：https://pan.baidu.com/s/xxx'
    assert log.share_link == 'https://pan.baidu.com/s/xxx'
    assert log.folder_name == '260723'
    assert log.status == 'pending'
    assert log.ID is None
    assert log.CREATED_AT is None

def test_message_process_log_with_optional_fields():
    """测试包含可选字段的MessageProcessLog"""
    log = MessageProcessLog(
        message_hash='def456',
        original_message='test message',
        share_link='https://pan.baidu.com/s/yyy',
        folder_name='260724',
        status='success',
        error_message=None,
        execution_summary_id=123,
        processing_time=5000,
        ID=1,
        CREATED_AT=datetime.now(),
        UPDATED_AT=datetime.now()
    )

    assert log.execution_summary_id == 123
    assert log.processing_time == 5000
    assert log.ID == 1
    assert log.CREATED_AT is not None
    assert log.UPDATED_AT is not None
