"""
微信公众号文章处理核心逻辑

包含账号同步、文章处理、PDF生成等功能。
"""

import logging
from typing import Dict, List, Optional
import pymysql
import time
import os

from playwright.sync_api import sync_playwright

from src.config.settings import Settings
from src.wxchat.models import WeChatAccount, WeChatArticle, ProcessResult

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
