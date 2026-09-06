import os
import re
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

        # 飞书配置
        self.feishu_app_id = os.getenv('FEISHU_APP_ID', '')
        self.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', '')
        self.feishu_chat_id = os.getenv('FEISHU_CHAT_ID', '')
        self.feishu_hours_limit = self._get_int_env('FEISHU_HOURS_LIMIT', default=24)  # 默认24小时

        # 钉钉配置
        self.dingtalk_app_key = os.getenv('DINGTALK_APP_KEY', '')
        self.dingtalk_app_secret = os.getenv('DINGTALK_APP_SECRET', '')
        self.dingtalk_chat_id = os.getenv('DINGTALK_CHAT_ID', '')
        self.dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK', '')

        # 消息处理配置
        self.message_default_extraction_code = os.getenv('MESSAGE_DEFAULT_EXTRACTION_CODE', '0409')
        self.max_message_retries = self._get_int_env('MESSAGE_MAX_RETRIES', default=10)  # 消息最大重试次数

        # 文件夹智能检测配置
        self.enable_folder_detection = os.getenv('ENABLE_FOLDER_DETECTION', 'true').lower() == 'true'
        self.folder_detection_timeout = self._get_int_env('FOLDER_DETECTION_TIMEOUT', default=300)
        self.temp_folder_prefix = os.getenv('TEMP_FOLDER_PREFIX', 'temp_detect_')

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

        # 重试机制配置 (Task 7: 错误处理和重试机制完善)
        self.retry_max_attempts = self._get_int_env('RETRY_MAX_ATTEMPTS', default=3)
        self.retry_base_delay_ms = self._get_int_env('RETRY_BASE_DELAY_MS', default=1000)
        self.retry_max_delay_ms = self._get_int_env('RETRY_MAX_DELAY_MS', default=16000)
        self.retry_exponential_base = self._get_int_env('RETRY_EXPONENTIAL_BASE', default=2)

        # PDF文件大小限制（MB）
        self.max_pdf_size_mb = self._get_int_env('MAX_PDF_SIZE_MB', default=200)

        # 微信公众号配置
        self.wxchat_enabled = os.getenv('WXCHAT_ENABLED', 'false').lower() == 'true'
        self.wxchat_wewe_db_host = os.getenv('WXCHAT_WEWE_DB_HOST', '')
        self.wxchat_wewe_db_port = self._get_int_env('WXCHAT_WEWE_DB_PORT', default=3306)
        self.wxchat_wewe_db_user = os.getenv('WXCHAT_WEWE_DB_USER', '')
        self.wxchat_wewe_db_password = os.getenv('WXCHAT_WEWE_DB_PASSWORD', '')
        self.wxchat_wewe_db_name = os.getenv('WXCHAT_WEWE_DB_NAME', '')
        self.wxchat_sftp_remote_path = os.getenv('WXCHAT_SFTP_REMOTE_PATH', '/wxchat')
        self.wxchat_base_url = os.getenv('WXCHAT_BASE_URL', 'https://mp.weixin.qq.com/s/')
        self.wxchat_pdf_timeout = self._get_int_env('WXCHAT_PDF_TIMEOUT', default=300)
        self.wxchat_image_wait_time = self._get_int_env('WXCHAT_IMAGE_WAIT_TIME', default=20)
        self.wxchat_download_delay = self._get_int_env('WXCHAT_DOWNLOAD_DELAY', default=5)
        # 每篇文章处理后随机延时的上限秒数（实际延时在 [download_delay, download_delay_max] 内随机）
        self.wxchat_download_delay_max = self._get_int_env('WXCHAT_DOWNLOAD_DELAY_MAX', default=10)
        # 浏览器持久化档案目录：保存微信验证后的cookie，供PDF生成浏览器复用以通过反爬
        self.wxchat_browser_profile = os.getenv('WXCHAT_BROWSER_PROFILE', './.wxchat_browser_profile')
        self.wxchat_max_days = self._get_int_env('WXCHAT_MAX_DAYS', default=30)

        # 外部SFTP配置 (可选)
        self.wxchat_external_sftp_host = os.getenv('WXCHAT_EXTERNAL_SFTP_HOST', '')
        self.wxchat_external_sftp_port = self._get_int_env('WXCHAT_EXTERNAL_SFTP_PORT', default=22)
        self.wxchat_external_sftp_username = os.getenv('WXCHAT_EXTERNAL_SFTP_USERNAME', '')
        self.wxchat_external_sftp_password = os.getenv('WXCHAT_EXTERNAL_SFTP_PASSWORD', '')
        self.wxchat_external_sftp_folder = os.getenv('WXCHAT_EXTERNAL_SFTP_FOLDER', '')

        # 排除的公众号名称列表
        exclude_accounts_str = os.getenv('WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS', '')
        self.wxchat_external_exclude_accounts = [
            account.strip() for account in exclude_accounts_str.split(',')
            if account.strip()
        ] if exclude_accounts_str else []

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
        # 处理可能包含注释的情况（如："60 # comment"）
        if value and isinstance(value, str):
            # 移除注释部分（# 及其后面的内容）
            value = value.split('#')[0].strip()
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

        # 验证飞书配置（用于自动化模式）
        self._validate_feishu_config()

        # 验证钉钉配置（用于自动化模式）
        self._validate_dingtalk_config()

        # 验证提取码格式（应该是4位数字）
        if self.message_default_extraction_code:
            if not re.match(r'^\d{4}$', self.message_default_extraction_code):
                raise ConfigError(f"Invalid MESSAGE_DEFAULT_EXTRACTION_CODE format: {self.message_default_extraction_code}. Expected 4 digits.")

        # 验证消息重试次数范围（应该是1-100）
        if not (1 <= self.max_message_retries <= 100):
            raise ConfigError(f"MESSAGE_MAX_RETRIES must be between 1 and 100: {self.max_message_retries}")

        # 验证重试机制配置 (Task 7: 错误处理和重试机制完善)
        if not (1 <= self.retry_max_attempts <= 10):
            raise ConfigError(f"RETRY_MAX_ATTEMPTS must be between 1 and 10: {self.retry_max_attempts}")
        if not (100 <= self.retry_base_delay_ms <= 60000):
            raise ConfigError(f"RETRY_BASE_DELAY_MS must be between 100 and 60000: {self.retry_base_delay_ms}")
        if self.retry_max_delay_ms < self.retry_base_delay_ms:
            raise ConfigError(f"RETRY_MAX_DELAY_MS ({self.retry_max_delay_ms}) must be >= RETRY_BASE_DELAY_MS ({self.retry_base_delay_ms})")
        if not (2 <= self.retry_exponential_base <= 5):
            raise ConfigError(f"RETRY_EXPONENTIAL_BASE must be between 2 and 5: {self.retry_exponential_base}")

        # 验证微信配置（如果启用）
        if self.wxchat_enabled:
            if not self.wxchat_wewe_db_host:
                raise ConfigError("WXCHAT_WEWE_DB_HOST is required when WXCHAT_ENABLED is true")
            if not self.wxchat_wewe_db_user:
                raise ConfigError("WXCHAT_WEWE_DB_USER is required when WXCHAT_ENABLED is true")
            if not self.wxchat_wewe_db_password:
                raise ConfigError("WXCHAT_WEWE_DB_PASSWORD is required when WXCHAT_ENABLED is true")
            if not self.wxchat_wewe_db_name:
                raise ConfigError("WXCHAT_WEWE_DB_NAME is required when WXCHAT_ENABLED is true")

            # 验证数值参数合理性
            if self.wxchat_pdf_timeout < 10 or self.wxchat_pdf_timeout > 300:
                raise ConfigError(f"WXCHAT_PDF_TIMEOUT must be between 10 and 300: {self.wxchat_pdf_timeout}")
            if self.wxchat_image_wait_time < 5 or self.wxchat_image_wait_time > 120:
                raise ConfigError(f"WXCHAT_IMAGE_WAIT_TIME must be between 5 and 120: {self.wxchat_image_wait_time}")
            if self.wxchat_download_delay < 1 or self.wxchat_download_delay > 60:
                raise ConfigError(f"WXCHAT_DOWNLOAD_DELAY must be between 1 and 60: {self.wxchat_download_delay}")
            if self.wxchat_download_delay_max < 1 or self.wxchat_download_delay_max > 300:
                raise ConfigError(f"WXCHAT_DOWNLOAD_DELAY_MAX must be between 1 and 300: {self.wxchat_download_delay_max}")
            if self.wxchat_max_days < 1 or self.wxchat_max_days > 365:
                raise ConfigError(f"WXCHAT_MAX_DAYS must be between 1 and 365: {self.wxchat_max_days}")

    def _validate_feishu_config(self):
        """验证飞书配置的完整性（用于自动化模式）"""
        if self.feishu_app_id and not self.feishu_app_secret:
            raise ConfigError("FEISHU_APP_ID provided but FEISHU_APP_SECRET missing")
        if self.feishu_app_secret and not self.feishu_app_id:
            raise ConfigError("FEISHU_APP_SECRET provided but FEISHU_APP_ID missing")
        if self.feishu_chat_id and not (self.feishu_app_id and self.feishu_app_secret):
            raise ConfigError("FEISHU_CHAT_ID provided but FEISHU_APP_ID or FEISHU_APP_SECRET missing")

    def _validate_dingtalk_config(self):
        """验证钉钉配置的完整性（用于自动化模式）"""
        if self.dingtalk_app_key and not self.dingtalk_app_secret:
            raise ConfigError("DINGTALK_APP_SECRET is required when DINGTALK_APP_KEY is set")
        if self.dingtalk_app_secret and not self.dingtalk_app_key:
            raise ConfigError("DINGTALK_APP_KEY is required when DINGTALK_APP_SECRET is set")

        # 验证钉钉webhook URL格式（如果提供）
        if self.dingtalk_webhook:
            if not self._is_valid_url(self.dingtalk_webhook):
                raise ConfigError(f"Invalid DINGTALK_WEBHOOK URL format: {self.dingtalk_webhook}")

    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式的有效性"""
        try:
            import urllib.parse
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
