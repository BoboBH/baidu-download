"""
文件名处理工具模块
处理超长文件名、特殊字符等问题，智能提取关键信息生成简化文件名
"""

import hashlib
import re
import os
from typing import Tuple, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FilenameHandler:
    """文件名处理器，处理各种文件名问题"""

    # 最大文件名长度（考虑Windows路径限制）
    MAX_FILENAME_LENGTH = 200

    # 文件名中的特殊字符映射
    CHAR_REPLACEMENTS = {
        '：': '_',
        '，': '_',
        '；': '_',
        '、': '_',
        '！': '_',
        '？': '_',
        '…': '_',
        '—': '_',
        '–': '_',
        '•': '_',
        '↑': '_',
        '↓': '_',
        '→': '_',
        '←': '_',
        ' ': '_',
        '~': '_',
        '`': '_',
        '@': '_',
        '#': '_',
        '$': '_',
        '%': '_',
        '&': '_',
        '*': '_',
        '(': '_',
        ')': '_',
        '+': '_',
        '=': '_',
        '[': '_',
        ']': '_',
        '{': '_',
        '}': '_',
        '|': '_',
        '\\': '_',
        ':': '_',
        ';': '_',
        '"': '_',
        "'": '_',
        '<': '_',
        '>': '_',
        ',': '_',
        '?': '_',
    }

    @staticmethod
    def clean_filename(filename: str) -> str:
        """
        清理文件名中的特殊字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        if not filename:
            return "unknown.pdf"

        # 替换特殊字符
        cleaned = filename
        for old_char, new_char in FilenameHandler.CHAR_REPLACEMENTS.items():
            cleaned = cleaned.replace(old_char, new_char)

        # 移除其他特殊字符，只保留字母、数字、下划线、点和连字符
        cleaned = re.sub(r'[^\w\.\-_]', '_', cleaned)

        # 移除连续的下划线
        cleaned = re.sub(r'_{2,}', '_', cleaned)

        # 去除首尾的下划线和点
        cleaned = cleaned.strip('_.')

        # 确保不为空
        if not cleaned:
            return "unknown.pdf"

        return cleaned

    @staticmethod
    def truncate_filename(filename: str, max_length: int = None) -> str:
        """
        截断过长的文件名

        Args:
            filename: 原始文件名
            max_length: 最大长度，默认使用类常量

        Returns:
            截断后的文件名
        """
        if max_length is None:
            max_length = FilenameHandler.MAX_FILENAME_LENGTH

        if len(filename) <= max_length:
            return filename

        # 保留扩展名
        name, ext = os.path.splitext(filename)

        # 截断文件名部分，保留扩展名
        max_name_length = max_length - len(ext)
        truncated_name = name[:max_name_length]

        return truncated_name + ext

    @staticmethod
    def generate_hash_filename(filename: str) -> Tuple[str, str]:
        """
        生成基于哈希的文件名

        Args:
            filename: 原始文件名

        Returns:
            (哈希文件名, 哈希值)
        """
        # 生成MD5哈希
        hash_obj = hashlib.md5(filename.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()

        # 使用前8位作为短哈希
        short_hash = hash_hex[:8]

        # 保留原始扩展名
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = '.pdf'

        # 生成新文件名：原文件名前缀_哈希.扩展名
        # 但如果原文件名太长，只使用哈希
        cleaned = FilenameHandler.clean_filename(filename)

        if len(cleaned) > 50:
            # 文件名太长，只用哈希
            hash_filename = f"file_{short_hash}{ext}"
        else:
            # 文件名适中，使用：原名_哈希
            prefix = cleaned[:30]  # 限制前缀长度
            hash_filename = f"{prefix}_{short_hash}{ext}"

        return hash_filename, hash_hex

    @staticmethod
    def extract_user_id_from_path(remote_path: str) -> Optional[str]:
        """
        从远程路径中提取用户ID

        Args:
            remote_path: 远程文件路径

        Returns:
            提取的用户ID，如果没有找到返回None
        """
        # 处理路径分隔符
        path_parts = remote_path.replace('\\', '/').split('/')

        # 查找包含数字和下划线的部分（可能是用户ID）
        for part in path_parts:
            # 匹配类似 "901741041_Bobo_Huang123" 的模式
            if re.search(r'\d+_[A-Za-z]+', part):
                logger.debug(f"Found potential user ID: {part}")
                return part

        return None

    @staticmethod
    def extract_key_info(filename: str) -> dict:
        """
        从文件名中提取关键信息

        Args:
            filename: 原始文件名

        Returns:
            包含关键信息的字典
        """
        info = {
            'date': None,
            'institution': None,
            'doc_type': None,
            'subject': None,
            'region': None
        }

        # 提取日期 (匹配6位数字)
        date_match = re.search(r'(\d{6})\.pdf$', filename)
        if date_match:
            info['date'] = date_match.group(1)

        # 提取机构信息
        if 'Goldman' in filename:
            info['institution'] = 'Goldman_Sachs'
        elif 'Morgan' in filename:
            info['institution'] = 'Morgan_Stanley'
        elif 'JP' in filename or 'J.P.' in filename:
            info['institution'] = 'JP_Morgan'
        elif 'Citi' in filename:
            info['institution'] = 'Citigroup'

        # 提取文档类型
        if 'Weekly' in filename:
            info['doc_type'] = 'Weekly'
        elif 'Monthly' in filename:
            info['doc_type'] = 'Monthly'
        elif 'Daily' in filename:
            info['doc_type'] = 'Daily'

        # 提取主题
        if 'Fund Flows' in filename:
            info['subject'] = 'Fund_Flows'
        elif 'Equity' in filename:
            info['subject'] = 'Equity'
        elif 'Leveraged' in filename:
            info['subject'] = 'Leveraged_Flows'

        # 提取地区
        if 'EM' in filename:
            info['region'] = 'EM'
        elif 'APAC' in filename:
            info['region'] = 'APAC'
        elif 'US' in filename:
            info['region'] = 'US'

        return info

    @staticmethod
    def generate_smart_filename(remote_path: str) -> Tuple[str, str, str]:
        """
        智能生成简化文件名，保留可读性，只在必要时截断

        策略：
        - 优先保留原始文件名，确保可读性
        - 只有超过200字符时才截断并添加哈希
        - 清理特殊字符但保留可读性

        Args:
            remote_path: 远程文件路径

        Returns:
            (处理后的文件名, 原始文件名, 元数据)
        """
        # 🔥 关键修复：验证输入不为空
        if not remote_path:
            logger.error("Empty remote_path received in generate_smart_filename!")
            return "empty_path_error.pdf", "unknown.pdf", "error:empty_path"

        # 提取文件名
        filename = os.path.basename(remote_path.replace('\\', '/'))

        # 🔥 验证提取的文件名不为空
        if not filename:
            logger.error(f"Failed to extract filename from path: {remote_path}")
            # 使用路径本身作为文件名
            filename = remote_path.replace('/', '_').replace('\\', '_')
            if not filename.endswith('.pdf'):
                filename += '.pdf'

        # 清理特殊字符，但保留可读性
        cleaned_filename = FilenameHandler.clean_filename(filename)

        # 🔥 新策略：只有在文件名超过200字符时才进行截断处理
        MAX_FILENAME_LENGTH = 200
        original_length = len(cleaned_filename)

        if original_length <= MAX_FILENAME_LENGTH:
            # 文件名长度合适，直接使用清理后的文件名，只添加哈希确保唯一性
            hash_obj = hashlib.md5(remote_path.encode('utf-8'))
            unique_hash = hash_obj.hexdigest()[:6]

            # 在扩展名前插入哈希
            name_without_ext, ext = os.path.splitext(cleaned_filename)
            unique_filename = f"{name_without_ext}_{unique_hash}{ext}"

            metadata = f"original_length:{original_length},no_truncation,hash:{unique_hash}"
            logger.info(f"Filename kept original: {cleaned_filename[:50]}... ({original_length} chars)")
        else:
            # 文件名超过200字符，需要截断处理
            # 保留前200个字符的文件名部分（不包括扩展名）
            name_without_ext, ext = os.path.splitext(cleaned_filename)

            # 截取文件名部分，确保总长度不超过200字符
            max_name_length = MAX_FILENAME_LENGTH - len(ext) - 8  # 预留8位给哈希（包括下划线）
            truncated_name = name_without_ext[:max_name_length]

            # 添加哈希确保唯一性
            hash_obj = hashlib.md5(remote_path.encode('utf-8'))
            unique_hash = hash_obj.hexdigest()[:6]

            # 组合：截断的文件名 + 哈希 + 扩展名
            unique_filename = f"{truncated_name}_{unique_hash}{ext}"

            metadata = f"original_length:{original_length},truncated,hash:{unique_hash}"
            logger.info(f"Filename truncated: {original_length} -> {len(unique_filename)} chars")
            logger.info(f"Original: {cleaned_filename[:60]}...")
            logger.info(f"Result: {unique_filename[:60]}...")

        logger.debug(f"Metadata: {metadata}")

        return unique_filename, filename, metadata

    @staticmethod
    def process_filename(filename: str) -> Tuple[str, str]:
        """
        综合处理文件名：清理、截断、哈希化

        Args:
            filename: 原始文件名

        Returns:
            (处理后文件名, 原始文件名哈希)
        """
        # 1. 先清理特殊字符
        cleaned = FilenameHandler.clean_filename(filename)

        # 2. 检查长度
        if len(cleaned) > FilenameHandler.MAX_FILENAME_LENGTH:
            # 3. 如果太长，使用哈希方法
            return FilenameHandler.generate_hash_filename(filename)
        else:
            # 长度合适，直接使用清理后的文件名
            hash_obj = hashlib.md5(filename.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()
            return cleaned, hash_hex

def test_filename_handler():
    """测试文件名处理器"""

    # 测试超长文件名（包含路径）
    long_path = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-EM Weekly Fund Flows Monitor：Foreign selling continues driven by North Asia， while Southbound flows stay strong； HF de~grossing continues in July， while MFs rotate exposure to India in June； Korea Leveraged Flows Update-260717.pdf"

    handler = FilenameHandler()

    print("🔍 智能文件名处理测试")
    print("=" * 60)

    print("\n📄 原始路径:")
    print(f"长度: {len(long_path)} 字符")
    print(f"内容: {long_path[:100]}...")

    # 测试智能文件名生成
    print("\n🎯 智能处理结果:")
    smart_filename, original_filename, metadata = handler.generate_smart_filename(long_path)

    print(f"✨ 简化文件名: {smart_filename}")
    print(f"📏 长度: {len(smart_filename)} 字符")
    print(f"📊 缩短率: {((1 - len(smart_filename)/len(original_filename)) * 100):.1f}%")
    print(f"ℹ️  元数据: {metadata}")

    # 测试普通文件名处理
    print("\n🔧 传统处理对比:")
    cleaned = handler.clean_filename(original_filename)
    print(f"清理后: {cleaned[:80]}... (长度: {len(cleaned)})")

    hash_filename, hash_hex = handler.generate_hash_filename(original_filename)
    print(f"哈希化: {hash_filename} (长度: {len(hash_filename)})")

    print("\n🎉 推荐使用智能文件名处理:")
    print(f"   原因: 保持可读性，大幅缩短，包含关键信息")

if __name__ == "__main__":
    test_filename_handler()