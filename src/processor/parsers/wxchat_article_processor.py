"""
微信文章链接处理器

处理微信文章链接的PDF生成和SFTP上传。
复用wxchat的PDFGenerator核心代码。
"""
import os
import tempfile
import requests
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup

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


class WxchatArticleProcessor:
    """微信文章链接处理器"""

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

    def can_process(self, message_type: str) -> bool:
        """检查是否支持该消息类型"""
        return message_type == 'wxchat-article'

    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        从微信文章页面提取元数据

        Args:
            parse_result: 解析结果

        Returns:
            DownloadResult包含文章标题和公众号名称
        """
        if not parse_result.wxchat_article_url:
            return DownloadResult(
                success=False,
                error="微信文章URL为空"
            )

        article_url = parse_result.wxchat_article_url
        self.logger.info(f"正在获取微信文章信息: {article_url}")

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
                return DownloadResult(
                    success=False,
                    error="无法从页面提取文章标题"
                )

            # 清理文件名
            article_title = self._clean_filename(article_title)
            account_name = self._clean_filename(account_name) if account_name else '未知公众号'

            self.logger.info(f"文章信息获取成功 - 标题: {article_title}, 公众号: {account_name}")

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
        if not download_result.success:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=download_result.error
            )

        article_id = parse_result.wxchat_article_id
        if not article_id:
            return ProcessResult(
                success=False,
                processed_files=[],
                error="文章ID为空"
            )

        # 生成PDF文件名
        filename = f"{download_result.account_name}_{download_result.article_title}.pdf"
        local_path = os.path.join(self.temp_dir, filename)

        self.logger.info(f"正在生成PDF: {filename}")

        try:
            # 复用wxchat的PDF生成逻辑
            success = self.pdf_generator.generate_pdf(article_id, local_path)

            if not success:
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF生成失败"
                )

            # 验证文件存在
            if not os.path.exists(local_path):
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF文件生成后未找到"
                )

            file_size = os.path.getsize(local_path)
            self.logger.info(f"PDF生成成功: {filename} ({file_size / (1024*1024):.2f} MB)")

            return ProcessResult(
                success=True,
                processed_files=[local_path],
                article_title=download_result.article_title,
                account_name=download_result.account_name
            )

        except Exception as e:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"PDF生成异常: {str(e)}"
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
            # 生成与wxchat一致的路径结构
            filename = os.path.basename(local_path)
            year_month = datetime.now().strftime('%Y%m')

            # 路径: /wxchat/YYYYMM/公众号_文章标题.pdf
            remote_path = f"{self.settings.wxchat_sftp_remote_path}/{year_month}/{filename}"

            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            upload_files.append({
                'local_path': local_path,
                'remote_path': remote_path,
                'size': file_size
            })

            self.logger.info(f"准备上传文件: {local_path} -> {remote_path}")

        return upload_files

    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"清理临时目录失败: {self.temp_dir}, 错误: {e}")
            finally:
                self.temp_dir = None

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
