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
    process_status: str = 'pending'  # pending, processing, success, failed, critical_error
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time_ms: Optional[int] = None  # 毫秒
    retry_count: int = 0  # 失败重试次数
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
