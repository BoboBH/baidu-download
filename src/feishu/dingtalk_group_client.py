import asyncio
import sys
import os
import json
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
                           is_valid: bool, details: str = "", sender_nick: str = None, sender_id: str = None, conversation_type: int = None):
        """
        发送处理反馈到钉钉群

        Args:
            conversation_title: 群聊名称
            message_content: 原始消息内容
            is_valid: 消息是否有效
            details: 详细信息（成功时显示记录内容，失败时显示错误原因）
            sender_nick: 发送者昵称（可选）
            sender_id: 发送者ID（可选）
            conversation_type: 会话类型（1=群聊, 2=私聊）
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

            # 根据conversation_title确定聊天显示名称
            if conversation_title:
                # 有群名称，显示群名
                chat_display = conversation_title
            else:
                # 无群名称，根据其他信息判断
                chat_display = "钉钉群" if conversation_type == 1 else "私聊"

            if is_valid:
                title = "消息成功"
                content = f"""## 消息处理成功

**聊天**: {chat_display}
**消息**: {message_content[:50]}...
**状态**: 已记录到数据库，等待处理

{details}
"""
            else:
                title = "消息失败"
                content_lines = [
                    "## 消息处理失败",
                    "",
                    f"**聊天**: {chat_display}",
                    f"**消息**: {message_content[:50]}...",
                    f"**原因**: {details}",
                    ""
                ]

                # 添加发送者信息（如果可用）
                if sender_nick:
                    content_lines.append(f"**发送者**: {sender_nick}")
                    if sender_id:
                        content_lines.append(f"")
                    content_lines.append("")

                content_lines.extend([
                    "## 📝 使用说明",
                    "",
                    "### 文件消息（PDF/ZIP）",
                    "**必须单独发送给机器人**，不支持群聊处理",
                    "",
                    "### 文本消息",
                    "- 群聊：@机器人发送",
                    "- 私聊：直接发送",
                    "",
                    "## 支持的消息格式",
                    "",
                    "### 1. 百度网盘链接",
                    "```",
                    "https://pan.baidu.com/s/1aBcDeFgHiJkLmNoPqRsTu 提取码: 260723",
                    "```",
                    "",
                    "### 2. PDF文件",
                    "**私发给机器人**：直接上传PDF文件",
                    "",
                    "### 3. PDF链接",
                    "```",
                    "https://example.com/document.pdf",
                    "```",
                    "",
                    "### 4. ZIP文件",
                    "**私发给机器人**：直接上传ZIP文件",
                    "",
                    "### 5. 微信文章链接",
                    "```",
                    "https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ",
                    "```",
                    "",
                    "请检查消息格式后重新发送。"
                ])

                content = "\n".join(content_lines)

            logger.info(f"📝 反馈标题: {title}")
            logger.info(f"📄 反馈内容: {content[:100]}...")

            # 异步发送，不阻塞主流程（兼容Python 3.8）
            loop = asyncio.get_running_loop()
            logger.info(f"🔄 开始异步发送...")

            # 先发送webhook群消息
            webhook_result = await loop.run_in_executor(
                None,
                self.notifier.send_notification,
                title,
                content
            )

            if webhook_result:
                logger.info(f"✅ 反馈消息发送成功: {title}")

                # 🔥 如果有发送者信息，用相同的内容发送私信
                if sender_id:
                    logger.info(f"📤 准备发送私信给发送者: {sender_id}（复用webhook内容）")

                    # 个性化称呼（如果需要）
                    private_content = content
                    if sender_nick:
                        private_content = f"@{sender_nick} " + content

                    private_result = await loop.run_in_executor(
                        None,
                        self.notifier.send_private_message,
                        sender_id,
                        title,
                        private_content
                    )

                    if private_result:
                        logger.info(f"✅ 发送者私信发送成功: {sender_id}")
                    else:
                        logger.warning(f"⚠️ 发送者私信发送失败: {sender_id}")
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

        # 🔍 显示支持的消息类型
        supported_types = "📋 支持的消息类型:\n" \
                          "  1. 百度网盘链接 (baidupan): https://pan.baidu.com/s/xxx?pwd=xxx\n" \
                          "  2. PDF链接 (pdf_link): https://example.com/file.pdf\n" \
                          "  3. 钉钉PDF文件 (dingtalk_pdf): 直接上传PDF文件\n" \
                          "  4. 钉钉ZIP文件 (dingtalk_zip): 直接上传ZIP文件"

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
            # 🤖 接收消息的机器人身份：robotUserId 即回调里的 chatbotUserId
            logger.info(f"接收机器人: RobotCode={chatbot_message.robot_code}, RobotUserId={chatbot_message.chatbot_user_id}")

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

            elif chatbot_message.message_type == 'file':
                # 文件消息处理 - 支持PDF和ZIP
                logger.info("📎 文件消息检测到")
                logger.info("=" * 80)
                logger.info(f"🔍 DETAILED FILE MESSAGE INFORMATION:")

                # 尝试获取 file 对象（可能为 None）
                file_obj = getattr(chatbot_message, 'file', None)
                logger.info(f"File object: {file_obj}")
                if file_obj and hasattr(file_obj, '__dict__'):
                    logger.info(f"File attributes: {file_obj.__dict__}")
                else:
                    logger.info("File object is None or has no attributes, checking extensions.content")

                # 🔍 关键修复：钉钉文件消息数据在 content 字段中，不是在 file 对象中
                # 从用户提供的样本：extensions.content.fileName, extensions.content.fileId 等
                message_data = {}

                # 先尝试从 file 对象直接获取属性（兼容旧SDK）
                file_name = None
                file_id = None
                space_id = None
                download_code = None

                if hasattr(file_obj, 'file_name'):
                    file_name = file_obj.file_name
                elif hasattr(file_obj, 'fileName'):
                    file_name = file_obj.fileName
                elif hasattr(file_obj, 'name'):
                    file_name = file_obj.name

                if hasattr(file_obj, 'file_id'):
                    file_id = file_obj.file_id
                elif hasattr(file_obj, 'fileId'):
                    file_id = file_obj.fileId

                if hasattr(file_obj, 'space_id'):
                    space_id = file_obj.space_id
                elif hasattr(file_obj, 'spaceId'):
                    space_id = file_obj.spaceId

                if hasattr(file_obj, 'download_code'):
                    download_code = file_obj.download_code
                elif hasattr(file_obj, 'downloadCode'):
                    download_code = file_obj.downloadCode

                # 🔍 如果 file 对象没有数据，尝试从 extensions.content 获取（新SDK格式）
                if not all([file_name, file_id, space_id, download_code]):
                    logger.info("🔍 file 对象属性不完整，尝试从 extensions.content 获取数据")

                    # 尝试访问 extensions.content 字段
                    extensions_content = None
                    if hasattr(chatbot_message, 'extensions'):
                        extensions = chatbot_message.extensions
                        if isinstance(extensions, dict) and 'content' in extensions:
                            extensions_content = extensions['content']

                    if extensions_content and isinstance(extensions_content, dict):
                        logger.info(f"🔍 extensions.content 数据: {list(extensions_content.keys())}")

                        # 从 extensions.content 提取字段
                        if not file_name and 'fileName' in extensions_content:
                            file_name = extensions_content['fileName']
                        if not file_id and 'fileId' in extensions_content:
                            file_id = extensions_content['fileId']
                        if not space_id and 'spaceId' in extensions_content:
                            space_id = extensions_content['spaceId']
                        if not download_code and 'downloadCode' in extensions_content:
                            download_code = extensions_content['downloadCode']

                # 构建最终的 message_data（使用驼峰命名）
                if file_name:
                    message_data['fileName'] = file_name
                if file_id:
                    message_data['fileId'] = file_id
                if space_id:
                    message_data['spaceId'] = space_id
                if download_code:
                    message_data['downloadCode'] = download_code

                logger.info(f"🔍 提取的文件数据 (驼峰命名): {message_data}")
                logger.info(f"📋 字段详情 - fileName={file_name}, fileId={file_id}, spaceId={space_id}, downloadCode={download_code}")

                # 🔍 检查必需字段是否完整
                missing_fields = []
                if not file_name:
                    missing_fields.append('fileName')
                if not file_id:
                    missing_fields.append('fileId')
                if not space_id:
                    missing_fields.append('spaceId')
                if not download_code:
                    missing_fields.append('downloadCode')

                if missing_fields:
                    logger.warning(f"⚠️  文件数据缺少必需字段: {', '.join(missing_fields)}")
                    logger.warning(f"🔍 实际数据结构: file_obj={file_obj}, extensions={getattr(chatbot_message, 'extensions', 'N/A')}")

                logger.info("=" * 80)

                # 🔥 对于钉钉文件消息，直接传递文件信息给解析器
                if message_data:
                    logger.info(f"📎 钉钉文件消息，直接使用文件信息解析")
                    parse_result = self.parser.parse_message("", source='dingtalk', message_data=message_data)
                else:
                    # 其他消息类型，正常解析
                    parse_result = self.parser.parse_message(message_content, source='dingtalk', message_data=message_data)

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
                logger.warning(f"⏭️  不支持的消息类型: {chatbot_message.message_type}")
                logger.warning(f"{supported_types}")
                self.total_skipped += 1

                # 发送不支持消息类型的反馈
                unsupported_details = f"""不支持的消息类型：{chatbot_message.message_type}

