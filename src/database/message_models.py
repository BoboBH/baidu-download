from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MessageProcessLog:
    """消息处理日志模型"""
    message_hash: str
    original_message: Optional[str] = None
    share_link: Optional[str] = None
    folder_name: Optional[str] = None
    extraction_code: Optional[str] = None
    source: str = 'feishu'  # 新增：消息来源，默认 feishu
    message_type: str = 'baidupan'  # 消息类型：baidupan/pdf_link/dingtalk_pdf/dingtalk_zip/wxchat-article
    raw_message: Optional[str] = None  # 原始消息内容（JSON格式）
    file_info: Optional[str] = None  # 文件元数据信息（JSON格式）
    sender_id: Optional[str] = None  # 发送者ID
    sender_nick: Optional[str] = None  # 发送者昵称
    process_status: str = 'pending'  # pending, processing, success, failed, critical_error
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time_ms: Optional[int] = None  # 毫秒
    retry_count: int = 0  # 失败重试次数
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
