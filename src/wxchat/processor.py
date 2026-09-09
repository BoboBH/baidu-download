"""
微信公众号文章处理核心逻辑

包含账号同步、文章处理、PDF生成等功能。
"""

from typing import Dict, List, Optional
import pymysql
import random
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
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ===== 假PDF检测与失败记账配置 =====
# 低于该大小的PDF视为微信拦截页（"环境异常"验证页）打印出的假PDF
MIN_VALID_PDF_SIZE = 100 * 1024
# 连续假PDF阈值：达到即判定已被微信风控，中止本次运行（避免继续撞墙）
FAKE_PDF_CIRCUIT_BREAKER = 5
# 失败退避基数：失败N次的文章需等 N * 该分钟数 后才会被再次扫描
RETRY_BACKOFF_MINUTES = 20


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
        # 早期拦截页检测结果：True表示本次访问被微信"环境异常"验证页拦截
        self.last_page_blocked = False
        # 批次级复用的浏览器会话（惰性启动）
        self._pw = None
        self._context = None

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
        return self.generate_pdf_from_url(url, output_path)

    def generate_pdf_from_url(self, url: str, output_path: str) -> bool:
        """
        从完整URL生成PDF文件 - 使用Playwright生成真正的PDF

        Args:
            url: 文章完整URL
            output_path: PDF输出路径

        Returns:
            是否生成成功
        """
        logger.info(f"使用Playwright生成PDF: {url}")

        # 使用Playwright生成PDF
        if sync_playwright and self._generate_pdf_with_playwright(url, output_path):
            return True

        # Playwright失败，记录错误并返回False
        logger.error("Playwright PDF生成失败，无法生成PDF文件")
        return False

    # 拟真Chrome的User-Agent（微信反爬会识别HeadlessChrome标记）
    _STEALTH_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    def _launch_stealth_browser(self, p, executable_path: Optional[str] = None, headful: bool = False):
        """以拟真+持久化档案配置启动浏览器。

        实测（2026-09-05）：微信反爬按"IP+无cookie新访客"返回"环境异常"验证页，
        与无头/自动化指纹无关（隐藏webdriver、真实Chrome有头均仍被拦），
        因此使用持久化用户档案：首次人工完成验证后cookie复用，后续免验证。
        优先系统Chrome（channel='chrome'），未安装时回落Playwright自带Chromium。

        Returns:
            BrowserContext（与Browser同样支持 new_page()/close()）
        """
        profile_dir = os.path.abspath(self.config.wxchat_browser_profile)
        os.makedirs(profile_dir, exist_ok=True)

        common_kwargs = dict(
            headless=not headful,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1440, "height": 900},
            # 注意：持久化 context 的 UA 只能在启动时指定（context.new_page() 不接受该参数）
            user_agent=self._STEALTH_USER_AGENT,
        )
        attempt_kwargs = dict(common_kwargs)
        if executable_path:
            attempt_kwargs["executable_path"] = executable_path
        else:
            attempt_kwargs["channel"] = "chrome"
        try:
            context = p.chromium.launch_persistent_context(profile_dir, **attempt_kwargs)
        except Exception as e:
            if executable_path:
                raise
            attempt_kwargs.pop("channel", None)
            logger.warning(f"系统Chrome不可用（{e}），回落到Playwright自带Chromium")
            context = p.chromium.launch_persistent_context(profile_dir, **attempt_kwargs)

        logger.info(f"浏览器已启动（{'有头' if headful else '无头'}, "
                    f"{'指定路径' if executable_path else attempt_kwargs.get('channel') or 'Playwright Chromium'}, "
                    f"档案: {profile_dir}）")
        return context

    def _get_context(self):
        """惰性启动并复用浏览器会话（整个批次共用一个浏览器实例）。

        实测（2026-09-05）：每篇文章都新开浏览器进程，短时间内大量"新会话"
        是微信风控的自动化特征（会连续被拦"环境异常"）；单会话内连续翻页
        则全程放行。因此批次只启动一次浏览器，文章间仅新开/关闭页面。
        """
        if self._context is not None:
            return self._context

        self._pw = sync_playwright().start()
        try:
            import sys
            is_frozen = getattr(sys, 'frozen', False)
            executable_path = None
            if is_frozen:
                # 在PyInstaller打包环境中，动态检测系统浏览器路径
                user_profile = os.environ.get('USERPROFILE', 'C:\\Users\\Default')
                possible_paths = [
                    # 当前用户的Playwright浏览器
                    os.path.join(user_profile, 'AppData', 'Local', 'ms-playwright', 'chromium-1140', 'chrome-win', 'chrome.exe'),
                    # 默认用户路径
                    r"C:\Users\Default\AppData\Local\ms-playwright\chromium-1140\chrome-win\chrome.exe",
                    # 系统程序路径中的Chrome（如果安装了）
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        executable_path = path
                        logger.info(f"Found system browser: {executable_path}")
                        break

            self._context = self._launch_stealth_browser(self._pw, executable_path=executable_path)
            return self._context
        except Exception as browser_error:
            self._pw.stop()
            self._pw = None
            logger.error(f"Chromium浏览器启动失败: {browser_error}")
            logger.error("请确保已安装系统Chrome，或执行 playwright install chromium")
            raise

    def close_browser(self):
        """关闭复用的浏览器会话（批次/进程结束时调用）"""
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None

    def _generate_pdf_with_playwright(self, url: str, output_path: str) -> bool:
        """
        使用Playwright生成完美的PDF（复用批次级浏览器会话，每篇文章新开页面）

        Args:
            url: 微信文章URL
            output_path: PDF输出路径

        Returns:
            是否生成成功
        """
        page = None
        try:
            context = self._get_context()
            page = context.new_page()
            # 隐藏 navigator.webdriver 自动化标记（微信反爬检测点之一）
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info(f"访问微信文章页面: {url}")

            # 访问文章页面
            try:
                page.goto(url, wait_until='networkidle', timeout=self.timeout)
            except Exception as goto_error:
                logger.error(f"访问页面失败: {goto_error}")
                return False

            # 早期拦截页检测：命中"环境异常"验证页直接失败，
            # 省掉图片等待与打印（约40秒/次），并记录页面标题供排查
            self.last_page_blocked = False
            try:
                early_body = page.evaluate("document.body ? document.body.innerText.slice(0, 300) : ''")
                if '环境异常' in early_body or '完成验证' in early_body:
                    self.last_page_blocked = True
                    logger.warning(f"页面为微信验证页（早期检测）: {page.title()} | {early_body[:60]!r}")
                    return False
            except Exception:
                pass  # 检测本身失败不阻断正常流程

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
                return False


            # 检查生成的文件
            file_size = os.path.getsize(output_path)
            logger.info(f"Playwright PDF生成成功，文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")

            return file_size > 10000  # 至少10KB才算成功

        except Exception as e:
            logger.error(f"Playwright执行失败: {e}")
            return False
        finally:
            # 只关页面不关浏览器：浏览器会话批次内复用（防风控关键）
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass


class WeChatArticleProcessor:
    """微信公众号文章处理器"""

    def __init__(self, config: Settings, source: str = "wewe"):
        """
        初始化文章处理器

        Args:
            config: 配置对象
            source: 数据源，"wewe"=wewe_rss库（默认，--wxchat），
                    "crawler"=主库wechat_crawler_articles表（--crawler-wxchat）

        Raises:
            ValueError: source 不是支持的取值
        """
        if source not in ("wewe", "crawler"):
            raise ValueError(f"不支持的数据源: {source}，仅支持 'wewe' 或 'crawler'")
        self.config = config
        self.source = source
        self.pdf_generator = PDFGenerator(config)
        # 最近一次 _process_single_article 是否因微信拦截页假PDF而失败（供风控熔断统计）
        self.last_pdf_blocked = False

    def process_articles(self, days: Optional[int] = None) -> ProcessResult:
        """
        处理微信公众号文章

        Args:
            days: 处理最近几天的文章。wewe源默认3天（None时回落3）；
                  crawler源None表示处理所有未成功处理过的文章（不限时间窗），
                  提供时按publish_date过滤最近N天

        Returns:
            处理结果统计
        """
        if self.source == "crawler":
            logger.info(f"开始处理爬虫源微信文章 (days={days if days is not None else '全部未处理'})")
        else:
            if days is None:
                days = 3  # 保持wewe源原有默认行为
            logger.info(f"开始处理最近 {days} 天的微信文章")

        result = ProcessResult()
        result.start_time = datetime.now()

        try:
            # 获取文章列表
            if self.source == "crawler":
                articles, window_total = self._fetch_articles_from_crawler(days)
                # 窗口统计：总数含已成功文章，差值即"跳过(已处理)"，供报告展示
                result.window_total = window_total
                result.skipped_articles = max(window_total - len(articles), 0)
            else:
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

            # 处理每篇文章；连续假PDF达到阈值时判定被微信风控，中止本次运行
            consecutive_blocked = 0
            for article in articles:
                try:
                    # 去重键：wewe源用文章id，crawler源用dedup_key（爬虫侧业务唯一键）
                    if self.source == "crawler":
                        article_key = article.get('dedup_key')
                    else:
                        article_key = article.get('id')

                    if not article_key:
                        logger.warning(f"文章缺少去重键: {article}")
                        result.failed_articles += 1
                        continue

                    # 检查是否已处理
                    if self._is_article_processed(article_key):
                        logger.info(f"文章已处理，跳过: {article_key}")
                        result.skipped_articles += 1
                        continue

                    # 处理单篇文章
                    if self._process_single_article(article):
                        result.processed_articles += 1
                        consecutive_blocked = 0
                    else:
                        result.failed_articles += 1
                        if self.last_pdf_blocked:
                            consecutive_blocked += 1
                            if consecutive_blocked >= FAKE_PDF_CIRCUIT_BREAKER:
                                msg = (f"连续 {consecutive_blocked} 篇文章生成拦截页假PDF，"
                                       f"判定已被微信风控，中止本次运行（未处理文章下次运行自动继续）")
                                logger.error(msg)
                                result.errors.append(msg)
                                break
                        else:
                            consecutive_blocked = 0

                    # 文章间随机延时：在 [wxchat_download_delay, wxchat_download_delay_max] 内随机，
                    # 模拟人工节奏降低触发微信频控的概率（配置缺失时默认20~50秒）
                    delay_min = self.config.wxchat_download_delay
                    delay_max = max(self.config.wxchat_download_delay_max, delay_min)
                    delay_seconds = random.uniform(delay_min, delay_max)
                    logger.info(f"⏸️  随机暂停 {delay_seconds:.0f} 秒后继续...")
                    time.sleep(delay_seconds)

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
        finally:
            # 批次结束关闭复用的浏览器会话
            self.pdf_generator.close_browser()

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
                    # 失败退避：new_wx_article状态表在主库（与wewe_rss同服务器），跨库JOIN过滤
                    status_table = f"`{self.config.db_name}`.`new_wx_article`"
                    cursor.execute(f"""
                        SELECT
                            articles.id,
                            articles.mp_id,
                            articles.title,
                            articles.publish_time
                        FROM articles
                        LEFT JOIN {status_table} s ON s.article_id = articles.id
                        WHERE FROM_UNIXTIME(publish_time) BETWEEN %s AND %s
                          AND (s.article_id IS NULL OR s.retry_count = 0
                               OR NOW() >= DATE_ADD(s.updated_at, INTERVAL s.retry_count * %s MINUTE))
                        ORDER BY COALESCE(s.retry_count, 0) ASC, publish_time DESC
                    """, (start_date, end_date, RETRY_BACKOFF_MINUTES))

                    articles = cursor.fetchall()

            logger.info(f"从wewe_rss获取到 {len(articles)} 篇文章")
            return articles

        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")
            return []

    def _fetch_articles_from_crawler(self, days: Optional[int] = None):
        """
        从主库wechat_crawler_articles表获取爬虫源待处理文章列表（只读，禁止写爬虫表）

        已成功下载（状态表processed_at非空）的文章在拆分逻辑中过滤，
        不再进入处理循环；失败退避期内的文章同样暂不拉取。

        Args:
            days: 可选，只取最近N天（按publish_date）发布的文章；None表示全部

        Returns:
            (待处理文章列表, 窗口内文章总数) 元组；
            文章含 id/dedup_key/url/title/publish_date/account_id/account_name 及状态列
        """
        articles = []

        try:
            start_date = None
            if days is not None:
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    # 窗口内文章总数（只过滤空URL/无发布日期，不含处理状态），供统计"最近N天共多少篇/跳过多少已处理"
                    cursor.execute("""
                        SELECT COUNT(*) AS cnt
                        FROM wechat_crawler_articles a
                        WHERE a.url IS NOT NULL AND a.url != ''
                          AND a.publish_date IS NOT NULL AND a.publish_date != ''
                          AND (%s IS NULL OR a.publish_date >= %s)
                    """, (start_date, start_date))
                    window_total = cursor.fetchone()['cnt']

                    # publish_date为VARCHAR 'YYYY-MM-DD'，字典序比较即日期比较
                    # 只过滤空URL；url_status属于爬虫侧语义，此处不做过滤
                    # 处理状态过滤与失败退避在 _split_pending_articles 中统一判断
                    cursor.execute("""
                        SELECT
                            a.id,
                            a.dedup_key,
                            a.url,
                            a.title,
                            a.publish_date,
                            a.account_id,
                            b.name AS account_name,
                            s.processed_at AS s_processed_at,
                            s.retry_count AS s_retry_count,
                            s.updated_at AS s_updated_at
                        FROM wechat_crawler_articles a
                        LEFT JOIN wechat_crawler_accounts b ON b.id = a.account_id
                        -- 爬虫表为utf8mb4_0900_ai_ci、本系统状态表为utf8mb4_unicode_ci，显式COLLATE避免混合排序规则报错
                        LEFT JOIN wechat_crawler_article_status s ON s.article_key = a.dedup_key COLLATE utf8mb4_0900_ai_ci
                        WHERE a.url IS NOT NULL AND a.url != ''
                          AND a.publish_date IS NOT NULL AND a.publish_date != ''
                          AND (%s IS NULL OR a.publish_date >= %s)
                        -- 被风控标记过的文章（retry_count高）垫底，避免每轮开局就撞拦截页浪费额度
                        ORDER BY COALESCE(s.retry_count, 0) ASC, a.publish_date DESC, a.id DESC
                    """, (start_date, start_date))

                    articles = cursor.fetchall()

            pending, window_total = self._split_pending_articles(articles)
            logger.info(f"从wechat_crawler_articles获取到 {len(pending)} 篇待处理文章"
                        f"（窗口内共 {window_total} 篇）")
            return pending, window_total

        except Exception as e:
            logger.error(f"获取爬虫源文章列表失败: {e}")
            return [], 0

    def _split_pending_articles(self, articles: List[Dict]):
        """
        将窗口内文章拆分为待处理与需跳过两类（纯逻辑，便于测试）

        过滤规则：
        - 发布日期缺失或无法解析 → 直接过滤（不进待处理，也不计入窗口总数）
        - 状态表processed_at非空 → 已成功下载，跳过
        - 失败退避期内（retry_count*20分钟未到期）→ 暂不拉取，下次运行再试

        Args:
            articles: 带状态列（s_processed_at/s_retry_count/s_updated_at）的文章列表

        Returns:
            (待处理文章列表, 窗口内文章总数) 元组
        """
        pending = []
        window_total = 0
        now = datetime.now()
        for article in articles:
            # 无发布日期的文章无法归档YYYYMM目录，直接过滤
            if self._parse_publish_date(article.get('publish_date')) is None:
                continue
            window_total += 1
            if article.get('s_processed_at') is not None:
                continue  # 已成功下载，跳过
            retry_count = article.get('s_retry_count') or 0
            updated_at = article.get('s_updated_at')
            if retry_count > 0 and updated_at is not None:
                backoff = timedelta(minutes=retry_count * RETRY_BACKOFF_MINUTES)
                if now < updated_at + backoff:
                    continue  # 失败退避期内，暂不拉取
            pending.append(article)
        return pending, window_total

    def _parse_publish_date(self, raw: Optional[str]) -> Optional[datetime]:
        """
        解析发布日期，兼容两种格式：
        - wewe源: '%Y-%m-%d %H:%M:%S'
        - crawler源: '%Y-%m-%d'

        Args:
            raw: 原始日期字符串

        Returns:
            datetime对象，解析失败返回None
        """
        if not raw:
            return None
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def _process_single_article(self, article: Dict) -> bool:
        """
        处理单篇文章：生成PDF并上传

        Args:
            article: 文章信息

        Returns:
            是否处理成功
        """
        article_id = article.get('id')
        # 去重键：wewe源=文章id，crawler源=dedup_key（与process_articles循环一致）
        article_key = article.get('dedup_key') or article.get('id')
        self.last_pdf_blocked = False
        # 字段适配：wewe源为(mp_id, publish_time)，crawler源为(account_id, publish_date)
        if self.source == "crawler":
            account_id = article.get('account_id')
            publish_date = article.get('publish_date')
        else:
            account_id = article.get('mp_id')
            publish_time = article.get('publish_time')
            publish_date = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M:%S') if publish_time else None
        title = article.get('title')

        # 文章链接：wewe源按base_url+id拼接，crawler源为完整URL（日志必备，方便排查）
        article_url = article.get('url') or f"{self.pdf_generator.base_url}{article_id}"
        logger.info(f"📄 开始处理文章: {title} ({article_id})")
        logger.info(f"   链接: {article_url}")
        logger.info(f"   账号ID: {account_id}, 发布时间: {publish_date}")

        pdf_url = None
        error_message = None

        try:
            # 发布日期校验：解析失败直接失败，避免PDF落入错误的年月目录
            if self._parse_publish_date(publish_date) is None:
                error_message = "发布日期缺失或无法解析"
                logger.error(f"❌ {error_message}: {title} ({article_key})")
                self._update_article_status(article_key, account_id, title, publish_date, pdf_url, error_message, article=article)
                return False

            # 创建临时文件
            logger.info(f"   创建临时PDF文件...")
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                temp_pdf_path = tmp_file.name

            # 生成PDF（含假PDF检测）：wewe源按base_url+article_id拼URL，crawler源直接用完整URL
            # 微信反爬会返回"环境异常"拦截页，被打印成约29KB的假PDF，因此生成后校验文件大小
            # 单次运行内不重试：失败立即记账返回，重试交给下次运行的退避重扫（retry_count * 20分钟）
            logger.info(f"   开始生成PDF: {article_id}")
            logger.info(f"   文章链接: {article_url}")
            fail_kind = None  # None=成功；"生成失败" / "为拦截页假PDF"
            if not self.pdf_generator.generate_pdf_from_url(article_url, temp_pdf_path):
                # 早期检测命中验证页时按拦截页归类（供风控熔断统计），否则为普通生成失败
                if getattr(self.pdf_generator, 'last_page_blocked', False):
                    fail_kind = "为拦截页假PDF"
                else:
                    fail_kind = "生成失败"
                logger.warning(f"   PDF生成失败({fail_kind}): {article_id}")
            elif os.path.getsize(temp_pdf_path) < MIN_VALID_PDF_SIZE:
                fail_kind = "为拦截页假PDF"
                pdf_size = os.path.getsize(temp_pdf_path)
                logger.warning(f"   PDF仅 {pdf_size // 1024} KB"
                               f"（低于 {MIN_VALID_PDF_SIZE // 1024} KB 阈值），疑似微信拦截页: {article_id}")

            if fail_kind:
                error_message = f"PDF{fail_kind}"
                # last_pdf_blocked 供 process_articles 风控熔断统计使用
                self.last_pdf_blocked = (fail_kind == "为拦截页假PDF")
                logger.error(f"❌ {error_message}: {article_id}")
                try:
                    os.unlink(temp_pdf_path)
                except Exception:
                    pass
                self._update_article_status(article_key, account_id, title, publish_date, pdf_url, error_message, article=article)
                return False

            self.last_pdf_blocked = False
            logger.info(f"✅ PDF生成完成: {temp_pdf_path}")

            # 上传到SFTP
            logger.info(f"   准备上传PDF到SFTP服务器...")
            try:
                with SFTPClient() as sftp:
                    # 生成YYYYMM格式的目录（兼容wewe源完整时间与crawler源纯日期）
                    publish_date_obj = self._parse_publish_date(publish_date)
                    yymm = publish_date_obj.strftime('%Y%m')
                    logger.info(f"   目标目录: {yymm}")

                    # 获取账号名称用于文件命名（crawler源JOIN直接带出，wewe源查库）
                    account_name = article.get('account_name') or self._get_account_name(account_id)
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
            self._update_article_status(article_key, account_id, title, publish_date, pdf_url, error_message, article=article)

            if error_message is None:
                logger.info(f"🎉 文章处理完成: {title} ({article_id})")
            else:
                logger.error(f"❌ 文章处理失败: {title} - {error_message}")

            return error_message is None

        except Exception as e:
            error_message = f"处理异常: {str(e)}"
            logger.error(f"处理文章异常: {e}")
            self._update_article_status(article_key, account_id, title, publish_date, pdf_url, error_message, article=article)
            return False

    def _is_article_processed(self, article_id: str) -> bool:
        """
        检查文章是否已处理

        Args:
            article_id: 去重键（wewe源=文章id，crawler源=dedup_key）

        Returns:
            是否已处理
        """
        # 按数据源选状态表：表名/列名为静态字符串，无注入风险
        if self.source == "crawler":
            table, key_column = "wechat_crawler_article_status", "article_key"
        else:
            table, key_column = "new_wx_article", "article_id"

        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(*) as count
                        FROM {table}
                        WHERE {key_column} = %s
                        AND processed_at IS NOT NULL
                    """, (article_id,))

                    result = cursor.fetchone()
                    is_processed = result['count'] > 0

                    logger.debug(f"文章处理状态检查: {article_id} -> {is_processed}")
                    return is_processed

        except Exception as e:
            logger.error(f"检查文章处理状态失败: {e}")
            return False

    def _update_article_status(self, article_id, account_id, title, publish_date, pdf_url, error_message, article: Optional[Dict] = None):
        """
        更新文章处理状态

        Args:
            article_id: 去重键（wewe源=文章id，crawler源=dedup_key）
            account_id: 账号ID
            title: 文章标题
            publish_date: 发布日期
            pdf_url: PDF URL
            error_message: 错误信息
            article: 原始文章信息（crawler源必传，用于溯源id与账号名快照）
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    processed_at = datetime.now() if error_message is None else None

                    if self.source == "crawler":
                        # crawler源：写入wechat_crawler_article_status（不含外键，article为溯源快照）
                        crawler_article_id = (article or {}).get('id', 0)
                        account_name = (article or {}).get('account_name') or str(account_id)
                        cursor.execute("""
                            INSERT INTO wechat_crawler_article_status (
                                article_key,
                                crawler_article_id,
                                account_id,
                                account_name,
                                title,
                                publish_date,
                                pdf_url,
                                error_message,
                                processed_at,
                                retry_count,
                                updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON DUPLICATE KEY UPDATE
                                crawler_article_id = VALUES(crawler_article_id),
                                account_id = VALUES(account_id),
                                account_name = VALUES(account_name),
                                title = VALUES(title),
                                publish_date = VALUES(publish_date),
                                pdf_url = VALUES(pdf_url),
                                error_message = VALUES(error_message),
                                processed_at = VALUES(processed_at),
                                retry_count = IF(VALUES(processed_at) IS NULL, wechat_crawler_article_status.retry_count + 1, 0),
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            article_id,
                            crawler_article_id,
                            account_id,
                            account_name,
                            title,
                            publish_date,
                            pdf_url,
                            error_message,
                            processed_at,
                            1 if error_message is not None else 0
                        ))
                    else:
                        # wewe源：写入new_wx_article（原有UPSERT）
                        cursor.execute("""
                            INSERT INTO new_wx_article (
                                article_id,
                                account_id,
                                title,
                                publish_date,
                                pdf_url,
                                error_message,
                                processed_at,
                                retry_count,
                                updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON DUPLICATE KEY UPDATE
                                account_id = VALUES(account_id),
                                title = VALUES(title),
                                publish_date = VALUES(publish_date),
                                pdf_url = VALUES(pdf_url),
                                error_message = VALUES(error_message),
                                processed_at = VALUES(processed_at),
                                retry_count = IF(VALUES(processed_at) IS NULL, new_wx_article.retry_count + 1, 0),
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            article_id,
                            account_id,
                            title,
                            publish_date,
                            pdf_url,
                            error_message,
                            processed_at,
                            1 if error_message is not None else 0
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
