from src.database.models import FileTransferLog, ExecutionSummary, create_tables
import pytest

def test_file_transfer_log_model():
    """测试文件传输日志模型"""
    log = FileTransferLog(
        share_link='https://pan.baidu.com/s/test',
        extraction_code='1234',
        folder_name='test-folder',
        file_name='test.pdf',
        file_path='/test/test.pdf',
        transfer_status='pending'
    )

    assert log.share_link == 'https://pan.baidu.com/s/test'
    assert log.extraction_code == '1234'
    assert log.transfer_status == 'pending'
    assert log.file_size is None  # 默认值

def test_execution_summary_model():
    """测试执行摘要模型"""
    summary = ExecutionSummary(
        share_link='https://pan.baidu.com/s/test',
        folder_name='test-folder',
        total_files=10,
        success_count=8,
        failed_count=2
    )

    assert summary.total_files == 10
    assert summary.success_count == 8
    assert summary.failed_count == 2

def test_create_tables_sql_generation():
    """测试表创建SQL生成"""
    sql = create_tables()

    assert 'CREATE DATABASE' in sql
    assert 'file_transfer_log' in sql
    assert 'execution_summary' in sql
    assert 'share_link' in sql
    assert 'transfer_status' in sql
