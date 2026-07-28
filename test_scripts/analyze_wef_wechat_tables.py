#!/usr/bin/env python
"""
wefe-rss数据库微信表分析脚本
"""
import pymysql
import json

def main():
    # 连接到wefe_rss数据库
    print("=" * 60)
    print("wefe-rss Database WeChat Tables Analysis")
    print("=" * 60)

    connection = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='wewe_rss',
        charset='utf8mb4'
    )

    cursor = connection.cursor()

    # 获取所有表
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\nTotal tables: {len(tables)}")

    # 查找微信相关表
    print("\n=== Looking for WeChat Tables ===")
    wechat_tables = []
    for table in tables:
        table_name = table[0]
        if 'wx' in table_name.lower() or 'wechat' in table_name.lower() or 'account' in table_name.lower():
            wechat_tables.append(table_name)
            print(f"Found: {table_name}")

    if not wechat_tables:
        print("No WeChat tables found!")
        connection.close()
        return

    # 详细分析每个表
    for table in wechat_tables:
        table_name = table[0]
        print(f"\n{'='*60}")
        print(f"Analyzing Table: {table_name}")
        print(f"{'='*60}")

        # 表结构
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        print(f"\nColumns ({len(columns)}):")
        for col in columns:
            field = col[0]
            type_info = col[1]
            null_info = col[2]
            key_info = col[3]
            default_info = col[4]
            extra_info = col[5]

            key_marker = f" [{key_info}]" if key_info else ""
            print(f"  {field:25s} {type_info:25s} {null_info:8s}{key_marker} {default_info or 'NULL':15s}")

        # 记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nTotal Records: {count}")

        if count > 0:
            # 获取最新的记录
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 2")
            rows = cursor.fetchall()

            print(f"\n=== Latest 2 Records ===")
            for i, row in enumerate(rows, 1):
                print(f"\n--- Record {i} --- ID: {row[0]} ---")
                for j, col_info in enumerate(columns):
                    field_name = col_info[0]
                    value = row[j]
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        print(f"  {field_name:25s}: {value_str}")
                    else:
                        print(f"  {field_name:25s}: NULL")

    cursor.close()
    connection.close()

    print("\n" + "=" * 60)
    print("Analysis Completed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()