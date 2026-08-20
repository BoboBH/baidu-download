import asyncio
import sys
import os
from datetime import datetime
from dingtalk_stream import AckMessage, DingTalkStreamClient, ChatbotMessage, Credential, CallbackHandler, CallbackMessage

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.feishu.message_parser import MessageParser
from src.database.message_models import MessageProcessLog
from src.database.repository import DatabaseRepository
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MessageHandler(CallbackHandler):
    def __init__(self, settings: Settings = None):
        super().__init__()

        # 初始化组件
        self.parser = MessageParser()
        self.settings = settings or Settings()

        # 初始化消息发送功能（用于反馈）
        if self.settings.dingtalk_webhook:
            from src.notification.dingtalk_notifier import DingtalkNotifier
            self.notifier = DingtalkNotifier(self.settings)
            logger.info("消息反馈功能已启用")
        else:
            self.notifier = None
            logger.warning("未配置Webhook，消息反馈功能不可用")

        # 初始化统一路由器用于多消息类型处理
        try:
            from src.processor.parsers.router import ProcessorRouter
            self.router = ProcessorRouter(self.settings)
            logger.info("统一路由器已初始化")
        except ImportError as e:
            self.router = None
            logger.warning(f"无法导入统一路由器: {e}")

        # 消息统计
        self.total_received = 0
        self.total_processed = 0
        self.total_skipped = 0
        self.total_errors = 0
        self.total_at_bot = 0  # @机器人的消息数

        logger.info("MessageHandler initialized successfully")
        logger.info("消息要求：必须@机器人才会处理")
        logger.info("支持消息类型：百度网盘链接、PDF链接、钉钉文件(PDF/ZIP)")

    async def send_feedback(self, conversation_title: str, message_content: str,
                           is_valid: bool, details: str = ""):
        """
        发送处理反馈到钉钉群

        Args:
            conversation_title: 群聊名称
            message_content: 原始消息内容
            is_valid: 消息是否有效
            details: 详细信息（成功时显示记录内容，失败时显示错误原因）
        """
        if not self.notifier:
            logger.warning("⚠️  未配置通知器，无法发送反馈消息")
            return

        try:
            logger.info("=" * 60)
            logger.info(f"🎯 准备发送反馈消息...")
            logger.info(f"📱 群聊: {conversation_title}")
            logger.info(f"💬 原消息: {message_content[:50]}...")
            logger.info(f"✅ 有效: {is_valid}")
            logger.info(f"📋 详情: {details}")

            if is_valid:
                title = "feedback: 收到有效百度网盘链接"
                content = f"""## 消息处理成功

**群聊**: {conversation_title}
**消息**: {message_content[:50]}...
**状态**: 已记录到数据库，等待处理

{details}
"""
            else:
                title = "feedback: 消息格式无效"
                content = f"""## 消息处理失败

**群聊**: {conversation_title}
**消息**: {message_content[:50]}...
**原因**: {details}

请检查消息格式，正确格式：`260723：https://pan.baidu.com/s/xxx`
"""

            logger.info(f"📝 反馈标题: {title}")
            logger.info(f"📄 反馈内容: {content[:100]}...")

            # 异步发送，不阻塞主流程（兼容Python 3.8）
            loop = asyncio.get_running_loop()
            logger.info(f"🔄 开始异步发送...")
            result = await loop.run_in_executor(
                None,
                self.notifier.send_notification,
                title,
                content
            )

            if result:
                logger.info(f"✅ 反馈消息发送成功: {title}")
            else:
                logger.error(f"❌ 反馈消息发送失败: {title}")
                logger.error("💡 请检查:")
                logger.error("   1. 钉钉机器人关键词设置")
                logger.error("   2. Webhook URL 配置")
                logger.error("   3. 网络连接状态")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 发送反馈消息异常: {e}")
            logger.error("=" * 60)

    async def process(self, callback_message: CallbackMessage):
        """处理钉钉消息 - 快速响应避免丢消息"""
        start_time = datetime.now()
        self.total_received += 1
        db_repo = None

        try:
            # 🔍 打印原始callback_message完整内容（用于分析文件消息结构）
            logger.info("=" * 80)
            logger.info(f"🔍 RAW CALLBACK MESSAGE (Full Content):")
            logger.info(f"Type: {type(callback_message)}")
            if hasattr(callback_message, 'data'):
                logger.info(f"Data Type: {type(callback_message.data)}")
                logger.info(f"Data Content: {callback_message.data}")
            if hasattr(callback_message, 'topic'):
                logger.info(f"Topic: {callback_message.topic}")
            logger.info("=" * 80)

            # 将 CallbackMessage 的 data 转换为 ChatbotMessage
            chatbot_message = ChatbotMessage.from_dict(callback_message.data)

            # 🔍 详细诊断信息
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            logger.info("=" * 50)
            logger.info(f"⏰ {current_time} - 📨 消息 #{self.total_received}")
            logger.info(f"Conversation ID: {chatbot_message.conversation_id}")
            logger.info(f"群名称: {chatbot_message.conversation_title}")
            logger.info(f"发送者: {chatbot_message.sender_nick} ({chatbot_message.sender_id})")
            logger.info(f"消息类型: {chatbot_message.message_type}")

            # 🔍 打印所有消息类型的完整内容
            logger.info("=" * 80)
            logger.info(f"🔍 FULL CHATBOT MESSAGE ATTRIBUTES:")
            for attr in dir(chatbot_message):
                if not attr.startswith('_'):
                    try:
                        value = getattr(chatbot_message, attr)
                        if not callable(value):
                            logger.info(f"  {attr}: {value}")
                    except Exception as e:
                        logger.info(f"  {attr}: [Error accessing: {e}]")
            logger.info("=" * 80)

            # 初始化消息数据和内容
            message_content = ""
            message_data = None

            # 处理不同类型的消息
            if chatbot_message.message_type == 'text' and chatbot_message.text:
                # 文本消息处理
                message_content = chatbot_message.text.content
                logger.info(f"📝 文本消息内容: {message_content}")
                logger.info(f"@机器人: {chatbot_message.is_in_at_list}")

            elif chatbot_message.message_type == 'file' and hasattr(chatbot_message, 'file') and chatbot_message.file:
                # 文件消息处理 - 支持PDF和ZIP
                logger.info("📎 文件消息检测到")
                logger.info("=" * 80)
                logger.info(f"🔍 DETAILED FILE MESSAGE INFORMATION:")

                file_obj = chatbot_message.file
                logger.info(f"File attributes: {file_obj.__dict__ if hasattr(file_obj, '__dict__') else file_obj}")

                # 构建文件消息数据结构
                message_data = {}
                if hasattr(file_obj, 'file_name'):
                    message_data['fileName'] = file_obj.file_name
                if hasattr(file_obj, 'file_id'):
                    message_data['fileId'] = file_obj.file_id
                if hasattr(file_obj, 'space_id'):
                    message_data['spaceId'] = file_obj.space_id
                if hasattr(file_obj, 'download_code'):
                    message_data['downloadCode'] = file_obj.download_code

                logger.info(f"提取的文件数据: {message_data}")
                logger.info("=" * 80)

                # 使用空字符串作为文件消息的文本内容
                message_content = ""

            else:
                # 🔍 其他非文本消息类型 - 详细打印所有内容
                logger.info(f"🔍 非文本消息类型: {chatbot_message.message_type}")
                logger.info("=" * 80)
                logger.info(f"🔍 DETAILED MESSAGE CONTENT FOR NON-TEXT MESSAGES:")

                # 打印所有可能的属性
                for attr in ['text', 'image', 'file', 'audio', 'video', 'rich']:
                    if hasattr(chatbot_message, attr):
                        attr_value = getattr(chatbot_message, attr)
                        logger.info(f"  {attr}: {attr_value}")
                        if attr_value and hasattr(attr_value, '__dict__'):
                            logger.info(f"    {attr} attributes: {attr_value.__dict__}")

                logger.info("=" * 80)
                logger.info(f"⏭️  不支持的消息类型，跳过处理")
                self.total_skipped += 1
                return AckMessage.STATUS_OK, "OK"

            logger.info(f"消息内容: {message_content}")
            logger.info(f"@机器人: {chatbot_message.is_in_at_list}")

            # 检查是否@机器人（必须）
            if not chatbot_message.is_in_at_list:
                logger.info(f"⚠️  消息未@机器人，跳过")
                self.total_skipped += 1
                return AckMessage.STATUS_OK, "OK"

            self.total_at_bot += 1

            # 解析消息内容，支持文本消息和文件消息
            parse_result = self.parser.parse_message(message_content, source='dingtalk', message_data=message_data)

            if not parse_result:
                logger.info(f"⚠️  消息不包含支持的链接或文件，跳过: {message_content[:50]}...")
                self.total_skipped += 1

                # 发送无效消息反馈
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content if message_content else "文件消息",
                    is_valid=False,
                    details="消息不包含百度网盘链接、PDF链接或支持的文件类型(PDF/ZIP)"
                )
                return AckMessage.STATUS_OK, "OK"

            # 检查是否为钉钉消息
            if parse_result.source != 'dingtalk':
                logger.warning(f"Unexpected message source: {parse_result.source}")
                self.total_skipped += 1
                return AckMessage.STATUS_OK, "OK"

            # 计算文件唯一键 - 根据消息类型使用不同的计算方式
            if parse_result.is_baidupan():
                # 百度网盘消息：使用share_link
                message_hash = self.parser.calculate_file_key(
                    parse_result.message_type,
                    parse_result.unique_identifier
                )
            elif parse_result.is_dingtalk_file():
                # 钉钉文件消息：使用file_id:space_id (已在unique_identifier中)
                message_hash = self.parser.calculate_file_key(
                    parse_result.message_type,
                    parse_result.unique_identifier
                )
            else:
                # 其他消息类型：使用unique_identifier
                message_hash = self.parser.calculate_file_key(
                    parse_result.message_type,
                    parse_result.unique_identifier
                )

            logger.info(f"消息唯一键: {message_hash[:8]}... (类型: {parse_result.message_type})")

            # 🔑 只在需要时才创建数据库连接
            db_repo = DatabaseRepository(
                host=self.settings.db_host,
                port=self.settings.db_port,
                user=self.settings.db_user,
                password=self.settings.db_password,
                database=self.settings.db_name
            )
            logger.debug("数据库连接已创建")

            # 检查消息是否已处理
            existing_message = db_repo.get_message_by_hash(message_hash)
            if existing_message:
                logger.info(f"♻️  消息已处理，跳过: {message_hash[:8]}...")
                self.total_skipped += 1

                # 发送重复消息反馈
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content,
                    is_valid=False,
                    details=f"重复消息，已存在记录。当前状态: {existing_message.process_status}，已重试: {existing_message.retry_count}次"
                )
                return AckMessage.STATUS_OK, "OK"

            # 创建消息处理日志 - 支持多种消息类型
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 根据消息类型设置不同的字段
            if parse_result.is_baidupan():
                # 百度网盘消息
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=message_content,
                    share_link=parse_result.share_link,
                    folder_name=parse_result.folder_name,
                    extraction_code=parse_result.extraction_code,
                    source='dingtalk',
                    process_status='pending',
                    processing_time_ms=processing_time_ms
                )
            elif parse_result.is_dingtalk_file():
                # 钉钉文件消息 - 使用新字段
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=f"钉钉文件: {parse_result.file_name}",
                    share_link=None,  # 钉钉文件没有share_link
                    folder_name=parse_result.file_name,  # 使用文件名作为folder_name
                    extraction_code=parse_result.download_code,  # 使用download_code作为extraction_code
                    source='dingtalk',
                    process_status='pending',
                    processing_time_ms=processing_time_ms
                )
            else:
                # 其他消息类型（如PDF链接）
                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=message_content,
                    share_link=parse_result.share_link,
                    folder_name=parse_result.folder_name,
                    extraction_code=parse_result.extraction_code,
                    source='dingtalk',
                    process_status='pending',
                    processing_time_ms=processing_time_ms
                )

            # 存储到数据库
            log_id = db_repo.insert_message_log(message_log)
            self.total_processed += 1

            logger.info(f"✅ 消息已存储: {parse_result.folder_name} (ID: {log_id})")
            logger.info(f"📊 统计: 收到={self.total_received}, @机器={self.total_at_bot}, 处理={self.total_processed}, 跳过={self.total_skipped}, 错误={self.total_errors}")

            # 发送成功消息反馈 - 根据消息类型显示不同信息
            if parse_result.is_baidupan():
                folder_display = parse_result.folder_name if parse_result.folder_name else "百度网盘链接"
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content,
                    is_valid=True,
                    details=f"已记录百度网盘链接: {folder_display}"
                )
            elif parse_result.is_dingtalk_pdf():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    f"钉钉文件: {parse_result.file_name}",
                    is_valid=True,
                    details=f"已记录钉钉PDF文件: {parse_result.file_name}"
                )
            elif parse_result.is_dingtalk_zip():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    f"钉钉文件: {parse_result.file_name}",
                    is_valid=True,
                    details=f"已记录钉钉ZIP文件: {parse_result.file_name}"
                )
            elif parse_result.is_pdf_link():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content,
                    is_valid=True,
                    details=f"已记录PDF链接: {parse_result.pdf_url[:50]}..."
                )
            else:
                # 通用消息
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content if message_content else "文件消息",
                    is_valid=True,
                    details=f"已记录消息: {parse_result.message_type}"
                )

            return AckMessage.STATUS_OK, "OK"

        except Exception as e:
            self.total_errors += 1
            logger.error(f"❌ 处理消息时出错: {e}", exc_info=True)
            logger.info(f"📊 统计: 收到={self.total_received}, @机器={self.total_at_bot}, 处理={self.total_processed}, 跳过={self.total_skipped}, 错误={self.total_errors}")
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)

        finally:
            # 🔑 立即关闭数据库连接
            if db_repo:
                db_repo.close()
                logger.debug("数据库连接已关闭")

