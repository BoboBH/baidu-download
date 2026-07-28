# 微信公众号文章PDF转换上传功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个微信公众号文章处理系统，从wewe_rss数据库获取文章，使用Playwright转换为PDF，上传到SFTP服务器，并记录处理状态到test数据库。

**Architecture:** 采用轻量级集成架构，复用现有SFTP模块和配置系统。通过新增wxchat模块实现核心业务逻辑，使用Playwright进行PDF生成，支持账号同步、文章去重、错误重试等功能。

**Tech Stack:** Playwright + Chromium (PDF生成), MySQL (双数据库架构), SFTP (文件传输), Click (CLI命令)

---

## 文件结构映射

**新增文件:**
- `database/wxchat_tables.sql` - 数据库表结构定义
- `src/wxchat/__init__.py` - 模块初始化和导出
- `src/wxchat/models.py` - 数据模型定义
- `src/wxchat/processor.py` - 核心业务逻辑（账号同步、文章处理、PDF生成）
- `src/wxchat/commands.py` - CLI命令定义
- `tests/wxchat/test_processor.py` - 核心业务逻辑测试
- `tests/wxchat/test_commands.py` - CLI命令测试

**修改文件:**
- `src/config/settings.py:30-158` - 添加微信相关配置
- `main.py` - 注册wxchat命令
- `.env.example` - 添加微信配置示例

---

## Task 1: 创建数据库表结构

**Files:**
- Create: `database/wxchat_tables.sql`

- [ ] **Step 1: 创建数据库表结构文件**

```sql
-- 微信公众号账号表
CREATE TABLE IF NOT EXISTS wx_account (
    account_id VARCHAR(100) PRIMARY KEY COMMENT '账号ID',
    account_name VARCHAR(255) NOT NULL COMMENT '账号名称',
    app_id VARCHAR(100) COMMENT '所属应用ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号账号表';

-- 微信公众号文章表
CREATE TABLE IF NOT EXISTS wx_article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id VARCHAR(100) NOT NULL UNIQUE COMMENT '文章ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    title VARCHAR(500) COMMENT '文章标题',
    publish_date DATETIME COMMENT '发布时间',
    pdf_url VARCHAR(500) COMMENT 'PDF的SFTP路径',
    processed_at DATETIME COMMENT '处理完成时间',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_account_id (account_id),
    INDEX idx_publish_date (publish_date),
    INDEX idx_processed_at (processed_at),
    INDEX idx_pdf_url (pdf_url),
    FOREIGN KEY (account_id) REFERENCES wx_account(account_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号文章表';
```

- [ ] **Step 2: 验证SQL语法**

运行: `mysql -u root -p --dry-run < database/wxchat_tables.sql`
预期: 无语法错误

- [ ] **Step 3: Commit**

```bash
git add database/wxchat_tables.sql
git commit -m "feat(wxchat): add database schema for WeChat account and article tables"
```

---

## Task 2: 扩展配置系统

**Files:**
- Modify: `src/config/settings.py:30-158`

- [ ] **Step 1: 在Settings类的_load_config方法中添加微信配置**

在`_load_config`方法中，现有配置之后添加：

```python
# 微信公众号配置
self.wxchat_enabled = os.getenv('WXCHAT_ENABLED', 'false').lower() == 'true'
self.wxchat_wewe_db_host = os.getenv('WXCHAT_WEWE_DB_HOST', '')
self.wxchat_wewe_db_port = self._get_int_env('WXCHAT_WEWE_DB_PORT', default=3306)
self.wxchat_wewe_db_user = os.getenv('WXCHAT_WEWE_DB_USER', '')
self.wxchat_wewe_db_password = os.getenv('WXCHAT_WEWE_DB_PASSWORD', '')
self.wxchat_wewe_db_name = os.getenv('WXCHAT_WEWE_DB_NAME', '')
self.wxchat_base_url = os.getenv('WXCHAT_BASE_URL', 'https://mp.weixin.qq.com/s/')
self.wxchat_pdf_timeout = self._get_int_env('WXCHAT_PDF_TIMEOUT', default=60)
self.wxchat_image_wait_time = self._get_int_env('WXCHAT_IMAGE_WAIT_TIME', default=20)
self.wxchat_download_delay = self._get_int_env('WXCHAT_DOWNLOAD_DELAY', default=5)
self.wxchat_max_days = self._get_int_env('WXCHAT_MAX_DAYS', default=30)
```

