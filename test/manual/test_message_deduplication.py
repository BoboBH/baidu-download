#!/usr/bin/env python3
"""
测试消息去重逻辑
验证：
1. 基于消息内容（message_hash）去重，而不是 folder_name + URL
2. 相同消息内容不会重复插入
3. 不同消息内容但相同 folder_name + URL 可以插入
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.feishu.message_parser import MessageParser

def test_message_deduplication():
    """测试消息去重逻辑"""
    parser = MessageParser()

    print("=" * 80)
    print("Message Deduplication Test")
    print("=" * 80)
    print()

    # 测试1: 完全相同的消息 - 应该生成相同的 hash
    print("1. Test identical messages (should have SAME hash):")
    message1a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message1b = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    hash1a = parser.calculate_message_hash(message1a)
    hash1b = parser.calculate_message_hash(message1b)
    print(f"   Message 1A: {message1a}")
    print(f"   Message 1B: {message1b}")
    print(f"   Hash 1A: {hash1a}")
    print(f"   Hash 1B: {hash1b}")
    if hash1a == hash1b:
        print(f"   [PASS] - Identical messages have same hash")
    else:
        print(f"   [FAIL] - Identical messages should have same hash")
    print()

    # 测试2: 相同消息但前后空格不同 - 应该生成相同的 hash（标准化）
    print("2. Test messages with different spacing (should have SAME hash after normalization):")
    message2a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message2b = "  260807   https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ  "
    hash2a = parser.calculate_message_hash(message2a)
    hash2b = parser.calculate_message_hash(message2b)
    print(f"   Message 2A: '{message2a}'")
    print(f"   Message 2B: '{message2b}'")
    print(f"   Hash 2A: {hash2a}")
    print(f"   Hash 2B: {hash2b}")
    if hash2a == hash2b:
        print(f"   [PASS] - Normalized messages have same hash")
    else:
        print(f"   [FAIL] - Normalized messages should have same hash")
    print()

    # 测试3: 相同 folder_name + URL 但不同文字描述 - 应该生成不同的 hash
    print("3. Test same folder_name+URL with different text (should have DIFFERENT hash):")
    message3a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message3b = "这是今天的研报 260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    hash3a = parser.calculate_message_hash(message3a)
    hash3b = parser.calculate_message_hash(message3b)
    print(f"   Message 3A: {message3a}")
    print(f"   Message 3B: {message3b}")
    print(f"   Hash 3A: {hash3a}")
    print(f"   Hash 3B: {hash3b}")
    if hash3a != hash3b:
        print(f"   [PASS] - Different text content produces different hash")
    else:
        print(f"   [FAIL] - Different text content should produce different hash")
    print()

    # 测试4: 完全不同的消息 - 应该生成不同的 hash
    print("4. Test completely different messages (should have DIFFERENT hash):")
    message4a = "260807 https://pan.baidu.com/s/1fEf56rtPCKyWGVreGiA6qQ"
    message4b = "260808 https://pan.baidu.com/s/anotherlink123"
    hash4a = parser.calculate_message_hash(message4a)
    hash4b = parser.calculate_message_hash(message4b)
    print(f"   Message 4A: {message4a}")
    print(f"   Message 4B: {message4b}")
    print(f"   Hash 4A: {hash4a}")
    print(f"   Hash 4B: {hash4b}")
    if hash4a != hash4b:
        print(f"   [PASS] - Different messages have different hash")
    else:
        print(f"   [FAIL] - Different messages should have different hash")
    print()

    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("Deduplication Logic:")
    print("- Based on message_hash (MD5 of normalized message content)")
    print("- NOT based on folder_name + URL combination")
    print("- Message content is normalized (extra spaces removed)")
    print("- Same message content = same hash = duplicate")
    print("- Different message content = different hash = can insert")
    print()
    print("Database Constraint:")
    print("- message_hash column has UNIQUE constraint")
    print("- Duplicate hash will cause database insertion error")
    print("- Application checks for existing hash before insertion")
    print()

if __name__ == "__main__":
    test_message_deduplication()
