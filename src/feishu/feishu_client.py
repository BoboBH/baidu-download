import time
import requests
from typing import Optional, List, Dict, Any
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeishuMessageClient:
    """
    飞书消息客户端

    用于从飞书开放平台获取消息，支持：
    - tenant_access_token认证
    - 指数退避重试机制
    - 消息历史获取
    - API限流处理
    """

    # API endpoints
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGES_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化飞书客户端

        Args:
            settings: 配置对象，如果不提供则创建新实例
        """
        self.settings = settings or Settings()
        self.app_id = self.settings.feishu_app_id
        self.app_secret = self.settings.feishu_app_secret
        self.chat_id = self.settings.feishu_chat_id
        self.token: Optional[str] = None
        self.max_retries = 5

        if not self.app_id or not self.app_secret:
            logger.warning("Feishu app_id or app_secret is empty")
        if not self.chat_id:
            logger.warning("Feishu chat_id is empty")

    def get_tenant_access_token(self) -> str:
        """
        获取tenant_access_token，使用指数退避重试机制

        Returns:
            tenant_access_token

        Raises:
            Exception: 获取token失败时抛出异常
        """
        if self.token:
            return self.token

        url = self.TOKEN_URL
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        self.token = data.get("tenant_access_token")
                        logger.info("Successfully obtained tenant_access_token")
                        return self.token
                    else:
                        error_msg = data.get("msg", "Unknown error")
                        logger.error(f"API returned error: {error_msg}")
                        raise Exception(f"API error: {error_msg}")
                else:
                    # 5xx错误重试，4xx错误不重试
                    if self._should_retry_error(response.status_code):
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Token request failed with status {response.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._wait_with_backoff(wait_time)
                    else:
                        raise Exception(f"HTTP error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Token request failed with exception: {e}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    self._wait_with_backoff(wait_time)
                else:
                    raise Exception(f"Failed to get tenant_access_token after {self.max_retries} attempts: {e}")

        raise Exception(f"Failed to get tenant_access_token after {self.max_retries} attempts")

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        从指定聊天获取消息历史，支持自动重试

        Args:
            limit: 获取消息数量，默认50

        Returns:
            消息列表

        Raises:
            Exception: 获取消息失败时抛出异常
        """
        if not self.chat_id:
            raise Exception("chat_id is not configured")

        # 确保有token
        if not self.token:
            self.get_tenant_access_token()

        params = {
            "container_id": self.chat_id,
            "container_id_type": "chat",
            "limit": limit
        }

        headers = self._build_request_headers()

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.MESSAGES_URL,
                    params=params,
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        messages = data.get("data", {}).get("items", [])
                        logger.info(f"Successfully retrieved {len(messages)} messages")
                        return messages
                    else:
                        error_msg = data.get("msg", "Unknown error")
                        logger.error(f"API returned error: {error_msg}")
                        raise Exception(f"API error: {error_msg}")
                else:
                    # 处理限流和服务器错误
                    if self._is_rate_limit_error(response.status_code):
                        retry_after = self._extract_retry_after(response)
                        logger.warning(
                            f"Rate limited, retrying after {retry_after}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._wait_with_backoff(retry_after)
                    elif self._should_retry_error(response.status_code):
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Messages request failed with status {response.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._wait_with_backoff(wait_time)
                    else:
                        raise Exception(f"HTTP error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Messages request failed with exception: {e}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    self._wait_with_backoff(wait_time)
                else:
                    raise Exception(f"Failed to get messages after {self.max_retries} attempts: {e}")

        raise Exception(f"Failed to get messages after {self.max_retries} attempts")

    def _build_request_headers(self) -> Dict[str, str]:
        """
        构建请求头

        Returns:
            包含认证信息的请求头
        """
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _is_rate_limit_error(self, status_code: int) -> bool:
        """
        判断是否为限流错误

        Args:
            status_code: HTTP状态码

        Returns:
            是否为限流错误
        """
        return status_code == 429

    def _should_retry_error(self, status_code: int) -> bool:
        """
        判断错误是否应该重试

        Args:
            status_code: HTTP状态码

        Returns:
            是否应该重试
        """
        # 5xx服务器错误应该重试
        if 500 <= status_code < 600:
            return True
        # 429限流错误应该重试
        if status_code == 429:
            return True
        # 其他错误不重试
        return False

    def _calculate_backoff(self, attempt: int) -> int:
        """
        计算指数退避等待时间

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            等待秒数 (1, 2, 4, 8, 16)
        """
        return min(2 ** attempt, 16)

    def _wait_with_backoff(self, wait_time: int) -> None:
        """
        等待指定时间

        Args:
            wait_time: 等待秒数
        """
        logger.debug(f"Waiting for {wait_time} seconds...")
        time.sleep(wait_time)

    def _extract_retry_after(self, response: requests.Response) -> int:
        """
        从响应中提取Retry-After时间

        Args:
            response: HTTP响应对象

        Returns:
            重试等待秒数，默认1秒
        """
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                return 1
        return 1