支持的消息类型：
1. 百度网盘链接：https://pan.baidu.com/s/xxx?pwd=xxx
2. PDF链接：https://example.com/file.pdf
3. 钉钉PDF文件：直接上传PDF文件
4. 钉钉ZIP文件：直接上传ZIP文件

请发送支持的消息类型。
"""

                await self.send_feedback(
                    chatbot_message.conversation_title or "钉钉群",
                    f"不支持的类型: {chatbot_message.message_type}",
                    is_valid=False,
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type,  # 添加会话类型
                    details=unsupported_details
                )
                return AckMessage.STATUS_OK, "OK"

            logger.info(f"消息内容: {message_content}")
            logger.info(f"@机器人: {chatbot_message.is_in_at_list}")
            logger.info(f"会话类型: {chatbot_message.conversation_type} (1=群聊, 2=私聊)")

            # 检查是否需要@机器人（根据会话类型）
            # conversation_type=1 可能是群聊或某些私聊，conversation_type=2 是标准私聊
            # 私定策略：只检查明确的群聊需要@机器人，其他情况都允许处理
            is_group_chat = (chatbot_message.conversation_type == 1 and chatbot_message.conversation_title is not None)

            if is_group_chat and chatbot_message.is_in_at_list is not True:
                logger.info(f"⚠️  群聊消息未@机器人 (is_in_at_list={chatbot_message.is_in_at_list})，跳过")

                # 发送未@机器人的反馈提示
                await self.send_feedback(
                    chatbot_message.conversation_title or "钉钉群",
                    message_content if message_content else "文件消息",
                    is_valid=False,
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type,  # 添加会话类型
                    details="群聊消息未@机器人，无法处理。请在消息中@机器人以触发处理。"
                )

                self.total_skipped += 1
                return AckMessage.STATUS_OK, "OK"

            # 私聊消息或已@机器人的群聊消息
            if is_group_chat:
                logger.info(f"✅ 群聊消息已@机器人，继续处理")
            else:
                logger.info(f"✅ 私聊消息 (conversation_type={chatbot_message.conversation_type})，无需@机器人，继续处理")

            self.total_at_bot += 1

            # 解析消息内容，支持文本消息和文件消息
            parse_result = self.parser.parse_message(message_content, source='dingtalk', message_data=message_data)

            if not parse_result:
                logger.info(f"⚠️  消息不包含支持的链接或文件，跳过: {message_content[:50]}...")
                logger.warning(f"{supported_types}")
                self.total_skipped += 1

                # 发送无效消息反馈 - 显示支持的消息类型
                error_details = f"""消息不包含支持的类型。

