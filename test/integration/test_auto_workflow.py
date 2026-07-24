"""
Integration tests for the complete automatic message processing workflow.

Tests the end-to-end workflow from Feishu message retrieval through DingTalk notification,
verifying the integration of all components: FeishuMessageClient, MessageParser,
DatabaseRepository, FileProcessor, DingtalkNotifier, and AutoProcessor.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from src.processor.auto_processor import AutoProcessor, ProcessResult
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser, ParseResult
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.database.models import ExecutionSummary
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.config.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings configuration"""
    with patch('src.config.settings.os.environ', {
        'SFTP_HOST': 'localhost',
        'SFTP_PORT': '22',
        'SFTP_USERNAME': 'testuser',
        'SFTP_PASSWORD': 'testpass',
        'SFTP_REMOTE_PATH': '/upload',
        'DB_HOST': 'localhost',
        'DB_PORT': '3306',
        'DB_USER': 'root',
        'DB_PASSWORD': 'password',
        'DB_NAME': 'test_baidu_download',
        'BAIDUPCS_GO_PATH': './fake/BaiduPCS-Go.exe',
        'TEMP_DIR': './temp_test',
        'FEISHU_APP_ID': 'test_app_id',
        'FEISHU_APP_SECRET': 'test_app_secret',
        'FEISHU_CHAT_ID': 'test_chat_id',
        'DINGTALK_WEBHOOK': 'https://oapi.dingtalk.com/robot/send?access_token=test',
        'MESSAGE_DEFAULT_EXTRACTION_CODE': '0409',
        'MAX_RETRIES': '3'
    }):
        # Create fake BaiduPCS-Go file
        import os
        os.makedirs('./fake', exist_ok=True)
        with open('./fake/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        os.makedirs('./temp_test', exist_ok=True)

        yield Settings()

        # Cleanup
        import shutil
        if os.path.exists('./fake'):
            shutil.rmtree('./fake')
        if os.path.exists('./temp_test'):
            shutil.rmtree('./temp_test')


@pytest.fixture
def mock_database():
    """Create mock database repository for testing"""
    mock_db = Mock(spec=DatabaseRepository)

    # Setup common mock behaviors
    mock_db.get_message_by_hash.return_value = None  # No duplicates by default
    mock_db.insert_message_log.return_value = 1  # Return fake message ID
    mock_db.update_message_status.return_value = None

    yield mock_db


@pytest.fixture
def sample_feishu_messages():
    """Sample Feishu messages for testing"""
    return [
        {
            "message_id": "msg_001",
            "content": "240724: https://pan.baidu.com/s/abc123"
        },
        {
            "message_id": "msg_002",
            "content": "240725: https://pan.baidu.com/s/def456"
        },
        {
            "message_id": "msg_003",
            "content": "240726: https://pan.baidu.com/s/ghi789"
        }
    ]


@pytest.fixture
def mock_execution_summary():
    """Create mock execution summary"""
    return ExecutionSummary(
        share_link='https://pan.baidu.com/s/abc123',
        folder_name='240724',
        total_files=2,
        success_count=2,
        failed_count=0,
        skipped_count=0,
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_size=1024000
    )


class TestAutoWorkflowIntegration:
    """Integration tests for complete automatic workflow"""

    def test_complete_successful_workflow(self, test_settings, mock_database, sample_feishu_messages):
        """Test complete successful workflow: message → parsing → processing → notification"""

        # Setup mocks
        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = sample_feishu_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock
            mock_processor = Mock()
            mock_summary = ExecutionSummary(
                share_link='https://pan.baidu.com/s/abc123',
                folder_name='240724',
                total_files=2,
                success_count=2,
                failed_count=0,
                skipped_count=0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_size=1024000
            )
            mock_processor.process_files.return_value = mock_summary
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor with test settings
            processor = AutoProcessor(test_settings)

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify overall success
            assert exit_code == 0, "Process should return success exit code"

            # Verify Feishu client was called
            mock_feishu_client.get_messages.assert_called_once()

            # Verify all messages were processed
            assert mock_processor.process_files.call_count == 3, "Should process all 3 messages"

            # Verify database operations
            assert mock_database.insert_message_log.call_count == 3, "Should insert 3 messages"

            # Verify notification was sent
            mock_dingtalk.send_notification.assert_called_once()
            call_args = mock_dingtalk.send_notification.call_args
            assert call_args[0][0] == "百度网盘文件处理报告"
            assert "成功: 3 条" in call_args[0][1]  # Should have 3 successful messages

            # Verify database operations were called correctly
            assert mock_database.insert_message_log.call_count == 3, "Should insert 3 messages"
            assert mock_database.update_message_status.call_count >= 6, "Should update status at least 6 times (3 messages, 2 updates each)"

            # Verify each message was inserted with correct initial status
            for call in mock_database.insert_message_log.call_args_list:
                message_log = call[0][0]  # Get the MessageProcessLog object
                assert message_log.status == "pending", "Initial status should be pending"
                assert message_log.message_hash is not None
                assert message_log.share_link is not None
                assert message_log.folder_name is not None

            # Verify status updates from pending -> processing -> success
            processing_updates = [call for call in mock_database.update_message_status.call_args_list if call[0][1] == "processing"]
            success_updates = [call for call in mock_database.update_message_status.call_args_list if call[0][1] == "success"]

            assert len(processing_updates) == 3, "Should have 3 processing status updates"
            assert len(success_updates) == 3, "Should have 3 success status updates"

    def test_duplicate_message_handling(self, test_settings, mock_database, sample_feishu_messages):
        """Test duplicate message handling: existing message skipped, new message processed"""

        # Setup: Configure mock database to return existing message for first message (duplicate)
        parser = MessageParser()
        first_msg_content = sample_feishu_messages[0]["content"]
        first_msg_hash = parser.calculate_message_hash(first_msg_content)

        # Configure mock to return existing message for first message (duplicate)
        # but return None for other messages (new)
        def mock_get_by_hash(message_hash):
            if message_hash == first_msg_hash:
                return MessageProcessLog(
                    message_hash=first_msg_hash,
                    original_message=first_msg_content,
                    share_link='https://pan.baidu.com/s/abc123',
                    folder_name='240724',
                    status='success',
                    processing_time=1000
                )
            return None

        mock_database.get_message_by_hash.side_effect = mock_get_by_hash

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock - return same messages (first one is duplicate)
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = sample_feishu_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock - only process new messages (should be called twice)
            mock_processor = Mock()
            mock_processor.process_files.return_value = ExecutionSummary(
                share_link='https://pan.baidu.com/s/test',
                folder_name='240725',
                total_files=1,
                success_count=1,
                failed_count=0,
                skipped_count=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify success
            assert exit_code == 0

            # Verify FileProcessor was called only for new messages (2 times, not 3)
            assert mock_processor.process_files.call_count == 2, "Should only process 2 new messages, skip 1 duplicate"

            # Verify notification mentions skipped message
            mock_dingtalk.send_notification.assert_called_once()
            call_args = mock_dingtalk.send_notification.call_args
            notification_content = call_args[0][1]
            assert "跳过: 1 条" in notification_content, "Should report 1 skipped message"

            # Verify first message was checked for duplicate
            assert mock_database.get_message_by_hash.called, "Should check for duplicate messages"
            assert mock_database.get_message_by_hash.call_count >= 1, "Should check at least one message hash"

            # Verify only new messages were inserted (2 messages, not 3)
            assert mock_database.insert_message_log.call_count == 2, "Should only insert 2 new messages"

    def test_mixed_results_workflow(self, test_settings, mock_database):
        """Test mixed results workflow: some messages succeed, some fail"""

        mixed_messages = [
            {"message_id": "msg_001", "content": "240724: https://pan.baidu.com/s/success1"},
            {"message_id": "msg_002", "content": "240725: https://pan.baidu.com/s/success2"},
            {"message_id": "msg_003", "content": "240726: https://pan.baidu.com/s/fail1"},
            {"message_id": "msg_004", "content": "240727: https://pan.baidu.com/s/fail2"}
        ]

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = mixed_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock - mixed results
            mock_processor = Mock()

            def mock_process_files(share_link, code, folder_name):
                if "fail" in share_link:
                    return None  # Simulate failure
                else:
                    return ExecutionSummary(
                        share_link=share_link,
                        folder_name=folder_name,
                        total_files=1,
                        success_count=1,
                        failed_count=0,
                        skipped_count=0,
                        start_time=datetime.now(),
                        end_time=datetime.now()
                    )

            mock_processor.process_files.side_effect = mock_process_files
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify overall success (partial failures still return 0)
            assert exit_code == 0

            # Verify all messages were attempted
            assert mock_processor.process_files.call_count == 4

            # Verify notification reports both successes and failures
            mock_dingtalk.send_notification.assert_called_once()
            call_args = mock_dingtalk.send_notification.call_args
            notification_content = call_args[0][1]

            assert "成功: 2 条" in notification_content
            assert "失败: 2 条" in notification_content
            assert "## 处理失败" in notification_content

            # Verify database states for failed messages
            # Check that update_message_status was called with 'failed' status for failed messages
            failed_status_updates = [call for call in mock_database.update_message_status.call_args_list if call[0][1] == "failed"]
            assert len(failed_status_updates) == 2, "Should have 2 failed status updates"

            # Verify error messages were provided
            for update_call in failed_status_updates:
                kwargs = update_call[1]
                assert 'error_message' in kwargs
                assert kwargs['error_message'] is not None

    def test_feishu_api_failure(self, test_settings, mock_database):
        """Test workflow behavior when Feishu API fails"""

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client to raise exception
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.side_effect = Exception("Feishu API connection failed")
            mock_feishu_cls.return_value = mock_feishu_client

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify critical failure returns exit code 1
            assert exit_code == 1, "Critical API failure should return exit code 1"

    def test_database_error_handling(self, test_settings, mock_database):
        """Test workflow behavior when database operations fail"""

        sample_messages = [
            {"message_id": "msg_001", "content": "240724: https://pan.baidu.com/s/abc123"}
        ]

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = sample_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock
            mock_processor = Mock()
            mock_processor.process_files.return_value = ExecutionSummary(
                share_link='https://pan.baidu.com/s/abc123',
                folder_name='240724',
                total_files=1,
                success_count=1,
                failed_count=0,
                skipped_count=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)

            # Mock database to fail on insert
            mock_db_repo = Mock()
            mock_db_repo.insert_message_log.side_effect = Exception("Database connection lost")
            mock_db_repo.get_message_by_hash.return_value = None  # No duplicate
            processor.db_repo = mock_db_repo

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify graceful handling - database errors during individual message processing
            # should not crash the entire workflow
            assert exit_code == 0, "Should continue processing despite database errors"

    def test_file_processor_error_handling(self, test_settings, mock_database):
        """Test workflow behavior when FileProcessor fails"""

        sample_messages = [
            {"message_id": "msg_001", "content": "240724: https://pan.baidu.com/s/abc123"}
        ]

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = sample_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock to return None (failure)
            mock_processor = Mock()
            mock_processor.process_files.return_value = None
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify workflow continues despite file processing failure
            assert exit_code == 0

            # Verify message marked as failed in database
            # Find the failed status update
            failed_updates = [call for call in mock_database.update_message_status.call_args_list if call[0][1] == "failed"]
            assert len(failed_updates) > 0, "Should have at least one failed status update"

            failed_update = failed_updates[0]
            kwargs = failed_update[1]
            assert 'error_message' in kwargs
            assert kwargs['error_message'] is not None

    def test_notification_format_and_content(self, test_settings, mock_database):
        """Test notification format and content verification"""

        sample_messages = [
            {"message_id": "msg_001", "content": "240724: https://pan.baidu.com/s/success1"},
            {"message_id": "msg_002", "content": "240725: https://pan.baidu.com/s/fail1"},
            {"message_id": "msg_003", "content": "240726: https://pan.baidu.com/s/success2"}
        ]

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = sample_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock
            mock_processor = Mock()

            def mock_process_files(share_link, code, folder_name):
                if "fail" in share_link:
                    return None  # Simulate failure
                else:
                    return ExecutionSummary(
                        share_link=share_link,
                        folder_name=folder_name,
                        total_files=1,
                        success_count=1,
                        failed_count=0,
                        skipped_count=0,
                        start_time=datetime.now(),
                        end_time=datetime.now()
                    )

            mock_processor.process_files.side_effect = mock_process_files
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify notification structure
            assert exit_code == 0
            mock_dingtalk.send_notification.assert_called_once()

            call_args = mock_dingtalk.send_notification.call_args
            title, content = call_args[0]

            # Verify title
            assert title == "百度网盘文件处理报告"

            # Verify required sections
            assert "## 处理结果摘要" in content
            assert "总计处理: 3 条消息" in content
            assert "成功: 2 条" in content
            assert "失败: 1 条" in content

            # Verify success section
            assert "## 成功处理" in content
            assert "✅ 240724 - 文件传输成功" in content
            assert "✅ 240726 - 文件传输成功" in content

            # Verify failure section
            assert "## 处理失败" in content
            assert "❌ 240725 - " in content  # Should have error message

            # Verify timestamp
            assert "## 处理时间" in content
            assert "完成时间:" in content

    def test_empty_message_list(self, test_settings, mock_database):
        """Test workflow behavior with empty message list"""

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client to return empty list
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = []
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify success
            assert exit_code == 0

            # Verify notification sent with 0 messages
            mock_dingtalk.send_notification.assert_called_once()
            call_args = mock_dingtalk.send_notification.call_args
            notification_content = call_args[0][1]
            assert "总计处理: 0 条消息" in notification_content

    def test_invalid_message_content_handling(self, test_settings, mock_database):
        """Test workflow behavior with invalid/unparseable message content"""

        invalid_messages = [
            {"message_id": "msg_001", "content": ""},  # Empty content
            {"message_id": "msg_002", "content": "invalid message format"},  # Wrong format
            {"message_id": "msg_003", "content": "240724: https://pan.baidu.com/s/valid123"}  # Valid
        ]

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = invalid_messages
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock
            mock_processor = Mock()
            mock_processor.process_files.return_value = ExecutionSummary(
                share_link='https://pan.baidu.com/s/valid123',
                folder_name='240724',
                total_files=1,
                success_count=1,
                failed_count=0,
                skipped_count=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify success - invalid messages should be skipped
            assert exit_code == 0

            # Verify only valid message was processed
            assert mock_processor.process_files.call_count == 1

            # Verify valid message was processed
            assert mock_processor.process_files.call_count == 1
            assert mock_database.insert_message_log.call_count == 1

            # Verify the processed message was the valid one
            insert_call = mock_database.insert_message_log.call_args_list[0]
            message_log = insert_call[0][0]
            assert message_log.folder_name == "240724"

    def test_message_parsing_and_hashing(self, test_settings, mock_database):
        """Test message parsing and hashing integration"""

        parser = MessageParser()

        # Test valid message parsing
        valid_content = "240724: https://pan.baidu.com/s/abc123"
        parse_result = parser.parse_message(valid_content)

        assert parse_result is not None
        assert parse_result.folder_name == "240724"
        assert parse_result.share_link == "https://pan.baidu.com/s/abc123"
        assert parse_result.code == test_settings.message_default_extraction_code

        # Test hash calculation
        msg_hash = parser.calculate_message_hash(valid_content)
        assert len(msg_hash) == 32  # MD5 hash length
        assert msg_hash == msg_hash.lower()  # Should be lowercase

        # Test duplicate detection using hash
        same_hash = parser.calculate_message_hash(valid_content)
        assert msg_hash == same_hash, "Same content should produce same hash"

        # Test different content produces different hash
        different_content = "240725: https://pan.baidu.com/s/def456"
        different_hash = parser.calculate_message_hash(different_content)
        assert msg_hash != different_hash, "Different content should produce different hash"

    def test_database_status_transitions(self, test_settings, mock_database):
        """Test database status transitions throughout message lifecycle"""

        sample_message = {
            "message_id": "msg_001",
            "content": "240724: https://pan.baidu.com/s/abc123"
        }

        with patch('src.processor.auto_processor.FeishuMessageClient') as mock_feishu_cls, \
             patch('src.processor.auto_processor.DatabaseRepository') as mock_db_repo_cls, \
             patch('src.processor.auto_processor.FileProcessor') as mock_processor_cls, \
             patch('src.processor.auto_processor.DingtalkNotifier') as mock_dingtalk_cls:

            # Configure DatabaseRepository mock to return our mock_database
            mock_db_repo_cls.return_value = mock_database

            # Configure Feishu client mock
            mock_feishu_client = Mock()
            mock_feishu_client.get_messages.return_value = [sample_message]
            mock_feishu_cls.return_value = mock_feishu_client

            # Configure FileProcessor mock
            mock_processor = Mock()
            mock_processor.process_files.return_value = ExecutionSummary(
                share_link='https://pan.baidu.com/s/abc123',
                folder_name='240724',
                total_files=1,
                success_count=1,
                failed_count=0,
                skipped_count=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            mock_processor_cls.return_value = mock_processor

            # Configure Dingtalk notifier mock
            mock_dingtalk = Mock()
            mock_dingtalk.send_notification.return_value = True
            mock_dingtalk_cls.return_value = mock_dingtalk

            # Create AutoProcessor
            processor = AutoProcessor(test_settings)
            # DatabaseRepository is mocked via patch, no need to set manually

            # Mock database to track status changes
            status_history = []

            def mock_update_status(message_hash, status, **kwargs):
                status_history.append((message_hash, status, kwargs))
                return None

            mock_database.update_message_status.side_effect = mock_update_status

            # Execute workflow
            exit_code = processor.process_messages()

            # Verify success
            assert exit_code == 0

            # Verify status transitions
            parser = MessageParser()
            msg_hash = parser.calculate_message_hash(sample_message["content"])

            # Should have status updates: pending -> processing -> success
            status_updates_for_message = [s for s in status_history if s[0] == msg_hash]
            assert len(status_updates_for_message) >= 2, "Should have at least 2 status updates"

            # Final status should be success
            final_status = status_updates_for_message[-1][1]
            assert final_status == 'success', f"Final status should be success, got {final_status}"

            # Verify processing time was recorded
            final_kwargs = status_updates_for_message[-1][2]
            assert 'processing_time' in final_kwargs
            assert final_kwargs['processing_time'] is not None
            assert final_kwargs['processing_time'] >= 0  # Processing time can be 0 in fast tests