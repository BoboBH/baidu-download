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

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    # Playwright not installed, will be handled in PDFGenerator
    sync_playwright = None

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
            # 连接wewe_rss数据库获取公众号信息
            with DatabaseConnection(self.config, use_wewe_db=True) as wewe_conn:
                with wewe_conn.cursor() as wewe_cursor:
                    # 从weme_rss的feeds表获取公众号信息
                    wewe_cursor.execute("""
                        SELECT DISTINCT
                            id,
                            mp_name
                        FROM feeds
                        WHERE id IS NOT NULL AND status = 1
                        ORDER BY mp_name
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
                        account_id = account['id']
                        account_name = account['mp_name']

                        # 使用UPSERT语法（MySQL 8.0+）
                        test_cursor.execute("""
                            INSERT INTO new_wx_account (account_id, account_name, app_id)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                account_name = VALUES(account_name),
                                app_id = VALUES(app_id),
                                updated_at = CURRENT_TIMESTAMP
                        """, (account_id, account_name, ''))

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
        生成PDF文件 - 使用Playwright生成真正的PDF

        Args:
            article_id: 文章ID
            output_path: PDF输出路径

        Returns:
            是否生成成功
        """
        url = f"{self.base_url}{article_id}"
        logger.info(f"使用Playwright生成PDF: {url}")

        # 使用Playwright生成PDF
        if sync_playwright and self._generate_pdf_with_playwright(url, output_path):
            return True

        # Playwright失败，记录错误并返回False
        logger.error("Playwright PDF生成失败，无法生成PDF文件")
        return False

    def _generate_pdf_with_playwright(self, url: str, output_path: str) -> bool:
        """
        使用Playwright生成完美的PDF

        Args:
            url: 微信文章URL
            output_path: PDF输出路径

        Returns:
            是否生成成功
        """
        try:
            with sync_playwright() as p:
                # 启动Chromium浏览器
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as browser_error:
                    logger.error(f"Chromium浏览器启动失败: {browser_error}")
                    logger.error("请确保Playwright浏览器已安装: playwright install chromium")
                    return False

                page = browser.new_page()

                logger.info(f"访问微信文章页面: {url}")

                # 访问文章页面
                try:
                    page.goto(url, wait_until='networkidle', timeout=self.timeout)
                except Exception as goto_error:
                    logger.error(f"访问页面失败: {goto_error}")
                    browser.close()
                    return False

                # 改进的图片加载等待逻辑 - 简化可靠版本
                logger.info(f"等待页面内容和图片加载...")

                # 1. 先等待主要内容区域出现
                try:
                    page.wait_for_selector('div.rich_media_content', timeout=10000)
                    logger.info("主要内容区域已加载")
                except:
                    logger.warning("未找到主要内容区域选择器，继续等待...")

                # 2. 简单但可靠的滚动方法
                logger.info("开始滚动页面触发图片加载...")

                # 获取页面高度并分步滚动
                scroll_height = page.evaluate("document.documentElement.scrollHeight")
                viewport_height = page.evaluate("window.innerHeight")
                steps = max(5, (scroll_height // viewport_height) + 2)  # 至少5步

                for i in range(steps):
                    # 计算滚动位置
                    scroll_position = (scroll_height * i) // steps
                    page.evaluate(f"window.scrollTo(0, {scroll_position})")
                    logger.info(f"滚动进度: {i+1}/{steps} (位置: {scroll_position}px)")
                    page.wait_for_timeout(1000)  # 每步等待1秒

                # 滚动回顶部
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(2000)  # 回到顶部后等待2秒

                # 3. 等待网络空闲
                logger.info("等待网络请求完成...")
                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                    logger.info("网络已空闲")
                except:
                    logger.warning("网络未完全空闲，但继续处理...")

                # 4. 额外等待图片渲染
                logger.info(f"额外等待图片渲染 ({self.image_wait_time}秒)...")
                page.wait_for_timeout(self.image_wait_time * 1000)

                # 5. 检查图片加载状态
                try:
                    image_count = page.evaluate("""
                        () => {
                            const images = document.querySelectorAll('img');
                            let loadedCount = 0;
                            let errorCount = 0;

                            images.forEach(img => {
                                if (img.complete && img.naturalHeight !== 0) {
                                    loadedCount++;
                                } else if (img.naturalHeight === 0 && !img.complete) {
                                    errorCount++;
                                }
                            });

                            return {
                                total: images.length,
                                loaded: loadedCount,
                                error: errorCount
                            };
                        }
                    """)
                    logger.info(f"图片状态: 总数={image_count['total']}, 已加载={image_count['loaded']}, 失败={image_count['error']}")
                except Exception as e:
                    logger.warning(f"无法检查图片状态: {e}")

                # 生成真正的PDF
                try:
                    page.pdf(
                        path=output_path,
                        format='A4',
                        print_background=True,
                        margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
                    )
                except Exception as pdf_error:
                    logger.error(f"PDF生成失败: {pdf_error}")
                    browser.close()
                    return False

                browser.close()

                # 检查生成的文件
                import os
                file_size = os.path.getsize(output_path)
                logger.info(f"Playwright PDF生成成功，文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")

                return file_size > 10000  # 至少10KB才算成功

        except Exception as e:
            logger.error(f"Playwright执行失败: {e}")
            return False

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
                    article_id = article.get('id')
                    if not article_id:
                        logger.warning(f"文章缺少id: {article}")
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
                    # 查询wewe_rss数据库中的文章表
                    cursor.execute("""
                        SELECT
                            id,
                            mp_id,
                            title,
                            publish_time
                        FROM articles
                        WHERE FROM_UNIXTIME(publish_time) BETWEEN %s AND %s
                        ORDER BY publish_time DESC
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
        article_id = article.get('id')
        account_id = article.get('mp_id')
        title = article.get('title')
        publish_time = article.get('publish_time')
        publish_date = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M:%S') if publish_time else None

        logger.info(f"📄 开始处理文章: {title} ({article_id})")
        logger.info(f"   账号ID: {account_id}, 发布时间: {publish_date}")

        pdf_url = None
        error_message = None

        try:
            # 创建临时文件
            logger.info(f"   创建临时PDF文件...")
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                temp_pdf_path = tmp_file.name

            # 生成PDF
            logger.info(f"   开始生成PDF: {article_id}")
            if not self.pdf_generator.generate_pdf(article_id, temp_pdf_path):
                error_message = "PDF生成失败"
                logger.error(f"❌ PDF生成失败: {article_id}")
                self._update_article_status(article_id, account_id, title, publish_date, pdf_url, error_message)
                return False

            logger.info(f"✅ PDF生成完成: {temp_pdf_path}")

            # 上传到SFTP
            logger.info(f"   准备上传PDF到SFTP服务器...")
            try:
                with SFTPClient() as sftp:
                    # 生成YYYYMM格式的目录
                    publish_date_obj = datetime.strptime(publish_date, '%Y-%m-%d %H:%M:%S')
                    yymm = publish_date_obj.strftime('%Y%m')
                    logger.info(f"   目标目录: {yymm}")

                    # 获取账号名称用于文件命名
                    account_name = self._get_account_name(account_id)
                    logger.info(f"   账号名称: {account_name}")

                    # 生成文件名：公众号名称_文章标题.pdf
                    # 清理文件名中的非法字符
                    safe_account_name = self._sanitize_filename(account_name)
                    safe_title = self._sanitize_filename(title)
                    remote_filename = f"{safe_account_name}_{safe_title}.pdf"
                    logger.info(f"   文件名: {remote_filename}")

                    # 生成远程路径：wxchat_sftp_remote_path/YYYYMM/文件名.pdf
                    remote_dir = f"{self.config.wxchat_sftp_remote_path}/{yymm}"
                    remote_path = f"{remote_dir}/{remote_filename}"
                    logger.info(f"   远程路径: {remote_path}")

                    # 上传文件到主SFTP
                    logger.info(f"   开始上传到主SFTP服务器...")
                    main_sftp_success = sftp.upload_file(temp_pdf_path, remote_path)
                    if main_sftp_success:
                        # 生成PDF URL
                        pdf_url = f"{remote_dir}/{remote_filename}"
                        logger.info(f"✅ 主SFTP上传成功: {pdf_url}")

                        # 尝试上传到外部SFTP（如果配置了且不在排除列表中）
                        logger.info(f"   尝试上传到外部SFTP...")
                        external_sftp_success = self._upload_to_external_sftp(
                            temp_pdf_path, safe_account_name, safe_title,
                            yymm, account_name
                        )

                        # 检查两个SFTP上传是否都成功
                        if not external_sftp_success:
                            error_message = "外部SFTP上传失败"
                            logger.error(f"⚠️  外部SFTP上传失败: {article_id}")
                        else:
                            logger.info(f"✅ 外部SFTP上传成功")
                    else:
                        error_message = "主SFTP上传失败"
                        logger.error(f"❌ 主SFTP上传失败: {article_id}")

            except Exception as e:
                error_message = f"SFTP上传异常: {str(e)}"
                logger.error(f"❌ SFTP上传异常: {e}")

            # 清理临时文件
            logger.info(f"   清理临时文件...")
            try:
                os.unlink(temp_pdf_path)
                logger.info(f"✅ 临时文件已清理: {temp_pdf_path}")
            except Exception as e:
                logger.warning(f"⚠️  清理临时文件失败: {e}")

            # 更新处理状态
            logger.info(f"   更新处理状态到数据库...")
            self._update_article_status(article_id, account_id, title, publish_date, pdf_url, error_message)

            if error_message is None:
                logger.info(f"🎉 文章处理完成: {title} ({article_id})")
            else:
                logger.error(f"❌ 文章处理失败: {title} - {error_message}")

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
                        FROM new_wx_article
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
                        INSERT INTO new_wx_article (
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

    def _get_account_name(self, account_id: str) -> str:
        """
        获取账号名称

        Args:
            account_id: 账号ID

        Returns:
            账号名称，如果找不到则返回account_id
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT account_name FROM new_wx_account WHERE account_id = %s
                    """, (account_id,))
                    result = cursor.fetchone()
                    if result:
                        return result['account_name']
                    else:
                        logger.warning(f"未找到账号名称: {account_id}")
                        return account_id
        except Exception as e:
            logger.error(f"获取账号名称失败: {e}")
            return account_id

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符

        Args:
            filename: 原始文件名

        Returns:
            安全的文件名
        """
        import re
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和点
        filename = re.sub(r'\s+', '_', filename)
        filename = re.sub(r'\.+', '.', filename)
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename.strip('.')

    def _upload_to_external_sftp(self, local_pdf_path: str, safe_account_name: str,
                                 safe_title: str, yymm: str, original_account_name: str) -> bool:
        """
        上传PDF到外部SFTP服务器

        Args:
            local_pdf_path: 本地PDF文件路径
            safe_account_name: 安全的公众号名称（用于文件名）
            safe_title: 安全的文章标题（用于文件名）
            yymm: 年月格式（如：202407）
            original_account_name: 原始公众号名称（用于排除检查）

        Returns:
            是否上传成功（排除的公众号视为成功）
        """
        # 检查是否配置了外部SFTP
        if not self.config.wxchat_external_sftp_host:
            logger.debug("外部SFTP未配置，跳过外部上传")
            return True  # 未配置外部SFTP，不视为失败

        # 检查公众号是否在排除列表中
        if original_account_name in self.config.wxchat_external_exclude_accounts:
            logger.info(f"公众号 '{original_account_name}' 在排除列表中，跳过外部SFTP上传")
            return True  # 排除的公众号，不视为失败

        try:
            # 构建外部SFTP配置
            external_config = {
                'host': self.config.wxchat_external_sftp_host,
                'port': self.config.wxchat_external_sftp_port,
                'username': self.config.wxchat_external_sftp_username,
                'password': self.config.wxchat_external_sftp_password,
                'remote_path': self.config.wxchat_external_sftp_folder
            }

            # 生成外部SFTP的远程路径
            external_remote_dir = f"{self.config.wxchat_external_sftp_folder}/{yymm}"
            external_remote_path = f"{external_remote_dir}/{safe_account_name}_{safe_title}.pdf"

            # 上传到外部SFTP
            logger.info(f"开始上传到外部SFTP: {self.config.wxchat_external_sftp_host}")
            with SFTPClient(custom_config=external_config) as external_sftp:
                if external_sftp.upload_file(local_pdf_path, external_remote_path):
                    logger.info(f"外部SFTP上传成功: {external_remote_path}")
                    return True
                else:
                    logger.error(f"外部SFTP上传失败: {external_remote_path}")
                    return False

        except Exception as e:
            # 外部SFTP上传失败应该返回False
            logger.error(f"外部SFTP上传异常: {e}")
            return False
