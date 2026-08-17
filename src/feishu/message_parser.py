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

    # 统一格式：消息中同时包含6位数字(文件夹名)和百度网盘链接（顺序不限）
    # 匹配示例：
    #   - 这是今天的研报260807 https://pan.baidu.com/s/xxx
    #   - 链接 https://pan.baidu.com/s/xxx 文件夹260723
    #   - 260723：https://pan.baidu.com/s/xxx
    #   - 提取码 260723\n链接：https://pan.baidu.com/s/xxx
    #   - 260723https://pan.baidu.com/s/xxx
    #   - https://pan.baidu.com/s/xxx 260723
    # 注意：使用负向断言确保6位数字不被匹配为8位数字的一部分
    COMBINED_PATTERN = re.compile(
        r'(?<!\d)(\d{6})(?!\d).*?(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)|' +
        r'(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+).*?(?<!\d)(\d{6})(?!\d)'
    )

    # Quant格式：quant-{yyyy}-{m}: URL?pwd=xxx
    # 匹配示例：
    #   - quant-2026-3: https://pan.baidu.com/s/xxx?pwd=gqi4
    #   - quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abcd
    #   - quant-2026-11: https://pan.baidu.com/s/xxx (pwd可选)
    QUANT_PATTERN = re.compile(
        r'(quant-\d{4}-\d{1,2})\s*:\s*(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)'
    )

    def __init__(self):
        """初始化解析器"""
        self.settings = Settings()

    def parse_message(self, content: str, source: str = 'feishu') -> Optional[ParseResult]:
        """
        解析消息内容 - 飞书和钉钉使用统一的解析逻辑

        解析优先级：
        1. 组合格式：同时包含6位数字(文件夹名)和百度网盘链接（顺序不限）
        2. 纯链接格式：只有百度网盘链接（使用配置中的提取码作为文件夹名）

        Args:
            content: 消息内容
            source: 消息来源 ('feishu' 或 'dingtalk')
                    - 钉钉群消息应传入 source='dingtalk'
                    - 飞书消息应传入 source='feishu'（默认）
                    ⚠️ 不通过消息格式推断source，由调用者明确指定

        Returns:
            ParseResult 对象，包含提取的链接、提取码、文件夹名和消息来源
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

        # 1. 尝试组合格式（同时有6位数字和链接，顺序不限）
        combined_match = self.COMBINED_PATTERN.search(content)
        if combined_match:
            # COMBINED_PATTERN 有两种匹配形式，需要判断哪个组捕获了内容
            # 形式1: (\d{6}).*?(https://...)  -> group1=6位数字, group2=链接
            # 形式2: (https://...).*?(\d{6})  -> group3=链接, group4=6位数字
            if combined_match.group(1) and combined_match.group(2):
                # 形式1：数字在前
                folder_name = combined_match.group(1)  # 260723 - 从消息中提取作为目录名
                share_link = combined_match.group(2).strip()    # https://... 删除前后空格
            else:
                # 形式2：链接在前
                share_link = combined_match.group(3).strip()   # https://... 删除前后空格
                folder_name = combined_match.group(4)  # 260723

            extraction_code = self.settings.message_default_extraction_code  # 从配置中取提取码，默认0409

            logger.info(f"Combined format parsed successfully: {folder_name}")
            logger.debug(f"Using folder name from message: {folder_name}, extraction code from config: {extraction_code}")
            logger.debug(f"Share link (cleaned): {share_link}")
            return ParseResult(
                source=source,  # 使用传入的消息来源参数
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,  # 使用配置中的提取码
                raw_content=content
            )

        # 2. 尝试纯链接格式（只有链接，没有目录名）
        # 匹配任何百度网盘链接，即使没有明确的6位数字
        link_pattern = re.compile(r'https://pan\.baidu\.com/s/[A-Za-z0-9_-]+')
        link_match = link_pattern.search(content)
        if link_match:
            share_link = link_match.group(0).strip()  # 删除前后空格

            # 验证：如果消息中包含7位或更多位连续数字，拒绝该消息
            # 这样可以避免将"20260807"错误识别为有效格式
            long_number_pattern = re.compile(r'\d{7,}')  # 匹配7位或更多数字
            if long_number_pattern.search(content):
                logger.debug(f"Rejected message with long number sequence (>=7 digits): {content[:50]}...")
                return None  # 拒绝包含长数字序列的消息

            # 从配置中取提取码，默认0409
            extraction_code = self.settings.message_default_extraction_code
            # 对于没有明确目录名的消息，使用提取码作为目录名
            folder_name = extraction_code

            logger.info(f"Link-only format parsed: {folder_name}")
            logger.debug(f"Using extraction code from config: {extraction_code}, folder name same as extraction code")
            logger.debug(f"Share link (cleaned): {share_link}")
            return ParseResult(
                source=source,  # 使用传入的消息来源参数
                share_link=share_link,
                folder_name=folder_name,
                extraction_code=extraction_code,
                raw_content=content
            )

        # 3. 完全无法识别
        logger.debug(f"Failed to parse message: {content[:50]}...")
        return None

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

        基于 folder_name + share_link 的组合生成唯一键，确保相同文件不重复处理。

        Args:
            folder_name: 文件夹名（YYMMDD格式）
            share_link: 百度网盘分享链接

        Returns:
            MD5哈希值（32位小写十六进制）
        """
        if not folder_name or not share_link:
            return ""

        # 标准化链接（删除前后空格）
        clean_link = share_link.strip()

        # 组合文件夹名和链接
        combined = f"{folder_name}|{clean_link}"

        # 计算MD5哈希作为唯一键
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
