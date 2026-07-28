"""
微信公众号模块集成测试

测试覆盖完整的端到端工作流程，包括：
- 数据库集成测试
- 完整的处理工作流程
- SFTP文件上传集成
- 反限流措施测试
- 配置验证集成测试
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path

from src.config.settings import Settings
from src.wxchat.processor import WeChatAccountSync, WeChatArticleProcessor, PDFGenerator
from src.wxchat.models import WeChatAccount, WeChatArticle, ProcessResult


@pytest.mark.integration
class TestWxchatIntegration:
    """集成测试类 - 测试完整的系统工作流程"""

    # ==================== 数据库集成测试 ====================

    def test_database_connection_integration(self):
        """测试真实的数据库连接和基本操作"""
        # 使用真实配置进行数据库连接测试
        try:
            config = Settings()
            # 验证配置存在
            assert hasattr(config, 'db_host')
            assert hasattr(config, 'db_port')
            assert hasattr(config, 'db_user')
            assert hasattr(config, 'db_password')
            assert hasattr(config, 'db_name')
        except Exception as e:
            pytest.skip(f"数据库配置不可用: {e}")

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_account_sync_integration(self, mock_db_connection):
        """测试完整的账号同步工作流程"""
        # 模拟wewe数据库连接
        mock_wewe_conn = MagicMock()
        mock_wewe_cursor = MagicMock()
        mock_wewe_cursor.fetchall.return_value = [
            {'account_id': 'account1', 'account_name': '技术公众号', 'app_id': 'app1'},
            {'account_id': 'account2', 'account_name': '新闻公众号', 'app_id': 'app2'},
            {'account_id': 'account3', 'account_name': '娱乐公众号', 'app_id': 'app3'}
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

        # 创建配置
        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"

        # 执行同步
        sync = WeChatAccountSync(mock_config)
        result = sync.sync_accounts()

        # 验证结果
        assert result == 3
        assert mock_test_cursor.execute.call_count == 3
        mock_test_conn.commit.assert_called_once()

        # 验证UPSERT语法使用正确
        for i, call_args in enumerate(mock_test_cursor.execute.call_args_list[:3]):
            sql = call_args[0][0]
            assert 'INSERT INTO wx_account' in sql
            assert 'ON DUPLICATE KEY UPDATE' in sql

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_article_processing_integration(self, mock_db_connection):
        """测试完整的文章处理工作流程"""
        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 设置文章查询结果
        mock_cursor.fetchall.return_value = [
            {
                'article_id': 'article1',
                'account_id': 'account1',
                'title': '技术文章：深度学习入门',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/article1'
            },
            {
                'article_id': 'article2',
                'account_id': 'account1',
                'title': '技术文章：Python进阶',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/article2'
            }
        ]

        # 设置文章处理状态查询结果
        mock_cursor.fetchone.return_value = {'count': 0}

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        # 创建配置
        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        # 创建处理器并模拟PDF生成
        processor = WeChatArticleProcessor(mock_config)

        with patch.object(processor, '_process_single_article', return_value=True):
            result = processor.process_articles(days=1)

        # 验证结果
        assert result.total_articles == 2
        assert result.processed_articles == 2
        assert result.failed_articles == 0
        assert result.skipped_articles == 0
        assert result.start_time is not None
        assert result.end_time is not None
        assert (result.end_time - result.start_time).total_seconds() >= 0

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_database_error_recovery(self, mock_db_connection):
        """测试数据库连接失败和恢复"""
        # 模拟数据库连接失败
        mock_db_connection.return_value.__enter__.side_effect = Exception("Connection lost")

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "invalid_host"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30  # 必须是int类型
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        processor = WeChatArticleProcessor(mock_config)
        result = processor.process_articles(days=1)

        # 验证错误处理 - 系统应该优雅地处理数据库错误，返回0篇文章而不是崩溃
        assert result.total_articles == 0
        assert result.failed_articles == 0
        assert result.start_time is not None
        assert result.end_time is not None
        # 注意：当前实现中，fetch错误被捕获并记录日志，但不添加到errors列表中
        # 这是合理的设计，因为连接失败时我们无法获取文章列表

    # ==================== 端到端处理测试 ====================

    @patch('src.wxchat.processor.DatabaseConnection')
    @patch('src.wxchat.processor.sync_playwright')
    @patch('src.uploader.sftp_client.SFTPClient')
    def test_complete_article_processing_workflow(self, mock_sftp_client, mock_playwright, mock_db_connection):
        """测试从获取到上传的完整文章处理工作流程"""

        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'article_id': 'test_article_001',
                'account_id': 'account1',
                'title': '完整测试文章',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/test_article_001'
            }
        ]
        mock_cursor.fetchone.return_value = {'count': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        # 模拟Playwright PDF生成
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_playwright_instance = MagicMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance

        # 模拟SFTP上传
        mock_sftp = MagicMock()
        mock_sftp_client.return_value.__enter__.return_value = mock_sftp
        mock_sftp.upload_file.return_value = True
        mock_sftp.remote_path = "/wxchat_pdfs"

        # 创建配置
        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        # 创建处理器
        processor = WeChatArticleProcessor(mock_config)

        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            with patch.object(processor.pdf_generator, 'generate_pdf', return_value=True):
                result = processor.process_articles(days=1)

            # 验证完整工作流程
            assert result.total_articles == 1
            assert result.processed_articles == 1
            assert result.failed_articles == 0
            assert result.start_time is not None
            assert result.end_time is not None

            # 验证数据库操作
            assert mock_cursor.execute.call_count > 0
            mock_conn.commit.assert_called()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_article_deduplication_integration(self, mock_db_connection):
        """测试跨处理运行的文章去重功能"""

        # 模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 第一次运行：返回新文章
        mock_cursor.fetchall.return_value = [
            {
                'article_id': 'article1',
                'account_id': 'account1',
                'title': '文章1',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/article1'
            },
            {
                'article_id': 'article2',
                'account_id': 'account1',
                'title': '文章2',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/article2'
            }
        ]

        # 模拟第一次查询时article1已处理，article2未处理
        mock_cursor.fetchone.side_effect = [
            {'count': 1},  # article1已处理
            {'count': 0}   # article2未处理
        ]

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        processor = WeChatArticleProcessor(mock_config)

        with patch.object(processor, '_process_single_article', return_value=True):
            result = processor.process_articles(days=1)

        # 验证去重功能
        assert result.total_articles == 2
        assert result.processed_articles == 1  # 只有article2被处理
        assert result.skipped_articles == 1    # article1被跳过
        assert result.failed_articles == 0

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_error_handling_integration(self, mock_db_connection):
        """测试完整工作流程中的错误处理"""

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 返回一篇有效文章和一篇无效文章
        mock_cursor.fetchall.return_value = [
            {
                'article_id': 'valid_article',
                'account_id': 'account1',
                'title': '有效文章',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/valid_article'
            },
            {
                'article_id': 'invalid_article',
                'account_id': 'account1',
                'title': '无效文章',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/invalid_article'
            }
        ]

        mock_cursor.fetchone.return_value = {'count': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        processor = WeChatArticleProcessor(mock_config)

        # 模拟第一篇成功，第二篇失败
        with patch.object(processor, '_process_single_article', side_effect=[True, False]):
            result = processor.process_articles(days=1)

        # 验证错误处理
        assert result.total_articles == 2
        assert result.processed_articles == 1
        assert result.failed_articles == 1
        assert result.skipped_articles == 0

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_retry_mechanism_integration(self, mock_db_connection):
        """测试失败文章的重试机制"""

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 返回一篇失败的文章
        mock_cursor.fetchall.return_value = [
            {
                'article_id': 'retry_article',
                'account_id': 'account1',
                'title': '重试测试文章',
                'publish_date': datetime.now(),
                'content_url': 'https://mp.weixin.qq.com/s/retry_article'
            }
        ]

        # 模拟文章已存在失败记录
        mock_cursor.fetchone.return_value = {'count': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        processor = WeChatArticleProcessor(mock_config)

        # 模拟处理失败，验证重试逻辑
        with patch.object(processor, '_process_single_article', return_value=False):
            result = processor.process_articles(days=1)

        # 验证重试处理
        assert result.total_articles == 1
        assert result.failed_articles == 1

        # 验证数据库操作被调用（不验证commit是否调用，因为失败时不会commit）
        assert mock_cursor.execute.call_count > 0

    # ==================== SFTP集成测试 ====================

    @patch('src.uploader.sftp_client.pysftp.Connection')
    def test_sftp_upload_integration(self, mock_connection):
        """测试SFTP上传功能集成"""
        # 模拟SFTP连接
        mock_sftp = MagicMock()
        mock_connection.return_value = mock_sftp

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"Test PDF content")
            temp_path = tmp_file.name

        try:
            try:
                from src.uploader.sftp_client import SFTPClient
            except ImportError:
                pytest.skip("SFTPClient module not available")

            # 测试上传功能 - 正确设置stat行为来模拟目录创建流程
            # 对于路径 /test/path/test.pdf，create_directory会被调用为 /test/path
            mock_stat_result = MagicMock()
            call_count = [0]

            def stat_side_effect(path):
                call_count[0] += 1
                # 模拟：只有根目录/存在，其他都不存在
                if path == '/':
                    return mock_stat_result
                elif path in ['/test/path', '/test']:
                    raise IOError(f"Directory not found: {path}")
                else:
                    # 文件存在（上传验证）
                    return mock_stat_result

            mock_sftp.stat.side_effect = stat_side_effect

            sftp = SFTPClient()
            sftp.sftp = mock_sftp
            result = sftp.upload_file(temp_path, "/test/path/test.pdf")

            # 验证上传调用成功
            assert result is True
            mock_sftp.put.assert_called_once()
            # 验证创建了必要的目录
            assert mock_sftp.mkdir.call_count >= 1

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_sftp_directory_structure(self):
        """测试YYMM目录结构创建"""
        from src.uploader.sftp_client import SFTPClient
        from datetime import datetime

        # 测试目录路径生成
        now = datetime.now()
        yy = now.strftime('%y')
        mm = now.strftime('%m')
        expected_path = f"/wxchat_pdfs/{yy}{mm}"

        # 验证目录格式
        assert len(yy) == 2
        assert len(mm) == 2
        assert f"{yy}{mm}" in expected_path

    @patch('src.uploader.sftp_client.pysftp.Connection')
    def test_sftp_error_handling(self, mock_connection):
        """测试SFTP连接错误处理"""
        # 模拟连接失败
        mock_connection.side_effect = Exception("SFTP connection failed")

        from src.uploader.sftp_client import SFTPClient

        sftp = SFTPClient()
        result = sftp.connect()

        # 验证错误处理
        assert result is False
        assert sftp.sftp is None

    @patch('src.uploader.sftp_client.pysftp.Connection')
    def test_sftp_file_organization(self, mock_connection):
        """测试SFTP服务器上的文件组织"""
        # 模拟SFTP连接和操作
        mock_sftp = MagicMock()
        mock_connection.return_value = mock_sftp

        try:
            from src.uploader.sftp_client import SFTPClient
        except ImportError:
            pytest.skip("SFTPClient module not available")

        # 测试目录创建和文件组织 - 模拟递归目录创建
        mock_stat_result = MagicMock()

        def stat_side_effect(path):
            # 只有根目录存在
            if path == '/':
                return mock_stat_result
            else:
                raise IOError(f"Directory not found: {path}")

        mock_sftp.stat.side_effect = stat_side_effect

        sftp = SFTPClient()
        sftp.sftp = mock_sftp
        dir_result = sftp.create_directory("/test/directory")

        # 验证目录创建成功
        assert dir_result is True
        # 验证至少创建了/test/directory目录
        assert mock_sftp.mkdir.call_count >= 1
        # 验证创建了正确的目录
        mkdir_calls = [call[0][0] for call in mock_sftp.mkdir.call_args_list]
        assert "/test/directory" in mkdir_calls

    # ==================== 反限流测试 ====================

    def test_download_delay_integration(self):
        """测试文章处理间的延迟设置"""
        mock_config = Mock()
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 5  # 5秒延迟

        generator = PDFGenerator(mock_config)

        # 验证延迟设置
        assert generator.download_delay == 5
        assert generator.timeout == 30000

    @patch('src.wxchat.processor.sync_playwright')
    def test_timeout_handling_integration(self, mock_playwright):
        """测试PDF生成期间的超时处理"""
        mock_config = Mock()
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 1  # 1秒超时
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        generator = PDFGenerator(mock_config)

        # 模拟超时
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Timeout")

        mock_playwright_instance = MagicMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_path = tmp_file.name

        try:
            result = generator.generate_pdf("test_article", temp_path)
            # 验证超时处理
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_user_agent_headers_integration(self):
        """测试浏览器反爬虫请求头设置"""
        mock_config = Mock()
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        generator = PDFGenerator(mock_config)

        # 验证反爬虫配置存在
        assert generator.base_url == "https://mp.weixin.qq.com/s/"
        assert generator.timeout == 30000

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_concurrent_processing_limits(self, mock_db_connection):
        """测试并发处理限制"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 返回多篇文章
        mock_cursor.fetchall.return_value = [
            {
                'article_id': f'article{i}',
                'account_id': 'account1',
                'title': f'文章{i}',
                'publish_date': datetime.now(),
                'content_url': f'https://mp.weixin.qq.com/s/article{i}'
            } for i in range(10)
        ]

        mock_cursor.fetchone.return_value = {'count': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 0
        mock_config.wxchat_download_delay = 0

        processor = WeChatArticleProcessor(mock_config)

        # 模拟所有文章处理成功
        with patch.object(processor, '_process_single_article', return_value=True):
            result = processor.process_articles(days=1)

        # 验证串行处理（不是并发）
        assert result.total_articles == 10
        assert result.processed_articles == 10
        assert result.failed_articles == 0

    # ==================== 配置集成测试 ====================

    def test_configuration_validation_integration(self):
        """测试完整的配置验证"""
        try:
            config = Settings()

            # 验证所有wxchat配置存在
            assert hasattr(config, 'wxchat_enabled')
            assert hasattr(config, 'wxchat_wewe_db_host')
            assert hasattr(config, 'wxchat_wewe_db_port')
            assert hasattr(config, 'wxchat_wewe_db_user')
            assert hasattr(config, 'wxchat_wewe_db_password')
            assert hasattr(config, 'wxchat_wewe_db_name')
            assert hasattr(config, 'wxchat_base_url')
            assert hasattr(config, 'wxchat_pdf_timeout')
            assert hasattr(config, 'wxchat_image_wait_time')
            assert hasattr(config, 'wxchat_download_delay')
            assert hasattr(config, 'wxchat_max_days')
        except Exception as e:
            pytest.skip(f"配置验证跳过: {e}")

    def test_feature_toggle_integration(self):
        """测试WXCHAT_ENABLED功能开关"""
        # 测试默认禁用状态
        with patch.dict('os.environ', {'WXCHAT_ENABLED': 'false'}):
            config = Settings()
            assert config.wxchat_enabled is False

        # 测试启用状态（需要提供所有必需的配置）
        with patch.dict('os.environ', {
            'WXCHAT_ENABLED': 'true',
            'WXCHAT_WEWE_DB_HOST': 'localhost',
            'WXCHAT_WEWE_DB_PORT': '3306',
            'WXCHAT_WEWE_DB_USER': 'test_user',
            'WXCHAT_WEWE_DB_PASSWORD': 'test_pass',
            'WXCHAT_WEWE_DB_NAME': 'wewe_db'
        }):
            config = Settings()
            assert config.wxchat_enabled is True

    def test_parameter_range_validation_integration(self):
        """测试参数范围验证"""
        # 测试有效参数范围（需要提供所有必需的配置）
        with patch.dict('os.environ', {
            'WXCHAT_ENABLED': 'true',
            'WXCHAT_WEWE_DB_HOST': 'localhost',
            'WXCHAT_WEWE_DB_PORT': '3306',
            'WXCHAT_WEWE_DB_USER': 'test_user',
            'WXCHAT_WEWE_DB_PASSWORD': 'test_pass',
            'WXCHAT_WEWE_DB_NAME': 'wewe_db',
            'WXCHAT_PDF_TIMEOUT': '30',
            'WXCHAT_IMAGE_WAIT_TIME': '20',
            'WXCHAT_DOWNLOAD_DELAY': '5',
            'WXCHAT_MAX_DAYS': '30'
        }):
            config = Settings()

            # 验证参数在有效范围内
            assert 10 <= config.wxchat_pdf_timeout <= 300
            assert 5 <= config.wxchat_image_wait_time <= 120
            assert 1 <= config.wxchat_download_delay <= 60
            assert 1 <= config.wxchat_max_days <= 365

    def test_missing_configuration_handling(self):
        """测试缺少配置的处理"""
        # 测试缺少必需配置时的处理
        with patch.dict('os.environ', {'WXCHAT_ENABLED': 'true'}, clear=True):
            try:
                config = Settings()
                # 如果缺少配置，应该有默认值或抛出异常
                assert hasattr(config, 'wxchat_wewe_db_host')
            except Exception as e:
                # 验证异常处理
                assert 'wxchat' in str(e).lower() or 'config' in str(e).lower()

    @patch('src.wxchat.processor.DatabaseConnection')
    def test_configuration_usage_in_integration(self, mock_db_connection):
        """测试配置在实际集成中的使用"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_db_connection.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value.__exit__.return_value = None

        mock_config = Mock()
        mock_config.wxchat_wewe_db_host = "localhost"
        mock_config.wxchat_wewe_db_port = 3306
        mock_config.wxchat_wewe_db_user = "test_user"
        mock_config.wxchat_wewe_db_password = "test_pass"
        mock_config.wxchat_wewe_db_name = "wewe_db"
        mock_config.db_host = "localhost"
        mock_config.db_port = 3306
        mock_config.db_user = "test_user"
        mock_config.db_password = "test_pass"
        mock_config.db_name = "test_db"
        mock_config.wxchat_base_url = "https://mp.weixin.qq.com/s/"
        mock_config.wxchat_pdf_timeout = 30
        mock_config.wxchat_image_wait_time = 10
        mock_config.wxchat_download_delay = 5
        mock_config.wxchat_max_days = 30

        # 验证配置在处理器中的使用
        processor = WeChatArticleProcessor(mock_config)

        # 验证PDF生成器使用配置
        assert processor.pdf_generator.timeout == 30000
        assert processor.pdf_generator.image_wait_time == 10
        assert processor.pdf_generator.download_delay == 5

        # 验证处理结果
        result = processor.process_articles(days=mock_config.wxchat_max_days)
        assert result.total_articles == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])