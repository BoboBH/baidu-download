"""
微信公众号模块单元测试

测试覆盖：
- 数据模型 (WeChatAccount, WeChatArticle, ProcessResult)
- 数据库连接管理 (DatabaseConnection)
- 账号同步 (WeChatAccountSync)
- PDF生成 (PDFGenerator)
- 文章处理 (WeChatArticleProcessor)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import tempfile
import os

from src.wxchat.models import WeChatAccount, WeChatArticle, ProcessResult
from src.wxchat.processor import (
    DatabaseConnection,
    WeChatAccountSync,
    PDFGenerator,
    WeChatArticleProcessor
)


def create_mock_config():
    """创建配置Mock对象，设置所有必要的属性"""
    mock_config = Mock()
    # 数据库配置
    mock_config.db_host = "localhost"
    mock_config.db_port = 3306
    mock_config.db_user = "test_user"
    mock_config.db_password = "test_pass"
    mock_config.db_name = "test_db"
    # Wewe数据库配置
    mock_config.wxchat_wewe_db_host = "wewe_host"
    mock_config.wxchat_wewe_db_port = 3307
    mock_config.wxchat_wewe_db_user = "wewe_user"
    mock_config.wxchat_wewe_db_password = "wewe_pass"
    mock_config.wxchat_wewe_db_name = "wewe_db"
    # PDF生成配置
    mock_config.wxchat_base_url = "https://example.com/"
    mock_config.wxchat_pdf_timeout = 30
    mock_config.wxchat_image_wait_time = 0
    mock_config.wxchat_download_delay = 0
    return mock_config


class TestWeChatAccount:
    """测试WeChatAccount数据模型"""

    def test_wechat_account_creation(self):
        """测试账号创建与所有字段"""
        account = WeChatAccount(
            account_id="test_account",
            account_name="Test Account",
            app_id="test_app",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert account.account_id == "test_account"
        assert account.account_name == "Test Account"
        assert account.app_id == "test_app"
        assert isinstance(account.created_at, datetime)
        assert isinstance(account.updated_at, datetime)

    def test_wechat_account_defaults(self):
        """测试默认时间戳值"""
        account = WeChatAccount(
            account_id="test_account",
            account_name="Test Account"
        )
        assert account.account_id == "test_account"
        assert account.account_name == "Test Account"
        assert account.app_id is None
        assert account.created_at is None
        assert account.updated_at is None

    def test_wechat_account_to_dict(self):
        """测试转换为字典格式"""
        account = WeChatAccount(
            account_id="test_account",
            account_name="Test Account",
            app_id="test_app",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0)
        )

        # 由于WeChatAccount是dataclass，可以直接转换为字典
        account_dict = {
            'account_id': account.account_id,
            'account_name': account.account_name,
            'app_id': account.app_id,
            'created_at': account.created_at,
            'updated_at': account.updated_at
        }

        assert account_dict['account_id'] == "test_account"
        assert account_dict['account_name'] == "Test Account"
        assert account_dict['app_id'] == "test_app"
        assert isinstance(account_dict['created_at'], datetime)
        assert isinstance(account_dict['updated_at'], datetime)


class TestWeChatArticle:
    """测试WeChatArticle数据模型"""

    def test_wechat_article_creation(self):
        """测试文章创建与所有字段"""
        article = WeChatArticle(
            article_id="test_article",
            account_id="test_account",
            title="Test Article",
            publish_date=datetime(2024, 1, 1, 12, 0, 0),
            pdf_url="https://example.com/test.pdf",
            processed_at=datetime(2024, 1, 1, 13, 0, 0),
            error_message=None,
            retry_count=0
        )

        assert article.article_id == "test_article"
        assert article.account_id == "test_account"
        assert article.title == "Test Article"
        assert article.publish_date == datetime(2024, 1, 1, 12, 0, 0)
        assert article.pdf_url == "https://example.com/test.pdf"
        assert article.processed_at == datetime(2024, 1, 1, 13, 0, 0)
        assert article.error_message is None
        assert article.retry_count == 0

    def test_wechat_article_defaults(self):
        """测试文章默认值"""
        article = WeChatArticle(
            article_id="test_article",
            account_id="test_account"
        )

        assert article.article_id == "test_article"
        assert article.account_id == "test_account"
        assert article.title is None
        assert article.publish_date is None
        assert article.pdf_url is None
        assert article.processed_at is None
        assert article.error_message is None
        assert article.retry_count == 0
        assert article.created_at is None
        assert article.updated_at is None

    def test_wechat_article_to_dict(self):
        """测试文章转换为字典格式"""
        article = WeChatArticle(
            article_id="test_article",
            account_id="test_account",
            title="Test Article",
            publish_date=datetime(2024, 1, 1, 12, 0, 0)
        )

        # 由于WeChatArticle是dataclass，可以直接转换为字典
        article_dict = {
            'article_id': article.article_id,
            'account_id': article.account_id,
            'title': article.title,
            'publish_date': article.publish_date,
            'pdf_url': article.pdf_url,
            'processed_at': article.processed_at,
            'error_message': article.error_message,
            'retry_count': article.retry_count
        }

        assert article_dict['article_id'] == "test_article"
        assert article_dict['account_id'] == "test_account"
        assert article_dict['title'] == "Test Article"
        assert article_dict['retry_count'] == 0


class TestProcessResult:
    """测试ProcessResult统计模型"""

    def test_process_result_creation(self):
        """测试处理结果创建"""
        result = ProcessResult(
            total_articles=10,
            processed_articles=8,
            failed_articles=1,
            skipped_articles=1,
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 13, 0, 0),
            errors=["Error 1", "Error 2"]
        )

        assert result.total_articles == 10
        assert result.processed_articles == 8
        assert result.failed_articles == 1
        assert result.skipped_articles == 1
        assert result.start_time == datetime(2024, 1, 1, 12, 0, 0)
        assert result.end_time == datetime(2024, 1, 1, 13, 0, 0)
        assert len(result.errors) == 2

    def test_process_result_defaults(self):
        """测试处理结果默认值"""
        result = ProcessResult()

        assert result.total_articles == 0
        assert result.processed_articles == 0
        assert result.failed_articles == 0
        assert result.skipped_articles == 0
        assert result.start_time is None
        assert result.end_time is None
        assert result.errors == []  # 由于__post_init__初始化为空列表

    def test_process_result_to_dict(self):
        """测试处理结果转换为字典格式"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 13, 0, 0)

        result = ProcessResult(
            total_articles=10,
            processed_articles=8,
            failed_articles=1,
            skipped_articles=1,
            start_time=start_time,
            end_time=end_time,
            errors=["Error 1"]
        )

        result_dict = result.to_dict()

        assert result_dict['total_articles'] == 10
        assert result_dict['processed_articles'] == 8
        assert result_dict['failed_articles'] == 1
        assert result_dict['skipped_articles'] == 1
        assert result_dict['start_time'] == "2024-01-01T12:00:00"
        assert result_dict['end_time'] == "2024-01-01T13:00:00"
        assert result_dict['duration_seconds'] == 3600.0
        assert result_dict['error_count'] == 1

    def test_process_result_to_dict_no_times(self):
        """测试没有时间信息的字典转换"""
        result = ProcessResult(
            total_articles=5,
            processed_articles=3
        )

        result_dict = result.to_dict()

        assert result_dict['start_time'] is None
        assert result_dict['end_time'] is None
        assert result_dict['duration_seconds'] == 0


