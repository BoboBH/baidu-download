"""
Execute database migration 004_add_message_type_support.sql
"""
import pymysql
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings


def execute_migration():
    """Execute the migration script"""
    print("="*70)
    print("Executing Migration 004: Add Message Type Support")
    print("="*70)

    try:
        # Load settings
        settings = Settings()

        # Connect to MySQL (without database first)
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

        # Use baidu_download database (migration script is specific to this database)
        db_name = 'baidu_download'
        print(f"Ensuring database '{db_name}' exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} "
                      "DEFAULT CHARACTER SET utf8mb4 "
                      "DEFAULT COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")

        # Read migration script
        migration_path = os.path.join(
            os.path.dirname(__file__),
            '004_add_message_type_support.sql'
        )

        print(f"Reading migration script: {migration_path}")
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        # Split and execute SQL statements
        print("\nExecuting migration statements...")

        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

        for i, statement in enumerate(statements, 1):
            if statement and not statement.startswith('--'):
                try:
                    # Skip comments and empty lines
                    if statement.strip().startswith('/*') or statement.strip().startswith('--'):
                        continue

                    cursor.execute(statement)
                    print(f"  [{i}] Executed: {statement[:60]}...")
                except Exception as e:
                    print(f"  [{i}] Warning: {e}")
                    # Continue execution for non-critical errors
                    if 'Duplicate column' in str(e) or 'Duplicate index' in str(e) or 'Duplicate key' in str(e):
                        print(f"       (Ignoring - likely already exists)")
                    else:
                        raise

        # Commit all changes
        connection.commit()
        print("\n[OK] Migration executed successfully!")

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
        cursor.execute("""
            SELECT CONSTRAINT_NAME, CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME = 'chk_message_type'
        """, ('baidu_download',))

        constraint = cursor.fetchone()
        if constraint:
            print(f"\n[OK] Constraint found: {constraint['CONSTRAINT_NAME']}")
            print(f"  {constraint['CHECK_CLAUSE']}")

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
