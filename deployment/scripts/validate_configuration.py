#!/usr/bin/env python3
"""
Configuration Validation Script for Message Retry Limit Feature

This script validates the application configuration for the message retry limit feature,
ensuring all required settings are present and within valid ranges.

Usage:
    python validate_configuration.py [--env-file .env]

Exit Codes:
    0: Configuration valid
    1: Configuration errors found
    2: Missing configuration file
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple


class ConfigurationValidator:
    """Validates application configuration for retry limit feature"""

    def __init__(self, env_file: str = '.env'):
        self.env_file = env_file
        self.errors = []
        self.warnings = []
        self.passed_checks = []

    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ ERROR: {message}")
        self.errors.append(message)

    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  WARNING: {message}")
        self.warnings.append(message)

    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
        self.passed_checks.append(message)

    def validate_env_file(self) -> bool:
        """Validate environment file exists and is readable"""
        self.print_header("Environment File Validation")

        if not Path(self.env_file).exists():
            self.print_error(f"Environment file not found: {self.env_file}")
            return False

        self.print_success(f"Environment file found: {self.env_file}")

        # Check file is readable
        try:
            with open(self.env_file, 'r') as f:
                content = f.read()
            self.print_success("Environment file is readable")
            return True
        except Exception as e:
            self.print_error(f"Cannot read environment file: {str(e)}")
            return False

    def load_env_variables(self) -> Dict[str, str]:
        """Load environment variables from file"""
        self.print_header("Loading Environment Variables")

        env_vars = {}
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                        os.environ[key.strip()] = value.strip()

            self.print_success(f"Loaded {len(env_vars)} environment variables")
            return env_vars
        except Exception as e:
            self.print_error(f"Failed to load environment variables: {str(e)}")
            return {}

    def validate_retry_limit_configuration(self) -> bool:
        """Validate MESSAGE_MAX_RETRIES configuration"""
        self.print_header("Retry Limit Configuration Validation")

        # Check if MESSAGE_MAX_RETRIES is set
        max_retries_str = os.getenv('MESSAGE_MAX_RETRIES')

        if not max_retries_str:
            self.print_error("MESSAGE_MAX_RETRIES not set in environment")
            return False

        self.print_success(f"MESSAGE_MAX_RETRIES is set: {max_retries_str}")

        # Validate it's a valid integer
        try:
            max_retries = int(max_retries_str)
        except ValueError:
            self.print_error(f"MESSAGE_MAX_RETRIES is not a valid integer: {max_retries_str}")
            return False

        self.print_success(f"MESSAGE_MAX_RETRIES is valid integer: {max_retries}")

        # Validate range (1-100)
        if not (1 <= max_retries <= 100):
            self.print_error(f"MESSAGE_MAX_RETRIES out of valid range: {max_retries} (must be 1-100)")
            return False

        self.print_success(f"MESSAGE_MAX_RETRIES within valid range: {max_retries}")

        # Provide recommendations based on value
        if max_retries <= 5:
            self.print_warning("MESSAGE_MAX_RETRIES is conservative (<=5). This may exclude recoverable failures.")
        elif max_retries >= 20:
            self.print_warning("MESSAGE_MAX_RETRIES is aggressive (>=20). This may increase resource usage.")

        return True

    def validate_database_configuration(self) -> bool:
        """Validate database configuration is present"""
        self.print_header("Database Configuration Validation")

        required_db_vars = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        all_present = True

        for var in required_db_vars:
            value = os.getenv(var)
            if not value:
                self.print_error(f"Required database variable not set: {var}")
                all_present = False
            else:
                # Hide sensitive values
                display_value = "***" if 'PASSWORD' in var else value
                self.print_success(f"{var}={display_value}")

        return all_present

    def validate_settings_class(self) -> bool:
        """Validate Settings class can be instantiated"""
        self.print_header("Settings Class Validation")

        try:
            # Try to import Settings class
            from src.config.settings import Settings, ConfigError

            self.print_success("Settings class import successful")

            # Try to instantiate
            try:
                settings = Settings()
                self.print_success("Settings class instantiation successful")

                # Verify max_message_retries property
                max_retries = settings.max_message_retries
                self.print_success(f"Settings.max_message_retries: {max_retries}")

                # Verify it matches environment variable
                env_max_retries = int(os.getenv('MESSAGE_MAX_RETRIES', '0'))
                if max_retries != env_max_retries:
                    self.print_error(f"Settings value ({max_retries}) doesn't match environment ({env_max_retries})")
                    return False

                self.print_success("Settings configuration matches environment variables")

                return True

            except ConfigError as e:
                self.print_error(f"Settings configuration error: {str(e)}")
                return False

        except ImportError as e:
            self.print_error(f"Cannot import Settings class: {str(e)}")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error validating Settings class: {str(e)}")
            return False

    def validate_python_dependencies(self) -> bool:
        """Validate required Python dependencies are available"""
        self.print_header("Python Dependencies Validation")

        required_modules = [
            ('dotenv', 'python-dotenv'),
            ('mysql.connector', 'mysql-connector-python'),
            ('dataclasses', 'built-in'),
        ]

        all_available = True
        for module_name, package_name in required_modules:
            try:
                __import__(module_name)
                self.print_success(f"{module_name} ({package_name}) available")
            except ImportError:
                self.print_error(f"{module_name} ({package_name}) not available")
                all_available = False

        return all_available

    def validate_recommendations(self):
        """Provide configuration recommendations"""
        self.print_header("Configuration Recommendations")

        max_retries_str = os.getenv('MESSAGE_MAX_RETRIES', '10')

        print(f"\n💡 Current MESSAGE_MAX_RETRIES: {max_retries_str}")
        print("\nRecommended settings based on environment:")
        print("  Conservative (high-volume, low-criticality): 5-8 retries")
        print("  Standard (balanced): 10 retries (default)")
        print("  Aggressive (critical messages): 15-20 retries")

        print("\n📋 Configuration best practices:")
        print("  1. Test in staging environment before production")
        print("  2. Monitor retry patterns after deployment")
        print("  3. Adjust based on failure patterns and system load")
        print("  4. Review excluded messages periodically")
        print("  5. Keep backup of configuration before changes")

    def generate_summary(self) -> int:
        """Generate validation summary"""
        self.print_header("Validation Summary")

        total_checks = len(self.passed_checks) + len(self.errors) + len(self.warnings)
        passed = len(self.passed_checks)
        errors = len(self.errors)
        warnings = len(self.warnings)

        print(f"\n📊 Total Checks: {total_checks}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Errors: {errors}")
        print(f"⚠️  Warnings: {warnings}")

        if errors > 0:
            print("\n❌ Configuration validation FAILED - Fix errors before deployment")
            return 1
        elif warnings > 0:
            print("\n⚠️  Configuration validation completed with WARNINGS")
            return 0
        else:
            print("\n✅ Configuration validation PASSED - Ready for deployment")
            return 0

    def run_validation(self) -> int:
        """Run complete configuration validation"""
        print("🔍 Message Retry Limit Feature - Configuration Validation")
        print("=" * 60)

        # Run validation steps
        if not self.validate_env_file():
            return 2  # Missing config file

        self.load_env_variables()
        self.validate_retry_limit_configuration()
        self.validate_database_configuration()
        self.validate_settings_class()
        self.validate_python_dependencies()
        self.validate_recommendations()

        return self.generate_summary()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate configuration for Message Retry Limit Feature'
    )
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Path to environment file (default: .env)'
    )

    args = parser.parse_args()

    validator = ConfigurationValidator(args.env_file)
    return validator.run_validation()


if __name__ == '__main__':
    sys.exit(main())