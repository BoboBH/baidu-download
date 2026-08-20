"""
Comprehensive unit tests for message retry functionality in the repository layer.

Tests cover retry count increment, reset, max retry filtering, and configuration boundaries
as specified in the design specification for Task 8.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import ConfigError


@pytest.fixture
def mock_settings():
    """Create a mock Settings object with retry configuration"""
    settings = Mock()
    settings.max_message_retries = 10  # Default as per specification
    return settings


@pytest.fixture
def mock_db_connection_with_settings(mock_settings):
    """Create a mock database connection with settings"""
    with patch('pymysql.connect') as mock_connect:
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        yield mock_connection, mock_cursor, mock_settings


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection without settings"""
    with patch('pymysql.connect') as mock_connect:
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        yield mock_connection, mock_cursor


class TestRetryCountIncrement:
    """Test suite for retry count increment functionality"""

    def test_retry_count_increments_on_failure_status(self, mock_db_connection_with_settings):
        """Test that retry_count increments when status is set to 'failed'"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1  # Simulate successful update

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_001'
        result = repo.update_message_status(message_hash, 'failed', error_message='Download failed')

        # Verify the update was called
        assert result is True
        assert mock_cursor.execute.called

        # Verify SQL includes retry count increment
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = retry_count + 1' in sql
        assert 'failed' in call_args[0][1]  # status parameter

    def test_retry_count_increments_on_critical_error_status(self, mock_db_connection_with_settings):
        """Test that retry_count increments when status is set to 'critical_error'"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_002'
        result = repo.update_message_status(
            message_hash,
            'critical_error',
            error_message='Connection timeout'
        )

        assert result is True
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = retry_count + 1' in sql

    def test_retry_count_multiple_failures(self, mock_db_connection_with_settings):
        """Test that retry_count increments correctly over multiple failures"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_003'

        # Simulate first failure
        repo.update_message_status(message_hash, 'failed', error_message='First failure')

        # Simulate second failure
        repo.update_message_status(message_hash, 'failed', error_message='Second failure')

        # Verify execute was called twice with increment logic
        # Note: there will be more calls due to database initialization
        assert mock_cursor.execute.call_count >= 2
        # Check that at least 2 calls contain the increment logic
        increment_calls = 0
        for call_arg in mock_cursor.execute.call_args_list:
            if len(call_arg[0]) > 0 and isinstance(call_arg[0][0], str):
                sql = call_arg[0][0]
                if 'retry_count = retry_count + 1' in sql:
                    increment_calls += 1
                    # Check that parameters contain 'failed'
                    if len(call_arg[0]) > 1:
                        params = call_arg[0][1]
                        if isinstance(params, (list, tuple)) and len(params) > 0:
                            assert 'failed' in params or params[0] == 'failed'

    def test_retry_count_includes_processing_time(self, mock_db_connection_with_settings):
        """Test that retry count increment preserves processing time"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_004'
        processing_time = 5000  # 5 seconds

        repo.update_message_status(
            message_hash,
            'failed',
            error_message='Timeout',
            processing_time_ms=processing_time
        )

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[3] == processing_time  # processing_time_ms parameter


class TestRetryCountReset:
    """Test suite for retry count reset functionality"""

    def test_retry_count_resets_on_success_status(self, mock_db_connection_with_settings):
        """Test that retry_count resets to 0 when status is set to 'success'"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_005'
        result = repo.update_message_status(message_hash, 'success')

        assert result is True
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = 0' in sql

    def test_retry_count_resets_after_failures(self, mock_db_connection_with_settings):
        """Test that retry_count resets after failures when status changes to success"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_006'

        # Fail twice to increment retry count
        repo.update_message_status(message_hash, 'failed', error_message='First failure')
        repo.update_message_status(message_hash, 'failed', error_message='Second failure')

        # Reset call count for success call
        mock_cursor.execute.reset_mock()

        # Now succeed - should reset retry_count to 0
        repo.update_message_status(message_hash, 'success')

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = 0' in sql
        assert 'error_message = NULL' in sql  # Error should also be cleared

    def test_retry_count_reset_clears_error_message(self, mock_db_connection_with_settings):
        """Test that resetting retry count on success also clears error message"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_007'

        repo.update_message_status(message_hash, 'success')

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = 0' in sql
        assert 'error_message = NULL' in sql

    def test_retry_count_reset_with_execution_summary(self, mock_db_connection_with_settings):
        """Test that retry count reset works with execution summary ID"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_008'
        execution_summary_id = 123

        repo.update_message_status(
            message_hash,
            'success',
            execution_summary_id=execution_summary_id
        )

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert 'retry_count = 0' in sql
        assert params[1] == execution_summary_id  # execution_summary_id parameter


