"""
wefe-rss 数据库分析脚本
分析表结构并获取文章数据
"""
import pymysql
from datetime import datetime
import json

class WefRssDatabaseAnalyzer:
    """wefe-rss数据库分析器"""

    def __init__(self, host='localhost', database='wefe_rss', port=3306, username='root', password='123456'):
        self.host = host
        self.database = database
        self.port = port
        self.username = username
        self.password = password
        self.connection = None

    def connect(self):
        """连接数据库"""
        try:
            print(f"=== Connecting to wewe-rss Database ===")
            print(f"Host: {self.host}")
            print(f"Port: {self.port}")
            print(f"Database: {self.database}")
            print(f"User: {self.username}")

            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
                charset='utf8mb4'
            )
            print("[OK] Database connection successful!")
            return True

        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False

    def show_all_tables(self):
        """显示所有表"""
        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print(f"\n=== All Tables in {self.database} ===")
        print(f"Total tables: {len(tables)}")
        for table in tables:
            table_name = list(table.values())[0]
            print(f"  - {table_name}")

        cursor.close()
        return tables

    def analyze_table_structure(self, table_name):
        """分析表结构"""
        cursor = self.connection.cursor()

        print(f"\n=== Table: {table_name} ===")

        # 获取表结构
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        print(f"Columns ({len(columns)}):")
        for col in columns:
            field = col['Field']
            type_info = col['Type']
            null_info = col['Null']
            key_info = col['Key']
            default_info = col['Default']
            extra_info = col['Extra']

            key_marker = f" [{key_info}]" if key_info else ""
            print(f"  {field:20s} {type_info:20s} {null_info:8s}{key_marker} {default_info or '':10s} {extra_info or ''}")

        cursor.close()

    def get_table_count(self, table_name):
        """获取表记录数"""
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        result = cursor.fetchone()
        count = result['count']
        cursor.close()
        return count

    def find_account_tables(self):
        """查找account相关表"""
        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print("\n=== Looking for Account/Article Tables ===")

        account_tables = []
        article_tables = []

        for table in tables:
            table_name = list(table.values())[0]
            if 'account' in table_name.lower():
                account_tables.append(table_name)
            if 'article' in table_name.lower():
                article_tables.append(table_name)

        if account_tables:
            print(f"Account tables found: {account_tables}")
        else:
            print("No account tables found")

        if article_tables:
            print(f"Article tables found: {article_tables}")
        else:
            print("No article tables found")

        cursor.close()
        return account_tables, article_tables

    def get_sample_data(self, table_name, limit=5):
        """获取表的样本数据"""
        cursor = self.connection.cursor()

        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            results = cursor.fetchall()

            print(f"\n=== Sample Data from {table_name} ({len(results)} rows) ===")

            for row in results:
                print(f"Row {cursor.rownumber}:")
                for key, value in row.items():
                    # 截断过长的值
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:50] + "..."
                    print(f"  {key}: {value_str}")
                print()

            return results

        except Exception as e:
            print(f"[ERROR] Failed to get sample data: {e}")
            return []

        finally:
            cursor.close()

    def find_latest_articles(self, article_table):
        """查找最新的文章"""
        cursor = self.connection.cursor()

        try:
            # 先查看表结构，确定时间字段
            cursor.execute(f"DESCRIBE {article_table}")
            columns = cursor.fetchall()

            # 查找可能的时间字段
            time_fields = ['publish_time', 'created_at', 'updated_at', 'crawl_time', 'post_date']
            time_field = None
            for col in columns:
                if col['Field'] in time_fields:
                    time_field = col['Field']
                    break

            if time_field:
                print(f"[INFO] Using time field: {time_field}")
                query = f"SELECT * FROM {article_table} ORDER BY {time_field} DESC LIMIT 3"
            else:
                print("[WARN] No time field found, using ID")
                query = f"SELECT * FROM {article_table} ORDER BY id DESC LIMIT 3"

            cursor.execute(query)
            results = cursor.fetchall()

            print(f"\n=== Latest Articles from {article_table} ===")
            print(f"Found {len(results)} recent articles:")

            for i, row in enumerate(results, 1):
                print(f"\nArticle #{i}:")
                print(f"  ID: {row.get('id', 'N/A')}")

                # 根据表结构显示关键信息
                if 'title' in row:
                    print(f"  Title: {row['title']}")
                if 'url' in row:
                    print(f"  URL: {row['url']}")
                if 'author' in row:
                    print(f"  Author: {row['author']}")
                if 'source' in row:
                    print(f"  Source: {row['source']}")
                if 'publish_time' in row:
                    print(f"  Publish Time: {row['publish_time']}")
                if 'created_at' in row:
                    print(f"  Created At: {row['created_at']}")
                if 'pdf_url' in row:
                    print(f"  PDF URL: {row.get('pdf_url', 'Not generated')}")
                if 'pdf_path' in row:
                    print(f"  PDF Path: {row.get('pdf_path', 'Not generated')}")

            return results

        except Exception as e:
            print(f"[ERROR] Failed to get latest articles: {e}")
            return []

        finally:
            cursor.close()

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("\n[OK] Database connection closed")

def main():
    """主分析函数"""
    print("=" * 60)
    print("wefe-rss Database Analysis")
    print("=" * 60)

    # 创建分析器
    analyzer = WefRssDatabaseAnalyzer(
        host='localhost',
        database='wefe_rss',
        port=3306,
        username='root',
        password='123456'
    )

    try:
        # 连接数据库
        if not analyzer.connect():
            print("\n[FATAL] Cannot connect to database, exiting...")
            return

        # 显示所有表
        all_tables = analyzer.show_all_tables()

        # 查找account和article表
        account_tables, article_tables = analyzer.find_account_tables()

        # 分析account表结构
        for table in account_tables:
            count = analyzer.get_table_count(table)
            print(f"  Total records: {count}")
            analyzer.analyze_table_structure(table)
            analyzer.get_sample_data(table, limit=2)

        # 分析article表结构
        for table in article_tables:
            count = analyzer.get_table_count(table)
            print(f"  Total records: {count}")
            analyzer.analyze_table_structure(table)
            analyzer.get_sample_data(table, limit=2)

            # 获取最新文章
            analyzer.find_latest_articles(table)

    finally:
        analyzer.close()

    print("\n" + "=" * 60)
    print("Analysis Completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
