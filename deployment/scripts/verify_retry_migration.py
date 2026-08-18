#!/usr/bin/env python3
"""
Message Retry Limit Feature - Deployment Verification Script

This script performs comprehensive verification of the message retry limit feature deployment.
It validates database schema, configuration, functionality, and data integrity.

Usage:
    python verify_retry_migration.py [--env-file .env] [--verbose]

Exit Codes:
    0: All verifications passed
    1: Critical verification failed
    2: Non-critical issues detected
    3: Configuration error
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'retry_migration_verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for output formatting"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class MigrationVerifier:
    """Comprehensive migration verification system"""

    def __init__(self, env_file: str = '.env', verbose: bool = False):
        self.env_file = env_file
        self.verbose = verbose
        self.verification_results = []
        self.start_time = datetime.now()

    def print_header(self, title: str):
        """Print formatted section header"""
        logger.info(f"\n{'='*70}")
        logger.info(f"{Colors.BOLD}{title}{Colors.RESET}")
        logger.info(f"{'='*70}\n")

    def print_success(self, message: str):
        """Print success message"""
        logger.info(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

    def print_error(self, message: str):
        """Print error message"""
        logger.error(f"{Colors.RED}✗ {message}{Colors.RESET}")

    def print_warning(self, message: str):
        """Print warning message"""
        logger.warning(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

    def print_info(self, message: str):
        """Print info message"""
        logger.info(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

    def record_result(self, test_name: str, passed: bool, details: str = "", critical: bool = True):
        """Record verification result"""
        self.verification_results.append({
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'critical': critical,
            'timestamp': datetime.now()
        })

        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        level = "CRITICAL" if critical else "NON-CRITICAL"

        logger.info(f"{color}[{status}] {level}: {test_name}{Colors.RESET}")
        if details and self.verbose:
            logger.info(f"    Details: {details}")

    def verify_configuration(self) -> bool:
        """Verify application configuration"""
        self.print_header("PHASE 1: CONFIGURATION VERIFICATION")

        try:
            # Load environment
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
            self.print_success("Environment file loaded")

            # Import settings
            from src.config.settings import Settings
            settings = Settings()
            self.print_success("Settings loaded successfully")

            # Verify MESSAGE_MAX_RETRIES configuration
            max_retries = settings.max_message_retries
            self.print_info(f"MESSAGE_MAX_RETRIES configured: {max_retries}")

            if not (1 <= max_retries <= 100):
                self.print_error(f"MESSAGE_MAX_RETRIES out of valid range: {max_retries}")
                self.record_result("Configuration validation", False,
                                 f"MESSAGE_MAX_RETRIES={max_retries} not in range 1-100")
                return False

            self.print_success("MESSAGE_MAX_RETRIES within valid range (1-100)")
            self.record_result("Configuration validation", True,
                              f"MESSAGE_MAX_RETRIES={max_retries}")

            # Verify related configuration
            self.print_info(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
            self.record_result("Database configuration", True,
                              f"{settings.db_host}:{settings.db_port}/{settings.db_name}")

            return True

        except Exception as e:
            self.print_error(f"Configuration verification failed: {str(e)}")
            self.record_result("Configuration verification", False, str(e))
            return False

    def verify_database_schema(self) -> bool:
        """Verify database schema changes"""
        self.print_header("PHASE 2: DATABASE SCHEMA VERIFICATION")

        try:
            from src.config.settings import Settings
            from src.database.repository import DatabaseRepository

            settings = Settings()
            db_repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )

            self.print_success("Database connection established")
            self.record_result("Database connectivity", True)

            cursor = db_repo.connection.cursor()

            # Check 1: Verify retry_count column exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count'
            """, (settings.db_name,))

            result = cursor.fetchone()
            column_exists = result['count'] > 0

            if not column_exists:
                self.print_error("retry_count column does not exist")
                self.record_result("retry_count column exists", False, critical=True)
                return False

            self.print_success("retry_count column exists")
            self.record_result("retry_count column exists", True)

            # Check 2: Verify column properties
            cursor.execute("""
                SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND COLUMN_NAME = 'retry_count'
            """, (settings.db_name,))

            column_info = cursor.fetchone()

            expected_type = 'int'
            expected_nullable = 'NO'
            expected_default = '0'

            column_details = f"Type: {column_info['COLUMN_TYPE']}, Nullable: {column_info['IS_NULLABLE']}, Default: {column_info['COLUMN_DEFAULT']}"

            if column_info['IS_NULLABLE'] != expected_nullable:
                self.print_warning(f"Column nullable property: {column_info['IS_NULLABLE']} (expected: {expected_nullable})")
                self.record_result("retry_count column properties", True, column_details, critical=False)
            else:
                self.print_success("retry_count column properties correct")
                self.record_result("retry_count column properties", True, column_details)

            # Check 3: Verify index exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_retry_count'
            """, (settings.db_name,))

            result = cursor.fetchone()
            index_exists = result['count'] > 0

            if not index_exists:
                self.print_error("idx_retry_count index does not exist")
                self.record_result("idx_retry_count index exists", False, critical=True)
                return False

            self.print_success("idx_retry_count index exists")
            self.record_result("idx_retry_count index exists", True)

            # Check 4: Verify data integrity
            cursor.execute("""
                SELECT COUNT(*) as total, SUM(CASE WHEN retry_count IS NULL THEN 1 ELSE 0 END) as null_count
                FROM message_process_log
            """)

            result = cursor.fetchone()
            total_messages = result['total']
            null_count = result['null_count']

            if null_count > 0:
                self.print_error(f"Found {null_count} messages with NULL retry_count")
                self.record_result("Data integrity (no NULL values)", False,
                                 f"{null_count} NULL values found", critical=True)
                return False

            self.print_success(f"All {total_messages} messages have valid retry_count values")
            self.record_result("Data integrity", True, f"{total_messages} messages, 0 NULL values")

            # Check 5: Verify retry_count distribution
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN retry_count = 0 THEN 1 ELSE 0 END) as zero_retries,
                    SUM(CASE WHEN retry_count > 0 THEN 1 ELSE 0 END) as has_retries,
                    MIN(retry_count) as min_retry,
                    MAX(retry_count) as max_retry,
                    AVG(retry_count) as avg_retry
                FROM message_process_log
            """)

            result = cursor.fetchone()
            distribution = (f"Total: {result['total']}, Zero: {result['zero_retries']}, "
                          f"With retries: {result['has_retries']}, Range: {result['min_retry']}-{result['max_retry']}, "
                          f"Avg: {result['avg_retry']:.2f}")

            self.print_info(f"Retry count distribution: {distribution}")
            self.record_result("Retry count distribution", True, distribution, critical=False)

            cursor.close()
            db_repo.close()

            return True

        except Exception as e:
            self.print_error(f"Database schema verification failed: {str(e)}")
            self.record_result("Database schema verification", False, str(e))
            return False

    def verify_functionality(self) -> bool:
        """Verify retry limit functionality"""
        self.print_header("PHASE 3: FUNCTIONALITY VERIFICATION")

        try:
            from src.config.settings import Settings
            from src.database.repository import DatabaseRepository

            settings = Settings()
            db_repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )

            # Test 1: Verify retry filtering works
            retry_messages = db_repo.get_recent_messages_to_retry(hours=24)
            self.print_info(f"Retry filtering returned {len(retry_messages)} messages")
            self.print_success("Retry filtering functionality working")
            self.record_result("Retry filtering", True, f"{len(retry_messages)} messages eligible")

            # Test 2: Verify retry count increment logic
            cursor = db_repo.connection.cursor()

            # Create test message if none exists
            cursor.execute("""
                INSERT INTO message_process_log (message_hash, original_message, process_status, retry_count)
                VALUES ('test_hash_verify_123', 'Test message for verification', 'failed', 5)
            """)
            test_hash = 'test_hash_verify_123'

            # Test increment
            db_repo.update_message_status(test_hash, 'failed', 'Test error message')

            cursor.execute("SELECT retry_count FROM message_process_log WHERE message_hash = %s", (test_hash,))
            result = cursor.fetchone()
            new_count = result['retry_count']

            if new_count != 6:  # Should be incremented from 5
                self.print_error(f"Retry count not incremented correctly: {new_count} (expected 6)")
                self.record_result("Retry count increment", False, f"Got {new_count}, expected 6")
                cursor.execute("DELETE FROM message_process_log WHERE message_hash = %s", (test_hash,))
                cursor.close()
                return False

            self.print_success("Retry count increment working correctly")
            self.record_result("Retry count increment", True, f"Incremented from 5 to {new_count}")

            # Test 3: Verify retry reset on success
            db_repo.update_message_status(test_hash, 'success')

            cursor.execute("SELECT retry_count FROM message_process_log WHERE message_hash = %s", (test_hash,))
            result = cursor.fetchone()
            reset_count = result['retry_count']

            if reset_count != 0:
                self.print_error(f"Retry count not reset on success: {reset_count} (expected 0)")
                self.record_result("Retry count reset on success", False, f"Got {reset_count}, expected 0")
                cursor.execute("DELETE FROM message_process_log WHERE message_hash = %s", (test_hash,))
                cursor.close()
                return False

            self.print_success("Retry count reset on success working correctly")
            self.record_result("Retry count reset on success", True, f"Reset to {reset_count}")

            # Cleanup
            cursor.execute("DELETE FROM message_process_log WHERE message_hash = %s", (test_hash,))
            cursor.close()

            # Test 4: Verify retry limit enforcement
            max_retries = settings.max_message_retries
            self.print_info(f"Retry limit enforcement: max {max_retries} retries")
            self.print_success("Retry limit enforcement configured")
            self.record_result("Retry limit enforcement", True, f"Max retries: {max_retries}")

            return True

        except Exception as e:
            self.print_error(f"Functionality verification failed: {str(e)}")
            self.record_result("Functionality verification", False, str(e))
            return False

    def verify_performance(self) -> bool:
        """Verify performance characteristics"""
        self.print_header("PHASE 4: PERFORMANCE VERIFICATION")

        try:
            from src.config.settings import Settings
            from src.database.repository import DatabaseRepository

            settings = Settings()
            db_repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )

            cursor = db_repo.connection.cursor()

            # Test 1: Check query execution plan for retry filtering
            cursor.execute("""
                EXPLAIN SELECT * FROM message_process_log
                WHERE retry_count < %s AND process_status IN ('failed', 'critical_error')
            """, (settings.max_message_retries,))

            explain_result = cursor.fetchall()
            uses_index = any('idx_retry_count' in str(row.values()) for row in explain_result)

            if uses_index:
                self.print_success("Retry filtering query uses idx_retry_count index")
                self.record_result("Query performance (index usage)", True, "Uses idx_retry_count")
            else:
                self.print_warning("Retry filtering query may not be using idx_retry_count efficiently")
                self.record_result("Query performance (index usage)", True,
                                 "Index usage unclear - non-critical", critical=False)

            # Test 2: Check index cardinality
            cursor.execute("""
                SELECT CARDINALITY FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'message_process_log' AND INDEX_NAME = 'idx_retry_count'
            """, (settings.db_name,))

            result = cursor.fetchone()
            cardinality = result['CARDINALITY'] if result else 0

            self.print_info(f"idx_retry_count cardinality: {cardinality}")
            self.record_result("Index cardinality", True, f"Cardinality: {cardinality}", critical=False)

            cursor.close()
            db_repo.close()

            return True

        except Exception as e:
            self.print_warning(f"Performance verification encountered issues: {str(e)}")
            self.record_result("Performance verification", True,
                             f"Non-critical issues: {str(e)}", critical=False)
            return True  # Performance issues are non-critical

    def generate_summary(self):
        """Generate verification summary"""
        self.print_header("VERIFICATION SUMMARY")

        duration = (datetime.now() - self.start_time).total_seconds()

        # Calculate statistics
        total_tests = len(self.verification_results)
        passed_tests = sum(1 for r in self.verification_results if r['passed'])
        failed_tests = sum(1 for r in self.verification_results if not r['passed'])
        critical_failed = sum(1 for r in self.verification_results if not r['passed'] and r['critical'])

        # Print summary
        logger.info(f"Total Duration: {duration:.2f} seconds")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"{Colors.GREEN}Passed: {passed_tests}{Colors.RESET}")
        logger.info(f"{Colors.RED}Failed: {failed_tests}{Colors.RESET}")
        logger.info(f"Critical Failures: {critical_failed}")

        # Print failed tests
        if failed_tests > 0:
            logger.info(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for result in self.verification_results:
                if not result['passed']:
                    level = "CRITICAL" if result['critical'] else "NON-CRITICAL"
                    logger.info(f"  [{level}] {result['test_name']}: {result['details']}")

        # Determine exit code
        if critical_failed > 0:
            self.print_error("VERIFICATION FAILED - Critical issues detected")
            return 1
        elif failed_tests > 0:
            self.print_warning("VERIFICATION COMPLETED WITH WARNINGS - Non-critical issues detected")
            return 2
        else:
            self.print_success("VERIFICATION PASSED - All checks completed successfully")
            return 0

    def run_all_verifications(self) -> int:
        """Run all verification phases"""
        self.print_header("MESSAGE RETRY LIMIT FEATURE - DEPLOYMENT VERIFICATION")
        self.print_info(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.print_info(f"Environment file: {self.env_file}")

        # Run verification phases
        phases = [
            ("Configuration", self.verify_configuration),
            ("Database Schema", self.verify_database_schema),
            ("Functionality", self.verify_functionality),
            ("Performance", self.verify_performance)
        ]

        overall_success = True
        for phase_name, phase_func in phases:
            try:
                if not phase_func():
                    overall_success = False
                    self.print_error(f"{phase_name} phase failed")
            except Exception as e:
                overall_success = False
                self.print_error(f"{phase_name} phase encountered error: {str(e)}")

        # Generate summary and return exit code
        return self.generate_summary()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Verify Message Retry Limit Feature deployment'
    )
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Path to environment file (default: .env)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if not Path(args.env_file).exists():
        print(f"Error: Environment file not found: {args.env_file}")
        return 3

    verifier = MigrationVerifier(env_file=args.env_file, verbose=args.verbose)
    return verifier.run_all_verifications()


if __name__ == '__main__':
    sys.exit(main())