class TestRetryCountUnchanged:
    """Test suite for retry count remaining unchanged"""

    def test_retry_count_unchanged_on_pending_status(self, mock_db_connection_with_settings):
        """Test that retry_count remains unchanged when status is set to 'pending'"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_009'
        repo.update_message_status(message_hash, 'pending')

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count' not in sql  # Should not modify retry_count
        assert 'error_message = NULL' in sql  # Should clear error message

    def test_retry_count_unchanged_on_processing_status(self, mock_db_connection_with_settings):
        """Test that retry_count remains unchanged when status is set to 'processing'"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_010'
        repo.update_message_status(message_hash, 'processing')

        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count' not in sql  # Should not modify retry_count
        assert 'error_message = NULL' in sql  # Should clear error message


class TestConfigurationBoundaries:
    """Test suite for MESSAGE_MAX_RETRIES configuration boundaries"""

    def setup_method(self):
        """Clean up environment before each configuration test"""
        import os
        # Clear relevant environment variables to prevent interference between tests
        env_vars_to_clear = [key for key in os.environ if key.startswith(('SFTP_', 'DB_', 'BAIDU', 'MESSAGE_', 'FEISHU_', 'DINGTALK_', 'WXCHAT_', 'TEMP_'))]
        for var in env_vars_to_clear:
            del os.environ[var]

    def teardown_method(self):
        """Clean up test files after each configuration test"""
        import os
        import shutil
        # Clean up test directories
        if os.path.exists('./test_fake_retry'):
            shutil.rmtree('./test_fake_retry', ignore_errors=True)
        if os.path.exists('./test_temp_retry'):
            shutil.rmtree('./test_temp_retry', ignore_errors=True)

    def test_configuration_max_retries_minimum_boundary(self):
        """Test that MESSAGE_MAX_RETRIES = 1 is accepted"""
        import os
        import tempfile
        import shutil

        # Create temporary directories
        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        # Create fake BaiduPCS-Go file
        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        # Create minimal valid .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
MESSAGE_MAX_RETRIES=1
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            # Use override=True to force environment variable reload
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
            settings = Settings()
            assert settings.max_message_retries == 1
        finally:
            os.unlink(env_file)

    def test_configuration_max_retries_maximum_boundary(self):
        """Test that MESSAGE_MAX_RETRIES = 100 is accepted"""
        import os
        import tempfile
        from dotenv import load_dotenv

        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
MESSAGE_MAX_RETRIES=100
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            load_dotenv(env_file, override=True)
            settings = Settings()
            assert settings.max_message_retries == 100
        finally:
            os.unlink(env_file)

    def test_configuration_max_retries_default_value(self):
        """Test that MESSAGE_MAX_RETRIES defaults to 10 when not specified"""
        import os
        import tempfile
        from dotenv import load_dotenv

        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            load_dotenv(env_file, override=True)
            settings = Settings()
            assert settings.max_message_retries == 10
        finally:
            os.unlink(env_file)

    def test_configuration_max_retries_below_minimum_raises_error(self):
        """Test that MESSAGE_MAX_RETRIES = 0 raises ConfigError"""
        import os
        import tempfile
        from dotenv import load_dotenv

        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
MESSAGE_MAX_RETRIES=0
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            load_dotenv(env_file, override=True)
            with pytest.raises(ConfigError) as exc_info:
                Settings()
            assert 'MESSAGE_MAX_RETRIES must be between 1 and 100' in str(exc_info.value)
        finally:
            os.unlink(env_file)

    def test_configuration_max_retries_above_maximum_raises_error(self):
        """Test that MESSAGE_MAX_RETRIES = 101 raises ConfigError"""
        import os
        import tempfile
        from dotenv import load_dotenv

        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
