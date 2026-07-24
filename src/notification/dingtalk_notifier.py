import requests
from typing import Optional
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DingtalkNotifier:
    """
    钉钉通知客户端

    用于通过钉钉机器人webhook发送markdown格式通知，支持：
    - Markdown格式消息
    - HTTP错误和异常处理
    - 请求超时控制
    """

    # 超时时间（秒）
    TIMEOUT = 10

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化钉钉通知客户端

        Args:
            settings: 配置对象，如果不提供则创建新实例
        """
        self.settings = settings or Settings()
        self.webhook = self.settings.dingtalk_webhook

        if not self.webhook:
            logger.warning("DingTalk webhook is not configured")

    def send_notification(self, title: str, content: str) -> bool:
        """
        发送钉钉通知

        Args:
            title: 通知标题
            content: markdown格式的通知内容

        Returns:
            bool: 发送成功返回True，失败返回False
        """
        # 输入验证
        if not title or not content:
            logger.error("Title and content are required")
            return False

        if not self.webhook:
            logger.error("DingTalk webhook is not configured")
            return False

        # 构建请求数据
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            }
        }

        try:
            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.webhook,
                json=data,
                headers=headers,
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info(f"Successfully sent DingTalk notification: {title}")
                    return True
                else:
                    logger.error(f"DingTalk API error: errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")
                    return False
            else:
                logger.error(f"HTTP error: status={response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send DingTalk notification: {e}")
            return False