"""
Check and display current message_process_log table structure
"""
import pymysql
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings


def check_table_structure():
    """Check current table structure"""
    try:
        settings = Settings()

        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = connection.cursor()

        # Check if database exists
        cursor.execute("SHOW DATABASES LIKE 'baidu_download'")
        if not cursor.fetchone():
            print("Database 'baidu_download' does not exist.")
            cursor.close()
            connection.close()
            return False

        cursor.execute("USE baidu_download")

        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'baidu_download' AND TABLE_NAME = 'message_process_log'
        """)
        result = cursor.fetchone()

        if result['count'] == 0:
            print("Table 'message_process_log' does not exist in baidu_download database.")
            cursor.close()
            connection.close()
            return False

        # Get current table structure
        print("Current message_process_log table structure:")
        print("="*70)

        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'baidu_download' AND TABLE_NAME = 'message_process_log'
            ORDER BY ORDINAL_POSITION
        """)

        columns = cursor.fetchall()

        if not columns:
            print("No columns found!")
        else:
            for col in columns:
                default = col['COLUMN_DEFAULT'] if col['COLUMN_DEFAULT'] else 'NULL'
                print(f"  {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} (DEFAULT: {default}, NULL: {col['IS_NULLABLE']})")

        cursor.close()
        connection.close()
        return True

    except Exception as e:
        print(f"Error checking table structure: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    check_table_structure()
