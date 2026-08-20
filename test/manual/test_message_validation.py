#!/usr/bin/env python3
"""
测试消息解析验证
验证：
1. 8位数字（YYYYMMDD）不会被识别为有效文件夹名
2. URL末尾的空格会被正确删除
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.feishu.message_parser import MessageParser

def test_message_validation():
    """测试消息验证逻辑"""
    parser = MessageParser()

    print("=" * 80)
    print("Message Validation Test")
    print("=" * 80)
    print()

    # 测试1: 8位数字（YYYYMMDD）- 应该被拒绝
    print("1. Test 8-digit year format (should be REJECTED):")
    message1 = "20260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result1 = parser.parse_message(message1, source='dingtalk')
    if result1:
        print(f"   [FAIL] - Should reject 8-digit format, but got: {result1.folder_name}")
        print(f"   Message: {message1}")
    else:
        print(f"   [PASS] - Correctly rejected 8-digit format")
    print()

    # 测试2: 6位数字（YYMMDD）- 应该被接受
    print("2. Test 6-digit year format (should be ACCEPTED):")
    message2 = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result2 = parser.parse_message(message2, source='dingtalk')
    if result2:
        print(f"   [PASS] - Accepted 6-digit format")
        print(f"   Folder: {result2.folder_name}")
        print(f"   Link: {result2.share_link}")
    else:
        print(f"   [FAIL] - Should accept 6-digit format")
    print()

    # 测试3: URL末尾有空格 - 应该自动删除
    print("3. Test URL with trailing space (should be CLEANED):")
    message3 = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ "
    result3 = parser.parse_message(message3, source='dingtalk')
    if result3:
        # 检查URL末尾是否删除了空格
        if result3.share_link == "https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ":
            print(f"   [PASS] - Trailing space removed from URL")
            print(f"   Cleaned link: {result3.share_link}")
        else:
            print(f"   [FAIL] - Trailing space not removed")
            print(f"   Got: '{result3.share_link}'")
            print(f"   Expected: 'https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ'")
    else:
        print(f"   [FAIL] - Should accept message with trailing space")
    print()

    # 测试4: URL前面有空格 - 应该自动删除
    print("4. Test URL with leading space (should be CLEANED):")
    message4 = "260807  https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result4 = parser.parse_message(message4, source='dingtalk')
    if result4:
        if result4.share_link == "https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ":
            print(f"   [PASS] - Leading space removed from URL")
            print(f"   Cleaned link: {result4.share_link}")
        else:
            print(f"   [FAIL] - Leading space not removed")
            print(f"   Got: '{result4.share_link}'")
    else:
        print(f"   [FAIL] - Should accept message with leading space")
    print()

    # 测试5: 纯链接模式（没有6位数字）- 应该使用默认提取码作为文件夹名
    print("5. Test link-only format (should use default extraction code):")
    message5 = "https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ "
    result5 = parser.parse_message(message5, source='dingtalk')
    if result5:
        if result5.share_link == "https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ":
            print(f"   [PASS] - Trailing space removed")
            print(f"   Folder (default): {result5.folder_name}")
            print(f"   Link: {result5.share_link}")
        else:
            print(f"   [FAIL] - Space not removed properly")
    else:
        print(f"   [FAIL] - Should accept link-only format")
    print()

    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("Validation Rules:")
    print("- Only 6-digit numbers (YYMMDD) are valid folder names")
    print("- 8-digit numbers (YYYYMMDD) are REJECTED")
    print("- Leading and trailing spaces in URLs are automatically REMOVED")
    print()

if __name__ == "__main__":
    test_message_validation()