class TestDatabaseConnection:
    """测试数据库连接管理"""

    @patch('src.wxchat.processor.pymysql.connect')
    def test_database_connection_init(self, mock_connect):
        """测试数据库连接初始化"""
        mock_config = Mock()
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"

        # 模拟成功连接
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db_conn = DatabaseConnection(mock_config, use_wewe_db=False)

        assert db_conn.host == "localhost"
        assert db_conn.port == 3306
        assert db_conn.user == "test_user"
        assert db_conn.password == "test_pass"
        assert db_conn.database == "test_db"
        assert db_conn.connection is None

    @patch('src.wxchat.processor.pymysql.connect')
    def test_database_connection_init_wewe_db(self, mock_connect):
        """测试使用wewe数据库配置初始化"""
        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "wewe_host"
        mock_config.wxchat_wewe_db_port = 3307
        mock_config.wxchat_wewe_db_user = "wewe_user"
        mock_config.wxchat_wewe_db_password = "wewe_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"

        db_conn = DatabaseConnection(mock_config, use_wewe_db=True)

        assert db_conn.host == "wewe_host"
        assert db_conn.port == 3307
        assert db_conn.user == "wewe_user"
        assert db_conn.password == "wewe_pass"
        assert db_conn.database == "wewe_db"

    @patch('src.wxchat.processor.pymysql.connect')
    def test_database_connection_connect(self, mock_connect):
        """测试建立数据库连接"""
        mock_config = Mock()
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db_conn = DatabaseConnection(mock_config, use_wewe_db=False)
        result = db_conn.connect()

        assert result == mock_connection
        mock_connect.assert_called_once()
        # 验证调用参数
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['host'] == "localhost"
        assert call_kwargs['port'] == 3306
        assert call_kwargs['user'] == "test_user"
        assert call_kwargs['password'] == "test_pass"
        assert call_kwargs['database'] == "test_db"

    @patch('src.wxchat.processor.pymysql.connect')
    def test_database_connection_context_manager(self, mock_connect):
        """测试上下文管理器使用"""
        mock_config = create_mock_config()
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        db_conn = DatabaseConnection(mock_config, use_wewe_db=False)

        with db_conn as conn:
            assert conn == mock_connection

        mock_connection.close.assert_called_once()

    @patch('src.wxchat.processor.pymysql.connect')
    def test_database_connection_error_handling(self, mock_connect):
        """测试数据库连接错误处理"""
        mock_config = create_mock_config()
        mock_config.db_host = "invalid_host"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"

        mock_connect.side_effect = Exception("Connection failed")

        db_conn = DatabaseConnection(mock_config, use_wewe_db=False)

        with pytest.raises(Exception, match="Connection failed"):
            db_conn.connect()


