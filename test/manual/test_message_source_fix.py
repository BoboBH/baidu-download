#!/usr/bin/env python3
"""
测试消息来源修复
验证钉钉和飞书消息的source识别是否正确
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.feishu.message_parser import MessageParser

def test_message_source_parsing():
    """测试不同消息格式的source识别"""
    parser = MessageParser()

    print("=" * 80)
    print("Message Source Parsing Test")
    print("=" * 80)
    print()

    # 测试1: 钉钉格式消息（严格格式）
    print("1. DingTalk strict format test:")
    message1 = "260807:https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result1 = parser.parse_message(message1, source='dingtalk')
    if result1:
        print(f"   Message: {message1}")
        print(f"   Source: {result1.source}")
        print(f"   Expected: dingtalk")
        status = "PASS" if result1.source == 'dingtalk' else "FAIL"
        print(f"   {status}")
    else:
        print("   FAIL - No result")
    print()

    # 测试2: 钉钉消息（通用格式，只有链接）
    print("2. DingTalk general format test (user's case):")
    message2 = "这是今天的研报260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result2 = parser.parse_message(message2, source='dingtalk')
    if result2:
        print(f"   Message: {message2}")
        print(f"   Source: {result2.source}")
        print(f"   Expected: dingtalk")
        status = "PASS" if result2.source == 'dingtalk' else "FAIL"
        print(f"   {status}")
        print(f"   Folder: {result2.folder_name}")
        print(f"   Link: {result2.share_link}")
    else:
        print("   FAIL - No result")
    print()

    # 测试3: 飞书格式消息
    print("3. Feishu format test:")
    message3 = """提取码 260807
链接：https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ
文件夹：研报"""
    result3 = parser.parse_message(message3, source='feishu')
    if result3:
        print(f"   Message: [multiline format]")
        print(f"   Source: {result3.source}")
        print(f"   Expected: feishu")
        status = "PASS" if result3.source == 'feishu' else "FAIL"
        print(f"   {status}")
    else:
        print("   FAIL - No result")
    print()

    # 测试4: 默认参数测试
    print("4. Default parameter test (no source specified):")
    message4 = "https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result4 = parser.parse_message(message4)  # 不传source参数
    if result4:
        print(f"   Message: {message4}")
        print(f"   Source: {result4.source}")
        print(f"   Expected: feishu (default)")
        status = "PASS" if result4.source == 'feishu' else "FAIL"
        print(f"   {status}")
    else:
        print("   FAIL - No result")
    print()

    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("Expected behavior:")
    print("- DingTalk messages should have source='dingtalk'")
    print("- Feishu messages should have source='feishu'")
    print("- Default (no source parameter) should be source='feishu'")
    print()
    print("This fix resolves the issue where DingTalk messages were")
    print("incorrectly identified as Feishu messages, causing them to be")
    print("skipped during processing.")

if __name__ == "__main__":
    test_message_source_parsing()