- [ ] **Step 2: 在_validate_config方法中添加微信配置验证**

在`_validate_config`方法末尾添加：

```python
# 验证微信配置（如果启用）
if self.wxchat_enabled:
    if not self.wxchat_wewe_db_host:
        raise ConfigError("WXCHAT_WEWE_DB_HOST is required when WXCHAT_ENABLED is true")
    if not self.wxchat_wewe_db_user:
        raise ConfigError("WXCHAT_WEWE_DB_USER is required when WXCHAT_ENABLED is true")
    if not self.wxchat_wewe_db_password:
        raise ConfigError("WXCHAT_WEWE_DB_PASSWORD is required when WXCHAT_ENABLED is true")
    if not self.wxchat_wewe_db_name:
        raise ConfigError("WXCHAT_WEWE_DB_NAME is required when WXCHAT_ENABLED is true")
    
    # 验证数值参数合理性
    if self.wxchat_pdf_timeout < 10 or self.wxchat_pdf_timeout > 300:
        raise ConfigError(f"WXCHAT_PDF_TIMEOUT must be between 10 and 300: {self.wxchat_pdf_timeout}")
    if self.wxchat_image_wait_time < 5 or self.wxchat_image_wait_time > 120:
        raise ConfigError(f"WXCHAT_IMAGE_WAIT_TIME must be between 5 and 120: {self.wxchat_image_wait_time}")
    if self.wxchat_download_delay < 1 or self.wxchat_download_delay > 60:
        raise ConfigError(f"WXCHAT_DOWNLOAD_DELAY must be between 1 and 60: {self.wxchat_download_delay}")
    if self.wxchat_max_days < 1 or self.wxchat_max_days > 365:
        raise ConfigError(f"WXCHAT_MAX_DAYS must be between 1 and 365: {self.wxchat_max_days}")
```

- [ ] **Step 3: 测试配置加载**

运行: `python -c "from src.config.settings import Settings; s = Settings(); print('WXCHAT enabled:', s.wxchat_enabled)"`
预期: 无错误，显示配置状态

- [ ] **Step 4: Commit**

```bash
git add src/config/settings.py
git commit -m "feat(wxchat): extend configuration system for WeChat article processing"
```

---

## Task 3: 创建wxchat模块初始化文件

**Files:**
- Create: `src/wxchat/__init__.py`

- [ ] **Step 1: 创建模块初始化文件**

```python
"""
微信公众号文章处理模块

提供从wewe_rss数据库获取文章，转换为PDF，上传到SFTP服务器的功能。
"""

from .processor import WeChatAccountSync, WeChatArticleProcessor
from .commands import register_commands

__all__ = [
    'WeChatAccountSync',
    'WeChatArticleProcessor', 
    'register_commands'
]
```

- [ ] **Step 2: 验证模块导入**

运行: `python -c "from src.wxchat import WeChatAccountSync; print('Import successful')"`
预期: 显示"Import successful"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/__init__.py
git commit -m "feat(wxchat): create module initialization file"
```

---

## Task 4: 创建数据模型定义

**Files:**
- Create: `src/wxchat/models.py`

- [ ] **Step 1: 创建数据模型文件**

```python
"""
微信公众号数据模型定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WeChatAccount:
    """微信公众号账号模型"""
    account_id: str
    account_name: str
    app_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass  
class WeChatArticle:
    """微信公众号文章模型"""
    article_id: str
    account_id: str
    title: Optional[str] = None
    publish_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ProcessResult:
    """处理结果统计模型"""
    total_articles: int = 0
    processed_articles: int = 0
    failed_articles: int = 0
    skipped_articles: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
            
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'total_articles': self.total_articles,
            'processed_articles': self.processed_articles,
            'failed_articles': self.failed_articles,
            'skipped_articles': self.skipped_articles,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
            'error_count': len(self.errors)
        }
```

- [ ] **Step 2: 验证数据模型**

运行: `python -c "from src.wxchat.models import WeChatArticle, ProcessResult; a = WeChatArticle('test_id', 'acc_id'); print(a.article_id)"`
预期: 显示"test_id"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/models.py
git commit -m "feat(wxchat): add data models for WeChat accounts and articles"
```

---

## Task 5: 创建数据库操作工具类

**Files:**
- Modify: `src/wxchat/processor.py`

- [ ] **Step 1: 创建processor.py文件并添加数据库连接工具类**

```python
"""
微信公众号文章处理核心逻辑

