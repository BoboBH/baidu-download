"""
钉钉消息客户端

参考 FeishuMessageClient 实现，适配钉钉API：
- access_token 获取
- 群消息历史获取
- 指数退避重试机制
- API限流处理
"""

import time
import requests
from typing import Optional, List, Dict, Any
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DingtalkMessageClient:
    """
    钉钉消息客户端

    用于从钉钉开放平台获取消息，支持：
    - access_token 认证
    - 指数退避重试机制
    - 消息历史获取
    - API限流处理
    """

    # API endpoints（待根据实际钉钉API确认）
    TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    MESSAGES_URL = "https://api.dingtalk.com/v1.0/messages/send"  # 待确认

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化钉钉客户端

        Args:
            settings: 配置对象，如果不提供则创建新实例
        """
        self.settings = settings or Settings()
        self.app_key = self.settings.dingtalk_app_key
        self.app_secret = self.settings.dingtalk_app_secret
        self.chat_id = self.settings.dingtalk_chat_id
        self.token: Optional[str] = None
        self.max_retries = 5

        if not self.app_key or not self.app_secret:
            logger.warning("Dingtalk app_key or app_secret is empty")
        if not self.chat_id:
            logger.warning("Dingtalk chat_id is empty")

    def get_access_token(self) -> str:
        """
        获取access_token，使用指数退避重试机制

        Returns:
            access_token

        Raises:
            Exception: 获取token失败时抛出异常
        """
        if self.token:
            return self.token

        url = self.TOKEN_URL
        payload = {
            "appKey": self.app_key,
            "appSecret": self.app_secret
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    # 钉钉响应格式待确认，这里假设与飞书类似
                    if 'accessToken' in data:
                        self.token = data.get('accessToken')
                        logger.info("Successfully obtained access_token")
                        return self.token
                    else:
                        error_msg = data.get("message", "Unknown error")
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
                    raise Exception(f"Failed to get access_token after {self.max_retries} attempts: {e}")

        raise Exception(f"Failed to get access_token after {self.max_retries} attempts")

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        从钉钉群获取消息历史，支持自动重试

        Args:
            limit: 获取消息数量，默认50（钉钉API可能限制实际返回数量）

        Returns:
            消息列表，每个消息包含：
            - content: 消息文本内容
            - sender: 发送者ID
            - time: 时间戳
            - msgtype: 消息类型
            等字段

        Raises:
            Exception: 获取消息失败时抛出异常
        """
        # 确保已获取token
        if not self.token:
            self.get_access_token()

        # 钉钉API端点（已通过测试验证）
        url = f"https://oapi.dingtalk.com/chat/get"
        params = {
            "access_token": self.token,
            "chatId": self.chat_id
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=10)

                # 处理响应
                if response.status_code == 200:
                    data = response.json()

                    # 检查错误码
                    if data.get("errcode") == 0:
                        # 成功响应，提取消息列表
                        chat_info = data.get("chatinfo", {})
                        messages = chat_info.get("message", [])

                        logger.info(f"Successfully retrieved {len(messages)} messages from DingTalk")
                        return messages

                    else:
                        # 处理特定错误
                        errcode = data.get("errcode")
                        errmsg = data.get("errmsg", "Unknown error")

                        # 权限不足错误
                        if errcode == 60011:
                            error_msg = (
                                f"Missing required permission: {errmsg}. "
                                f"Please apply for 'qyapi_chat_read' permission at: "
                                f"https://open-dev.dingtalk.com/appscope/apply"
                            )
                            logger.error(error_msg)
                            raise Exception(error_msg)

                        # 其他可重试错误
                        if self._should_retry_error_by_code(errcode):
                            wait_time = self._calculate_backoff(attempt)
                            logger.warning(
                                f"Message request failed with error code {errcode}: {errmsg}, "
                                f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                            )
                            self._wait_with_backoff(wait_time)
                            continue

                        # 不可重试错误，直接抛出
                        raise Exception(f"API error: {errcode} - {errmsg}")

                else:
                    # HTTP错误处理
                    if self._should_retry_error(response.status_code):
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Message request failed with HTTP status {response.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._wait_with_backoff(wait_time)
                    else:
                        raise Exception(f"HTTP error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Message request failed with exception: {e}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    self._wait_with_backoff(wait_time)
                else:
                    raise Exception(f"Failed to get messages after {self.max_retries} attempts: {e}")

        raise Exception(f"Failed to get messages after {self.max_retries} attempts")

    def _should_retry_error_by_code(self, errcode: int) -> bool:
        """
        根据钉钉错误码判断是否应该重试

        Args:
            errcode: 钉钉API错误码

        Returns:
            是否应该重试
        """
        # 系统繁忙错误（通常5xx错误码对应的errcode）
        if errcode in [500, 503, 504]:
            return True
        # 限流错误
        if errcode == 450:
            return True
        # 权限错误不重试
        if errcode == 60011:
            return False
        # 参数错误不重试
        if errcode in [400, 404, 410]:
            return False

        # 未知错误码，保守起见不重试
        return False

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
