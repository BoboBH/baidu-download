"""
爬虫源（--crawler-wxchat）文章拉取过滤与统计单元测试

覆盖：
- 拉取时过滤已下载成功的文章（在拆分逻辑中排除，不再进入处理循环）
- 失败退避期内的文章暂不拉取
- ProcessResult 窗口统计：窗口总数 / 本次处理 / 跳过(已处理)
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from src.wxchat.models import ProcessResult
from src.wxchat.processor import WeChatArticleProcessor


def make_article(aid, processed_at=None, retry_count=0, updated_at=None, publish_date='2026-09-07'):
    """构造一条带状态列的爬虫源文章记录（模拟 _fetch_articles_from_crawler 查询结果）"""
    return {
        'id': aid,
        'dedup_key': f'url-{aid}',
        'url': f'https://mp.weixin.qq.com/s/{aid}',
        'title': f'文章{aid}',
        'publish_date': publish_date,
        'account_id': 1,
        'account_name': '测试号',
        's_processed_at': processed_at,
        's_retry_count': retry_count,
        's_updated_at': updated_at,
    }


class _StubConfig:
    """最小配置桩：仅提供 processor 初始化与循环延时所需字段"""
    wxchat_base_url = 'https://mp.weixin.qq.com/s/'
    wxchat_pdf_timeout = 1
    wxchat_image_wait_time = 1
    wxchat_download_delay = 0
    wxchat_download_delay_max = 0


def make_processor() -> WeChatArticleProcessor:
    return WeChatArticleProcessor(_StubConfig(), source='crawler')


def test_split_excludes_downloaded_success():
    """已成功下载（processed_at非空）的文章应被过滤，不再进入待处理列表"""
    processor = make_processor()
    rows = [
        make_article(1, processed_at=datetime(2026, 9, 6, 10, 0, 0)),  # 已成功 → 跳过
        make_article(2),                                               # 无状态 → 待处理
        make_article(3, processed_at=datetime(2026, 9, 7, 9, 0, 0)),   # 已成功 → 跳过
    ]

    pending, window_total = processor._split_pending_articles(rows)

    assert window_total == 3
    assert [a['id'] for a in pending] == [2]


def test_split_excludes_articles_without_publish_date():
    """无发布日期的文章应直接过滤，不进待处理列表也不计入窗口总数"""
    processor = make_processor()
    rows = [
        make_article(1, publish_date=None),    # 缺失 → 过滤
        make_article(2, publish_date=''),      # 空串 → 过滤
        make_article(3, publish_date='not-a-date'),  # 无法解析 → 过滤
        make_article(4),                       # 正常 → 待处理
    ]

    pending, window_total = processor._split_pending_articles(rows)

    assert window_total == 1  # 无日期文章不计入窗口总数
    assert [a['id'] for a in pending] == [4]


def test_split_respects_retry_backoff():
    """失败退避期内的文章暂不拉取，退避到期后重新进入待处理列表"""
    processor = make_processor()
    now = datetime.now()
    rows = [
        # 失败1次，25分钟前更新 → 退避20分钟已过 → 待处理
        make_article(1, retry_count=1, updated_at=now - timedelta(minutes=25)),
        # 失败3次，30分钟前更新 → 退避60分钟未到 → 暂不拉取
        make_article(2, retry_count=3, updated_at=now - timedelta(minutes=30)),
        # 失败5次，200分钟前更新 → 退避100分钟已过 → 待处理
        make_article(3, retry_count=5, updated_at=now - timedelta(minutes=200)),
    ]

    pending, window_total = processor._split_pending_articles(rows)

    assert window_total == 3
    assert [a['id'] for a in pending] == [1, 3]


def test_process_articles_stats_with_window():
    """统计应包含窗口总数与跳过(已处理)数：拉取2篇待处理、窗口共10篇 → 跳过8篇"""
    processor = make_processor()
    pending_rows = [make_article(8), make_article(9)]

    with patch.object(processor, '_fetch_articles_from_crawler',
                      return_value=(pending_rows, 10)) as mock_fetch, \
         patch.object(processor, '_is_article_processed', return_value=False), \
         patch.object(processor, '_process_single_article', return_value=True):
        result = processor.process_articles(days=3)

    mock_fetch.assert_called_once_with(3)
    assert isinstance(result, ProcessResult)
    assert result.window_total == 10
    assert result.skipped_articles == 8   # 已处理跳过 = 10 - 2
    assert result.total_articles == 2     # 本次拉取待处理
    assert result.processed_articles == 2
    assert result.failed_articles == 0


def test_process_result_has_window_total_default():
    """ProcessResult 默认 window_total=0，兼容 wewe 源（无窗口统计）"""
    result = ProcessResult()
    assert result.window_total == 0
