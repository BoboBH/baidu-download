#!/usr/bin/env python
"""
wefe-rss数据库完整表分析
"""
import pymysql

def main():
    print("=" * 60)
    print("wefe-rss Database Complete Analysis")
    print("=" * 60)

    connection = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='wefe_rss',
        charset='utf8mb4'
    )

    cursor = connection.cursor()

    # 获取所有表
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\n=== All Tables in wefe_rss Database ===")
    for i, table in enumerate(tables, 1):
        table_name = table[0]
        print(f"{i}. {table_name}")

    print(f"\n{'='*60}")
    print("Detailed Table Analysis")
    print(f"{'='*60}")

    # 分析每个表
    for table_info in tables:
        table_name = table_info[0]

        print(f"\n### Table: {table_name} ###")

        # 表结构
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        print(f"\nStructure ({len(columns)} columns):")
        for col in columns:
            field = col[0]
            type_info = col[1]
            null_info = col[2]
            key_info = col[3]
            default_info = col[4]
            extra_info = col[5]

            key_marker = f" [{key_info}]" if key_info else ""
            print(f"  {field:20s} {type_info:25s} {null_info:8s}{key_marker} {default_info or 'NULL':10s} {extra_info or ''}")

        # 记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nRecords: {count}")

        # 如果有数据，显示样本
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                print(f"\nSample Record:")
                for i, col_info in enumerate(columns):
                    field_name = col_info[0]
                    value = row[i]
                    if value is not None:
                        value_str = str(value)
                        if len(value_str) > 30:
                            value_str = value_str[:30] + "..."
                        print(f"  {field_name:20s}: {value_str}")

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