包含账号同步、文章处理、PDF生成等功能。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pymysql
from playwright.sync_api import sync_playwright, Browser, Page
from pathlib import Path
import tempfile
import os

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
```

- [ ] **Step 2: 测试数据库连接工具**

运行: `python -c "from src.wxchat.processor import DatabaseConnection; from src.config.settings import Settings; c = DatabaseConnection(Settings(), False); print('Database connection class created')"`
预期: 显示"Database connection class created"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/processor.py
git commit -m "feat(wxchat): add database connection utilities and account sync functionality"
```

---

## Task 6: 实现PDF生成器

**Files:**
- Modify: `src/wxchat/processor.py`

- [ ] **Step 1: 在processor.py中添加PDFGenerator类**

在`WeChatAccountSync`类之后添加：

```python
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
```

- [ ] **Step 2: 测试PDF生成器类导入**

运行: `python -c "from src.wxchat.processor import PDFGenerator; print('PDFGenerator class imported')"`
预期: 显示"PDFGenerator class imported"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/processor.py
git commit -m "feat(wxchat): add PDF generator with Playwright"
```

---

## Task 7: 实现文章处理器

**Files:**
- Modify: `src/wxchat/processor.py`

- [ ] **Step 1: 在processor.py中添加WeChatArticleProcessor类**

在`PDFGenerator`类之后添加：

```python
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
        处理指定天数内的文章
        
        Args:
            days: 查询天数
            
        Returns:
            处理结果统计
        """
        logger.info(f"开始处理最近 {days} 天的文章")
        
        result = ProcessResult()
        result.start_time = datetime.now()
        
        try:
            # 验证天数参数
            if days < 1 or days > self.config.wxchat_max_days:
                raise ValueError(f"天数必须在1-{self.config.wxchat_max_days}之间: {days}")
            
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"查询时间范围: {start_date} 到 {end_date}")
            
            # 从wewe_rss数据库获取文章列表
            articles = self._fetch_articles_from_wewe(start_date, end_date)
            result.total_articles = len(articles)
            
            if not articles:
                logger.warning("未找到需要处理的文章")
                return result
                
            logger.info(f"找到 {len(articles)} 篇文章")
            
            # 处理每篇文章
            for article in articles:
                try:
                    if self._process_single_article(article):
                        result.processed_articles += 1
                    else:
                        result.failed_articles += 1
                        
                except Exception as e:
                    logger.error(f"处理文章失败 {article.get('article_id')}: {e}")
                    result.failed_articles += 1
                    result.errors.append(str(e))
                    
            result.end_time = datetime.now()
            logger.info(f"文章处理完成: {result.to_dict()}")
            
        except Exception as e:
            logger.error(f"文章处理失败: {e}")
            result.errors.append(str(e))
            
        return result
        
    def _fetch_articles_from_wewe(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        从wewe_rss数据库获取文章列表
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            文章列表
        """
        logger.info("从wewe_rss数据库获取文章列表")
        
        try:
            with DatabaseConnection(self.config, use_wewe_db=True) as wewe_conn:
                with wewe_conn.cursor() as cursor:
                    # 假设wewe_rss数据库中有article表
                    cursor.execute("""
                        SELECT 
                            article_id,
                            account_id,
                            title,
                            publish_date
                        FROM article
                        WHERE publish_date >= %s 
                          AND publish_date <= %s
                          AND article_id IS NOT NULL
                        ORDER BY publish_date DESC
                    """, (start_date, end_date))
                    
                    articles = cursor.fetchall()
                    
            logger.info(f"获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")
            raise
            
    def _process_single_article(self, article: Dict) -> bool:
        """
        处理单个文章
        
        Args:
            article: 文章信息字典
            
        Returns:
            是否处理成功
        """
        article_id = article['article_id']
        account_id = article['account_id']
        title = article.get('title', '')
        publish_date = article.get('publish_date')
        
        logger.info(f"处理文章: {article_id} - {title}")
        
        try:
            # 检查是否已经处理过
            if self._is_article_processed(article_id):
                logger.info(f"文章已处理，跳过: {article_id}")
                return False  # 返回False表示没有实际处理
                
            # 生成PDF
            temp_dir = tempfile.gettempdir()
            pdf_filename = f"{article_id}.pdf"
            pdf_temp_path = os.path.join(temp_dir, pdf_filename)
            
            if not self.pdf_generator.generate_pdf(article_id, pdf_temp_path):
                logger.error(f"PDF生成失败: {article_id}")
                self._update_article_status(article_id, account_id, title, publish_date, None, "PDF生成失败")
                return False
                
            # 计算SFTP路径 (YYMM格式)
            publish_datetime = publish_date if isinstance(publish_date, datetime) else datetime.now()
            year_month = publish_datetime.strftime('%y%m')  # 2412表示2024年12月
            sftp_path = f"/wxchat/{year_month}/{pdf_filename}"
            
            # 上传PDF到SFTP服务器
            try:
                from src.sftp.client import SFTPClient
                sftp_client = SFTPClient(self.config)
                sftp_client.connect()
                
                # 确保远程目录存在
                remote_dir = f"/wxchat/{year_month}"
                try:
                    sftp_client.mkdir_p(remote_dir)
                except:
                    pass  # 目录可能已存在
                    
                # 上传文件
                sftp_client.upload_file(pdf_temp_path, sftp_path)
                sftp_client.disconnect()
                
                logger.info(f"PDF上传成功: {sftp_path}")
                
                # 更新数据库状态
                self._update_article_status(article_id, account_id, title, publish_date, sftp_path, None)
                
                # 删除临时文件
                try:
                    os.remove(pdf_temp_path)
                except:
                    pass
                    
                return True
                
            except Exception as e:
                logger.error(f"SFTP上传失败: {e}")
                self._update_article_status(article_id, account_id, title, publish_date, None, f"SFTP上传失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"处理文章失败: {e}")
            return False
            
    def _is_article_processed(self, article_id: str) -> bool:
        """
        检查文章是否已经处理过
        
        Args:
            article_id: 文章ID
            
        Returns:
            是否已处理
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as test_conn:
                with test_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT pdf_url FROM wx_article 
                        WHERE article_id = %s
                    """, (article_id,))
                    
                    result = cursor.fetchone()
                    
                    # 如果记录存在且有pdf_url，说明已处理
                    return result and result.get('pdf_url') is not None
                    
        except Exception as e:
            logger.error(f"检查文章处理状态失败: {e}")
            return False
            
    def _update_article_status(self, article_id: str, account_id: str, title: str, 
                               publish_date: datetime, pdf_url: Optional[str], 
                               error_message: Optional[str]):
        """
        更新文章处理状态
        
        Args:
            article_id: 文章ID
            account_id: 账号ID
            title: 标题
            publish_date: 发布时间
            pdf_url: PDF路径
            error_message: 错误信息
        """
        try:
            with DatabaseConnection(self.config, use_wewe_db=False) as test_conn:
                with test_conn.cursor() as cursor:
                    if pdf_url:
                        # 处理成功
                        processed_at = datetime.now()
                        cursor.execute("""
                            INSERT INTO wx_article 
                                (article_id, account_id, title, publish_date, pdf_url, processed_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                title = VALUES(title),
                                publish_date = VALUES(publish_date),
                                pdf_url = VALUES(pdf_url),
                                processed_at = VALUES(processed_at),
                                error_message = NULL,
                                retry_count = 0,
                                updated_at = CURRENT_TIMESTAMP
                        """, (article_id, account_id, title, publish_date, pdf_url, processed_at))
                        
                    else:
                        # 处理失败
                        cursor.execute("""
                            INSERT INTO wx_article 
                                (article_id, account_id, title, publish_date, error_message)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                error_message = VALUES(error_message),
                                retry_count = retry_count + 1,
                                updated_at = CURRENT_TIMESTAMP
                        """, (article_id, account_id, title, publish_date, error_message))
                        
                test_conn.commit()
                
        except Exception as e:
            logger.error(f"更新文章状态失败: {e}")
