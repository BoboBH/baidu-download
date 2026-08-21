"""Unit tests for WxchatArticleProcessor"""
import pytest
from src.processor.parsers.wxchat_article_processor import WxchatArticleProcessor, DownloadResult, ProcessResult
from src.config.settings import Settings
from src.feishu.models import ParseResult


def test_filename_cleaning():
    """测试文件名清理功能"""
    settings = Settings()
    processor = WxchatArticleProcessor(settings)

    # 测试非法字符清理
    cleaned = processor._clean_filename('测试/文件:名称?"<>|*.pdf')
    assert '/' not in cleaned
    assert ':' not in cleaned
    assert cleaned.startswith('测试')

    # 测试长度限制
    long_name = 'a' * 150
    cleaned = processor._clean_filename(long_name)
    assert len(cleaned) <= 100

    # 测试空字符串处理
    cleaned = processor._clean_filename('')
    assert cleaned == 'unknown'


def test_processor_initialization():
    """测试处理器初始化"""
    settings = Settings()
    processor = WxchatArticleProcessor(settings)

    assert processor.can_process('wxchat-article') is True
    assert processor.can_process('baidupan') is False
    assert processor.pdf_generator is not None


def test_download_result_creation():
    """测试DownloadResult创建"""
    result = DownloadResult(success=True, article_title='Test', account_name='TestAccount')
    assert result.success is True
    assert result.article_title == 'Test'
    assert result.account_name == 'TestAccount'


def test_process_result_creation():
    """测试ProcessResult创建"""
    result = ProcessResult(success=True, processed_files=['/path/to/file.pdf'])
    assert result.success is True
    assert len(result.processed_files) == 1
