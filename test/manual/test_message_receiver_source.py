#!/usr/bin/env python3
"""
测试MessageReceiver的source参数支持
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.processor.message_receiver import MessageReceiver

def test_message_receiver_source():
    """测试MessageReceiver支持source参数"""
    print("=" * 60)
    print("测试MessageReceiver source参数支持")
    print("=" * 60)

    try:
        settings = Settings()

        # 测试默认source（feishu）
        print("1. 测试默认source (feishu)...")
        try:
            receiver_feishu = MessageReceiver(settings)
            print(f"   [OK] 默认MessageReceiver创建成功")
            print(f"   source: {receiver_feishu.source}")
        except Exception as e:
            print(f"   [ERROR] 创建失败: {e}")
            return False

        # 测试显式source（feishu）
        print("\n2. 测试显式source (feishu)...")
        try:
            receiver_feishu_explicit = MessageReceiver(settings, source='feishu')
            print(f"   [OK] 显式feishu MessageReceiver创建成功")
            print(f"   source: {receiver_feishu_explicit.source}")
        except Exception as e:
            print(f"   [ERROR] 创建失败: {e}")
            return False

        # 测试钉钉source
        print("\n3. 测试钉钉source (dingtalk)...")
        try:
            receiver_dingtalk = MessageReceiver(settings, source='dingtalk')
            print(f"   [OK] 钉钉MessageReceiver创建成功")
            print(f"   source: {receiver_dingtalk.source}")
        except Exception as e:
            print(f"   [ERROR] 创建失败: {e}")
            return False

        # 测试无效source
        print("\n4. 测试无效source...")
        try:
            receiver_invalid = MessageReceiver(settings, source='invalid')
            print(f"   [ERROR] 应该抛出异常但没有")
            return False
        except ValueError as e:
            print(f"   [OK] 正确抛出异常: {e}")
        except Exception as e:
            print(f"   [ERROR] 抛出错误的异常类型: {e}")
            return False

        print("\n" + "=" * 60)
        print("[SUCCESS] MessageReceiver source参数测试通过!")
        print("=" * 60)

        print("\n支持的source:")
        print("  - feishu (默认)")
        print("  - dingtalk")

        return True

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_message_receiver_source()
    sys.exit(0 if success else 1)