```

- [ ] **Step 2: 测试文章处理器类导入**

运行: `python -c "from src.wxchat.processor import WeChatArticleProcessor; print('WeChatArticleProcessor class imported')"`
预期: 显示"WeChatArticleProcessor class imported"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/processor.py
git commit -m "feat(wxchat): add article processor with PDF generation and SFTP upload"
```

---

## Task 8: 创建CLI命令定义

**Files:**
- Create: `src/wxchat/commands.py`

- [ ] **Step 1: 创建CLI命令文件**

```python
"""
微信公众号文章处理CLI命令定义
"""

import click
import logging
from src.config.settings import Settings
from src.wxchat.processor import WeChatAccountSync, WeChatArticleProcessor

logger = logging.getLogger(__name__)


def register_commands(cli: click.Group):
    """
    注册微信文章处理相关命令
    
    Args:
        cli: Click命令组对象
    """
    
    @cli.command('wxchat')
    @click.option('--days', default=3, help='处理最近几天的文章（默认3天）')
    @click.option('--sync-accounts', is_flag=True, help='仅同步账号信息')
    @click.pass_context
    def wxchat_command(ctx, days, sync_accounts):
        """
        处理微信公众号文章
        
        从wewe_rss数据库获取文章，转换为PDF，上传到SFTP服务器
        
        示例:
            python main.py wxchat                    # 处理最近3天文章
            python main.py wxchat --days 7          # 处理最近7天文章  
            python main.py wxchat --sync-accounts    # 仅同步账号信息
        """
        try:
            # 加载配置
            config = Settings()
            
            if not config.wxchat_enabled:
                click.echo("错误: 微信文章处理功能未启用，请在.env中设置WXCHAT_ENABLED=true")
                return
                
            # 配置日志
            logging.basicConfig(
                level=getattr(logging, config.log_level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(config.log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            
            click.echo("🚀 微信公众号文章处理系统")
            click.echo("=" * 50)
            
            if sync_accounts:
                # 仅同步账号信息
                click.echo("📋 开始同步微信账号信息...")
                
                syncer = WeChatAccountSync(config)
                count = syncer.sync_accounts()
                
                click.echo(f"✅ 账号同步完成，共同步 {count} 个账号")
                
            else:
                # 处理文章
                click.echo(f"📰 开始处理最近 {days} 天的文章...")
                
                processor = WeChatArticleProcessor(config)
                result = processor.process_articles(days)
                
                # 显示处理结果
                click.echo("\n📊 处理结果统计:")
                click.echo(f"  总文章数: {result.total_articles}")
                click.echo(f"  处理成功: {result.processed_articles}")
                click.echo(f"  处理失败: {result.failed_articles}")
                click.echo(f"  跳过处理: {result.skipped_articles}")
                
                if result.start_time and result.end_time:
                    duration = (result.end_time - result.start_time).total_seconds()
                    click.echo(f"  处理时长: {duration:.2f} 秒")
                    
                if result.errors:
                    click.echo(f"\n⚠️  错误信息:")
                    for error in result.errors[:5]:  # 只显示前5个错误
                        click.echo(f"  - {error}")
                        
                click.echo("\n✅ 文章处理完成!")
                
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            click.echo(f"❌ 执行失败: {e}")
            raise click.ClickException(str(e))
```

