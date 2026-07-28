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
