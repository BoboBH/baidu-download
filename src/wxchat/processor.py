"""
微信公众号文章处理核心逻辑

包含账号同步、文章处理、PDF生成等功能。
"""

import logging
from typing import Dict, List, Optional
import pymysql
import time
import os
from datetime import datetime, timedelta
import tempfile

from playwright.sync_api import sync_playwright

from src.config.settings import Settings
from src.wxchat.models import WeChatAccount, WeChatArticle, ProcessResult
from src.uploader.sftp_client import SFTPClient

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """数据库连接管理类"""

    def __init__(self, config: Settings, use_wewe_db: bool = False):
        """
        初始化数据库连接

        Args:
            config: 配置对象
            use_wewe_db: 是否使用wewe_rss数据库（False使用test数据库）
        """
        if use_wewe_db:
            self.host = config.wxchat_wewe_db_host
            self.port = config.wxchat_wewe_db_port
            self.user = config.wxchat_wewe_db_user
            self.password = config.wxchat_wewe_db_password
            self.database = config.wxchat_wewe_db_name
        else:
            self.host = config.db_host
            self.port = config.db_port
            self.user = config.db_user
            self.password = config.db_password
            self.database = config.db_name

        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"成功连接到数据库: {self.database}")
            return self.connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info(f"数据库连接已关闭: {self.database}")

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class WeChatAccountSync:
    """微信公众号账号同步器"""

    def __init__(self, config: Settings):
        """
        初始化账号同步器

        Args:
            config: 配置对象
        """
        self.config = config

    def sync_accounts(self) -> int:
        """
        同步账号信息

        Returns:
            同步的账号数量
        """
        logger.info("开始同步微信账号信息")

        try:
            # 连接wewe_rss数据库获取账号信息
            with DatabaseConnection(self.config, use_wewe_db=True) as wewe_conn:
                with wewe_conn.cursor() as wewe_cursor:
                    # 假设wewe_rss数据库中有account表
                    wewe_cursor.execute("""
                        SELECT DISTINCT
                            account_id,
                            account_name,
                            app_id
                        FROM account
                        WHERE account_id IS NOT NULL
                        ORDER BY account_name
                    """)
                    accounts = wewe_cursor.fetchall()

            if not accounts:
                logger.warning("未找到任何账号信息")
                return 0

            logger.info(f"从wewe_rss数据库获取到 {len(accounts)} 个账号")

            # 连接test数据库进行同步
            with DatabaseConnection(self.config, use_wewe_db=False) as test_conn:
                synced_count = 0

                with test_conn.cursor() as test_cursor:
                    for account in accounts:
                        account_id = account['account_id']
                        account_name = account['account_name']
                        app_id = account.get('app_id')

                        # 使用UPSERT语法（MySQL 8.0+）
                        test_cursor.execute("""
                            INSERT INTO wx_account (account_id, account_name, app_id)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                account_name = VALUES(account_name),
                                app_id = VALUES(app_id),
                                updated_at = CURRENT_TIMESTAMP
                        """, (account_id, account_name, app_id))

                        synced_count += 1

                test_conn.commit()

            logger.info(f"成功同步 {synced_count} 个账号信息")
            return synced_count

        except Exception as e:
            logger.error(f"账号同步失败: {e}")
            raise


class PDFGenerator:
    """PDF生成器，使用Playwright生成网页PDF"""

    def __init__(self, config: Settings):
        """
        初始化PDF生成器

        Args:
            config: 配置对象
        """
        self.config = config
        self.base_url = config.wxchat_base_url
        self.timeout = config.wxchat_pdf_timeout * 1000  # 转换为毫秒
        self.image_wait_time = config.wxchat_image_wait_time
        self.download_delay = config.wxchat_download_delay

    def generate_pdf(self, article_id: str, output_path: str) -> bool:
        """
        生成PDF文件

        Args:
            article_id: 文章ID
            output_path: PDF输出路径

        Returns:
            是否生成成功
        """
        url = f"{self.base_url}{article_id}"
        logger.info(f"开始生成PDF: {url}")

        browser = None
        try:
            with sync_playwright() as playwright:
                # 启动Chromium浏览器
                browser = playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )

                # 创建浏览器上下文
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                # 创建新页面
                page = context.new_page()

                # 设置额外的请求头
                page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })

                # 访问文章页面
                logger.info(f"访问文章页面: {url}")
                page.goto(url, timeout=self.timeout, wait_until='networkidle')

                # 等待图片加载完成
                logger.info(f"等待图片加载 ({self.image_wait_time}秒)...")
                time.sleep(self.image_wait_time)

                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # 生成PDF
                page.pdf(
                    path=output_path,
                    format='A4',
                    print_background=True,
                    margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
                )

                page.close()
                context.close()

                # 反限流延迟
                logger.info(f"延迟 {self.download_delay} 秒...")
                time.sleep(self.download_delay)

                logger.info(f"PDF生成成功: {output_path}")
                return True

        except Exception as e:
            logger.error(f"PDF生成失败: {e}")
            return False

        finally:
            if browser:
                browser.close()