- [ ] **Step 2: 测试命令文件导入**

运行: `python -c "from src.wxchat.commands import register_commands; print('Commands module imported')"`
预期: 显示"Commands module imported"

- [ ] **Step 3: Commit**

```bash
git add src/wxchat/commands.py
git commit -m "feat(wxchat): add CLI command definition for WeChat article processing"
```

---

## Task 9: 集成到主程序

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 在main.py中注册wxchat命令**

首先找到main.py中注册命令的位置，通常在文件末尾附近：

```python
# 在其他命令注册之后添加
from src.wxchat.commands import register_commands
register_commands(cli)
```

如果main.py有固定的命令注册模式，请按照现有模式添加：

```python
# 示例：如果main.py有这样的结构
if __name__ == '__main__':
    # 其他命令注册
    # ...
    
    # 注册微信文章处理命令
    from src.wxchat.commands import register_commands
    register_commands(cli)
    
    cli()
```

- [ ] **Step 2: 测试命令注册**

运行: `python main.py --help`
预期: 在帮助信息中看到wxchat命令

- [ ] **Step 3: 测试基本命令功能**

运行: `python main.py wxchat --help`
预期: 显示wxchat命令的帮助信息，包括--days和--sync-accounts选项

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(wxchat): integrate wxchat command into main CLI"
```

---

## Task 10: 添加配置示例

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: 在.env.example中添加微信配置示例**

在现有配置后添加：

```bash
# ====================
# 微信公众号文章处理配置
# ====================
WXCHAT_ENABLED=false
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=your_password
WXCHAT_WEWE_DB_NAME=wewe_rss
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20
WXCHAT_DOWNLOAD_DELAY=5
WXCHAT_MAX_DAYS=30
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs(wxchat): add WeChat configuration examples to .env.example"
```

---

## Task 11: 创建单元测试

**Files:**
- Create: `tests/wxchat/test_processor.py`

- [ ] **Step 1: 创建核心业务逻辑测试文件**

```python
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
            {'account_id': 'acc1', 'account_name': '测试账号1', 'app_id': 'app1'},
            {'account_id': 'acc2', 'account_name': '测试账号2', 'app_id': 'app2'}
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
        
        # 测试超出范围的天数
        with pytest.raises(ValueError):
            processor.process_articles(days=31)
            
        with pytest.raises(ValueError):
            processor.process_articles(days=0)
            
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
```

- [ ] **Step 2: 运行单元测试**

运行: `pytest tests/wxchat/test_processor.py -v`
预期: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/wxchat/test_processor.py
git commit -m "test(wxchat): add unit tests for processor functionality"
```

