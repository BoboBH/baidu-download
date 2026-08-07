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

            # 添加详细日志
            logger.info("=" * 60)
            logger.info(f"📤 准备发送钉钉消息...")
            logger.info(f"🔗 Webhook URL: {self.webhook[:60]}...")
            logger.info(f"📝 消息标题: {title}")
            logger.info(f"📄 消息内容长度: {len(content)} 字符")
            logger.info(f"⏰ 超时设置: {self.TIMEOUT} 秒")
            logger.info("-" * 60)

            response = requests.post(
                self.webhook,
                json=data,
                headers=headers,
                timeout=self.TIMEOUT
            )

            # 详细的响应日志
            logger.info(f"📡 HTTP 状态码: {response.status_code}")
            logger.info(f"📦 响应内容: {response.text[:200]}...")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"🔍 钉钉响应码: {result.get('errcode')}")
                logger.info(f"🔍 钉响应消息: {result.get('errmsg')}")

                if result.get("errcode") == 0:
                    logger.info(f"✅ 成功发送钉钉通知: {title}")
                    logger.info("=" * 60)
                    return True
                else:
                    logger.error(f"❌ 钉钉API错误: errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")
                    logger.error("💡 可能原因:")
                    if result.get('errcode') == 310000:
                        logger.error("   - 关键词验证失败：消息标题不包含配置的关键词")
                        logger.error("   - 解决方案：在钉钉机器人设置中添加关键词 'feedback' 或关闭关键词验证")
                    logger.error("=" * 60)
                    return False
            else:
                logger.error(f"❌ HTTP错误: status={response.status_code}")
                logger.error(f"📦 响应内容: {response.text}")
                logger.error("=" * 60)
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {e}")
            logger.error("=" * 60)
            return False