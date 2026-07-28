#!/usr/bin/env python
"""
简化的微信表分析脚本
"""
import sys
import pymysql

def main():
    # 连接数据库
    print("=== Connecting to Database ===")
    connection = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='baidu_download',
        charset='utf8mb4'
    )
    print("[OK] Connected successfully")

    cursor = connection.cursor()

    # 获取所有表
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\n=== Total Tables: {len(tables)} ===")

    # 显示所有表名
    for table in tables:
        print(f"  - {table[0]}")

    # 查找微信相关表
    print("\n=== Looking for WeChat Tables ===")
    wechat_tables = []
    for table in tables:
        table_name = table[0]
        if 'wx' in table_name.lower():
            wechat_tables.append(table_name)
            print(f"Found: {table_name}")

    if not wechat_tables:
        print("No WeChat tables found!")
        return

    # 分析每个微信表
    for table in wechat_tables:
        table_name = table[0]
        print(f"\n{'='*50}")
        print(f"Table: {table_name}")
        print(f"{'='*50}")

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
            print(f"  {field:20s} {type_info:20s} {null_info:8s}{key_marker} {default_info or 'NULL':10s}")

        # 记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nTotal records: {count}")

        # 获取最新的几条记录
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 2")
            rows = cursor.fetchall()

            print(f"\n=== Latest Records (showing 2) ===")
            for i, row in enumerate(rows, 1):
                print(f"\n--- Record {i} ---")
                # 显示字段名和值
                for j, col_info in enumerate(columns):
                    field_name = col_info[0]
                    value = row[j]
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 40:
                            value_str = value_str[:40] + "..."
                        print(f"  {field_name}: {value_str}")
                    else:
                        print(f"  {field_name}: NULL")

    cursor.close()
    connection.close()
    print("\n=== Analysis Completed ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()