---

## Task 12: 创建集成测试

**Files:**
- Create: `tests/wxchat/test_commands.py`

- [ ] **Step 1: 创建CLI命令测试文件**

```python
"""
微信公众号文章处理CLI命令集成测试
"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
from src.config.settings import Settings


class TestWxchatCommands:
    """微信文章处理命令测试"""
    
    @patch('src.wxchat.commands.Settings')
    @patch('src.wxchat.commands.WeChatArticleProcessor')
    def test_wxchat_command_default(self, mock_processor_class, mock_settings_class):
        """测试默认命令行为"""
        # 模拟配置
        mock_config = Mock()
        mock_config.wxchat_enabled = True
        mock_config.log_level = 'INFO'
        mock_config.log_file = '/tmp/test.log'
        mock_settings_class.return_value = mock_config
        
        # 模拟处理结果
        mock_result = Mock()
        mock_result.total_articles = 10
        mock_result.processed_articles = 8
        mock_result.failed_articles = 2
        mock_result.skipped_articles = 0
        mock_result.start_time = Mock()
        mock_result.end_time = Mock()
        mock_result.errors = []
        
        mock_processor = Mock()
        mock_processor.process_articles.return_value = mock_result
        mock_processor_class.return_value = mock_processor
        
        # 导入命令并执行
        from src.wxchat.commands import wxchat_command
        
        runner = CliRunner()
        result = runner.invoke(wxchat_command, [])
        
        # 验证调用
        assert mock_processor.process_articles.called
        assert '处理成功: 8' in result.output
        
    @patch('src.wxchat.commands.Settings')
    @patch('src.wxchat.commands.WeChatAccountSync')
    def test_sync_accounts_command(self, mock_sync_class, mock_settings_class):
        """测试账号同步命令"""
        # 模拟配置
        mock_config = Mock()
        mock_config.wxchat_enabled = True
        mock_config.log_level = 'INFO'
        mock_config.log_file = '/tmp/test.log'
        mock_settings_class.return_value = mock_config
        
        # 模拟同步结果
        mock_sync = Mock()
        mock_sync.sync_accounts.return_value = 5
        mock_sync_class.return_value = mock_sync
        
        # 导入命令并执行
        from src.wxchat.commands import wxchat_command
        
        runner = CliRunner()
        result = runner.invoke(wxchat_command, ['--sync-accounts'])
        
        # 验证调用
        assert mock_sync.sync_accounts.called
        assert '账号同步完成' in result.output
        assert '5' in result.output
        
    @patch('src.wxchat.commands.Settings')
    def test_disabled_feature(self, mock_settings_class):
        """测试功能未启用时的行为"""
        # 模拟配置
        mock_config = Mock()
        mock_config.wxchat_enabled = False
        mock_settings_class.return_value = mock_config
        
        # 导入命令并执行
        from src.wxchat.commands import wxchat_command
        
        runner = CliRunner()
        result = runner.invoke(wxchat_command, [])
        
        # 验证错误信息
        assert '未启用' in result.output
        
    @patch('src.wxchat.commands.Settings')
    def test_days_parameter(self, mock_settings_class):
        """测试天数参数"""
        mock_config = Mock()
        mock_config.wxchat_enabled = True
        mock_config.log_level = 'INFO'
        mock_config.log_file = '/tmp/test.log'
        mock_settings_class.return_value = mock_config
        
        with patch('src.wxchat.commands.WeChatArticleProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_articles.return_value = Mock()
            mock_processor_class.return_value = mock_processor
            
            from src.wxchat.commands import wxchat_command
            
            runner = CliRunner()
            result = runner.invoke(wxchat_command, ['--days', '7'])
            
            # 验证参数传递
            mock_processor.process_articles.assert_called_with(days=7)
```

