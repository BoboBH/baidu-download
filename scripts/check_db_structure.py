#!/usr/bin/env python3
"""检查数据库表结构"""

import sys
import pymysql
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_database_structure():
    """检查数据库表结构"""
    try:
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            database='test'
        )
        cursor = conn.cursor()

        # 检查 message_process_log 表结构
        print("Current message_process_log table structure:")
        print("=" * 80)
        cursor.execute("DESCRIBE message_process_log")
        columns = cursor.fetchall()

        for col in columns:
            field = col[0]
            type_info = col[1]
            null = col[2]
            key = col[3]
            default = col[4]
            extra = col[5]
            print(f"{field:<25} {type_info:<20} NULL={null} Key={key}")

        print("\n" + "=" * 80)
        print("Expected fields (from code):")
        print("-" * 80)
        expected_fields = [
            "id", "message_hash", "folder_name", "share_link", "extraction_code",
            "original_message", "process_status", "error_message", "retry_count",
            "processed_file_count", "processing_time_ms", "feishu_message_time",
            "start_time", "end_time", "created_at", "updated_at"
        ]
        for field in expected_fields:
            print(f"  - {field}")

        conn.close()
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_database_structure()