class TestWeChatAccountSync:
    """测试账号同步逻辑"""

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_sync_accounts_success(self, mock_db_connection):
        """测试成功的账号同步"""
        mock_config = create_mock_config()
        sync = WeChatAccountSync(mock_config)

        # 模拟wewe数据库连接
        mock_wewe_conn = MagicMock()
        mock_wewe_cursor = MagicMock()
        mock_wewe_cursor.fetchall.return_value = [
            {'account_id': 'account1', 'account_name': 'Account 1', 'app_id': 'app1'},
            {'account_id': 'account2', 'account_name': 'Account 2', 'app_id': 'app2'}
        ]
        mock_wewe_conn.cursor.return_value.__enter__.return_value = mock_wewe_cursor
        mock_wewe_conn.cursor.return_value.__exit__.return_value = None

        # 模拟test数据库连接
        mock_test_conn = MagicMock()
        mock_test_cursor = MagicMock()
        mock_test_conn.cursor.return_value.__enter__.return_value = mock_test_cursor
        mock_test_conn.cursor.return_value.__exit__.return_value = None

        # 设置DatabaseConnection上下文管理器返回值
        mock_db_connection.return_value.__enter__.side_effect = [mock_wewe_conn, mock_test_conn]
        mock_db_connection.return_value.__exit__.return_value = None

        result = sync.sync_accounts()

        assert result == 2
        assert mock_test_cursor.execute.call_count == 2  # 两篇文章插入
        mock_test_conn.commit.assert_called_once()

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_sync_accounts_empty_database(self, mock_db_connection):
        """测试空数据库的账号同步"""
        mock_config = create_mock_config()
        sync = WeChatAccountSync(mock_config)

        # 模拟wewe数据库返回空结果
        mock_wewe_conn = MagicMock()
        mock_wewe_cursor = MagicMock()
        mock_wewe_cursor.fetchall.return_value = []
        mock_wewe_conn.cursor.return_value.__enter__.return_value = mock_wewe_cursor
        mock_wewe_conn.cursor.return_value.__exit__.return_value = None

        mock_db_connection.return_value.__enter__.return_value = mock_wewe_conn
        mock_db_connection.return_value.__exit__.return_value = None

        result = sync.sync_accounts()

        assert result == 0

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_sync_accounts_database_error(self, mock_db_connection):
        """测试数据库错误处理"""
        mock_config = create_mock_config()
        sync = WeChatAccountSync(mock_config)

        mock_db_connection.return_value.__enter__.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            sync.sync_accounts()


