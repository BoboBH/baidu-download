import pytest
from src.feishu.message_parser import MessageParser, ParseResult

class TestFinalSimplifiedParser:
    """最终简化版消息解析器测试 - folder_name由BaiduPCS-Go获取"""

    def test_parse_link_with_pwd_param(self):
        """测试解析包含pwd参数的链接 - 目标1"""
        parser = MessageParser()
        # 示例：https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4
        content = "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"

        result = parser.parse_message(content, source="feishu")

        assert result is not None
        assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
        assert result.extraction_code == "gqi4"  # 从pwd参数提取
        assert result.folder_name is None  # 由BaiduPCS-Go获取

    def test_parse_link_without_pwd_param(self):
        """测试解析不包含pwd参数的链接 - 目标2"""
        parser = MessageParser()
        # 示例：260817：https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ
        content = "260817：https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ"

        result = parser.parse_message(content, source="dingtalk")

        assert result is not None
        assert result.share_link == "https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ"
        assert result.extraction_code == "0409"  # 使用默认提取码
        assert result.folder_name is None  # 由BaiduPCS-Go获取

    def test_parse_various_messages_with_pwd(self):
        """测试解析各种包含pwd参数的消息格式"""
        parser = MessageParser()

        test_cases = [
            # 纯链接 + pwd参数
            "https://pan.baidu.com/s/1test?pwd=gqi4",
            # 文本描述 + 链接 + pwd参数
            "下载链接：https://pan.baidu.com/s/1abc?pwd=abcd",
            # quant格式 + pwd参数
            "quant-2026-3: https://pan.baidu.com/s/1xyz?pwd=1234",
            # 日期格式 + pwd参数
            "260817：https://pan.baidu.com/s/1test123?pwd=code",
        ]

        for content in test_cases:
            result = parser.parse_message(content, source="feishu")
            assert result is not None, f"Failed to parse: {content}"
            assert "https://pan.baidu.com/s/" in result.share_link
            assert result.extraction_code != "0409", f"Should extract pwd from URL: {content}"
            assert result.folder_name is None  # 总是由BaiduPCS-Go获取

    def test_parse_various_messages_without_pwd(self):
        """测试解析各种不包含pwd参数的消息格式"""
        parser = MessageParser()

        test_cases = [
            # 纯链接，无pwd参数
            "https://pan.baidu.com/s/1test",
            # 文本 + 链接，无pwd参数
            "下载：https://pan.baidu.com/s/1abc",
            # 日期格式，无pwd参数
            "260817：https://pan.baidu.com/s/1xyz",
            # quant格式，无pwd参数
            "quant-2026-3: https://pan.baidu.com/s/1test123",
        ]

        for content in test_cases:
            result = parser.parse_message(content, source="feishu")
            assert result is not None, f"Failed to parse: {content}"
            assert "https://pan.baidu.com/s/" in result.share_link
            assert result.extraction_code == "0409", f"Should use default extraction code: {content}"
            assert result.folder_name is None  # 总是由BaiduPCS-Go获取

    def test_parse_invalid_message_no_link(self):
        """测试解析无效消息（无百度网盘链接）"""
        parser = MessageParser()
        content = "This is just regular text without any links"

        result = parser.parse_message(content)

        assert result is None

    def test_parse_empty_message(self):
        """测试解析空消息"""
        parser = MessageParser()
        result = parser.parse_message("")

        assert result is None

    def test_parse_json_message_with_pwd(self):
        """测试解析JSON格式的消息（包含pwd参数）"""
        parser = MessageParser()
        content = '{"text":"https://pan.baidu.com/s/1test?pwd=gqi4"}'

        result = parser.parse_message(content, source="dingtalk")

        assert result is not None
        assert result.share_link == "https://pan.baidu.com/s/1test?pwd=gqi4"
        assert result.extraction_code == "gqi4"
        assert result.folder_name is None

    def test_extract_pwd_from_url(self):
        """测试从URL中提取pwd参数功能"""
        parser = MessageParser()

        # 测试包含pwd参数的URL
        url_with_pwd = "https://pan.baidu.com/s/1test?pwd=gqi4"
        pwd = parser.extract_pwd_from_url(url_with_pwd)
        assert pwd == "gqi4"

        # 测试不包含pwd参数的URL
        url_without_pwd = "https://pan.baidu.com/s/1test"
        pwd = parser.extract_pwd_from_url(url_without_pwd)
        assert pwd is None

        # 测试pwd参数与其他参数混合
        url_with_mixed_params = "https://pan.baidu.com/s/1test?pwd=abcd&other=value"
        pwd = parser.extract_pwd_from_url(url_with_mixed_params)
        assert pwd == "abcd"

    def test_parse_message_source_parameter(self):
        """测试消息来源参数正确传递"""
        parser = MessageParser()
        content = "https://pan.baidu.com/s/1test?pwd=code"

        # 测试钉钉来源
        result_dingtalk = parser.parse_message(content, source="dingtalk")
        assert result_dingtalk.source == "dingtalk"

        # 测试飞书来源
        result_feishu = parser.parse_message(content, source="feishu")
        assert result_feishu.source == "feishu"

    def test_final_goal_scenario_1(self):
        """测试最终目标场景1：有pwd参数的链接"""
        parser = MessageParser()
        # https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4
        # 能解析url中的提取码"gqi4"，通过baidupcs-go识别到文件夹
        content = "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"

        result = parser.parse_message(content, source="feishu")

        assert result is not None
        assert result.share_link == "https://pan.baidu.com/s/1X8iJtT2WNAlvcHH-4shLPA?pwd=gqi4"
        assert result.extraction_code == "gqi4"  # ✅ 解析到提取码
        assert result.folder_name is None  # ✅ 文件夹由BaiduPCS-Go识别

    def test_final_goal_scenario_2(self):
        """测试最终目标场景2：无pwd参数的链接"""
        parser = MessageParser()
        # 260817：https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ
        # 这种能识别到url，提取码是默认值0409，文件夹通过baidupcs-go来识别
        content = "260817：https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ"

        result = parser.parse_message(content, source="dingtalk")

        assert result is not None
        assert result.share_link == "https://pan.baidu.com/s/1btkiCVhD64ZAp4UnQnvWDQ"
        assert result.extraction_code == "0409"  # ✅ 使用默认提取码
        assert result.folder_name is None  # ✅ 文件夹由BaiduPCS-Go识别

    def test_parse_whitespace_variations(self):
        """测试各种空格变化的消息格式"""
        parser = MessageParser()

        test_cases = [
            "https://pan.baidu.com/s/1test?pwd=gqi4",
            " https://pan.baidu.com/s/1test?pwd=gqi4 ",
            "\nhttps://pan.baidu.com/s/1test?pwd=gqi4\n",
            "  https://pan.baidu.com/s/1test?pwd=gqi4  ",
        ]

        for content in test_cases:
            result = parser.parse_message(content, source="feishu")
            assert result is not None, f"Failed to parse with whitespace: {content!r}"
            assert result.share_link == "https://pan.baidu.com/s/1test?pwd=gqi4"
            assert result.extraction_code == "gqi4"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
