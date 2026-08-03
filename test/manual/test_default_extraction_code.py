#!/usr/bin/env python3
"""
测试默认提取码修复
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.feishu.message_parser import MessageParser
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_default_extraction_code():
    """测试默认提取码功能"""
    print("=" * 60)
    print("测试：默认提取码功能")
    print("=" * 60)

    settings = Settings()
    parser = MessageParser()

    print(f"配置的默认提取码: {settings.message_default_extraction_code}")

    # 测试用例
    test_cases = [
        {
            "name": "标准钉钉格式（有提取码）",
            "content": "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_code": "260723",
            "should_succeed": True
        },
        {
            "name": "标准飞书格式（有提取码）",
            "content": "提取码 260723\n链接：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_code": "260723",
            "should_succeed": True
        },
        {
            "name": "纯链接格式（无提取码，应使用默认）",
            "content": "https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_code": settings.message_default_extraction_code,
            "should_succeed": True
        },
        {
            "name": "链接带文字（无提取码，应使用默认）",
            "content": "请下载文件：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_code": settings.message_default_extraction_code,
            "should_succeed": True
        },
        {
            "name": "无效消息（无链接）",
            "content": "这是一条没有链接的消息",
            "expected_code": None,
            "should_succeed": False
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"内容: {test_case['content']}")

        result = parser.parse_message(test_case['content'])

        if result:
            print(f"[SUCCESS] Parse succeeded")
            print(f"   Extraction code: {result.extraction_code}")
            print(f"   Link: {result.share_link}")
            print(f"   Folder: {result.folder_name}")

            if result.extraction_code == test_case['expected_code']:
                print(f"[PASS] Extraction code correct: {result.extraction_code}")
                results.append(True)
            else:
                print(f"[FAIL] Extraction code wrong: expected {test_case['expected_code']}, got {result.extraction_code}")
                results.append(False)
        else:
            print(f"[FAIL] Parse failed")
            if test_case['should_succeed']:
                print(f"[FAIL] Test failed: should have parsed successfully but didn't")
                results.append(False)
            else:
                print(f"[PASS] Test passed: expected parse failure")
                results.append(True)

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过率: {passed}/{total}")

    if passed == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(test_default_extraction_code())