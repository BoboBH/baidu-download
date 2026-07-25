"""
测试 MessageParser 统一识别功能
"""

import pytest
from src.feishu.message_parser import MessageParser, ParseResult


class TestMessageParserUnified:
    """测试统一消息识别流程"""

    def setup_method(self):
        """设置测试环境"""
        self.parser = MessageParser()

    def test_dingtalk_format_basic(self):
        """测试基本钉钉格式识别"""
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'
        assert result.share_link == 'https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg'
        assert result.folder_name == '260723'

    def test_dingtalk_format_english_colon(self):
        """测试钉钉格式英文冒号"""
        content = "260723:https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'

    def test_dingtalk_format_with_spaces(self):
        """测试钉钉格式带空格"""
        content = "260723 ： https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'

    def test_dingtalk_format_with_text(self):
        """测试钉钉格式带额外文字"""
        content = "今天的文件 260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg 请查收"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'

    def test_feishu_format_still_works(self):
        """测试飞书格式仍然有效"""
        # 原始飞书格式与钉钉格式相同：260723：https://...
        # 由于钉钉优先级更高，会被识别为钉钉格式
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'  # 优先识别为钉钉格式
        assert result.extraction_code == '260723'
        assert result.share_link == 'https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg'

    def test_feishu_pattern_works_directly(self):
        """测试飞书模式直接匹配仍然有效"""
        # 测试飞书模式的正则表达式仍然可以匹配
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        feishu_match = self.parser.FEISHU_PATTERN.search(content)

        assert feishu_match is not None
        assert feishu_match.group(1) == '260723'
        assert feishu_match.group(2) == 'https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg'

    def test_unrecognized_format(self):
        """测试无法识别的格式"""
        content = "这是一条普通的消息，没有提取码和链接"
        result = self.parser.parse_message(content)

        assert result is None

    def test_dingtalk_priority_over_feishu(self):
        """测试钉钉格式优先级高于飞书"""
        # 同时匹配两种格式的消息
        content = "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'  # 应该优先识别为钉钉格式

    def test_empty_message(self):
        """测试空消息"""
        result = self.parser.parse_message("")
        assert result is None

    def test_json_formatted_dingtalk(self):
        """测试JSON格式的钉钉消息"""
        content = '{"text":"260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg"}'
        result = self.parser.parse_message(content)

        assert result is not None
        assert result.source == 'dingtalk'
        assert result.extraction_code == '260723'
