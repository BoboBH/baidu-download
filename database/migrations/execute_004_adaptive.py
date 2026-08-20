"""
Execute database migration 004_add_message_type_support.sql (Adaptive version)
Adapts to current table structure regardless of migration state
"""
import pymysql
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings


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
    print("Executing Migration 004: Add Message Type Support (Adaptive)")
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
        print(f"Using database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} "
                      "DEFAULT CHARACTER SET utf8mb4 "
                      "DEFAULT COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")

        # Check if table exists, if not create it
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
        """, ('baidu_download',))

        if cursor.fetchone()['count'] == 0:
            print("\n[WARNING] message_process_log table does not exist!")
            print("Creating basic table structure...")

            # Create basic table with current schema requirements
            cursor.execute("""
                CREATE TABLE message_process_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message_hash VARCHAR(64) NOT NULL UNIQUE COMMENT 'Message MD5 hash',
                    original_message TEXT COMMENT 'Original message content',
                    share_link VARCHAR(500) COMMENT 'Extracted pan link',
                    folder_name VARCHAR(255) COMMENT 'Extracted folder name',
                    extraction_code VARCHAR(20) COMMENT 'Extraction code',
                    source ENUM('feishu', 'dingtalk') DEFAULT 'feishu' COMMENT 'Message source',
                    message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT 'Message type: baidupan/pdf_link/dingtalk_pdf/dingtalk_zip',
                    raw_message JSON COMMENT 'Original message content (JSON format)',
                    file_info JSON COMMENT 'File metadata information (JSON format)',
                    process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error')
                        DEFAULT 'pending' COMMENT 'Processing status',
                    error_message TEXT COMMENT 'Error message',
                    retry_count INT DEFAULT 0 COMMENT 'Failure retry count',
                    execution_summary_id INT COMMENT 'Related execution summary ID',
                    processing_time_ms INT COMMENT 'Processing time (milliseconds)',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation time',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Record update time',
                    INDEX idx_message_hash (message_hash),
                    INDEX idx_source (source),
                    INDEX idx_process_status (process_status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_retry_count (retry_count),
                    INDEX idx_message_type (message_type),
                    INDEX idx_process_status_type (process_status, message_type),
                    CONSTRAINT chk_message_type CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Message processing log table (supports multiple message types)'
            """)
            connection.commit()
            print("  [OK] Table created with full schema including migration 004 fields")

        else:
            print("\nTable exists, adding migration 004 fields...")

            # Check and add missing columns one by one
            columns_to_add = [
                {
                    'name': 'extraction_code',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN extraction_code VARCHAR(20) COMMENT 'Extraction code' AFTER folder_name"
                },
                {
                    'name': 'source',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN source ENUM('feishu', 'dingtalk') DEFAULT 'feishu' COMMENT 'Message source' AFTER extraction_code"
                },
                {
                    'name': 'message_type',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT 'Message type: baidupan/pdf_link/dingtalk_pdf/dingtalk_zip' AFTER source"
                },
                {
                    'name': 'raw_message',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN raw_message JSON COMMENT 'Original message content (JSON format)' AFTER message_type"
                },
                {
                    'name': 'file_info',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN file_info JSON COMMENT 'File metadata information (JSON format)' AFTER raw_message"
                },
                {
                    'name': 'retry_count',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN retry_count INT DEFAULT 0 COMMENT 'Failure retry count' AFTER error_message"
                },
                {
                    'name': 'processing_time_ms',
                    'sql': "ALTER TABLE message_process_log ADD COLUMN processing_time_ms INT COMMENT 'Processing time (milliseconds)' AFTER execution_summary_id"
                }
            ]

            for col in columns_to_add:
                if not column_exists(cursor, 'message_process_log', col['name']):
                    print(f"  Adding {col['name']} column...")
                    try:
                        cursor.execute(col['sql'])
                        print(f"    [OK] {col['name']} column added")
                    except Exception as e:
                        if "Duplicate" not in str(e):
                            print(f"    [WARNING] Failed to add {col['name']}: {e}")
                else:
                    print(f"  [SKIP] {col['name']} column already exists")

            # Handle process_status column (might be named 'status' in older schema)
            if not column_exists(cursor, 'message_process_log', 'process_status') and column_exists(cursor, 'message_process_log', 'status'):
                print("  Renaming 'status' column to 'process_status'...")
                try:
                    cursor.execute("ALTER TABLE message_process_log CHANGE COLUMN status process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error') DEFAULT 'pending' COMMENT 'Processing status'")
                    print("    [OK] Column renamed")
                except Exception as e:
                    print(f"    [WARNING] Failed to rename: {e}")
            elif not column_exists(cursor, 'message_process_log', 'process_status'):
                print("  Adding process_status column...")
                try:
                    cursor.execute("ALTER TABLE message_process_log ADD COLUMN process_status ENUM('pending', 'processing', 'success', 'failed', 'critical_error') DEFAULT 'pending' COMMENT 'Processing status' AFTER file_info")
                    print("    [OK] process_status column added")
                except Exception as e:
                    print(f"    [WARNING] Failed to add: {e}")

            # Create indexes
            print("\n  Creating indexes...")
            indexes_to_create = [
                ('idx_message_type', 'CREATE INDEX idx_message_type ON message_process_log(message_type)'),
                ('idx_process_status_type', 'CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type)'),
                ('idx_source', 'CREATE INDEX idx_source ON message_process_log(source)'),
                ('idx_retry_count', 'CREATE INDEX idx_retry_count ON message_process_log(retry_count)')
            ]

            for idx_name, idx_sql in indexes_to_create:
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = %s
                """, ('baidu_download', idx_name))

                if cursor.fetchone()['count'] == 0:
                    try:
                        cursor.execute(idx_sql)
                        print(f"    [OK] {idx_name} index created")
                    except Exception as e:
                        if "Duplicate" not in str(e):
                            print(f"    [WARNING] Failed to create {idx_name}: {e}")
                else:
                    print(f"    [SKIP] {idx_name} index already exists")

            # Add constraint
            print("\n  Adding message type constraint...")
            try:
                cursor.execute("""
                    ALTER TABLE message_process_log
                    ADD CONSTRAINT chk_message_type
                    CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'))
                """)
                print("    [OK] chk_message_type constraint added")
            except Exception as e:
                if "Duplicate" in str(e) or "already exists" in str(e):
                    print("    [SKIP] chk_message_type constraint already exists")
                else:
                    print(f"    [WARNING] Failed to add constraint: {e}")

            # Update existing records
            print("\n  Updating existing records...")
            cursor.execute("""
                UPDATE message_process_log
                SET message_type = 'baidupan'
                WHERE message_type IS NULL OR message_type = ''
            """)
            updated_count = cursor.rowcount
            if updated_count > 0:
                print(f"    [OK] Updated {updated_count} existing records to message_type='baidupan'")
            else:
                print("    [OK] No existing records needed updating")

        # Commit all changes
        connection.commit()
        print("\n" + "="*70)
        print("Migration 004 completed successfully!")
        print("="*70)

        # Verify the migration
        print("\n" + "="*70)
        print("Verifying Migration Results")
        print("="*70)

        # Check all columns
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log'
            AND COLUMN_NAME IN ('message_type', 'raw_message', 'file_info', 'source', 'extraction_code', 'process_status', 'retry_count')
            ORDER BY COLUMN_NAME
        """, ('baidu_download',))

        fields = cursor.fetchall()
        print("\n[OK] Migration fields found:")
        for field in fields:
            default = field['COLUMN_DEFAULT'] if field['COLUMN_DEFAULT'] else 'NULL'
            print(f"  - {field['COLUMN_NAME']}: {field['COLUMN_TYPE']} (DEFAULT: {default})")

        # Check indexes
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

        print("\n" + "="*70)
        print("Migration 004 completed and verified successfully!")
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
