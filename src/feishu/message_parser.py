import re
import hashlib
import json as json_module
from typing import Optional
from dataclasses import dataclass
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ParseResult:
    """消息解析结果"""
    folder_name: str
    share_link: str
    code: str

class MessageParser:
    """飞书消息解析器"""

    def __init__(self):
        """初始化解析器"""
        self.settings = Settings()
        # 正则模式：匹配 YYMMDD：https://pan.baidu.com/s/xxx（允许前面有其他文字）
        self.pattern = r'(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)'

    def parse_message(self, content: str) -> Optional[ParseResult]:
        """
        解析飞书消息内容

        Args:
            content: 消息内容

        Returns:
            ParseResult对象，解析失败返回None
        """
        if not content:
            logger.warning("Empty message content")
            return None

        # 去除首尾空格
        content = content.strip()

        # 解析JSON格式的消息内容
        try:
            # 尝试解析JSON字符串 {"text":"内容"}
            parsed_content = json_module.loads(content)
            if isinstance(parsed_content, dict) and 'text' in parsed_content:
                content = parsed_content['text']
                logger.debug(f"Parsed JSON message content: {content}")
        except (json_module.JSONDecodeError, TypeError):
            # 不是JSON格式，直接使用原始内容
            logger.debug("Using raw message content (not JSON)")

        # 匹配正则表达式（使用search而不是match，可以在字符串任意位置匹配）
        match = re.search(self.pattern, content)

        if match:
            folder_name = match.group(1)  # 260723
            share_link = match.group(2)   # https://pan.baidu.com/s/xxx
            code = self.settings.message_default_extraction_code  # 0409

            logger.info(f"Message parsed successfully: {folder_name}")
            return ParseResult(
                folder_name=folder_name,
                share_link=share_link,
                code=code
            )
        else:
            logger.debug(f"Failed to parse message: {content[:50]}...")
            return None

    def calculate_message_hash(self, content: str) -> str:
        """
        计算消息内容的MD5哈希值

        Args:
            content: 消息内容

        Returns:
            MD5哈希值（32位小写十六进制）
        """
        if not content:
            return ""

        # 标准化消息内容（去除多余空格）
        normalized = re.sub(r'\s+', ' ', content.strip())

        # 计算MD5哈希
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
