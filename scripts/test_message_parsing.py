#!/usr/bin/env python3
"""测试消息解析功能"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.feishu.message_parser import MessageParser
from src.config.settings import Settings

def test_message_parsing():
    """测试消息解析"""
    settings = Settings()
    parser = MessageParser()

    # 模拟飞书返回的消息结构
    test_messages = [
        # 正常的JSON格式消息
        '{"text":"我是进的的\\n260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw"}',

        # 纯文本格式
        "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWw",

        # 带前缀的格式
        "今天收到文件 260724：https://pan.baidu.com/s/abc123 提取码abcd",

        # 格式错误的
        "invalid message format",

        # 空消息
        "",

        # JSON格式包含其他内容
        '{"text":"看看这个链接 260725：https://pan.baidu.com/s/xyz456"}',
    ]

    print("消息解析测试:")
    print("=" * 60)

    for i, content in enumerate(test_messages, 1):
        print(f"\n测试消息 {i}:")
        print(f"  输入: {repr(content)}")

        try:
            result = parser.parse_message(content)
            if result:
                print(f"  ✅ 解析成功:")
                print(f"     文件夹名: {result.folder_name}")
                print(f"     分享链接: {result.share_link}")
                print(f"     提取码: {result.extraction_code}")
            else:
                print(f"  ❌ 解析失败")
        except Exception as e:
            print(f"  ❌ 解析异常: {e}")

if __name__ == "__main__":
    test_message_parsing()