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

    def __init__(self, settings: Optional[Settings] = None, source: str = 'feishu'):
        """
        Initialize MessageReceiver with required dependencies

        Args:
            settings: Configuration object, defaults to new Settings instance
            source: Message source platform ('feishu' or 'dingtalk'), defaults to 'feishu'

        Note:
            钉钉消息接收请使用 --dingtalk-service 模式启动 dingtalk_group_client
        """
        self.source = source  # 支持飞书消息（钉钉暂不支持此模式）
        self.settings = settings or Settings()
        self.logger = logger

        # 根据source选择客户端
        if source == 'feishu':
            from src.feishu.feishu_client import FeishuMessageClient
            self.client = FeishuMessageClient(self.settings)
        elif source == 'dingtalk':
            raise ValueError("钉钉消息接收请使用 --dingtalk-service 模式启动 dingtalk_group_client，而不是 --receive-messages")
        else:
            raise ValueError(f"Unsupported source: {source}. Must be 'feishu' or 'dingtalk' (but dingtalk requires --dingtalk-service mode)")

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

        self.logger.info(f"MessageReceiver initialized successfully ({self.source})")

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

                    # 解析消息内容，传入消息来源
                    parse_result = self.message_parser.parse_message(content, source=self.source)
                    if not parse_result:
                        self.logger.debug(f"Failed to parse message: {content[:50]}...")
                        results['filtered_messages'].append({
                            'reason': 'Parse failed',
                            'content': content[:50]
                        })
                        continue

                    # 验证解析结果结构 - 支持多种消息类型
                    # 每种消息类型有不同的必需字段
                    has_required_fields = False
                    if parse_result.is_baidupan():
                        # 百度网盘消息需要 share_link 和 extraction_code
                        has_required_fields = (hasattr(parse_result, 'share_link') and
                                              hasattr(parse_result, 'extraction_code'))
                    elif parse_result.is_pdf_link():
                        # PDF链接消息需要 pdf_url
                        has_required_fields = hasattr(parse_result, 'pdf_url')
                    elif parse_result.is_dingtalk_file():
                        # 钉钉文件消息需要 file_id, space_id, download_code, file_name
                        has_required_fields = (hasattr(parse_result, 'file_id') and
                                              hasattr(parse_result, 'space_id') and
                                              hasattr(parse_result, 'download_code') and
                                              hasattr(parse_result, 'file_name'))
                    else:
                        # 未知消息类型
                        self.logger.debug(f"Unknown message type: {parse_result.message_type}")
                        results['filtered_messages'].append({
                            'reason': 'Unknown message type',
                            'content': content[:50]
                        })
                        continue

                    if not has_required_fields:
                        self.logger.debug(f"Invalid parse result structure for message: {content[:50]}...")
                        results['filtered_messages'].append({
                            'reason': 'Invalid parse structure',
                            'content': content[:50]
                        })
                        continue

                    # 计算文件唯一键 - 根据消息类型使用不同的标识符
                    message_hash = self.message_parser.calculate_file_key(
                        parse_result.message_type,
                        parse_result.unique_identifier
                    )

                    # 检查重复文件（基于消息哈希）
                    existing_message = self.db_repo.get_message_by_hash(message_hash)
                    if existing_message:
                        # 根据消息类型显示不同的重复信息
                        if parse_result.is_baidupan():
                            display_info = parse_result.share_link[:50] if parse_result.share_link else "unknown"
                        elif parse_result.is_pdf_link():
                            display_info = parse_result.pdf_url[:50] if parse_result.pdf_url else "unknown"
                        elif parse_result.is_dingtalk_file():
                            display_info = parse_result.file_name if parse_result.file_name else "unknown"
                        else:
                            display_info = "unknown"

                        logger.info(f"Duplicate message found: {display_info}...")
                        results['duplicate_messages'].append({
                            'message_type': parse_result.message_type,
                            'display_info': display_info,
                            'existing_status': existing_message.process_status
                        })
                        continue

                    # 插入新消息到数据库（状态为 pending）- 支持多种消息类型
                    if parse_result.is_baidupan():
                        # 百度网盘消息
                        message_log = MessageProcessLog(
                            message_hash=message_hash,
                            original_message=content,
                            share_link=parse_result.share_link,
                            folder_name=parse_result.folder_name,
                            extraction_code=parse_result.extraction_code,
                            source=parse_result.source,
                            process_status="pending"
                        )
                        display_name = parse_result.folder_name if parse_result.folder_name else "BaiduPan链接"

                    elif parse_result.is_pdf_link():
                        # PDF链接消息
                        message_log = MessageProcessLog(
                            message_hash=message_hash,
                            original_message=content,
                            share_link=parse_result.pdf_url,  # 将PDF URL存储在share_link字段
                            folder_name=None,
                            extraction_code=None,
                            source=parse_result.source,
                            process_status="pending"
                        )
                        display_name = parse_result.pdf_url[:50] if parse_result.pdf_url else "PDF链接"

                    elif parse_result.is_dingtalk_file():
                        # 钉钉文件消息
                        message_log = MessageProcessLog(
                            message_hash=message_hash,
                            original_message=f"钉钉文件: {parse_result.file_name}",
                            share_link=None,  # 钉钉文件没有share_link
                            folder_name=parse_result.file_name,  # 使用文件名作为folder_name
                            extraction_code=parse_result.download_code,  # 将download_code存储在extraction_code字段
                            source=parse_result.source,
                            process_status="pending"
                        )
                        display_name = parse_result.file_name

                    else:
                        # 其他未知消息类型，不应到达这里
                        logger.warning(f"Unknown message type during insertion: {parse_result.message_type}")
                        results['filtered_messages'].append({
                            'reason': 'Unknown message type',
                            'content': content[:50]
                        })
                        continue

                    message_id = self.db_repo.insert_message_log(message_log)

                    logger.info(f"✅ New message inserted: {display_name} (ID: {message_id})")
                    results['new_messages'].append({
                        'message_id': message_id,
                        'message_type': parse_result.message_type,
                        'display_name': display_name
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
            # 构建通知内容（添加钉钉机器人关键词"Foundry"）
            content_lines = [
                f"## 📢 Foundry：{self.source.upper()}消息接收报告",
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