支持的消息类型：
1. 百度网盘链接：https://pan.baidu.com/s/xxx?pwd=xxx
2. PDF链接：https://example.com/file.pdf
3. 钉钉PDF文件：直接上传PDF文件
4. 钉钉ZIP文件：直接上传ZIP文件

请确保：
- 文本消息包含支持的链接格式
- 文件消息为PDF或ZIP格式
- 必须在消息中@机器人
"""

                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content if message_content else "文件消息",
                    is_valid=False,
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type,  # 添加会话类型
                    details=error_details
                )
                return AckMessage.STATUS_OK, "OK"

            # 检查是否为钉钉消息
            if parse_result.source != 'dingtalk':
                logger.warning(f"Unexpected message source: {parse_result.source}")
                self.total_skipped += 1

                # 发送非钉钉消息源的反馈
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content if message_content else "文件消息",
                    is_valid=False,
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type,  # 添加会话类型
                    details=f"消息源异常：{parse_result.source}，当前仅支持钉钉消息源"
                )
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
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type,  # 添加会话类型
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
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    sender_nick=chatbot_message.sender_nick,
                    message_type='baidupan',  # 设置消息类型
                    raw_message=json.dumps({
                        'conversation_id': chatbot_message.conversation_id,
                        'conversation_title': chatbot_message.conversation_title,
                        'sender_id': chatbot_message.sender_id,
                        'sender_nick': chatbot_message.sender_nick,
                        'message_type': chatbot_message.message_type,
                        'content': message_content,
                        'is_in_at_list': chatbot_message.is_in_at_list,
                        'sender_staff_id': getattr(chatbot_message, 'sender_staff_id', None)
                    }, ensure_ascii=False),
                    process_status='pending',
                    processing_time_ms=processing_time_ms
                )
            elif parse_result.is_dingtalk_file():
                # 钉钉文件消息 - 统一使用 share_link 字段存储文件标识符
                # 格式：dingtalk:file_id:space_id:download_code
                dingtalk_file_id = f"dingtalk:{parse_result.file_id}:{parse_result.space_id}:{parse_result.download_code}"

                # 根据文件扩展名确定消息类型
                file_type = 'dingtalk_pdf' if parse_result.file_name.lower().endswith('.pdf') else 'dingtalk_zip'

                message_log = MessageProcessLog(
                    message_hash=message_hash,
                    original_message=f"钉钉文件: {parse_result.file_name}",
                    share_link=dingtalk_file_id,  # 统一使用 share_link 字段
                    folder_name=parse_result.file_name,  # 使用文件名作为folder_name
                    extraction_code=parse_result.download_code,  # 使用download_code作为extraction_code
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    sender_nick=chatbot_message.sender_nick,
                    source='dingtalk',
                    message_type=file_type,  # 设置消息类型：dingtalk_pdf 或 dingtalk_zip
                    raw_message=json.dumps({
                        'conversation_id': chatbot_message.conversation_id,
                        'conversation_title': chatbot_message.conversation_title,
                        'sender_id': chatbot_message.sender_id,
                        'sender_nick': chatbot_message.sender_nick,
                        'message_type': chatbot_message.message_type,
                        'file_name': parse_result.file_name,
                        'file_id': parse_result.file_id,
                        'space_id': parse_result.space_id,
                        'download_code': parse_result.download_code,
                        'is_in_at_list': chatbot_message.is_in_at_list,
                        'sender_staff_id': getattr(chatbot_message, 'sender_staff_id', None)
                    }, ensure_ascii=False),
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
                    message_type=parse_result.message_type,  # 使用解析结果的消息类型（pdf_link等）
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    sender_nick=chatbot_message.sender_nick,
                    raw_message=json.dumps({
                        'conversation_id': chatbot_message.conversation_id,
                        'conversation_title': chatbot_message.conversation_title,
                        'sender_id': chatbot_message.sender_id,
                        'sender_nick': chatbot_message.sender_nick,
                        'message_type': chatbot_message.message_type,
                        'content': message_content,
                        'is_in_at_list': chatbot_message.is_in_at_list,
                        'sender_staff_id': getattr(chatbot_message, 'sender_staff_id', None)
                    }, ensure_ascii=False),
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
                    details=f"已记录百度网盘链接: {folder_display}",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
                )
            elif parse_result.is_dingtalk_pdf():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    f"钉钉文件: {parse_result.file_name}",
                    is_valid=True,
                    details=f"已记录钉钉PDF文件: {parse_result.file_name}",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
                )
            elif parse_result.is_dingtalk_zip():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    f"钉钉文件: {parse_result.file_name}",
                    is_valid=True,
                    details=f"已记录钉钉ZIP文件: {parse_result.file_name}",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
                )
            elif parse_result.is_pdf_link():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content,
                    is_valid=True,
                    details=f"已记录PDF链接: {parse_result.pdf_url[:50]}...",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
                )
            elif parse_result.is_wxchat_article():
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content,
                    is_valid=True,
                    details=f"已记录微信文章: {parse_result.wxchat_article_id[:30]}...",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
                )
            else:
                # 通用消息
                await self.send_feedback(
                    chatbot_message.conversation_title,
                    message_content if message_content else "文件消息",
                    is_valid=True,
                    details=f"已记录消息: {parse_result.message_type}",
                    sender_nick=chatbot_message.sender_nick,
                    sender_id=chatbot_message.sender_staff_id or chatbot_message.sender_id,  # 优先使用sender_staff_id
                    conversation_type=chatbot_message.conversation_type  # 添加会话类型
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
        logger.info("📝 支持格式:")
        logger.info("   - 百度网盘: https://pan.baidu.com/s/xxx 提取码: xxx")
        logger.info("   - PDF文件: 直接上传PDF")
        logger.info("   - PDF链接: https://example.com/file.pdf")
        logger.info("   - ZIP文件: 直接上传ZIP")
        logger.info("   - 微信文章: https://mp.weixin.qq.com/s/xxx")
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
