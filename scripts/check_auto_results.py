#!/usr/bin/env python3
"""检查auto模式处理结果"""

import sys
import pymysql
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_results():
    """检查处理结果"""
    try:
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            database='test'
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        print("=" * 60)
        print("AUTO 模式处理结果统计")
        print("=" * 60)

        # 消息处理状态
        cursor.execute("SELECT process_status, COUNT(*) as count FROM message_process_log GROUP BY process_status")
        results = cursor.fetchall()
        print("\n消息处理状态:")
        for row in results:
            print(f"  {row['process_status']}: {row['count']}")

        # 文件传输状态
        cursor.execute("SELECT transfer_status, COUNT(*) as count FROM file_transfer_log GROUP BY transfer_status")
        results = cursor.fetchall()
        print("\n文件传输状态:")
        for row in results:
            print(f"  {row['transfer_status']}: {row['count']}")

        # 总文件数
        cursor.execute("SELECT COUNT(*) as total FROM file_transfer_log")
        total = cursor.fetchone()
        print(f"\n总计处理文件数: {total['total']}")

        # 最近的消息记录
        cursor.execute("SELECT folder_name, process_status, error_message, created_at FROM message_process_log ORDER BY created_at DESC LIMIT 1")
        msg = cursor.fetchone()
        if msg:
            print(f"\n最近处理的消息:")
            print(f"  文件夹: {msg['folder_name']}")
            print(f"  状态: {msg['process_status']}")
            print(f"  错误: {msg['error_message'] or 'None'}")
            print(f"  时间: {msg['created_at']}")

        # 成功传输的文件大小统计
        cursor.execute("SELECT SUM(file_size) as total_size, COUNT(*) as count FROM file_transfer_log WHERE transfer_status='success'")
        size_result = cursor.fetchone()
        if size_result and size_result['total_size']:
            total_mb = size_result['total_size'] / (1024 * 1024)
            print(f"\n成功传输文件统计:")
            print(f"  文件数: {size_result['count']}")
            print(f"  总大小: {total_mb:.2f} MB")

        conn.close()
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_results()