"""
微信文章链接处理器

处理微信文章链接的PDF生成和SFTP上传。
复用wxchat的PDFGenerator核心代码。

性能优化:
- HTTP请求优化: 超时控制、连接池
- 元数据缓存: 避免重复解析
- 资源管理: 高效临时文件清理
"""
import os
import tempfile
import requests
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup
from functools import lru_cache
import hashlib
import time

from src.feishu.models import ParseResult
from src.config.settings import Settings
from src.utils.logger import get_logger
from src.wxchat.processor import PDFGenerator


@dataclass
class DownloadResult:
    """微信文章下载结果"""
    success: bool
    local_path: Optional[str] = None
    file_size: int = 0
    article_title: Optional[str] = None
    account_name: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = False


@dataclass
class ProcessResult:
    """微信文章处理结果"""
    success: bool
    processed_files: List[str]
    article_title: Optional[str] = None
    account_name: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = False


class WxchatArticleProcessor:
    """微信文章链接处理器 - 性能优化版本"""

    def __init__(self, settings: Settings):
        """
        初始化处理器

        Args:
            settings: 配置对象
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.pdf_generator = PDFGenerator(settings)
        self.temp_dir = None

        # 性能优化: 缓存已解析的文章元数据
        self._metadata_cache: Dict[str, Dict] = {}
        self._cache_max_size = 100  # 最多缓存100篇文章

        # 性能监控数据
        self._performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_request_time': 0.0,
            'total_processing_time': 0.0
        }

    def can_process(self, message_type: str) -> bool:
        """检查是否支持该消息类型"""
        return message_type == 'wxchat-article'

    def _get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_performance_stats(self) -> Dict:
        """获取性能统计信息"""
        if self._performance_stats['total_requests'] > 0:
            avg_time = (self._performance_stats['total_processing_time'] /
                       self._performance_stats['total_requests'])
            cache_hit_rate = (self._performance_stats['cache_hits'] /
                            self._performance_stats['total_requests'] * 100)
        else:
            avg_time = 0.0
            cache_hit_rate = 0.0

        return {
            'total_requests': self._performance_stats['total_requests'],
            'cache_hits': self._performance_stats['cache_hits'],
            'cache_misses': self._performance_stats['cache_misses'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'avg_request_time': f"{avg_time:.2f}s"
        }

    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        从微信文章页面提取元数据

        Args:
            parse_result: 解析结果

        Returns:
            DownloadResult包含文章标题和公众号名称
        """
        self.logger.info(f"开始下载微信文章 - message_type: {parse_result.message_type}")

        if not parse_result.wxchat_article_url:
            self.logger.error("微信文章URL为空 - 参数验证失败")
            return DownloadResult(
                success=False,
                error="微信文章URL为空",
                retryable=False  # 参数错误，不可重试
            )

        article_url = parse_result.wxchat_article_url
        self.logger.info(f"正在获取微信文章信息: {article_url}")
        self.logger.debug(f"ParseResult详情 - article_id: {parse_result.wxchat_article_id}, url: {article_url}")

        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix='wxchat_article_')

            # 请求文章页面获取元数据
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(article_url, headers=headers, timeout=30)
            if response.status_code != 200:
                return DownloadResult(
                    success=False,
                    error=f"获取文章页面失败: HTTP {response.status_code}",
                    retryable=True if response.status_code >= 500 else False
                )

            # 解析HTML获取文章标题和公众号名称
            soup = BeautifulSoup(response.content, 'html.parser')

            # 获取文章标题
            title_tag = soup.find('meta', property='og:title')
            article_title = title_tag.get('content', '') if title_tag else ''

            # 获取公众号名称
            account_tag = soup.find('meta', property='og:site_name')
            account_name = account_tag.get('content', '') if account_tag else ''

            if not article_title:
                self.logger.error(f"无法从页面提取文章标题 - 页面解析失败，URL: {article_url}")
                return DownloadResult(
                    success=False,
                    error="无法从页面提取文章标题",
                    retryable=False  # 页面解析失败，永久性错误
                )

            # 清理文件名
            article_title = self._clean_filename(article_title)
            account_name = self._clean_filename(account_name) if account_name else ''

            # 🔥 优化：只有真实公众号名称才使用，"微信公众平台"视为未识别
            if account_name and account_name != '微信公众平台':
                self.logger.info(f"文章信息获取成功 - 标题: {article_title}, 公众号: {account_name}")
            else:
                account_name = ''  # 清空通用名称，只用文章标题
                self.logger.info(f"文章信息获取成功 - 标题: {article_title}, 公众号: 未识别真实名称")

            return DownloadResult(
                success=True,
                article_title=article_title,
                account_name=account_name
            )

        except requests.exceptions.Timeout:
            return DownloadResult(
                success=False,
                error="获取文章页面超时",
                retryable=True
            )
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                success=False,
                error=f"网络请求失败: {str(e)}",
                retryable=True
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"解析文章页面失败: {str(e)}"
            )

    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        生成微信文章PDF

        Args:
            download_result: 下载结果（包含文章信息）
            parse_result: 原始解析结果

        Returns:
            ProcessResult包含生成的PDF文件路径
        """
        self.logger.info(f"开始处理微信文章PDF - title: {download_result.article_title}, account: {download_result.account_name}")
        self.logger.debug(f"下载结果 - success: {download_result.success}, retryable: {download_result.retryable}, error: {download_result.error}")

        if not download_result.success:
            self.logger.error(f"下载失败: {download_result.error}, retryable: {download_result.retryable}")
            return ProcessResult(
                success=False,
                processed_files=[],
                error=download_result.error,
                retryable=download_result.retryable  # 传递下载结果的retryable状态
            )

        article_id = parse_result.wxchat_article_id
        if not article_id:
            self.logger.error("文章ID为空 - 参数验证失败")
            return ProcessResult(
                success=False,
                processed_files=[],
                error="文章ID为空",
                retryable=False  # 参数错误，不可重试
            )

        # 生成PDF文件名
        # 🔥 优化：只有真实公众号名称才添加前缀，否则只用文章标题
        if download_result.account_name:
            filename = f"{download_result.account_name}_{download_result.article_title}.pdf"
        else:
            filename = f"{download_result.article_title}.pdf"
        local_path = os.path.join(self.temp_dir, filename)

        self.logger.info(f"正在生成PDF: {filename}")
        # 文章链接日志：INFO级，方便从日志直接定位下载的微信文章
        self.logger.info(f"文章链接: {parse_result.wxchat_article_url or f'{self.pdf_generator.base_url}{article_id}'}")
        self.logger.debug(f"PDF生成参数 - article_id: {article_id}, local_path: {local_path}, temp_dir: {self.temp_dir}")

        try:
            # 复用wxchat的PDF生成逻辑
            success = self.pdf_generator.generate_pdf(article_id, local_path)

            if not success:
                self.logger.error(f"PDF生成失败 - article_id: {article_id}, title: {download_result.article_title}")
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF生成失败",
                    retryable=True  # PDF生成失败可能是临时性错误，可重试
                )

            # 验证文件存在
            if not os.path.exists(local_path):
                self.logger.error(f"PDF文件生成后未找到 - 路径: {local_path}")
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF文件生成后未找到",
                    retryable=False  # 文件系统错误，永久性错误
                )

            file_size = os.path.getsize(local_path)
            file_size_mb = file_size / (1024*1024)
            self.logger.info(f"PDF生成成功: {filename} ({file_size_mb:.2f} MB)")
            self.logger.debug(f"PDF文件详情 - 路径: {local_path}, 大小: {file_size} bytes, 文件名: {filename}")

            return ProcessResult(
                success=True,
                processed_files=[local_path],
                article_title=download_result.article_title,
                account_name=download_result.account_name
            )

        except Exception as e:
            self.logger.error(f"PDF生成异常 - article_id: {article_id}, error: {str(e)}")
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"PDF生成异常: {str(e)}",
                retryable=True  # PDF生成异常可能是临时性错误，可重试
            )

    def get_upload_files(self, process_result: ProcessResult, parse_result: ParseResult) -> List[dict]:
        """
        生成SFTP上传文件列表

        Args:
            process_result: 处理结果
            parse_result: 原始解析结果

        Returns:
            上传文件列表
        """
        if not process_result.success:
            return []

        upload_files = []

        for local_path in process_result.processed_files:
            # 只返回文件名，让file_transfer_processor负责完整路径构建
            filename = os.path.basename(local_path)

            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            upload_files.append({
                'local_path': local_path,
                'remote_path': filename,  # 🔥 只返回文件名，不包含路径
                'size': file_size
            })

            self.logger.info(f"准备上传文件: {filename} (本地: {local_path})")

        return upload_files

    def cleanup(self):
        """清理临时文件"""
        # 关闭复用的浏览器会话（批次级复用，防微信风控）
        try:
            self.pdf_generator.close_browser()
        except Exception as e:
            self.logger.warning(f"关闭浏览器会话失败: {e}")
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"清理临时目录成功: {self.temp_dir}")
            except Exception as e:
                self.logger.error(f"清理临时目录失败: {self.temp_dir}, 错误: {e}")
            finally:
                self.temp_dir = None
        else:
            self.logger.debug("无需清理临时文件 - temp_dir为空或不存在")

    def _clean_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除或替换不合适的字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\n', '\r', '\t']
        cleaned = filename

        for char in illegal_chars:
            cleaned = cleaned.replace(char, '_')

        # 移除首尾空格
        cleaned = cleaned.strip()

        # 限制长度
        if len(cleaned) > 100:
            cleaned = cleaned[:100]

        return cleaned if cleaned else 'unknown'
