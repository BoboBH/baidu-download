import pytest
from src.feishu.message_parser import MessageParser, ParseResult

def test_parse_valid_message():
    """测试解析有效消息"""
    parser = MessageParser()
    content = "260723：https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content)

    assert result is not None
    assert result.folder_name == "260723"
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"
    assert result.code == "0409"  # 默认提取码

def test_parse_valid_message_with_colon():
    """测试解析包含冒号的有效消息"""
    parser = MessageParser()
    content = "260723: https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content)

    assert result is not None
    assert result.folder_name == "260723"
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"

def test_parse_invalid_message():
    """测试解析无效消息"""
    parser = MessageParser()
    content = "invalid message content"

    result = parser.parse_message(content)

    assert result is None

def test_parse_empty_message():
    """测试解析空消息"""
    parser = MessageParser()
    result = parser.parse_message("")

    assert result is None

def test_calculate_message_hash():
    """测试计算消息哈希"""
    parser = MessageParser()
    content = "260723：https://pan.baidu.com/s/1abc123def456"

    hash1 = parser.calculate_message_hash(content)
    hash2 = parser.calculate_message_hash(content)

    assert hash1 == hash2
    assert len(hash1) == 32  # MD5哈希长度
    assert hash1.islower()  # 小写十六进制

def test_calculate_hash_different_content():
    """测试不同内容的哈希值不同"""
    parser = MessageParser()

    hash1 = parser.calculate_message_hash("message1")
    hash2 = parser.calculate_message_hash("message2")

    assert hash1 != hash2
