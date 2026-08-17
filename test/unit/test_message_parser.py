import pytest
from src.feishu.message_parser import MessageParser, ParseResult

def test_parse_valid_message():
    """测试解析有效消息（钉钉格式优先）"""
    parser = MessageParser()
    content = "260723：https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content, source="dingtalk")

    assert result is not None
    assert result.source == "dingtalk"  # 钉钉格式优先匹配
    assert result.folder_name == "260723"
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"
    assert result.extraction_code == "0409"  # 使用配置默认提取码

def test_parse_valid_message_with_colon():
    """测试解析包含冒号的有效消息（钉钉格式优先）"""
    parser = MessageParser()
    content = "260723: https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content, source="dingtalk")

    assert result is not None
    assert result.source == "dingtalk"  # 钉钉格式优先匹配
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

def test_parse_dingtalk_format():
    """测试解析钉钉格式消息"""
    parser = MessageParser()
    content = "260723：https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content, source="dingtalk")

    assert result is not None
    assert result.source == "dingtalk"  # 钉钉格式优先匹配
    assert result.folder_name == "260723"
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"
    assert result.extraction_code == "0409"  # 使用配置默认提取码

def test_parse_dingtalk_with_spaces():
    """测试解析钉钉格式带空格的消息"""
    parser = MessageParser()
    content = "260723 ： https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content, source="dingtalk")

    assert result is not None
    assert result.source == "dingtalk"  # 钉钉格式优先匹配
    assert result.folder_name == "260723"
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"

def test_raw_content_preserved():
    """测试原始内容被保留"""
    parser = MessageParser()
    content = "260723：https://pan.baidu.com/s/1abc123def456"

    result = parser.parse_message(content)

    assert result is not None
    assert result.raw_content == content

def test_parse_quant_format_with_pwd():
    """测试解析quant格式消息（包含pwd参数）"""
    parser = MessageParser()
    content = "quant-2026-3: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
    result = parser.parse_message(content)

    assert result is not None
    assert result.folder_name == "quant-2026-3"
    assert result.extraction_code == "gqi4"
    assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
    assert "quant-2026-3" in result.raw_content

def test_parse_quant_format_without_pwd():
    """测试解析quant格式消息（不包含pwd参数，使用配置默认值）"""
    parser = MessageParser()
    content = "quant-2026-10: https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA"
    result = parser.parse_message(content)

    assert result is not None
    assert result.folder_name == "quant-2026-10"
    assert result.extraction_code == "0409"  # config default
    assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA"

def test_parse_quant_format_different_months():
    """测试解析quant格式不同月份格式（单月份和双月份）"""
    parser = MessageParser()

    # Single digit month
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"

    # Double digit months
    result = parser.parse_message("quant-2026-10: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-10"

    result = parser.parse_message("quant-2026-11: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-11"

    result = parser.parse_message("quant-2026-12: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-12"

def test_reject_other_prefixes():
    """测试其他前缀不作为quant格式解析（但会被解析为link-only格式）"""
    parser = MessageParser()

    # Wrong prefix - should not be parsed as quant format
    result = parser.parse_message("research-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None  # Still parsed as link-only format
    assert result.folder_name != "research-2026-3"  # Not parsed as quant format
    assert "research-2026-3" not in result.raw_content or result.folder_name != "research-2026-3"

    result = parser.parse_message("report-2026-11: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None  # Still parsed as link-only format
    assert result.folder_name != "report-2026-11"  # Not parsed as quant format

    result = parser.parse_message("data-2026-5: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None  # Still parsed as link-only format
    assert result.folder_name != "data-2026-5"  # Not parsed as quant format

def test_reject_invalid_months():
    """测试拒绝无效月份（0, 13等）"""
    parser = MessageParser()

    # Invalid months
    result = parser.parse_message("quant-2026-0: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None

    result = parser.parse_message("quant-2026-13: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None

    result = parser.parse_message("quant-2026-99: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is None

def test_quant_format_spacing_variations():
    """测试quant格式不同空格变体"""
    parser = MessageParser()

    # No spaces
    result = parser.parse_message("quant-2026-3:https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"

    # Spaces around colon
    result = parser.parse_message("quant-2026-3 : https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"

    # Multiple spaces
    result = parser.parse_message("quant-2026-3   :   https://pan.baidu.com/s/xxx?pwd=abc")
    assert result is not None
    assert result.folder_name == "quant-2026-3"

def test_existing_formats_still_work():
    """测试现有格式仍然正常工作（向后兼容性）"""
    parser = MessageParser()

    # Combined format (6-digit + link) - with explicit dingtalk source
    result = parser.parse_message("260723：https://pan.baidu.com/s/1abc123def456", source="dingtalk")
    assert result is not None
    assert result.folder_name == "260723"
    assert result.extraction_code == "0409"  # Uses config default extraction code
    assert result.source == "dingtalk"  # Source explicitly specified

    # Combined format with default feishu source
    result = parser.parse_message("260723：https://pan.baidu.com/s/1abc123def456")
    assert result is not None
    assert result.folder_name == "260723"
    assert result.source == "feishu"  # Default source

    # Link-only format
    result = parser.parse_message("https://pan.baidu.com/s/1abc123def456")
    assert result is not None
    assert result.share_link == "https://pan.baidu.com/s/1abc123def456"
    assert result.folder_name == "0409"  # Uses config default as folder name
    assert result.extraction_code == "0409"  # Uses config default as extraction code

def test_quant_format_source_preservation():
    """测试quant格式消息来源保留"""
    parser = MessageParser()

    # Feishu source (default)
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc")
    assert result.source == "feishu"

    # DingTalk source
    result = parser.parse_message("quant-2026-3: https://pan.baidu.com/s/xxx?pwd=abc", source="dingtalk")
    assert result.source == "dingtalk"

def test_extract_pwd_from_url():
    """测试从URL中提取提取码"""
    parser = MessageParser()

    # With ?pwd= parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?pwd=gqi4") == "gqi4"

    # With &pwd= parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx?foo=bar&pwd=abcd") == "abcd"

    # Without pwd parameter
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/xxx") is None

    # Complex URL
    assert parser.extract_pwd_from_url("https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4&foo=bar") == "gqi4"
