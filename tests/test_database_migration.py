"""
Database Migration Tests for Message Type Support (004_add_message_type_support.sql)

Tests the migration that adds support for multiple message types:
- baidupan: Baidu Pan share links
- pdf_link: Direct PDF file links
- dingtalk_pdf: DingTalk PDF files
- dingtalk_zip: DingTalk ZIP archives

This test uses REAL database connections - no mocks.
"""

import unittest
import json
import hashlib
import sys
import os
from datetime import datetime
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import database components
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings


class TestDatabaseMigration(unittest.TestCase):
    """Test suite for database migration 004_add_message_type_support"""

    # Test data tracking for cleanup
    test_message_hashes: List[str] = []

    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        print("\n" + "="*70)
        print("Database Migration Test Suite - Message Type Support (004)")
        print("="*70)

        # Load settings for database credentials
        try:
            cls.settings = Settings()
            cls.DB_HOST = cls.settings.db_host
            cls.DB_PORT = cls.settings.db_port
            cls.DB_USER = cls.settings.db_user
            cls.DB_PASSWORD = cls.settings.db_password
            cls.DB_NAME = 'baidu_download'  # Fixed database name for migration tests
        except Exception as e:
            print(f"Warning: Could not load settings: {e}")
            cls.settings = None

    @classmethod
    def tearDownClass(cls):
        """Clean up all test data after tests complete"""
        print("\n" + "="*70)
        print("Cleaning up test data...")
        print("="*70)

        if not hasattr(cls, 'settings') or cls.settings is None:
            print("Warning: Settings not loaded, skipping cleanup")
            return

        try:
            with DatabaseRepository(
                host=cls.DB_HOST,
                port=cls.DB_PORT,
                user=cls.DB_USER,
                password=cls.DB_PASSWORD,
                database=cls.DB_NAME
            ) as repo:
                cursor = repo.connection.cursor()

                # Delete all test messages
                for msg_hash in cls.test_message_hashes:
                    try:
                        cursor.execute(
                            "DELETE FROM message_process_log WHERE message_hash = %s",
                            (msg_hash,)
                        )
                        print(f"  Deleted test message: {msg_hash[:16]}...")
                    except Exception as e:
                        print(f"  Warning: Failed to delete {msg_hash[:16]}...: {e}")

                repo.connection.commit()
                cursor.close()
                print(f"Cleaned up {len(cls.test_message_hashes)} test messages")

        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

    def setUp(self):
        """Set up each test with fresh database connection"""
        self.repo = None
        try:
            self.repo = DatabaseRepository(
                host=self.DB_HOST,
                port=self.DB_PORT,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                database=self.DB_NAME
            )
        except Exception as e:
            self.skipTest(f"Database connection failed: {e}")

    def tearDown(self):
        """Clean up after each test"""
        if self.repo:
            self.repo.close()

    def test_001_field_exists_message_type(self):
        """Test that message_type field exists in database"""
        print("\n[TEST 1] Verifying message_type field exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'message_type'
            """, (self.DB_NAME,))

            result = cursor.fetchone()

            self.assertIsNotNone(result, "message_type field should exist")
            self.assertEqual(result['COLUMN_NAME'], 'message_type')
            self.assertEqual(result['COLUMN_TYPE'], 'varchar(20)')
            self.assertEqual(result['COLUMN_DEFAULT'], 'baidupan')
            self.assertEqual(result['IS_NULLABLE'], 'YES')

            print(f"  [OK] message_type field exists: {result['COLUMN_TYPE']}, DEFAULT: {result['COLUMN_DEFAULT']}")

        finally:
            cursor.close()

    def test_002_field_exists_raw_message(self):
        """Test that raw_message field exists in database"""
        print("\n[TEST 2] Verifying raw_message field exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'raw_message'
            """, (self.DB_NAME,))

            result = cursor.fetchone()

            self.assertIsNotNone(result, "raw_message field should exist")
            self.assertEqual(result['COLUMN_NAME'], 'raw_message')
            self.assertEqual(result['COLUMN_TYPE'], 'json')
            self.assertEqual(result['IS_NULLABLE'], 'YES')

            print(f"  [OK] raw_message field exists: {result['COLUMN_TYPE']}")

        finally:
            cursor.close()

    def test_003_field_exists_file_info(self):
        """Test that file_info field exists in database"""
        print("\n[TEST 3] Verifying file_info field exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'file_info'
            """, (self.DB_NAME,))

            result = cursor.fetchone()

            self.assertIsNotNone(result, "file_info field should exist")
            self.assertEqual(result['COLUMN_NAME'], 'file_info')
            self.assertEqual(result['COLUMN_TYPE'], 'json')
            self.assertEqual(result['IS_NULLABLE'], 'YES')

            print(f"  [OK] file_info field exists: {result['COLUMN_TYPE']}")

        finally:
            cursor.close()

    def test_004_index_exists_message_type(self):
        """Test that idx_message_type index exists"""
        print("\n[TEST 4] Verifying idx_message_type index exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT INDEX_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_message_type'
            """, (self.DB_NAME,))

            result = cursor.fetchone()

            self.assertIsNotNone(result, "idx_message_type index should exist")
            self.assertEqual(result['INDEX_NAME'], 'idx_message_type')
            self.assertEqual(result['COLUMN_NAME'], 'message_type')

            print(f"  [OK] idx_message_type index exists on column: {result['COLUMN_NAME']}")

        finally:
            cursor.close()

    def test_005_index_exists_process_status_type(self):
        """Test that idx_process_status_type composite index exists"""
        print("\n[TEST 5] Verifying idx_process_status_type composite index exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_process_status_type'
                ORDER BY SEQ_IN_INDEX
            """, (self.DB_NAME,))

            results = cursor.fetchall()

            self.assertTrue(len(results) >= 2, "idx_process_status_type should be a composite index")
            self.assertEqual(results[0]['INDEX_NAME'], 'idx_process_status_type')
            self.assertEqual(results[0]['COLUMN_NAME'], 'process_status')
            self.assertEqual(results[0]['SEQ_IN_INDEX'], 1)
            self.assertEqual(results[1]['COLUMN_NAME'], 'message_type')
            self.assertEqual(results[1]['SEQ_IN_INDEX'], 2)

            print(f"  [OK] idx_process_status_type composite index exists: process_status, message_type")

        finally:
            cursor.close()

    def test_006_constraint_exists_message_type(self):
        """Test that chk_message_type constraint exists"""
        print("\n[TEST 6] Verifying chk_message_type constraint exists...")
        cursor = self.repo.connection.cursor()

        try:
            cursor.execute("""
                SELECT CONSTRAINT_NAME, CHECK_CLAUSE
                FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME = 'chk_message_type'
            """, (self.DB_NAME,))

            result = cursor.fetchone()

            self.assertIsNotNone(result, "chk_message_type constraint should exist")
            self.assertEqual(result['CONSTRAINT_NAME'], 'chk_message_type')
            self.assertIn('message_type', result['CHECK_CLAUSE'])

            print(f"  [OK] chk_message_type constraint exists: {result['CHECK_CLAUSE']}")

        finally:
            cursor.close()

    def test_007_insert_baidupan_message(self):
        """Test inserting a Baidu Pan message with new fields"""
        print("\n[TEST 7] Testing Baidu Pan message insertion...")

        # Create test message
        test_hash = hashlib.md5(f"test_baidupan_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test Baidu Pan message",
            share_link="https://pan.baidu.com/s/test123",
            folder_name="test_folder",
            extraction_code="abcd",
            source="feishu",
            message_type="baidupan",
            raw_message=json.dumps({"type": "baidupan", "link": "https://pan.baidu.com/s/test123"}),
            file_info=json.dumps({"name": "test.pdf", "size": 1024}),
            process_status="pending"
        )

        # Insert message
        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0, "Insert should return valid ID")
        print(f"  [OK] Inserted Baidu Pan message with ID: {record_id}")

        # Retrieve and verify
        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved, "Should retrieve inserted message")
        self.assertEqual(retrieved.message_type, "baidupan")
        self.assertIsNotNone(retrieved.raw_message)
        self.assertIsNotNone(retrieved.file_info)
        print(f"  [OK] Retrieved and verified message_type: {retrieved.message_type}")

    def test_008_insert_pdf_link_message(self):
        """Test inserting a PDF link message"""
        print("\n[TEST 8] Testing PDF link message insertion...")

        test_hash = hashlib.md5(f"test_pdf_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test PDF link message",
            share_link="https://example.com/file.pdf",
            folder_name=None,
            extraction_code=None,
            source="dingtalk",
            message_type="pdf_link",
            raw_message=json.dumps({"type": "pdf", "url": "https://example.com/file.pdf"}),
            file_info=json.dumps({"filename": "document.pdf", "size": 2048}),
            process_status="pending"
        )

        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0)
        print(f"  [OK] Inserted PDF link message with ID: {record_id}")

        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_type, "pdf_link")
        print(f"  [OK] Verified message_type: {retrieved.message_type}")

    def test_009_insert_dingtalk_pdf_message(self):
        """Test inserting a DingTalk PDF message"""
        print("\n[TEST 9] Testing DingTalk PDF message insertion...")

        test_hash = hashlib.md5(f"test_dingtalk_pdf_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test DingTalk PDF message",
            share_link="https://dingtalk.com/file/abc123",
            folder_name=None,
            extraction_code=None,
            source="dingtalk",
            message_type="dingtalk_pdf",
            raw_message=json.dumps({"type": "file", "fileType": "pdf"}),
            file_info=json.dumps({"name": "report.pdf", "size": 3072, "media_id": "abc123"}),
            process_status="pending"
        )

        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0)
        print(f"  [OK] Inserted DingTalk PDF message with ID: {record_id}")

        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_type, "dingtalk_pdf")
        print(f"  [OK] Verified message_type: {retrieved.message_type}")

    def test_010_insert_dingtalk_zip_message(self):
        """Test inserting a DingTalk ZIP message"""
        print("\n[TEST 10] Testing DingTalk ZIP message insertion...")

        test_hash = hashlib.md5(f"test_dingtalk_zip_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test DingTalk ZIP message",
            share_link="https://dingtalk.com/file/xyz789",
            folder_name=None,
            extraction_code=None,
            source="dingtalk",
            message_type="dingtalk_zip",
            raw_message=json.dumps({"type": "file", "fileType": "zip"}),
            file_info=json.dumps({"name": "archive.zip", "size": 10240, "media_id": "xyz789"}),
            process_status="pending"
        )

        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0)
        print(f"  [OK] Inserted DingTalk ZIP message with ID: {record_id}")

        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_type, "dingtalk_zip")
        print(f"  [OK] Verified message_type: {retrieved.message_type}")

    def test_011_message_type_constraint(self):
        """Test that message type constraint rejects invalid types"""
        print("\n[TEST 11] Testing message type constraint...")
        cursor = self.repo.connection.cursor()

        try:
            test_hash = hashlib.md5(f"test_invalid_{datetime.now().isoformat()}".encode()).hexdigest()

            # Try to insert message with invalid type
            try:
                cursor.execute("""
                    INSERT INTO message_process_log
                    (message_hash, original_message, message_type, process_status)
                    VALUES (%s, %s, %s, %s)
                """, (test_hash, "Test invalid type", "invalid_type", "pending"))

                self.repo.connection.commit()
                self.fail("Should have failed with constraint violation")

            except Exception as e:
                self.repo.connection.rollback()
                # Check if error is about constraint violation
                error_msg = str(e).lower()
                self.assertTrue('constraint' in error_msg or 'check' in error_msg,
                              f"Error should mention constraint: {e}")
                print(f"  [OK] Constraint correctly rejected invalid type")

        finally:
            cursor.close()

    def test_012_json_fields_handling(self):
        """Test that JSON fields properly store and retrieve data"""
        print("\n[TEST 12] Testing JSON fields handling...")

        test_hash = hashlib.md5(f"test_json_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        # Create complex JSON data
        raw_msg = {
            "sender": "user123",
            "timestamp": "2026-08-20T10:30:00Z",
            "content": {"type": "pdf_link", "url": "https://example.com/doc.pdf"}
        }
        file_info = {
            "name": "document.pdf",
            "size": 5120,
            "mime_type": "application/pdf",
            "metadata": {"author": "Test Author", "pages": 10}
        }

        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test JSON handling",
            share_link="https://example.com/doc.pdf",
            folder_name=None,
            extraction_code=None,
            source="feishu",
            message_type="pdf_link",
            raw_message=json.dumps(raw_msg),
            file_info=json.dumps(file_info),
            process_status="pending"
        )

        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0)
        print(f"  [OK] Inserted message with complex JSON data")

        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved)

        # Parse and verify JSON
        parsed_raw = json.loads(retrieved.raw_message)
        parsed_file = json.loads(retrieved.file_info)

        self.assertEqual(parsed_raw['sender'], 'user123')
        self.assertEqual(parsed_file['metadata']['pages'], 10)
        print(f"  [OK] JSON data correctly stored and retrieved")

    def test_013_backwards_compatibility(self):
        """Test that existing code without new fields still works"""
        print("\n[TEST 13] Testing backwards compatibility...")

        test_hash = hashlib.md5(f"test_compat_{datetime.now().isoformat()}".encode()).hexdigest()
        self.test_message_hashes.append(test_hash)

        # Create message without setting new fields (testing defaults)
        test_message = MessageProcessLog(
            message_hash=test_hash,
            original_message="Test backwards compatibility",
            share_link="https://pan.baidu.com/s/compat123",
            folder_name="compat_folder",
            extraction_code="1234",
            source="feishu",
            # message_type should default to 'baidupan'
            # raw_message and file_info should default to None
            process_status="pending"
        )

        record_id = self.repo.insert_message_log(test_message)
        self.assertTrue(record_id > 0)
        print(f"  [OK] Inserted message with default values")

        retrieved = self.repo.get_message_by_hash(test_hash)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.message_type, 'baidupan', "Default message_type should be 'baidupan'")
        self.assertIsNone(retrieved.raw_message, "raw_message should be None when not set")
        self.assertIsNone(retrieved.file_info, "file_info should be None when not set")
        print(f"  [OK] Default values correctly applied")


def main():
    """Run the test suite"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    main()
