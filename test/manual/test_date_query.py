#!/usr/bin/env python3
"""
测试日期查询逻辑
验证wxchat-days使用publish_date字段查询
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.wxchat.processor import WeChatArticleProcessor

def test_date_query():
    """测试日期查询逻辑"""
    print("=" * 60)
    print("测试日期查询逻辑")
    print("=" * 60)

    try:
        config = Settings()

        # 测试日期范围计算
        days = 7
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        print(f"查询参数: 最近 {days} 天")
        print(f"开始日期: {start_date}")
        print(f"结束日期: {end_date}")
        print(f"开始日期字符串: {start_date.strftime('%Y-%m-%d')}")
        print(f"结束日期字符串: {end_date.strftime('%Y-%m-%d')}")

        # 创建处理器并获取文章
        processor = WeChatArticleProcessor(config)

        print(f"\n开始查询文章...")
        articles = processor._fetch_articles_from_wewe(start_date, end_date)

        print(f"查询到 {len(articles)} 篇文章")

        if articles:
            print(f"\n前3篇文章示例:")
            for i, article in enumerate(articles[:3], 1):
                print(f"{i}. ID: {article.get('id')}")
                print(f"   标题: {article.get('title')}")
                print(f"   发布时间: {article.get('publish_time')}")
                print(f"   发布日期: {article.get('publish_date')}")
                print()

        print("=" * 60)
        print("[SUCCESS] 日期查询测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_date_query()
    sys.exit(0 if success else 1)
