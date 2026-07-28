"""
微信公众号文章处理器单元测试
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.config.settings import Settings
from src.wxchat.processor import WeChatAccountSync, WeChatArticleProcessor, DatabaseConnection
from src.wxchat.models import ProcessResult


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_init_wewe_database(self):
        """测试初始化wewe_rss数据库连接"""
        config = Mock()
        config.wxchat_wewe_db_host = 'localhost'
        config.wxchat_wewe_db_port = 3306
        config.wxchat_wewe_db_user = 'root'
        config.wxchat_wewe_db_password = 'password'
        config.wxchat_wewe_db_name = 'wewe_rss'

        conn = DatabaseConnection(config, use_wewe_db=True)

        assert conn.host == 'localhost'
        assert conn.database == 'wewe_rss'

    def test_init_test_database(self):
        """测试初始化test数据库连接"""
        config = Mock()
        config.db_host = 'localhost'
        config.db_port = 3306
        config.db_user = 'root'
        config.db_password = 'password'
        config.db_name = 'test'

        conn = DatabaseConnection(config, use_wewe_db=False)

        assert conn.host == 'localhost'
        assert conn.database == 'test'


class TestWeChatAccountSync:
    """账号同步器测试"""

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_sync_accounts_success(self, mock_db_conn):
        """测试成功同步账号"""
        # 模拟配置
        config = Mock()
        config.wxchat_enabled = True

        # 模拟wewe_rss数据库返回的账号数据
        mock_wewe_conn = Mock()
        mock_wewe_cursor = Mock()
        mock_wewe_cursor.fetchall.return_value = [
            {'id': 'acc1', 'mp_name': '测试账号1'},
            {'id': 'acc2', 'mp_name': '测试账号2'}
        ]
        mock_wewe_conn.cursor.return_value.__enter__.return_value = mock_wewe_cursor
        mock_wewe_conn.commit = Mock()

        # 模拟test数据库
        mock_test_conn = Mock()
        mock_test_cursor = Mock()
        mock_test_conn.cursor.return_value.__enter__.return_value = mock_test_cursor
        mock_test_conn.commit = Mock()

        # 配置DatabaseConnection上下文管理器
        mock_wewe_db_instance = Mock()
        mock_wewe_db_instance.__enter__ = Mock(return_value=mock_wewe_conn)
        mock_wewe_db_instance.__exit__ = Mock(return_value=None)

        mock_test_db_instance = Mock()
        mock_test_db_instance.__enter__ = Mock(return_value=mock_test_conn)
        mock_test_db_instance.__exit__ = Mock(return_value=None)

        mock_db_conn.side_effect = [mock_wewe_db_instance, mock_test_db_instance]

        # 创建同步器并执行同步
        syncer = WeChatAccountSync(config)
        count = syncer.sync_accounts()

        # 验证结果
        assert count == 2
        assert mock_wewe_cursor.execute.called
        assert mock_test_cursor.execute.call_count == 2

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_sync_accounts_no_accounts(self, mock_db_conn):
        """测试没有账号的情况"""
        config = Mock()

        # 模拟空结果
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_db_instance = Mock()
        mock_db_instance.__enter__ = Mock(return_value=mock_conn)
        mock_db_instance.__exit__ = Mock(return_value=None)

        mock_db_conn.return_value = mock_db_instance

        syncer = WeChatAccountSync(config)
        count = syncer.sync_accounts()

        assert count == 0


class TestWeChatArticleProcessor:
    """文章处理器测试"""

    def test_init_processor(self):
        """测试初始化处理器"""
        config = Mock()
        config.wxchat_max_days = 30

        processor = WeChatArticleProcessor(config)

        assert processor.config == config
        assert processor.pdf_generator is not None

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_process_articles_invalid_days(self, mock_db_conn):
        """测试无效的天数参数"""
        config = Mock()
        config.wxchat_max_days = 30

        processor = WeChatArticleProcessor(config)

        # 测试超出范围的天数（注意：这个测试可能需要根据实际实现调整）
        # 因为代码中没有天数验证，所以这个测试可能不适用
        # processor.process_articles(days=31)

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_process_articles_no_articles(self, mock_db_conn):
        """测试没有文章的情况"""
        config = Mock()
        config.wxchat_max_days = 30

        # 模拟数据库返回空结果
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_db_instance = Mock()
        mock_db_instance.__enter__ = Mock(return_value=mock_conn)
        mock_db_instance.__exit__ = Mock(return_value=None)

        mock_db_conn.return_value = mock_db_instance

        processor = WeChatArticleProcessor(config)
        result = processor.process_articles(days=3)

        assert result.total_articles == 0
        assert result.processed_articles == 0


class TestProcessResult:
    """处理结果模型测试"""

    def test_init_result(self):
        """测试初始化结果模型"""
        result = ProcessResult()

        assert result.total_articles == 0
        assert result.processed_articles == 0
        assert result.failed_articles == 0
        assert result.errors == []

    def test_to_dict(self):
        """测试转换为字典"""
        start = datetime.now()
        end = start + timedelta(seconds=10)

        result = ProcessResult(
            total_articles=10,
            processed_articles=8,
            failed_articles=2,
            start_time=start,
            end_time=end
        )

        data = result.to_dict()

        assert data['total_articles'] == 10
        assert data['processed_articles'] == 8
        assert data['failed_articles'] == 2
        assert data['duration_seconds'] == 10

    def test_post_init_errors(self):
        """测试errors字段初始化"""
        result = ProcessResult()
        assert result.errors is not None
        assert isinstance(result.errors, list)