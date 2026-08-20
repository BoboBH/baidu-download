"""
Execute database migration 004_add_message_type_support.sql (Robust version)
"""
import pymysql
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings


def table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """, ('baidu_download', table_name))
    result = cursor.fetchone()
    return result['count'] > 0


def column_exists(cursor, table_name, column_name):
    """Check if column exists in table"""
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, ('baidu_download', table_name, column_name))
    result = cursor.fetchone()
    return result['count'] > 0


def execute_migration():
    """Execute the migration script"""
    print("="*70)
    print("Executing Migration 004: Add Message Type Support (Robust)")
    print("="*70)

    try:
        # Load settings
        settings = Settings()

        # Connect to MySQL
        print(f"\nConnecting to MySQL at {settings.db_host}:{settings.db_port}...")

        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = connection.cursor()

        # Ensure database exists
        db_name = 'baidu_download'
        print(f"Ensuring database '{db_name}' exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} "
                      "DEFAULT CHARACTER SET utf8mb4 "
                      "DEFAULT COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")

        # Check if table exists
        if not table_exists(cursor, 'message_process_log'):
            print("\n[WARNING] message_process_log table does not exist!")
            print("Creating table structure first...")

            # Create the table using the model definition
            from src.database.models import create_tables
            sql_commands = create_tables(db_name).split(';')
            for command in sql_commands:
                command = command.strip()
                if command and not command.startswith('--'):
                    try:
                        cursor.execute(command)
                    except Exception as e:
                        if "Duplicate" not in str(e):
                            print(f"  Warning: {e}")
            connection.commit()
            print("Table structure created.")

        # Add message_type column if it doesn't exist
        if not column_exists(cursor, 'message_process_log', 'message_type'):
            print("\n[1/4] Adding message_type column...")
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan'
                COMMENT 'Message type: baidupan/pdf_link/dingtalk_pdf/dingtalk_zip'
                AFTER source
            """)
            print("  [OK] message_type column added")
        else:
            print("\n[1/4] message_type column already exists, skipping...")

        # Add raw_message column if it doesn't exist
        if not column_exists(cursor, 'message_process_log', 'raw_message'):
            print("\n[2/4] Adding raw_message column...")
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN raw_message JSON
                COMMENT 'Original message content (JSON format)'
                AFTER message_type
            """)
            print("  [OK] raw_message column added")
        else:
            print("\n[2/4] raw_message column already exists, skipping...")

        # Add file_info column if it doesn't exist
        if not column_exists(cursor, 'message_process_log', 'file_info'):
            print("\n[3/4] Adding file_info column...")
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN file_info JSON
                COMMENT 'File metadata information (JSON format)'
                AFTER raw_message
            """)
            print("  [OK] file_info column added")
        else:
            print("\n[3/4] file_info column already exists, skipping...")

        # Create indexes
        print("\n[4/4] Creating indexes...")

        # Check and create idx_message_type
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
            AND INDEX_NAME = 'idx_message_type'
        """, ('baidu_download',))
        if cursor.fetchone()['count'] == 0:
            cursor.execute("""
                CREATE INDEX idx_message_type ON message_process_log(message_type)
            """)
            print("  [OK] idx_message_type index created")
        else:
            print("  [SKIP] idx_message_type index already exists")

        # Check and create idx_process_status_type
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
            AND INDEX_NAME = 'idx_process_status_type'
        """, ('baidu_download',))
        if cursor.fetchone()['count'] == 0:
            cursor.execute("""
                CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type)
            """)
            print("  [OK] idx_process_status_type index created")
        else:
            print("  [SKIP] idx_process_status_type index already exists")

        # Add constraint if it doesn't exist
        print("\n[5/5] Adding message type constraint...")
        try:
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD CONSTRAINT chk_message_type
                CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'))
            """)
            print("  [OK] chk_message_type constraint added")
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e):
                print("  [SKIP] chk_message_type constraint already exists")
            else:
                raise

        # Update existing records
        print("\n[6/6] Updating existing records...")
        cursor.execute("""
            UPDATE message_process_log
            SET message_type = 'baidupan'
            WHERE message_type IS NULL OR message_type = ''
        """)
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"  [OK] Updated {updated_count} existing records")
        else:
            print("  [OK] No existing records needed updating")

        # Commit all changes
        connection.commit()
        print("\n" + "="*70)
        print("Migration 004 completed successfully!")
        print("="*70)

        # Verify the migration
        print("\n" + "="*70)
        print("Verifying Migration Results")
        print("="*70)

        # Check new fields
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
            AND COLUMN_NAME IN ('message_type', 'raw_message', 'file_info')
            ORDER BY COLUMN_NAME
        """, ('baidu_download',))

        fields = cursor.fetchall()
        print("\n[OK] New fields found:")
        for field in fields:
            print(f"  - {field['COLUMN_NAME']}: {field['COLUMN_TYPE']} (DEFAULT: {field['COLUMN_DEFAULT']})")

        # Check new indexes
        cursor.execute("""
            SELECT INDEX_NAME, COLUMN_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
            AND INDEX_NAME IN ('idx_message_type', 'idx_process_status_type')
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """, ('baidu_download',))

        indexes = cursor.fetchall()
        print("\n[OK] New indexes found:")
        for idx in indexes:
            print(f"  - {idx['INDEX_NAME']} on {idx['COLUMN_NAME']}")

        # Check constraint
        try:
            cursor.execute("""
                SELECT CONSTRAINT_NAME, CHECK_CLAUSE
                FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME = 'chk_message_type'
            """, ('baidu_download',))

            constraint = cursor.fetchone()
            if constraint:
                print(f"\n[OK] Constraint found: {constraint['CONSTRAINT_NAME']}")
                print(f"  {constraint['CHECK_CLAUSE']}")
        except Exception as e:
            print(f"\n[WARNING] Could not verify constraint: {e}")

        # Check existing data
        cursor.execute("""
            SELECT message_type, process_status, COUNT(*) as count
            FROM message_process_log
            GROUP BY message_type, process_status
            ORDER BY message_type, process_status
        """)
        data_stats = cursor.fetchall()

        if data_stats:
            print(f"\n[OK] Existing data compatibility:")
            for stat in data_stats:
                print(f"  - {stat['message_type']}/{stat['process_status']}: {stat['count']} records")
        else:
            print(f"\n[OK] No existing data found")

        print("\n" + "="*70)
        print("Migration 004 completed successfully!")
        print("="*70)

        cursor.close()
        connection.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = execute_migration()
    sys.exit(0 if success else 1)
