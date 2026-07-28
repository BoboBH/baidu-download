#!/usr/bin/env python
"""
简化的wefe-rss数据库连接测试
"""
import pymysql

def test_connection():
    print("=" * 60)
    print("wefe-rss Database Connection Test")
    print("=" * 60)

    try:
        # 先测试基本连接
        print("1. Testing basic MySQL connection...")
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            charset='utf8mb4'
        )
        print("[OK] Basic MySQL connection successful")

        cursor = conn.cursor()

        # 查看所有数据库
        print("\n2. Available databases:")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        for db in databases:
            db_name = db[0]
            print(f"  - {db_name}")

        # 测试wefe_rss数据库
        print("\n3. Testing wefe_rss database...")
        try:
            cursor.execute("USE wefe_rss")
            print("[OK] Can USE wefe_rss database")

            # 查看表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"Tables in wefe_rss: {len(tables)}")

            for table in tables:
                table_name = table[0]
                print(f"  - {table_name}")

        except Exception as e:
            print(f"[ERROR] Cannot USE wefe_rss: {e}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
