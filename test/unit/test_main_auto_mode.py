"""
Unit tests for main.py automatic mode functionality
"""
import pytest
import sys
from unittest.mock import patch, MagicMock, call
from pathlib import Path


class TestMainAutoMode:
    """Test suite for main.py automatic mode (--auto flag)"""

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_flag_triggers_auto_processor(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that --auto flag triggers AutoProcessor instead of FileProcessor
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor instance
        mock_auto_processor = MagicMock()
        mock_auto_processor.process_messages.return_value = 0
        mock_auto_processor_class.return_value = mock_auto_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify AutoProcessor was instantiated
        mock_auto_processor_class.assert_called_once()

        # Verify process_messages was called
        mock_auto_processor.process_messages.assert_called_once()

        # Verify exit code is 0 (success)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_returns_success_exit_code(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode returns exit code 0 when AutoProcessor succeeds
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor to return success
        mock_auto_processor = MagicMock()
        mock_auto_processor.process_messages.return_value = 0
        mock_auto_processor_class.return_value = mock_auto_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify exit code is 0 (success)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_returns_failure_exit_code(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode returns exit code 1 when AutoProcessor fails
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor to return failure
        mock_auto_processor = MagicMock()
        mock_auto_processor.process_messages.return_value = 1
        mock_auto_processor_class.return_value = mock_auto_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify exit code is 1 (failure)
        assert exit_code == 1

    @patch('src.config.settings.Settings')
    @patch('main.FileProcessor')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_manual_mode_still_works_without_auto_flag(self, mock_parse_args, mock_auto_processor_class, mock_file_processor_class, mock_settings):
        """
        Test backward compatibility - manual mode still works without --auto flag

        This ensures existing functionality is preserved
        """
        # Setup mock arguments WITHOUT --auto flag
        mock_args = MagicMock()
        mock_args.auto = False  # or just don't set it
        mock_args.link = "https://pan.baidu.com/s/test"
        mock_args.code = "1234"
        mock_args.folder = "test_folder"
        mock_args.config = None
        mock_args.dry_run = False
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock FileProcessor
        mock_file_processor = MagicMock()
        mock_summary = MagicMock()
        mock_summary.total_files = 5
        mock_summary.success_count = 5
        mock_summary.failed_count = 0
        mock_summary.skipped_count = 0
        mock_summary.total_size = 1024 * 1024 * 10  # 10 MB
        mock_summary.start_time = None
        mock_summary.end_time = None
        mock_file_processor.process_files.return_value = mock_summary

        # Setup context manager for FileProcessor
        mock_file_processor_class.return_value.__enter__.return_value = mock_file_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify AutoProcessor was NOT called
        mock_auto_processor_class.assert_not_called()

        # Verify FileProcessor WAS called
        mock_file_processor.process_files.assert_called_once_with(
            share_link="https://pan.baidu.com/s/test",
            code="1234",
            folder_name="test_folder"
        )

        # Verify exit code is 0 (success)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_with_config_argument(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode works with custom config file argument
        """
        # Setup mock arguments with --auto flag and custom config
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = "/path/to/custom.env"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor
        mock_auto_processor = MagicMock()
        mock_auto_processor.process_messages.return_value = 0
        mock_auto_processor_class.return_value = mock_auto_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify AutoProcessor was called
        mock_auto_processor.process_messages.assert_called_once()

        # Verify exit code is 0 (success)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_with_verbose_flag(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode works with verbose flag for detailed logging
        """
        # Setup mock arguments with --auto flag and verbose
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = True
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor
        mock_auto_processor = MagicMock()
        mock_auto_processor.process_messages.return_value = 0
        mock_auto_processor_class.return_value = mock_auto_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify AutoProcessor was called
        mock_auto_processor.process_messages.assert_called_once()

        # Verify exit code is 0 (success)
        assert exit_code == 0


class TestMainAutoModeExceptionHandling:
    """Test suite for exception handling in automatic mode"""

    @patch('main.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_handles_config_error(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode handles ConfigError correctly
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock Settings to raise ConfigError during instantiation
        from src.config.settings import ConfigError
        mock_settings.side_effect = ConfigError("Invalid configuration")

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify exit code is 1 (error)
        assert exit_code == 1

        # Verify that AutoProcessor was not called due to config error
        mock_auto_processor_class.assert_not_called()

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_handles_keyboard_interrupt(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode handles KeyboardInterrupt correctly
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor to raise KeyboardInterrupt
        mock_auto_processor_instance = MagicMock()
        mock_auto_processor_class.return_value = mock_auto_processor_instance
        mock_auto_processor_instance.process_messages.side_effect = KeyboardInterrupt()

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify exit code is 130 (user interrupt)
        assert exit_code == 130

    @patch('src.config.settings.Settings')
    @patch('main.AutoProcessor')
    @patch('main.parse_arguments')
    def test_auto_mode_handles_generic_exception(self, mock_parse_args, mock_auto_processor_class, mock_settings):
        """
        Test that auto mode handles generic Exception correctly
        """
        # Setup mock arguments with --auto flag
        mock_args = MagicMock()
        mock_args.auto = True
        mock_args.config = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Setup mock AutoProcessor to raise generic Exception
        mock_auto_processor_instance = MagicMock()
        mock_auto_processor_class.return_value = mock_auto_processor_instance
        mock_auto_processor_instance.process_messages.side_effect = Exception("Unexpected error")

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify exit code is 1 (error)
        assert exit_code == 1


class TestMainManualModeBackwardCompatibility:
    """Test suite to ensure backward compatibility with existing manual mode"""

    @patch('src.config.settings.Settings')
    @patch('main.FileProcessor')
    @patch('main.parse_arguments')
    def test_manual_mode_all_required_arguments(self, mock_parse_args, mock_file_processor_class, mock_settings):
        """
        Test that manual mode still requires link, code, and folder arguments
        """
        # Setup mock arguments for manual mode
        mock_args = MagicMock()
        mock_args.auto = False
        mock_args.link = "https://pan.baidu.com/s/abc123"
        mock_args.code = "xyz8"
        mock_args.folder = "documents"
        mock_args.config = None
        mock_args.dry_run = False
        mock_args.verbose = True
        mock_parse_args.return_value = mock_args

        # Setup mock FileProcessor
        mock_file_processor = MagicMock()
        mock_summary = MagicMock()
        mock_summary.total_files = 3
        mock_summary.success_count = 2
        mock_summary.failed_count = 1
        mock_summary.skipped_count = 0
        mock_summary.total_size = 1024 * 1024 * 5
        mock_summary.start_time = None
        mock_summary.end_time = None
        mock_file_processor.process_files.return_value = mock_summary

        # Setup context manager for FileProcessor
        mock_file_processor_class.return_value.__enter__.return_value = mock_file_processor

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify FileProcessor was called with correct arguments
        mock_file_processor.process_files.assert_called_once_with(
            share_link="https://pan.baidu.com/s/abc123",
            code="xyz8",
            folder_name="documents"
        )

        # Verify exit code is 0 (even with some failures)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.FileProcessor')
    @patch('main.parse_arguments')
    def test_manual_mode_dry_run(self, mock_parse_args, mock_file_processor_class, mock_settings):
        """
        Test that manual mode dry-run flag still works
        """
        # Setup mock arguments for dry-run mode
        mock_args = MagicMock()
        mock_args.auto = False
        mock_args.link = "https://pan.baidu.com/s/test"
        mock_args.code = "1234"
        mock_args.folder = "test"
        mock_args.config = None
        mock_args.dry_run = True  # Enable dry-run
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Import and run main function
        import main
        exit_code = main.main()

        # Verify FileProcessor was NOT called in dry-run mode
        mock_file_processor_class.assert_not_called()

        # Verify exit code is 0 (success)
        assert exit_code == 0

    @patch('src.config.settings.Settings')
    @patch('main.parse_arguments')
    def test_manual_mode_missing_arguments_still_validates(self, mock_parse_args, mock_settings):
        """
        Test that manual mode still validates required arguments
        """
        # Setup mock arguments missing required fields
        # The argument parser should catch this, but we're testing the logic
        mock_args = MagicMock()
        mock_args.auto = False
        mock_args.link = None  # Missing required argument
        mock_args.code = "1234"
        mock_args.folder = "test"
        mock_args.config = None
        mock_args.dry_run = False
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        # Import and run main function
        import main

        # The argument parser should handle validation before main() logic
        # This tests that the validation logic is preserved
        exit_code = main.main()

        # Should fail due to missing arguments
        assert exit_code == 1