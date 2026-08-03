#!/usr/bin/env python3
"""
测试正确的逻辑：目录名称从消息提取，提取码从配置取
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.feishu.message_parser import MessageParser
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_correct_logic():
    """测试正确的逻辑：目录名称从消息提取，提取码从配置取"""
    print("=" * 60)
    print("测试：目录名称从消息提取，提取码从配置取")
    print("=" * 60)

    settings = Settings()
    parser = MessageParser()

    default_code = settings.message_default_extraction_code
    print(f"配置的默认提取码: {default_code}")
    print()

    # 测试用例
    test_cases = [
        {
            "name": "钉钉格式（包含日期编号）",
            "content": "260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_folder": "260723",  # 应该从消息中提取
            "expected_extraction": default_code  # 应该从配置中取
        },
        {
            "name": "飞书格式（包含日期编号）",
            "content": "提取码 260723\n链接：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_folder": "260723",  # 应该从消息中提取
            "expected_extraction": default_code  # 应该从配置中取
        },
        {
            "name": "纯链接格式（无日期编号）",
            "content": "https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_folder": default_code,  # 应该使用配置中的提取码作为目录名
            "expected_extraction": default_code  # 应该从配置中取
        },
        {
            "name": "链接带文字（无日期编号）",
            "content": "请下载文件：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            "expected_folder": default_code,  # 应该使用配置中的提取码作为目录名
            "expected_extraction": default_code  # 应该从配置中取
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"内容: {test_case['content']}")

        result = parser.parse_message(test_case['content'])

        if result:
            print(f"解析成功")
            print(f"  目录名称: {result.folder_name}")
            print(f"  提取码: {result.extraction_code}")
            print(f"  链接: {result.share_link}")

            # 检查目录名称
            folder_correct = (result.folder_name == test_case['expected_folder'])
            extraction_correct = (result.extraction_code == test_case['expected_extraction'])

            if folder_correct and extraction_correct:
                print(f"[通过] 目录名称和提取码都正确")
                results.append(True)
            else:
                if not folder_correct:
                    print(f"[失败] 目录名称错误: 期望 {test_case['expected_folder']}, 实际 {result.folder_name}")
                if not extraction_correct:
                    print(f"[失败] 提取码错误: 期望 {test_case['expected_extraction']}, 实际 {result.extraction_code}")
                results.append(False)
        else:
            print(f"[失败] 解析失败")
            results.append(False)

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过率: {passed}/{total}")

    if passed == total:
        print("[成功] 所有测试通过！")
        print("  - 目录名称从消息中正确提取")
        print("  - 提取码从配置中正确获取")
        return 0
    else:
        print("[失败] 部分测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(test_correct_logic())