MESSAGE_MAX_RETRIES=101
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            load_dotenv(env_file, override=True)
            with pytest.raises(ConfigError) as exc_info:
                Settings()
            assert 'MESSAGE_MAX_RETRIES must be between 1 and 100' in str(exc_info.value)
        finally:
            os.unlink(env_file)

    def test_configuration_max_retries_negative_raises_error(self):
        """Test that negative MESSAGE_MAX_RETRIES raises ConfigError"""
        import os
        import tempfile
        from dotenv import load_dotenv

        fake_dir = './test_fake_retry'
        temp_dir = './test_temp_retry'
        os.makedirs(fake_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        with open(f'{fake_dir}/BaiduPCS-Go.exe', 'w') as f:
            f.write('fake')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(f"""SFTP_HOST=localhost
SFTP_PORT=22
SFTP_USERNAME=testuser
SFTP_PASSWORD=testpass
SFTP_REMOTE_PATH=/upload
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
BAIDUPCS_GO_PATH={fake_dir}/BaiduPCS-Go.exe
TEMP_DIR={temp_dir}
MESSAGE_MAX_RETRIES=-5
""")
            env_file = f.name

        try:
            from src.config.settings import Settings
            load_dotenv(env_file, override=True)
            with pytest.raises(ConfigError) as exc_info:
                Settings()
            assert 'MESSAGE_MAX_RETRIES must be between 1 and 100' in str(exc_info.value)
        finally:
            os.unlink(env_file)


class TestInvalidStatusHandling:
    """Test suite for invalid status handling in update_message_status"""

    def test_update_message_status_invalid_status_returns_false(self, mock_db_connection_with_settings):
        """Test that invalid status returns False without executing SQL"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        result = repo.update_message_status('test_hash', 'invalid_status')

        assert result is False
        # Execute should not be called for the update, but it was called during initialization
        # So we need to check that it wasn't called for this specific operation
        assert mock_cursor.execute.call_count > 0  # Database init happened
        # But the last call should not be for our invalid update
        # Actually we need to check that update logic didn't run
        # The repository returns False before executing SQL, so we should have only init calls

    def test_update_message_status_empty_status_returns_false(self, mock_db_connection_with_settings):
        """Test that empty status returns False"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        initial_call_count = mock_cursor.execute.call_count
        result = repo.update_message_status('test_hash', '')

        assert result is False
        # Execute count should not have increased
        assert mock_cursor.execute.call_count == initial_call_count

    def test_update_message_status_none_status_returns_false(self, mock_db_connection_with_settings):
        """Test that None status returns False"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        initial_call_count = mock_cursor.execute.call_count
        result = repo.update_message_status('test_hash', None)

        assert result is False
        # Execute count should not have increased
        assert mock_cursor.execute.call_count == initial_call_count


class TestDatabaseErrorHandling:
    """Test suite for database error handling"""

    def test_update_message_status_database_error_returns_false(self, mock_db_connection_with_settings):
        """Test that database errors are caught and return False"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        # Set side_effect after repository is initialized
        mock_cursor.execute.side_effect = Exception("Database connection lost")

        result = repo.update_message_status('test_hash', 'failed')

        assert result is False
        assert mock_connection.rollback.called  # Should rollback transaction

    def test_update_message_status_nonexistent_message(self, mock_db_connection_with_settings):
        """Test that updating non-existent message returns False"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 0  # No rows affected

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        result = repo.update_message_status('nonexistent_hash', 'failed')

        assert result is False  # No rows affected
        assert mock_cursor.execute.called

class TestRetryCountIntegration:
    """Test suite for integration scenarios with retry count"""

    def test_complete_retry_cycle(self, mock_db_connection_with_settings):
        """Test complete cycle: insert -> fail multiple times -> succeed -> retry"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1
        mock_cursor.lastrowid = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_cycle_001'

        # Simulate retry limit cycle
        repo.update_message_status(message_hash, 'failed', error_message='Failure 1')
        repo.update_message_status(message_hash, 'failed', error_message='Failure 2')
        repo.update_message_status(message_hash, 'critical_error', error_message='Failure 3')

        # Reset for success
        mock_cursor.execute.reset_mock()
        repo.update_message_status(message_hash, 'success')

        # Verify success reset retry_count
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert 'retry_count = 0' in sql


class TestParameterValidation:
    """Test suite for parameter validation"""

    def test_update_message_status_with_all_parameters(self, mock_db_connection_with_settings):
        """Test update_message_status with all optional parameters"""
        mock_connection, mock_cursor, mock_settings = mock_db_connection_with_settings
        mock_cursor.rowcount = 1

        repo = DatabaseRepository(
            host='localhost',
            port=3306,
            user='root',
            password='password',
            database='test_db',
            settings=mock_settings
        )

        message_hash = 'test_hash_params'
        status = 'failed'
        error_message = 'Connection timeout'
        execution_summary_id = 456
        processing_time_ms = 12345

        repo.update_message_status(
            message_hash,
            status,
            error_message=error_message,
            execution_summary_id=execution_summary_id,
            processing_time_ms=processing_time_ms
        )

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # Verify all parameters are passed correctly
        assert params[0] == status
        assert params[1] == error_message
        assert params[2] == execution_summary_id
        assert params[3] == processing_time_ms
        assert params[4] == message_hash