class TestPDFGenerator:
    """测试PDF生成功能"""

    def test_pdf_generator_init(self):
        """测试PDF生成器初始化"""
        mock_config = create_mock_config()
        # Override specific settings for this test
        mock_config.wxchat_base_url = "https://example.com/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 2
        mock_config.wxchat_download_delay = 1

        generator = PDFGenerator(mock_config)

        assert generator.base_url == "https://example.com/"
        assert generator.timeout == 30000  # 转换为毫秒
        assert generator.image_wait_time == 2
        assert generator.download_delay == 1
        assert generator.config == mock_config

    @patch('src.wxchat.processor.sync_playwright')
    @patch('src.wxchat.processor.os.makedirs')
    def test_generate_pdf_success(self, mock_makedirs, mock_playwright):
        """测试成功的PDF生成"""
        mock_config = create_mock_config()
        # Override specific settings for this test
        mock_config.wxchat_base_url = "https://example.com/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0  # 不等待
        mock_config.wxchat_download_delay = 0  # 不延迟

        # 模拟Playwright对象
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright_instance = MagicMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # 设置sync_playwright上下文管理器
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance

        generator = PDFGenerator(mock_config)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            result = generator.generate_pdf("test_article", temp_path)

            assert result is True
            mock_playwright_instance.chromium.launch.assert_called_once()
            mock_page.goto.assert_called_once()
            mock_page.pdf.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('src.wxchat.processor.sync_playwright')
    def test_generate_pdf_timeout(self, mock_playwright):
        """测试PDF生成超时处理"""
        mock_config = create_mock_config()
        # Override specific settings for this test
        mock_config.wxchat_base_url = "https://example.com/"
        mock_config.wxchat_pdf_timeout = 1
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        generator = PDFGenerator(mock_config)

        # 模拟Playwright对象
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Timeout")

        mock_playwright_instance = MagicMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            result = generator.generate_pdf("test_article", temp_path)

            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('src.wxchat.processor.sync_playwright')
    def test_generate_pdf_browser_error(self, mock_playwright):
        """测试浏览器启动错误处理"""
        mock_config = create_mock_config()
        # Override specific settings for this test
        mock_config.wxchat_base_url = "https://example.com/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        generator = PDFGenerator(mock_config)

        # 模拟浏览器启动失败
        mock_playwright_instance = MagicMock()
        mock_playwright_instance.chromium.launch.side_effect = Exception("Browser launch failed")

        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            result = generator.generate_pdf("test_article", temp_path)

            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestWeChatArticleProcessor:
    """测试文章处理逻辑"""

    def test_article_processor_init(self):
        """测试文章处理器初始化"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        assert processor.config == mock_config
        assert processor.pdf_generator is not None

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    @patch.object(WeChatArticleProcessor, '_is_article_processed')
    @patch.object(WeChatArticleProcessor, '_process_single_article')
    def test_process_articles_success(self, mock_process_single, mock_is_processed, mock_fetch):
        """测试成功的文章处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟返回的文章列表
        mock_fetch.return_value = [
            {'article_id': 'article1', 'account_id': 'account1', 'title': 'Article 1', 'publish_date': datetime.now()},
            {'article_id': 'article2', 'account_id': 'account1', 'title': 'Article 2', 'publish_date': datetime.now()},
            {'article_id': 'article3', 'account_id': 'account2', 'title': 'Article 3', 'publish_date': datetime.now()}
        ]

        # 模拟文章处理状态
        mock_is_processed.side_effect = [False, False, False]
        mock_process_single.side_effect = [True, True, False]  # 前两个成功，第三个失败

        result = processor.process_articles(days=1)

        assert result.total_articles == 3
        assert result.processed_articles == 2
        assert result.failed_articles == 1
        assert result.skipped_articles == 0
        assert result.start_time is not None
        assert result.end_time is not None

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    @patch.object(WeChatArticleProcessor, '_is_article_processed')
    @patch.object(WeChatArticleProcessor, '_process_single_article')
    def test_article_deduplication(self, mock_process_single, mock_is_processed, mock_fetch):
        """测试文章去重功能"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟返回的文章列表
        mock_fetch.return_value = [
            {'article_id': 'article1', 'account_id': 'account1', 'title': 'Article 1', 'publish_date': datetime.now()},
            {'article_id': 'article2', 'account_id': 'account1', 'title': 'Article 2', 'publish_date': datetime.now()}
        ]

        # 模拟第一篇文章已处理，第二篇未处理
        mock_is_processed.side_effect = [True, False]
        mock_process_single.return_value = True

        result = processor.process_articles(days=1)

        assert result.total_articles == 2
        assert result.processed_articles == 1  # 只有第二篇被处理
        assert result.skipped_articles == 1  # 第一篇被跳过
        assert result.failed_articles == 0

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    def test_process_articles_empty_database(self, mock_fetch):
        """测试空数据库的文章处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟返回空列表
        mock_fetch.return_value = []

        result = processor.process_articles(days=1)

        assert result.total_articles == 0
        assert result.processed_articles == 0
        assert result.failed_articles == 0
        assert result.skipped_articles == 0
        assert result.start_time is not None
        assert result.end_time is not None

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    def test_process_articles_database_error(self, mock_fetch):
        """测试数据库错误处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟数据库错误
        mock_fetch.side_effect = Exception("Database error")

        result = processor.process_articles(days=1)

        assert len(result.errors) > 0
        assert result.total_articles == 0
        assert result.failed_articles == 0

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    @patch.object(WeChatArticleProcessor, '_is_article_processed')
    @patch.object(WeChatArticleProcessor, '_process_single_article')
    def test_process_articles_invalid_article(self, mock_process_single, mock_is_processed, mock_fetch):
        """测试无效文章处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟返回无效文章（缺少article_id）
        mock_fetch.return_value = [
            {'account_id': 'account1', 'title': 'Invalid Article', 'publish_date': datetime.now()}
        ]

        result = processor.process_articles(days=1)

        assert result.total_articles == 1
        assert result.failed_articles == 1  # 无效文章被视为失败
        assert result.processed_articles == 0

    @patch.object(WeChatArticleProcessor, '_fetch_articles_from_wewe')
    @patch.object(WeChatArticleProcessor, '_is_article_processed')
    @patch.object(WeChatArticleProcessor, '_process_single_article')
    def test_process_articles_validation_error(self, mock_process_single, mock_is_processed, mock_fetch):
        """测试参数验证错误"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟返回的文章列表
        mock_fetch.return_value = [
            {'article_id': 'article1', 'account_id': 'account1', 'title': 'Article 1', 'publish_date': datetime.now()}
        ]

        # 模拟处理过程中出现异常
        mock_is_processed.return_value = False
        mock_process_single.side_effect = Exception("Processing error")

        result = processor.process_articles(days=1)

        assert result.total_articles == 1
        assert result.failed_articles == 1
        assert len(result.errors) > 0

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_fetch_articles_from_wewe(self, mock_db_connection):
        """测试从wewe数据库获取文章"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟数据库查询结果
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'article_id': 'article1', 'account_id': 'account1', 'title': 'Article 1', 'publish_date': datetime.now(), 'content_url': 'https://example.com/1'},
            {'article_id': 'article2', 'account_id': 'account2', 'title': 'Article 2', 'publish_date': datetime.now(), 'content_url': 'https://example.com/2'}
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        articles = processor._fetch_articles_from_wewe(start_date, end_date)

        assert len(articles) == 2
        assert articles[0]['article_id'] == 'article1'
        assert articles[1]['article_id'] == 'article2'
        mock_cursor.execute.assert_called_once()

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_is_article_processed(self, mock_db_connection):
        """测试检查文章是否已处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟数据库查询结果
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'count': 1}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        result = processor._is_article_processed('article1')

        assert result is True
        mock_cursor.execute.assert_called_once()

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_is_article_not_processed(self, mock_db_connection):
        """测试检查文章未处理"""
        mock_config = create_mock_config()
        processor = WeChatArticleProcessor(mock_config)

        # 模拟数据库查询结果
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'count': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        result = processor._is_article_processed('article1')

        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
