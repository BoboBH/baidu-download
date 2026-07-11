import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class ConfigError(Exception):
    """配置错误异常"""
    pass

class Settings:
    """配置管理类，从环境变量加载配置"""

    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置

        Args:
            env_file: 环境变量文件路径，默认为.env
        """
        # 加载环境变量
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # 验证和加载配置
        self._load_config()

    def _load_config(self):
        """加载并验证所有配置"""
        # SFTP配置
        self.sftp_host = self._get_required_env('SFTP_HOST')
        self.sftp_port = self._get_int_env('SFTP_PORT', default=22)
        self.sftp_username = self._get_required_env('SFTP_USERNAME')
        self.sftp_password = self._get_required_env('SFTP_PASSWORD')
        self.sftp_remote_path = self._get_required_env('SFTP_REMOTE_PATH')

        # 数据库配置
        self.db_host = self._get_required_env('DB_HOST')
        self.db_port = self._get_int_env('DB_PORT', default=3306)
        self.db_user = self._get_required_env('DB_USER')
        self.db_password = self._get_required_env('DB_PASSWORD')
        self.db_name = self._get_required_env('DB_NAME')

        # 百度网盘配置
        self.baidupcs_go_path = self._get_required_env('BAIDUPCS_GO_PATH')
        self.baidu_cookies_path = os.getenv('BAIDU_COOKIES_PATH', './baidu-cookies.txt')
        self.temp_dir = os.getenv('TEMP_DIR', './temp')

        # 日志配置
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', './logs/transfer.log')

        # 性能配置
        self.max_retries = self._get_int_env('MAX_RETRIES', default=3)
        self.concurrent_uploads = self._get_int_env('CONCURRENT_UPLOADS', default=1)

        # 验证关键配置
        self._validate_config()

    def _get_required_env(self, key: str) -> str:
        """获取必需的环境变量"""
        value = os.getenv(key)
        if not value:
            raise ConfigError(f"Missing required environment variable: {key}")
        return value

    def _get_int_env(self, key: str, default: int = 0) -> int:
        """获取整数类型的环境变量"""
        value = os.getenv(key, str(default))
        try:
            return int(value)
        except ValueError:
            raise ConfigError(f"Invalid integer value for {key}: {value}")

    def _validate_config(self):
        """验证配置的有效性"""
        # 验证BaiduPCS-Go路径
        baidupcs_path = Path(self.baidupcs_go_path)
        if not baidupcs_path.exists():
            raise ConfigError(f"BaiduPCS-Go not found at: {self.baidupcs_go_path}")

        # 验证临时目录
        temp_path = Path(self.temp_dir)
        try:
            temp_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigError(f"Cannot create temp directory: {self.temp_dir}, error: {e}")

        # 验证端口号范围
        if not (1 <= self.sftp_port <= 65535):
            raise ConfigError(f"Invalid SFTP port: {self.sftp_port}")
        if not (1 <= self.db_port <= 65535):
            raise ConfigError(f"Invalid DB port: {self.db_port}")
