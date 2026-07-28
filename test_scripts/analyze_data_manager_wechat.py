#!/usr/bin/bin python
"""
data_manager数据库微信表详细分析
"""
import pymysql
from datetime import datetime

def analyze_data_manager_wechat():
    print("=" * 60)
    print("data_manager WeChat Tables Analysis")
    print("=" * 60)

    connection = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='data_manager',
        charset='utf8mb4'
    )

    cursor = connection.cursor()

    # 分析wx_account表
    print("\n" + "="*60)
    print("### wx_account Table Analysis ###")
    print("="*60)

    cursor.execute("DESCRIBE wx_account")
    account_columns = cursor.fetchall()

    print(f"\nwx_account Structure ({len(account_columns)} columns):")
    for col in account_columns:
        field = col[0]
        type_info = col[1]
        null_info = col[2]
        key_info = col[3]
        default_info = col[4] extra_info or ''
        print(f"  {field:20s} {type_info:25s} {null_info:8s} [{key_info}] {default_info}")

    cursor.execute("SELECT COUNT(*) FROM wx_account")
    account_count = cursor.fetchone()[0]
    print(f"\nTotal Accounts: {account_count}")

    if account_count > 0:
        cursor.execute("SELECT * FROM wx_account ORDER BY id DESC LIMIT 3")
        accounts = cursor.fetchall()
        print(f"\nLatest {len(accounts)} accounts:")
        for i, acc in enumerate(accounts, 1):
            print(f"\n--- Account #{i} ---")
            for j, col in enumerate(account_columns):
                field_name = col[0]
                value = acc[j]
                if value is not None:
                    value_str = str(value)
                    if len(value_str) > 40:
                        value_str = value_str[:40] + "..."
                    print(f"  {field_name:20s}: {value_str}")

    # 分析wx_article表
    print("\n" + "="*60)
    print("### wx_article Table Analysis ###")
    print("="*60)

    cursor.execute("DESCRIBE wx_article")
    article_columns = cursor.fetchall()

    print(f"\nwx_article Structure ({len(article_columns)} columns):")
    for col in article_columns:
        field = col[0]
        type_info = col[1]
        null_info = col[2]
        key_info = col[3]
        default_info = col[4] extra_info or ''
        print(f"  {field:20s} {type_info:25s} {null_info:8s} [{key_info}] {default_info}")

    cursor.execute("SELECT COUNT(*) FROM wx_article")
    article_count = cursor.fetchone()[0]
    print(f"\nTotal Articles: {article_count}")

    if article_count > 0:
        cursor.execute("SELECT * FROM wx_article ORDER BY id DESC LIMIT 3")
        articles = cursor.fetchall()
        print(f"\nLatest {len(articles)} articles:")
        for i, art in enumerate(articles, 1):
            print(f"\n--- Article #{i} ---")
            print(f"  Article ID: {art[0]}")

            # 显示关键字段
            key_fields = ['title', 'author', 'url', 'publish_time', 'crawl_time', 'source', 'pdf_path', 'pdf_url']
            for field in key_fields:
                if field in article_columns[0]:
                    field_idx = article_columns[0].index(field)
                    value = art[field_idx]
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        print(f"  {field:20s}: {value_str}")

            # 显示content字段的部分内容
            if 'content' in article_columns[0]:
                content_idx = article_columns[0].index('content')
                content = art[content_idx]
                if content:
                    content_str = str(content)
                    if len(content_str) > 80:
                        content_str = content_str[:80] + "..."
                    print(f"  content: {content_str}")

    cursor.close()
    connection.close()

    print("\n" + "="*60)
    print("Analysis Completed!")
    print("="*60)

if __name__ == "__main__":
    try:
        analyze_data_manager_wechat()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