class WeChatArticleProcessor:
    """微信公众号文章处理器"""

    def __init__(self, config: Settings):
        """
        初始化文章处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.pdf_generator = PDFGenerator(config)

    def process_articles(self, days: int = 3) -> ProcessResult:
        """
        处理微信公众号文章

        Args:
            days: 处理最近几天的文章，默认3天

        Returns:
            处理结果统计
        """
        logger.info(f"开始处理最近 {days} 天的微信文章")

        result = ProcessResult()
        result.start_time = datetime.now()

        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 从wewe_rss获取文章列表
            articles = self._fetch_articles_from_wewe(start_date, end_date)
            result.total_articles = len(articles)

            logger.info(f"获取到 {len(articles)} 篇文章")

            if not articles:
                logger.warning("没有找到需要处理的文章")
                result.end_time = datetime.now()
                return result

            # 处理每篇文章
            for article in articles:
                try:
                    article_id = article.get('article_id')
                    if not article_id:
                        logger.warning(f"文章缺少article_id: {article}")
                        result.failed_articles += 1
                        continue

                    # 检查是否已处理
                    if self._is_article_processed(article_id):
                        logger.info(f"文章已处理，跳过: {article_id}")
                        result.skipped_articles += 1
                        continue

                    # 处理单篇文章
                    if self._process_single_article(article):
                        result.processed_articles += 1
                    else:
                        result.failed_articles += 1

                except Exception as e:
                    logger.error(f"处理文章失败: {e}")
                    result.failed_articles += 1
                    result.errors.append(str(e))

            result.end_time = datetime.now()
            logger.info(f"文章处理完成: 总计={result.total_articles}, "
                       f"成功={result.processed_articles}, "
                       f"失败={result.failed_articles}, "
                       f"跳过={result.skipped_articles}")

        except Exception as e:
            logger.error(f"文章处理异常: {e}")
            result.errors.append(str(e))
            result.end_time = datetime.now()

        return result

    def _fetch_articles_from_wewe(self, start_date, end_date) -> List[Dict]:
        """
        从wewe_rss数据库获取文章列表

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            文章列表
        """
        articles = []

        try:
            with DatabaseConnection(self.config, use_wewe_db=True) as conn:
                with conn.cursor() as cursor:
                    # 假设wewe_rss数据库中有article表
                    cursor.execute("""
                        SELECT
                            article_id,
                            account_id,
                            title,
                            publish_date,
                            content_url
                        FROM article
                        WHERE publish_date BETWEEN %s AND %s
                        ORDER BY publish_date DESC
                    """, (start_date, end_date))

                    articles = cursor.fetchall()

            logger.info(f"从wewe_rss获取到 {len(articles)} 篇文章")
            return articles

        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")
            return []

    def _process_single_article(self, article: Dict) -> bool:
        """
        处理单篇文章：生成PDF并上传

        Args:
            article: 文章信息

        Returns:
            是否处理成功
        """
        article_id = article.get('article_id')
        account_id = article.get('account_id')
        title = article.get('title')
        publish_date = article.get('publish_date')

        logger.info(f"处理文章: {title} ({article_id})")

        pdf_url = None
        error_message = None

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                temp_pdf_path = tmp_file.name

            # 生成PDF
            if not self.pdf_generator.generate_pdf(article_id, temp_pdf_path):
                error_message = "PDF生成失败"
                logger.error(f"PDF生成失败: {article_id}")
                self._update_article_status(article_id, account_id, title, publish_date, pdf_url, error_message)
                return False

            # 上传到SFTP
            try:
                with SFTPClient() as sftp:
                    # 生成远程路径
                    remote_filename = f"{article_id}.pdf"
                    remote_path = f"{sftp.remote_path}/{remote_filename}"

                    # 上传文件
                    if sftp.upload_file(temp_pdf_path, remote_path):
                        # 生成PDF URL
                        pdf_url = f"{sftp.remote_path}/{remote_filename}"
                        logger.info(f"PDF上传成功: {pdf_url}")
                    else:
                        error_message = "SFTP上传失败"
                        logger.error(f"SFTP上传失败: {article_id}")

            except Exception as e:
                error_message = f"SFTP上传异常: {str(e)}"
                logger.error(f"SFTP上传异常: {e}")

            # 清理临时文件
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            # 更新处理状态
            self._update_article_status(article_id, account_id, title, publish_date, pdf_url, error_message)

            return error_message is None

        except Exception as e:
            error_message = f"处理异常: {str(e)}"
            logger.error(f"处理文章异常: {e}")
            self._update_article_status(article_id, account_id, title, publish_date, pdf_url, error_message)
            return False

    def _is_article_processed(self, article_id: str) -> bool:
        """
        检查文章是否已处理

        Args:
            article_id: 文章ID

        Returns:
            是否已处理
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM wx_article
                        WHERE article_id = %s
                        AND processed_at IS NOT NULL
                    """, (article_id,))

                    result = cursor.fetchone()
                    is_processed = result['count'] > 0

                    logger.debug(f"文章处理状态检查: {article_id} -> {is_processed}")
                    return is_processed

        except Exception as e:
            logger.error(f"检查文章处理状态失败: {e}")
            return False

    def _update_article_status(self, article_id, account_id, title, publish_date, pdf_url, error_message):
        """
        更新文章处理状态

        Args:
            article_id: 文章ID
            account_id: 账号ID
            title: 文章标题
            publish_date: 发布日期
            pdf_url: PDF URL
            error_message: 错误信息
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    # 使用UPSERT语法
                    cursor.execute("""
                        INSERT INTO wx_article (
                            article_id,
                            account_id,
                            title,
                            publish_date,
                            pdf_url,
                            error_message,
                            processed_at,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON DUPLICATE KEY UPDATE
                            account_id = VALUES(account_id),
                            title = VALUES(title),
                            publish_date = VALUES(publish_date),
                            pdf_url = VALUES(pdf_url),
                            error_message = VALUES(error_message),
                            processed_at = VALUES(processed_at),
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        article_id,
                        account_id,
                        title,
                        publish_date,
                        pdf_url,
                        error_message,
                        datetime.now() if error_message is None else None
                    ))

                conn.commit()
                logger.debug(f"文章状态已更新: {article_id}")

        except Exception as e:
            logger.error(f"更新文章状态失败: {e}")
