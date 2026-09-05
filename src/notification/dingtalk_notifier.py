import requests
import urllib3
from typing import Optional, Dict
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 禁用SSL警告（仅用于钉钉webhook，这是安全的外部API调用）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DingtalkNotifier:
    """
    钉钉通知客户端

    用于通过钉钉机器人webhook和OpenAPI发送通知，支持：
    - Webhook群聊通知（逐步废弃）
    - OpenAPI私信通知
    - Markdown格式消息
    - HTTP错误和异常处理
    - 请求超时控制
    """

    # 超时时间（秒）
    TIMEOUT = 10

    # 钉钉OpenAPI配置
    OAPI_BASE_URL = "https://api.dingtalk.com"
    TOKEN_URL = f"{OAPI_BASE_URL}/gettoken"
    SEND_MESSAGE_URL = f"{OAPI_BASE_URL}/v1.0/robot/oToMessages/batchSend"

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化钉钉通知客户端

        Args:
            settings: 配置对象，如果不提供则创建新实例
        """
        self.settings = settings or Settings()
        self.webhook = self.settings.dingtalk_webhook
        self.app_key = self.settings.dingtalk_app_key
        self.app_secret = self.settings.dingtalk_app_secret
        self.access_token = None
        self.token_expires_at = None

        if not self.webhook:
            logger.warning("DingTalk webhook is not configured")

        if not self.app_key or not self.app_secret:
            logger.warning("DingTalk OpenAPI credentials (app_key/app_secret) not configured")

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
                timeout=self.TIMEOUT,
                verify=False  # 禁用SSL验证，解决钉钉webhook SSL连接问题
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

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {e}")
            logger.error("=" * 60)
            return False

    def _get_access_token(self) -> Optional[str]:
        """
        获取钉钉OpenAPI access_token

        Returns:
            access_token or None
        """
        if not self.app_key or not self.app_secret:
            logger.error("DingTalk app_key or app_secret not configured")
            return None

        # 检查token是否过期
        if self.access_token and self.token_expires_at:
            import time
            if time.time() < self.token_expires_at:
                logger.debug(f"Using cached access_token (expires in {self.token_expires_at - time.time():.0f}s)")
                return self.access_token

        try:
            logger.info("获取钉钉access_token...")
            params = {
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            response = requests.get(
                self.TOKEN_URL,
                params=params,
                timeout=self.TIMEOUT,
                verify=False  # 禁用SSL验证
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    self.access_token = result.get("access_token")
                    # token有效期7200秒(2小时)，提前5分钟过期
                    import time
                    self.token_expires_at = time.time() + 7150
                    logger.info(f"✅ 成功获取access_token")
                    return self.access_token
                else:
                    logger.error(f"❌ 获取access_token失败: {result.get('errmsg')}")
                    return None
            else:
                logger.error(f"❌ 获取access_tokenHTTP错误: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取access_token异常: {e}")
            return None

    def send_private_message(self, user_id: str, title: str, content: str) -> bool:
        """
        发送钉钉私信给指定用户（独立方法，供两个场景调用）

        Args:
            user_id: 接收者用户ID
            title: 消息标题
            content: markdown格式的消息内容

        Returns:
            bool: 发送成功返回True，失败返回False
        """
        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取access_token，私信发送失败")
            return False

        try:
            # 构建请求数据 - 使用正确的钉钉机器人私信格式
            # 尝试使用Markdown格式
            data = {
                "robotCode": self.app_key,
                "userIds": [user_id],
                "msgKey": "sampleMarkdown",
                "msgParam": f'{{"title":"{title}","text":"{content}"}}'
            }

            headers = {
                "Content-Type": "application/json",
                "x-acs-dingtalk-access-token": access_token
            }

            logger.info("=" * 60)
            logger.info(f"📤 准备发送钉钉私信...")
            logger.info(f"👤 用户ID: {user_id}")
            logger.info(f"📝 消息标题: {title}")
            logger.info(f"📄 消息内容长度: {len(content)} 字符")
            logger.info(f"🔗 请求URL: {self.SEND_MESSAGE_URL}")
            logger.info(f"🤖 RobotCode: {self.app_key}")
            logger.info(f"🔑 Access Token: {access_token[:20]}...{access_token[-10:]}")
            logger.info(f"📦 请求数据: robotCode={data['robotCode']}, userIds={data['userIds']}, msgKey={data['msgKey']}")
            logger.info(f"📝 msgParam长度: {len(data['msgParam'])} 字符")

            response = requests.post(
                self.SEND_MESSAGE_URL,
                json=data,
                headers=headers,
                timeout=self.TIMEOUT,
                verify=False  # 禁用SSL验证
            )

            logger.info(f"📡 HTTP 状态码: {response.status_code}")
            logger.info(f"📦 响应头: {dict(response.headers)}")
            logger.info(f"📦 响应内容长度: {len(response.content)} 字节")

            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 钉钉完整响应: {result}")
                    logger.info(f"🔍 钉钉响应码: {result.get('errcode')}")
                    logger.info(f"🔍 钉响应消息: {result.get('errmsg')}")

                    # 钉钉私信API有两种成功响应格式：
                    # 1. 同步格式: {"errcode": 0, "errmsg": "ok"}
                    # 2. 异步格式: {"processQueryKey": "...", "invalidStaffIdList": []}

                    is_success = False

                    # 检查同步成功格式
                    if result.get("errcode") == 0:
                        is_success = True
                        logger.info("✅ 识别为同步成功响应格式")
                    # 检查异步提交成功格式
                    elif "processQueryKey" in result:
                        invalid_list = result.get("invalidStaffIdList", [])
                        filtered_list = result.get("filteredStaffIdList", [])
                        # 如果没有无效或过滤的userId，认为提交成功
                        if not invalid_list and not filtered_list:
                            is_success = True
                            logger.info("✅ 识别为异步提交成功响应格式")
                            logger.info(f"📝 处理查询键: {result.get('processQueryKey')}")
                        else:
                            logger.error(f"❌ 用户ID无效或被过滤: invalid={invalid_list}, filtered={filtered_list}")
                    else:
                        logger.error(f"❌ 未知的响应格式")

                    if is_success:
                        logger.info(f"✅ 成功发送钉钉私信: {title} -> 用户{user_id}")
                        logger.info("=" * 60)
                        return True
                    else:
                        logger.error(f"❌ 钉钉API错误或用户ID无效")
                        logger.error(f"📦 完整响应内容: {result}")
                        logger.error("=" * 60)
                        return False

                except Exception as e:
                    logger.error(f"❌ JSON解析失败: {e}")
                    logger.error(f"📦 原始响应内容: {response.text[:1000]}")
                    logger.error(f"📦 响应内容类型: {response.headers.get('content-type')}")
                    logger.error("=" * 60)
                    return False
            else:
                logger.error(f"❌ HTTP错误: status={response.status_code}")
                logger.error(f"📦 响应内容: {response.text[:1000]}")
                logger.error("=" * 60)
                return False

        except Exception as e:
            logger.error(f"❌ 发送私信异常: {e}")
            logger.error("=" * 60)
            return False


        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {e}")
            logger.error("=" * 60)
            return False