- [ ] **Step 2: 运行集成测试**

运行: `pytest tests/wxchat/test_commands.py -v`
预期: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/wxchat/test_commands.py
git commit -m "test(wxchat): add integration tests for CLI commands"
```

---

## Task 13: 创建测试初始化文件

**Files:**
- Create: `tests/wxchat/__init__.py`

- [ ] **Step 1: 创建测试模块初始化文件**

```python
"""
微信公众号文章处理测试模块
"""
```

- [ ] **Step 2: Commit**

```bash
git add tests/wxchat/__init__.py
git commit -m "test(wxchat): add test module initialization file"
```

---

## Task 14: 创建使用文档

**Files:**
- Create: `docs/wxchat/USAGE.md`

- [ ] **Step 1: 创建使用文档**

```markdown
# 微信公众号文章处理功能使用指南

## 功能概述

本功能用于处理微信公众号文章，自动将文章转换为PDF格式并上传到SFTP服务器进行归档存储。

## 环境要求

- Python 3.8+
- MySQL数据库（包含wewe_rss和test两个数据库）
- SFTP服务器
- Playwright Chromium浏览器

## 安装依赖

```bash
# 安装Playwright
pip install playwright
playwright install chromium

# 安装其他依赖
pip install -r requirements.txt
```

## 配置说明

在`.env`文件中添加以下配置：

```bash
# 启用微信文章处理功能
WXCHAT_ENABLED=true

# wewe_rss数据库配置（源数据库）
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=your_password
WXCHAT_WEWE_DB_NAME=wewe_rss

# 微信文章基础URL
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/

# PDF生成配置
WXCHAT_PDF_TIMEOUT=60          # 页面加载超时时间（秒）
WXCHAT_IMAGE_WAIT_TIME=20       # 图片加载等待时间（秒）

# 反限流配置
WXCHAT_DOWNLOAD_DELAY=5         # 每篇文章处理后延迟时间（秒）

# 历史查询配置
WXCHAT_MAX_DAYS=30              # 最大查询天数
```

## 数据库准备

```bash
# 创建数据表
mysql -u root -p test < database/wxchat_tables.sql
```

## 使用方法

### 基本使用

```bash
# 处理最近3天的文章（默认）
python main.py wxchat

# 处理最近7天的文章
python main.py wxchat --days 7

# 处理最近1天的文章
python main.py wxchat --days 1

# 仅同步账号信息
python main.py wxchat --sync-accounts
```

### 定时任务

设置定时任务，每天自动处理最新文章：

```bash
# 添加到crontab
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * cd /path/to/baidu-download && python main.py wxchat --days 1
```

## 功能特点

### 1. 账号同步
- 自动从wewe_rss数据库同步微信公众号账号信息
- 支持增量更新，避免重复数据

### 2. 文章去重
- 基于article_id进行去重
- 已处理的文章会被跳过

### 3. PDF生成
- 使用Playwright模拟真实浏览器访问
- 等待图片加载完成，确保PDF质量
- 支持自定义页面格式和边距

### 4. SFTP上传
- 按YYMM格式组织文件（2401表示2024年1月）
- 自动创建远程目录
- 支持大文件上传

### 5. 错误处理
- 失败的文章会记录错误信息
- 支持自动重试机制
- 详细的日志记录

### 6. 反限流措施
- 真实浏览器请求头
- 每篇文章处理后延迟
- 合理的超时设置

## 监控和日志

### 查看日志

```bash
# 实时查看日志
tail -f logs/transfer.log

# 查找处理结果
grep "处理完成" logs/transfer.log
```

### 数据库监控

