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
    """消息解析器 - 飞书和钉钉使用统一的解析逻辑"""

    # 简化的百度网盘链接模式：只识别链接本身
    # 匹配示例：
    #   - https://pan.baidu.com/s/xxx?pwd=gqi4
    #   - https://pan.baidu.com/s/xxx
    #   - 任何包含百度网盘链接的消息
    BAIDU_LINK_PATTERN = re.compile(
        r'(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)'
    )

    def __init__(self):
        """初始化解析器"""
        self.settings = Settings()

    def parse_message(self, content: str, source: str = 'feishu') -> Optional[ParseResult]:
        """
        解析消息内容 - 飞书和钉钉使用统一的解析逻辑

        最终简化目标：
        1. 识别百度网盘链接（任何包含链接的消息）
        2. 从 pwd= 参数提取提取码，如果没有则使用默认值"0409"
        3. 文件夹名称由BaiduPCS-Go获取，不从消息中提取

        支持的格式示例：
        - https://pan.baidu.com/s/xxx?pwd=gqi4 (提取码=gqi4)
        - 260817：https://pan.baidu.com/s/xxx (提取码=0409默认值)
        - 任何包含百度网盘链接的消息

        Args:
            content: 消息内容
            source: 消息来源 ('feishu' 或 'dingtalk')

        Returns:
            ParseResult 对象，包含提取的链接、提取码和消息来源
            folder_name将为None，由后续BaiduPCS-Go获取
            如果无法解析则返回 None
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

        # 1. 识别百度网盘链接
        link_match = self.BAIDU_LINK_PATTERN.search(content)
        if not link_match:
            logger.debug(f"No Baidu link found in message: {content[:50]}...")
            return None

        share_link = link_match.group(1).strip()

        # 2. 从URL中提取pwd参数作为提取码，如果没有则使用默认值"0409"
        extraction_code = self.extract_pwd_from_url(share_link)
        if not extraction_code:
            extraction_code = self.settings.message_default_extraction_code
            logger.info(f"No pwd in URL, using default extraction code: {extraction_code}")
        else:
            logger.info(f"Extracted pwd from URL: {extraction_code}")

        # 3. 文件夹名称设为None，由BaiduPCS-Go获取
        folder_name = None

        logger.info(f"Baidu link parsed successfully: link={share_link[:50]}..., code={extraction_code}")
        logger.debug(f"Folder name will be determined by BaiduPCS-Go API")

        return ParseResult(
            source=source,
            share_link=share_link,
            folder_name=folder_name,  # 由BaiduPCS-Go获取
            extraction_code=extraction_code,
            raw_content=content
        )

    def calculate_message_hash(self, content: str) -> str:
        """
        计算消息内容的MD5哈希值（已弃用，仅用于日志标识）

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

    def calculate_file_key(self, folder_name: str, share_link: str) -> str:
        """
        计算文件唯一键（用于去重）

        现在简化为只基于 share_link 生成唯一键，确保相同链接不重复处理。
        由于文件夹名称现在由BaiduPCS-Go获取，同一个链接总是对应相同的文件夹。

        Args:
            folder_name: 文件夹名（可选，现在不再用于去重）
            share_link: 百度网盘分享链接

        Returns:
            MD5哈希值（32位小写十六进制）
        """
        if not share_link:
            return ""

        # 标准化链接（删除前后空格和pwd参数）
        clean_link = share_link.strip()
        # 移除pwd参数，确保 https://pan.baidu.com/s/xxx?pwd=a 和 ?pwd=b 被认为是同一个链接
        clean_link = clean_link.split('?pwd=')[0]

        # 计算MD5哈希作为唯一键（只用链接）
        return hashlib.md5(clean_link.encode('utf-8')).hexdigest()

    def extract_pwd_from_url(self, url: str) -> Optional[str]:
        """
        从百度网盘URL中提取pwd参数作为提取码

        Args:
            url: 百度网盘分享链接

        Returns:
            提取码，如果URL中没有pwd参数则返回None
        """
        pwd_pattern = re.compile(r'[?&]pwd=([a-zA-Z0-9]+)')
        match = pwd_pattern.search(url)
        if match:
            return match.group(1)
        return None
