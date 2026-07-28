"""
飞书消息接收器 - 专职接收和解析飞书消息
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReceiveResult:
    """消息接收结果"""
    total_messages: int
    new_messages: int
    duplicate_messages: int
    failed_messages: int
    processing_time_ms: int
    details: List[Dict[str, Any]]


class MessageReceiver:
    """飞书消息接收器 - 专职接收和解析飞书消息"""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize MessageReceiver with required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance

        Note:
            钉钉消息接收请使用 --dingtalk-service 模式启动 dingtalk_group_client
        """
        self.source = 'feishu'  # 只支持飞书消息
        self.settings = settings or Settings()
        self.logger = logger

        # 使用飞书客户端
        self.client = FeishuMessageClient(self.settings)

        # Initialize components
        self.message_parser = MessageParser()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        self.dingtalk_notifier = DingtalkNotifier(self.settings)

        self.logger.info("MessageReceiver initialized successfully (feishu)")

    def receive_messages(self) -> ReceiveResult:
        """
        接收飞书消息的主要工作流程

        Returns:
            ReceiveResult: 接收结果统计
        """
        try:
            start_time = datetime.now()
            self.logger.info("Starting message receiving process")

            # 从指定来源获取消息
            messages = self.client.get_messages()
            self.logger.info(f"Retrieved {len(messages)} messages from {self.source}")

            results = {
                'new_messages': [],
                'duplicate_messages': [],
                'filtered_messages': []  # 解析失败或格式不正确的消息
            }

            # 处理每条消息
            for message in messages:
                try:
                    # 提取消息内容
                    body = message.get("body", {})
                    if isinstance(body, str):
                        content = body
                    elif isinstance(body, dict):
                        content = body.get("content", "")
                    else:
                        content = ""

                    if not content:
                        self.logger.debug(f"Empty message content for message_id: {message.get('message_id')}")
                        results['filtered_messages'].append({
                            'reason': 'Empty content',
                            'message_id': message.get('message_id')
                        })
                        continue

                    # 解析消息内容
                    parse_result = self.message_parser.parse_message(content)
                    if not parse_result:
                        self.logger.debug(f"Failed to parse message: {content[:50]}...")
                        results['filtered_messages'].append({
                            'reason': 'Parse failed',
                            'content': content[:50]
                        })
                        continue

                    # 验证解析结果结构
                    if not hasattr(parse_result, 'folder_name') or not hasattr(parse_result, 'share_link') or not hasattr(parse_result, 'extraction_code'):
                        self.logger.debug(f"Invalid parse result structure for message: {content[:50]}...")
                        results['filtered_messages'].append({
                            'reason': 'Invalid parse structure',
                            'content': content[:50]
                        })
                        continue

                    # 计算消息哈希
                    message_hash = self.message_parser.calculate_message_hash(content)

                    # 检查重复消息
                    existing_message = self.db_repo.get_message_by_hash(message_hash)
                    if existing_message:
                        self.logger.info(f"Duplicate message found: {parse_result.folder_name}")
                        results['duplicate_messages'].append({
                            'folder_name': parse_result.folder_name,
                            'existing_status': existing_message.process_status
                        })
                        continue

                    # 插入新消息到数据库（状态为 pending）
                    message_log = MessageProcessLog(
                        message_hash=message_hash,
                        original_message=content,
                        share_link=parse_result.share_link,
                        folder_name=parse_result.folder_name,
                        extraction_code=parse_result.extraction_code,
                        source=parse_result.source,  # 新增：消息来源
                        process_status="pending"  # 待处理状态
                    )
                    message_id = self.db_repo.insert_message_log(message_log)

                    self.logger.info(f"✅ New message inserted: {parse_result.folder_name} (ID: {message_id})")
                    results['new_messages'].append({
                        'message_id': message_id,
                        'folder_name': parse_result.folder_name,
                        'share_link': parse_result.share_link
                    })

                except Exception as e:
                    # 个人消息处理异常不算作系统失败，继续处理下一条
                    self.logger.warning(f"Error processing individual message (skipped): {e}")
                    results['filtered_messages'].append({
                        'reason': 'Processing error',
                        'error': str(e)
                    })
                    continue

            # 计算处理时间
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 构建接收结果 - 只有在真正系统异常时才有failed_messages
            result = ReceiveResult(
                total_messages=len(messages),
                new_messages=len(results['new_messages']),
                duplicate_messages=len(results['duplicate_messages']),
                failed_messages=0,  # 消息接收总是成功的，解析失败的消息被过滤
                processing_time_ms=processing_time_ms,
                details=[{
                    'new_messages': results['new_messages'],
                    'duplicate_messages': results['duplicate_messages'],
                    'filtered_messages': results['filtered_messages']
                }]
            )

            # 发送接收结果通知
            self._send_receive_notification(result)

            self.logger.info(f"Message receiving completed in {processing_time_ms}ms")
            return result

        except Exception as e:
            # 这里才是真正的系统级异常（飞书接口异常、数据库异常等）
            self.logger.error(f"Critical failure during message receiving: {e}")

            # 系统级异常时返回失败结果
            return ReceiveResult(
                total_messages=0,
                new_messages=0,
                duplicate_messages=0,
                failed_messages=1,  # 系统异常才算失败
                processing_time_ms=0,
                details=[{
                    'system_error': str(e)
                }]
            )

    def _send_receive_notification(self, result: ReceiveResult) -> bool:
        """
        发送消息接收结果通知到钉钉

        Args:
            result: 接收结果统计

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # 构建通知内容（添加钉钉机器人关键词"海外研报"）
            content_lines = [
                f"## 📢 海外研报：{self.source.upper()}消息接收报告",
                "",
                "### 接收结果摘要",
                "",
                f"- **消息来源**: {self.source.upper()}",
                f"- **总计接收**: {result.total_messages} 条消息",
                f"- **新增消息**: {result.new_messages} 条",
                f"- **过滤消息**: {result.duplicate_messages + len(result.details[0].get('filtered_messages', []))} 条 (重复/无法解析)",
                f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
            ]

            # 只有在真正的系统异常时才显示错误详情
            if result.failed_messages > 0:
                content_lines.extend([
                    "",
                    "## ❌ 系统异常",
                    ""
                ])
                if result.details and 'system_error' in result.details[0]:
                    error_msg = result.details[0]['system_error']
                    content_lines.append(f"❌ 系统错误: {error_msg}")
                    content_lines.append("")
                    content_lines.append("这可能是由以下原因造成的：")
                    content_lines.append("- 飞书API接口异常")
                    content_lines.append("- 数据库连接异常")
                    content_lines.append("- 网络连接问题")
                    content_lines.append("- 配置错误")
                else:
                    content_lines.append("❌ 未知系统错误")
            else:
                # 成功接收时添加新消息的简单统计
                if result.details and result.details[0].get('new_messages'):
                    new_count = len(result.details[0]['new_messages'])
                    content_lines.extend([
                        "",
                        f"## ✅ 成功接收 {new_count} 条新消息"
                    ])

            # 添加时间戳
            content_lines.extend([
                "",
                f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])

            content = "\n".join(content_lines)

            # 发送通知
            title = "飞书消息接收报告"
            success = self.dingtalk_notifier.send_notification(title, content)

            if success:
                self.logger.info("DingTalk notification sent successfully")
            else:
                self.logger.warning("Failed to send DingTalk notification")

            return success

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False

    def close(self):
        """关闭资源"""
        if hasattr(self, 'db_repo'):
            self.db_repo.close()
            self.logger.info("MessageReceiver resources closed")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()