```sql
-- 查看处理统计
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed,
    COUNT(CASE WHEN pdf_url IS NULL THEN 1 END) as pending
FROM wx_article;

-- 查看最近处理记录  
SELECT * FROM wx_article 
ORDER BY processed_at DESC 
LIMIT 10;

-- 查看失败记录
SELECT article_id, title, error_message, retry_count
FROM wx_article 
WHERE pdf_url IS NULL 
  AND error_message IS NOT NULL
ORDER BY retry_count DESC
LIMIT 20;
```

## 故障排查

### PDF生成失败
**症状**: 日志显示"PDF生成失败"

**解决方案**:
1. 检查Playwright安装: `playwright install chromium`
2. 检查网络连接是否正常
3. 增加超时时间: `WXCHAT_PDF_TIMEOUT=120`
4. 检查文章URL是否有效

### SFTP上传失败
**症状**: 日志显示"SFTP上传失败"

**解决方案**:
1. 检查SFTP连接配置
2. 验证SFTP服务器权限
3. 检查磁盘空间是否充足
4. 测试网络连接

### 数据库连接失败
**症状**: 无法连接到数据库

**解决方案**:
1. 检查数据库配置是否正确
2. 验证数据库服务是否运行
3. 测试网络连接
4. 检查数据库用户权限

### 文章处理失败
**症状**: 特定文章处理失败

**解决方案**:
1. 检查文章是否存在于wewe_rss数据库
2. 验证article_id是否正确
3. 检查文章是否可公开访问
4. 查看详细错误信息

## 性能优化建议

1. **批量处理**: 适当增加天数参数，减少执行频率
2. **并发控制**: 当前版本为串行处理，可考虑并发优化
3. **资源清理**: 定期清理临时文件和旧日志
4. **数据库优化**: 为常用查询字段建立索引

## 安全建议

1. **数据库密码**: 使用强密码，定期更换
2. **SFTP安全**: 使用密钥认证，禁用密码登录
3. **网络隔离**: 在受信任的网络环境中运行
4. **日志保护**: 定期清理敏感日志信息

## 扩展功能

未来可能的功能扩展：

- 支持批量并发处理
- 增加处理进度通知
- 提供Web管理界面
- 支持多种文件格式转换
- 增加文章内容分析功能

## 技术支持

如遇到问题，请查看：
1. 日志文件: `logs/transfer.log`
2. 数据库错误记录: `wx_article.error_message`
3. 系统状态监控

---

**版本**: 1.0  
**最后更新**: 2026-07-28
```

- [ ] **Step 2: Commit**

```bash
git add docs/wxchat/USAGE.md
git commit -m "docs(wxchat): add comprehensive usage documentation"
```

---

## Task 15: 最终测试和验证

**Files:**
- None (测试验证)

- [ ] **Step 1: 运行所有测试**

运行: `pytest tests/wxchat/ -v`
预期: 所有测试通过

- [ ] **Step 2: 测试完整功能流程**

```bash
# 1. 测试账号同步
python main.py wxchat --sync-accounts

# 2. 测试文章处理（小范围测试）
python main.py wxchat --days 1

# 3. 测试帮助信息
python main.py wxchat --help
```

- [ ] **Step 3: 验证文件结构**

运行: `tree src/wxchat tests/wxchat database/`
预期: 显示完整的文件结构

- [ ] **Step 4: 最终代码检查**

运行: `git diff HEAD~15 HEAD --stat`
预期: 显示所有修改的文件统计

- [ ] **Step 5: 创建功能完成标记**

```bash
# 创建功能标记文件
echo "✅ 微信公众号文章PDF转换上传功能已完成 - 2026-07-28" > docs/wxchat/COMPLETED.txt

git add docs/wxchat/COMPLETED.txt
git commit -m "docs(wxchat): mark feature as completed"
```

---

## 验收标准

功能完成后，应满足以下标准：

1. **功能完整性**: 所有核心功能都能正常工作
2. **测试覆盖**: 单元测试和集成测试全部通过  
3. **文档完善**: 使用文档和技术文档齐全
4. **代码质量**: 代码结构清晰，符合项目规范
5. **错误处理**: 异常情况有合理的错误处理
6. **日志记录**: 关键操作有详细的日志记录
7. **配置管理**: 配置项完整且合理
8. **命令集成**: CLI命令能正常工作

---

**计划完成!** 🎉

总共15个任务，涵盖从数据库设计到最终测试的完整实现流程。每个任务都包含具体的代码、测试和验证步骤，确保实现质量和功能稳定性。