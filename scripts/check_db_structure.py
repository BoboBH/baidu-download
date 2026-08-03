#!/usr/bin/env python3
"""
检查wewe_rss数据库结构
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.wxchat.processor import DatabaseConnection

def check_articles_structure():
    """检查articles表结构"""
    print("=" * 60)
    print("检查wewe_rss数据库articles表结构")
    print("=" * 60)

    try:
        config = Settings()

        with DatabaseConnection(config, use_wewe_db=True) as conn:
            with conn.cursor() as cursor:
                # 查看表结构
                cursor.execute("DESCRIBE articles")
                columns = cursor.fetchall()

                print("Articles表字段:")
                print(f"{'字段名':<20} {'类型':<20} {'NULL':<10} {'键':<10}")
                print("-" * 60)

                for col in columns:
                    field = col.get('Field', col.get('field', ''))
                    type_info = col.get('Type', col.get('type', ''))
                    null = col.get('Null', col.get('null', ''))
                    key = col.get('Key', col.get('key', ''))
                    print(f"{field:<20} {type_info:<20} {null:<10} {key:<10}")

                # 查看几条数据示例
                print("\n数据示例:")
                cursor.execute("SELECT id, mp_id, title, publish_time FROM articles LIMIT 3")
                samples = cursor.fetchall()

                for i, row in enumerate(samples, 1):
                    print(f"{i}. ID: {row.get('id')}")
                    print(f"   标题: {row.get('title')}")
                    print(f"   发布时间: {row.get('publish_time')}")
                    print()

        print("=" * 60)
        return True

    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_articles_structure()
