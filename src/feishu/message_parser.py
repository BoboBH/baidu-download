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
    source: str  # 消息来源 'feishu' 或 'dingtalk'
    share_link: str
    folder_name: str
    extraction_code: str
    raw_content: str

class MessageParser:
    """飞书消息解析器"""

    # 飞书消息格式：260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
    FEISHU_PATTERN = re.compile(
        r'(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)'
    )

    # 钉钉消息格式：260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
    DINGTALK_PATTERN = re.compile(
        r'(\d{6})\s*[：:]\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)'
    )

    def __init__(self):
        """初始化解析器"""
        self.settings = Settings()
        # 正则模式：匹配 YYMMDD：https://pan.baidu.com/s/xxx（允许前面有其他文字）
        self.pattern = r'(\d{6})[:：]\s*(https://pan\.baidu\.com/s/[A-Za-z0-9_-]+)'

    def _match_dingtalk_format(self, content: str) -> Optional[re.Match]:
        """
        匹配钉钉消息格式

        Args:
            content: 消息内容

        Returns:
            匹配对象，如果不匹配则返回 None
        """
        return self.DINGTALK_PATTERN.search(content)

    def _match_feishu_format(self, content: str) -> Optional[re.Match]:
        """
        匹配飞书消息格式

        Args:
            content: 消息内容

        Returns:
            匹配对象，如果不匹配则返回 None
        """
        return self.FEISHU_PATTERN.search(content)

    def _extract_folder_name(self, content: str, extraction_code: str) -> Optional[str]:
        """
        从消息内容中提取文件夹名

        Args:
            content: 消息内容
            extraction_code: 提取码

        Returns:
            文件夹名，如果无法提取则返回 None
        """
        # 简单实现：直接使用提取码作为文件夹名
        return extraction_code

    def parse_message(self, content: str) -> Optional[ParseResult]:
        """
        解析消息内容，统一识别流程

        优先级：
        1. 钉钉格式（新增）
        2. 飞书格式（现有）

        Args:
            content: 消息内容

        Returns:
            ParseResult 对象，如果无法解析则返回 None
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

        # 1. 尝试钉钉格式
        dingtalk_match = self._match_dingtalk_format(content)
        if dingtalk_match:
            extraction_code = dingtalk_match.group(1)  # 260723
            share_link = dingtalk_match.group(2)       # https://...
            folder_name = extraction_code  # 直接使用提取码作为文件夹名

            logger.info(f"DingTalk message parsed successfully: {folder_name}")
            return ParseResult(
                source='dingtalk',
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,
                raw_content=content
            )

        # 2. 尝试飞书格式（保留原有逻辑）
        feishu_match = self._match_feishu_format(content)
        if feishu_match:
            extraction_code = feishu_match.group(1)
            share_link = feishu_match.group(2)

            # 从消息中提取文件夹名
            folder_name = self._extract_folder_name(content, extraction_code)
            if not folder_name:
                return None

            logger.info(f"Feishu message parsed successfully: {folder_name}")
            return ParseResult(
                source='feishu',
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,
                raw_content=content
            )

        # 3. 无法识别
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
