#!/usr/bin/env python
"""
检查所有数据库中的微信表
"""
import pymysql

def check_all_databases_for_wechat():
    print("=" * 60)
    print("Checking All Databases for WeChat Tables")
    print("=" * 60)

    try:
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            charset='utf8mb4'
        )
        print("[OK] Connected to MySQL")

        cursor = conn.cursor()

        # 获取所有数据库
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()

        print(f"\nSearching {len(databases)} databases for WeChat tables...\n")

        found_tables = {}

        for db_info in databases:
            db_name = db_info[0]
            if db_name in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                continue

            try:
                cursor.execute(f"USE {db_name}")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()

                # 查找微信相关表
                wx_tables = []
                for table in tables:
                    table_name = table[0]
                    if 'wx' in table_name.lower():
                        wx_tables.append(table_name)

                if wx_tables:
                    found_tables[db_name] = wx_tables
                    print(f"[OK] Found in {db_name}: {', '.join(wx_tables)}")

            except Exception as e:
                print(f"[SKIP] {db_name}: {e}")

        if found_tables:
            print(f"\n=== Summary ===")
            print("WeChat tables found in:")
            for db_name, tables in found_tables.items():
                print(f"  {db_name}: {', '.join(tables)}")
        else:
            print("[WARN] No WeChat tables found in any database")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    check_all_databases_for_wechat()
