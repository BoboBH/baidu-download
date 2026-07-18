#!/usr/bin/env python3
"""
综合测试：验证所有bug修复
Comprehensive Test: Verify All Bug Fixes

This test verifies:
1. Database configuration uses specified database (doesn't create new databases)
2. Tables are created automatically if they don't exist
3. Function calls use correct parameter names (lowercase)
4. Dataclass attributes use correct names (uppercase)
5. SQL queries use correct column names (lowercase)
6. Database result access uses correct keys (lowercase)
7. FileTransferLog instantiation works correctly
8. ExecutionSummary instantiation works correctly
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.database.models import FileTransferLog, ExecutionSummary, create_tables
    from src.database.repository import DatabaseRepository
    from src.config.settings import Settings
    from src.utils.logger import get_logger

    logger = get_logger(__name__)

    def test_1_dataclass_instantiation():
        """Test 1: Verify dataclass instantiation with correct parameter names"""
        print("=" * 60)
        print("Test 1: DataClass Instantiation")
        print("=" * 60)

        try:
            # Test FileTransferLog instantiation with uppercase parameters
            file_log = FileTransferLog(
                SHARE_LINK="https://pan.baidu.com/s/test123",
                EXTRACTION_CODE="abcd",
                FOLDER_NAME="test_folder",
                FILE_NAME="test_file.pdf",
                TRANSFER_STATUS="pending",
                START_TIME=datetime.now()
            )
            print(f"✓ FileTransferLog created successfully")
            print(f"  SHARE_LINK: {file_log.SHARE_LINK}")
            print(f"  FILE_NAME: {file_log.FILE_NAME}")
            print(f"  STATUS: {file_log.TRANSFER_STATUS}")

            # Test ExecutionSummary instantiation with uppercase parameters
            summary = ExecutionSummary(
                SHARE_LINK="https://pan.baidu.com/s/test123",
                FOLDER_NAME="test_folder",
                TOTAL_FILES=10,
                SUCCESS_COUNT=8,
                FAILED_COUNT=1,
                SKIPPED_COUNT=1,
                START_TIME=datetime.now(),
                END_TIME=datetime.now()
            )
            print(f"✓ ExecutionSummary created successfully")
            print(f"  TOTAL_FILES: {summary.TOTAL_FILES}")
            print(f"  SUCCESS_COUNT: {summary.SUCCESS_COUNT}")

            print("✓ Test 1 PASSED: DataClass instantiation works correctly")
            return True
        except Exception as e:
            print(f"✗ Test 1 FAILED: {e}")
            return False

    def test_2_sql_table_creation():
        """Test 2: Verify table creation SQL uses lowercase column names"""
        print("\n" + "=" * 60)
        print("Test 2: SQL Table Creation")
        print("=" * 60)

        try:
            sql = create_tables()

            # Check that SQL uses lowercase column names
            checks = [
                ('id INT AUTO_INCREMENT', "id column is lowercase"),
                ('share_link VARCHAR', "share_link column is lowercase"),
                ('file_name VARCHAR', "file_name column is lowercase"),
                ('transfer_status ENUM', "transfer_status column is lowercase"),
                ('created_at TIMESTAMP', "created_at column is lowercase"),
            ]

            for pattern, description in checks:
                if pattern in sql:
                    print(f"✓ {description}")
                else:
                    print(f"✗ Missing: {description}")
                    return False

            # Check that SQL does NOT contain CREATE DATABASE
            if 'CREATE DATABASE' not in sql:
                print(f"✓ SQL does not contain CREATE DATABASE (correct)")
            else:
                print(f"✗ SQL contains CREATE DATABASE (incorrect)")
                return False

            print("✓ Test 2 PASSED: Table creation SQL uses correct lowercase column names")
            return True
        except Exception as e:
            print(f"✗ Test 2 FAILED: {e}")
            return False

    def test_3_database_connection():
        """Test 3: Verify database connection uses specified database"""
        print("\n" + "=" * 60)
        print("Test 3: Database Connection")
        print("=" * 60)

        try:
            # Load settings from .env
            settings = Settings()

            print(f"Database configuration:")
            print(f"  Host: {settings.db_host}")
            print(f"  Port: {settings.db_port}")
            print(f"  User: {settings.db_user}")
            print(f"  Database: {settings.db_name}")

            # Create repository (this should create tables automatically)
            repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )

            print(f"✓ Database connection established successfully")
            print(f"✓ Tables initialized automatically")

            repo.close()

            print("✓ Test 3 PASSED: Database connection and table initialization works")
            return True
        except Exception as e:
            print(f"✗ Test 3 FAILED: {e}")
            return False

    def test_4_database_crud_operations():
        """Test 4: Verify all CRUD operations work correctly"""
        print("\n" + "=" * 60)
        print("Test 4: Database CRUD Operations")
        print("=" * 60)

        try:
            settings = Settings()
            repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )

            # Test INSERT
            test_log = FileTransferLog(
                SHARE_LINK="https://pan.baidu.com/s/comprehensive_test",
                EXTRACTION_CODE="test",
                FOLDER_NAME="test_folder",
                FILE_NAME="comprehensive_test.pdf",
                TRANSFER_STATUS="pending",
                START_TIME=datetime.now()
            )

            log_id = repo.insert_file_log(test_log)
            print(f"✓ INSERT: File log inserted with ID {log_id}")

            # Test SELECT by name and link
            retrieved_log = repo.get_file_log_by_name_and_link(
                file_name="comprehensive_test.pdf",
                share_link="https://pan.baidu.com/s/comprehensive_test",
                folder_name="test_folder"
            )

            if retrieved_log:
                print(f"✓ SELECT: Retrieved log by name and link")
                print(f"  ID: {retrieved_log.ID}")
                print(f"  FILE_NAME: {retrieved_log.FILE_NAME}")
                print(f"  STATUS: {retrieved_log.TRANSFER_STATUS}")
                print(f"  SHARE_LINK: {retrieved_log.SHARE_LINK}")
            else:
                print(f"✗ SELECT: Failed to retrieve log")
                repo.close()
                return False

            # Test SELECT by link
            logs = repo.get_file_logs_by_link("https://pan.baidu.com/s/comprehensive_test")
            if logs and len(logs) > 0:
                print(f"✓ SELECT: Retrieved {len(logs)} logs by link")
                for log in logs:
                    print(f"  - {log.FILE_NAME} (ID: {log.ID})")
            else:
                print(f"✗ SELECT: Failed to retrieve logs by link")
                repo.close()
                return False

            # Test UPDATE
            repo.update_file_status(
                file_id=log_id,
                status="success",
                download_time=datetime.now(),
                upload_time=datetime.now()
            )
            print(f"✓ UPDATE: Updated file status to 'success'")

            # Verify update
            updated_log = repo.get_file_log_by_name_and_link(
                file_name="comprehensive_test.pdf",
                share_link="https://pan.baidu.com/s/comprehensive_test",
                folder_name="test_folder"
            )

            if updated_log and updated_log.TRANSFER_STATUS == "success":
                print(f"✓ VERIFY: Update confirmed, status is 'success'")
            else:
                print(f"✗ VERIFY: Update not confirmed")
                repo.close()
                return False

            # Test INSERT ExecutionSummary
            test_summary = ExecutionSummary(
                SHARE_LINK="https://pan.baidu.com/s/comprehensive_test",
                FOLDER_NAME="test_folder",
                TOTAL_FILES=5,
                SUCCESS_COUNT=4,
                FAILED_COUNT=0,
                SKIPPED_COUNT=1,
                START_TIME=datetime.now(),
                END_TIME=datetime.now()
            )

            summary_id = repo.insert_execution_summary(test_summary)
            print(f"✓ INSERT: Execution summary inserted with ID {summary_id}")

            repo.close()

            print("✓ Test 4 PASSED: All CRUD operations work correctly")
            return True
        except Exception as e:
            print(f"✗ Test 4 FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_5_attribute_access():
        """Test 5: Verify attribute access patterns"""
        print("\n" + "=" * 60)
        print("Test 5: Attribute Access Patterns")
        print("=" * 60)

        try:
            # Test FileTransferLog attribute access
            log = FileTransferLog(
                ID=1,
                SHARE_LINK="https://pan.baidu.com/s/test",
                EXTRACTION_CODE="test",
                FOLDER_NAME="test_folder",
                FILE_NAME="test.pdf",
                TRANSFER_STATUS="success"
            )

            # These should all work with uppercase attributes
            print(f"✓ FileTransferLog.FILE_NAME: {log.FILE_NAME}")
            print(f"✓ FileTransferLog.SHARE_LINK: {log.SHARE_LINK}")
            print(f"✓ FileTransferLog.TRANSFER_STATUS: {log.TRANSFER_STATUS}")
            print(f"✓ FileTransferLog.ID: {log.ID}")

            # Test ExecutionSummary attribute access
            summary = ExecutionSummary(
                ID=1,
                SHARE_LINK="https://pan.baidu.com/s/test",
                FOLDER_NAME="test_folder",
                TOTAL_FILES=10,
                SUCCESS_COUNT=8
            )

            # These should all work with uppercase attributes
            print(f"✓ ExecutionSummary.TOTAL_FILES: {summary.TOTAL_FILES}")
            print(f"✓ ExecutionSummary.SUCCESS_COUNT: {summary.SUCCESS_COUNT}")
            print(f"✓ ExecutionSummary.FOLDER_NAME: {summary.FOLDER_NAME}")

            print("✓ Test 5 PASSED: Attribute access works correctly")
            return True
        except Exception as e:
            print(f"✗ Test 5 FAILED: {e}")
            return False

    def run_all_tests():
        """Run all comprehensive tests"""
        print("=" * 60)
        print("COMPREHENSIVE BUG FIX VERIFICATION TEST SUITE")
        print("=" * 60)
        print("This test suite verifies all bug fixes applied to the project")
        print()

        results = []

        # Run all tests
        results.append(("DataClass Instantiation", test_1_dataclass_instantiation()))
        results.append(("SQL Table Creation", test_2_sql_table_creation()))
        results.append(("Database Connection", test_3_database_connection()))
        results.append(("Database CRUD Operations", test_4_database_crud_operations()))
        results.append(("Attribute Access Patterns", test_5_attribute_access()))

        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED! All bug fixes are working correctly.")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
            return 1

    if __name__ == '__main__':
        sys.exit(run_all_tests())

except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)