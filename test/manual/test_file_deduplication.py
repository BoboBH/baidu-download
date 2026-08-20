#!/usr/bin/env python3
"""
测试基于 folder_name + URL 的文件去重逻辑
验证：
1. 相同的 folder_name + share_link = 重复
2. 不同的 folder_name 或 share_link = 不重复
3. 消息文字描述不同不影响去重
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.feishu.message_parser import MessageParser

def test_file_deduplication():
    """测试基于 folder_name + URL 的文件去重逻辑"""
    parser = MessageParser()

    print("=" * 80)
    print("File Deduplication Test (based on folder_name + share_link)")
    print("=" * 80)
    print()

    # 测试1: 相同的 folder_name + share_link - 应该生成相同的 file_key
    print("1. Test same folder_name + share_link (should have SAME file_key):")
    message1a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message1b = "这是今天的研报 260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result1a = parser.parse_message(message1a, source='dingtalk')
    result1b = parser.parse_message(message1b, source='dingtalk')
    if result1a and result1b:
        file_key1a = parser.calculate_file_key(result1a.folder_name, result1a.share_link)
        file_key1b = parser.calculate_file_key(result1b.folder_name, result1b.share_link)
        print(f"   Message 1A: {message1a}")
        print(f"   Message 1B: {message1b}")
        print(f"   File 1A: folder={result1a.folder_name}, link={result1a.share_link}")
        print(f"   File 1B: folder={result1b.folder_name}, link={result1b.share_link}")
        print(f"   File Key 1A: {file_key1a}")
        print(f"   File Key 1B: {file_key1b}")
        if file_key1a == file_key1b:
            print(f"   [PASS] - Same folder+link produces same file_key")
        else:
            print(f"   [FAIL] - Same folder+link should have same file_key")
    else:
        print(f"   [FAIL] - Parse failed")
    print()

    # 测试2: 相同 folder_name + share_link 但 URL 末尾有空格 - 应该生成相同的 file_key
    print("2. Test same folder+link with trailing space (should have SAME file_key):")
    message2a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message2b = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ "
    result2a = parser.parse_message(message2a, source='dingtalk')
    result2b = parser.parse_message(message2b, source='dingtalk')
    if result2a and result2b:
        file_key2a = parser.calculate_file_key(result2a.folder_name, result2a.share_link)
        file_key2b = parser.calculate_file_key(result2b.folder_name, result2b.share_link)
        print(f"   Message 2A: '{message2a}'")
        print(f"   Message 2B: '{message2b}'")
        print(f"   File Key 2A: {file_key2a}")
        print(f"   File Key 2B: {file_key2b}")
        if file_key2a == file_key2b:
            print(f"   [PASS] - Trailing space cleaned, same file_key")
        else:
            print(f"   [FAIL] - Should clean spaces and produce same file_key")
    else:
        print(f"   [FAIL] - Parse failed")
    print()

    # 测试3: 不同的 folder_name - 应该生成不同的 file_key
    print("3. Test different folder_name (should have DIFFERENT file_key):")
    message3a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message3b = "260808 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    result3a = parser.parse_message(message3a, source='dingtalk')
    result3b = parser.parse_message(message3b, source='dingtalk')
    if result3a and result3b:
        file_key3a = parser.calculate_file_key(result3a.folder_name, result3a.share_link)
        file_key3b = parser.calculate_file_key(result3b.folder_name, result3b.share_link)
        print(f"   Message 3A: {message3a}")
        print(f"   Message 3B: {message3b}")
        print(f"   File Key 3A: {file_key3a}")
        print(f"   File Key 3B: {file_key3b}")
        if file_key3a != file_key3b:
            print(f"   [PASS] - Different folder_name produces different file_key")
        else:
            print(f"   [FAIL] - Different folder_name should have different file_key")
    else:
        print(f"   [FAIL] - Parse failed")
    print()

    # 测试4: 不同的 share_link - 应该生成不同的 file_key
    print("4. Test different share_link (should have DIFFERENT file_key):")
    message4a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message4b = "260807 https://pan.baidu.com/s/anotherlink123"
    result4a = parser.parse_message(message4a, source='dingtalk')
    result4b = parser.parse_message(message4b, source='dingtalk')
    if result4a and result4b:
        file_key4a = parser.calculate_file_key(result4a.folder_name, result4a.share_link)
        file_key4b = parser.calculate_file_key(result4b.folder_name, result4b.share_link)
        print(f"   Message 4A: {message4a}")
        print(f"   Message 4B: {message4b}")
        print(f"   File Key 4A: {file_key4a}")
        print(f"   File Key 4B: {file_key4b}")
        if file_key4a != file_key4b:
            print(f"   [PASS] - Different share_link produces different file_key")
        else:
            print(f"   [FAIL] - Different share_link should have different file_key")
    else:
        print(f"   [FAIL] - Parse failed")
    print()

    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("New Deduplication Logic:")
    print("- Based on folder_name + share_link combination")
    print("- NOT based on message content (text description)")
    print("- Same folder+link = same file_key = duplicate")
    print("- Different folder OR link = different file_key = can insert")
    print("- URL spaces are automatically cleaned")
    print()

if __name__ == "__main__":
    test_file_deduplication()
