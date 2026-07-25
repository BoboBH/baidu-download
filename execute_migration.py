"""
执行数据库迁移脚本 - 添加 source 字段
"""
import pymysql
from pymysql import Error
from src.config.settings import Settings
from dotenv import load_dotenv
import sys

load_dotenv()
settings = Settings()

def check_column_exists(cursor, table_name, column_name):
    """检查字段是否存在"""
    try:
        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND COLUMN_NAME = %s
        """
        cursor.execute(query, (settings.db_name, table_name, column_name))
        result = cursor.fetchone()
        return result is not None
    except Error as e:
        print(f"Error checking column: {e}")
        return False

def add_source_column(cursor):
    """添加 source 字段"""
    try:
        alter_query = """
        ALTER TABLE message_process_log
        ADD COLUMN source ENUM('feishu', 'dingtalk')
        DEFAULT 'feishu'
        COMMENT '消息来源（飞书/钉钉）'
        """
        cursor.execute(alter_query)
        print("SUCCESS: Added source column to message_process_log table")
        return True
    except Error as e:
        if e.errno == 1060:  # Duplicate column name
            print("INFO: source column already exists")
            return True
        else:
            print(f"ERROR adding column: {e}")
            return False

def create_source_index(cursor):
    """创建索引"""
    try:
        create_index_query = """
        CREATE INDEX idx_source ON message_process_log(source)
        """
        cursor.execute(create_index_query)
        print("SUCCESS: Created idx_source index")
        return True
    except Error as e:
        if e.errno == 1061:  # Duplicate index name
            print("INFO: idx_source index already exists")
            return True
        else:
            print(f"ERROR creating index: {e}")
            return False

def verify_migration(cursor):
    """验证迁移结果"""
    try:
        # 检查字段
        query = """
        SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = 'message_process_log'
        AND COLUMN_NAME = 'source'
        """
        cursor.execute(query, (settings.db_name,))
        result = cursor.fetchone()

        if result:
            print("VERIFICATION: Source column details:")
            print(f"  Name: {result[0]}")
            print(f"  Type: {result[1]}")
            print(f"  Default: {result[2]}")
            print(f"  Comment: {result[3]}")
        else:
            print("WARNING: Source column not found in verification")
            return False

        # 检查现有数据兼容性
        count_query = """
        SELECT COUNT(*) as total, source, process_status
        FROM message_process_log
        GROUP BY source, process_status
        ORDER BY source, process_status
        """
        cursor.execute(count_query)
        stats = cursor.fetchall()

        print("DATA COMPATIBILITY CHECK:")
        print("  Source | Process Status | Count")
        print("  -------|----------------|-------")
        for row in stats:
            print(f"  {row[1]:7s} | {row[2]:14s} | {row[0]}")

        return True

    except Error as e:
        print(f"ERROR during verification: {e}")
        return False

def main():
    """主函数"""
    print("=== Database Migration: Add Source Field ===")
    print(f"Database: {settings.db_name}@{settings.db_host}:{settings.db_port}")
    print()

    try:
        # 连接数据库
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset='utf8mb4'
        )

        if connection.open:
            cursor = connection.cursor()

            # 检查字段是否存在
            print("STEP 1: Check if source column exists")
            if check_column_exists(cursor, 'message_process_log', 'source'):
                print("INFO: source column already exists, skipping creation")
            else:
                print("INFO: source column does not exist, will add it")

            # 添加字段
            print("\nSTEP 2: Add source column")
            if not add_source_column(cursor):
                print("ERROR: Failed to add source column")
                sys.exit(1)

            # 创建索引
            print("\nSTEP 3: Create index")
            if not create_source_index(cursor):
                print("ERROR: Failed to create index")
                sys.exit(1)

            # 提交更改
            connection.commit()
            print("\nSTEP 4: Changes committed to database")

            # 验证迁移
            print("\nSTEP 5: Verify migration")
            if not verify_migration(cursor):
                print("WARNING: Verification failed, but changes were committed")

            cursor.close()
            connection.close()

            print("\n=== Migration completed successfully ===")

    except Error as e:
        print(f"ERROR: Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()