async def main():
    """启动钉钉消息接收客户端"""
    handler = None
    connection_monitor = None

    async def monitor_connection():
        """连接状态监控"""
        while True:
            await asyncio.sleep(30)  # 每30秒报告一次
            if handler:
                logger.info(f"🔗 连接状态 - 📊 统计: 收到={handler.total_received}, @机器={handler.total_at_bot}, 处理={handler.total_processed}, 跳过={handler.total_skipped}, 错误={handler.total_errors}")

    try:
        # 加载配置
        settings = Settings()

        # 验证钉钉配置
        if not settings.dingtalk_app_key or not settings.dingtalk_app_secret:
            logger.error("DINGTALK_APP_KEY and DINGTALK_APP_SECRET must be set in .env file")
            return 1

        # 创建客户端和处理器
        client = DingTalkStreamClient(Credential(settings.dingtalk_app_key, settings.dingtalk_app_secret))
        handler = MessageHandler(settings)
        client.register_callback_handler(ChatbotMessage.TOPIC, handler)

        logger.info("=" * 50)
        logger.info("🚀 DingTalk Message Receiver Service Started!")
        logger.info("📱 消息要求：必须@机器人才会处理")
        logger.info("📝 Supported format: 260723：https://pan.baidu.com/s/xxx")
        logger.info("🔍 每30秒输出连接状态统计")
        logger.info("⏹️  Press Ctrl+C to stop the service")
        logger.info("=" * 50)

        # 启动连接监控
        connection_monitor = asyncio.create_task(monitor_connection())

        # 启动客户端
        await client.start()

    except KeyboardInterrupt:
        logger.info("⏹️  Received shutdown signal, stopping service...")

    except Exception as e:
        logger.error(f"❌ Service error: {e}", exc_info=True)
        return 1

    finally:
        # 取消监控任务
        if connection_monitor:
            connection_monitor.cancel()
        # 清理资源（数据库连接已在每次处理后自动关闭）
        logger.info("✅ Service stopped")

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
