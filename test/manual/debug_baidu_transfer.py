#!/usr/bin/env python3
"""
调试百度网盘转存功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_login():
    """测试登录"""
    print("=" * 60)
    print("测试：百度网盘登录")
    print("=" * 60)

    try:
        client = BaiduClient()
        print(f"BaiduPCS-Go 路径: {client.baidupcs_path}")
        print(f"Cookies 路径: {client.cookies_path}")

        # 检查文件是否存在
        if not Path(client.baidupcs_path).exists():
            print(f"[ERROR] BaiduPCS-Go 不存在: {client.baidupcs_path}")
            return False

        if not Path(client.cookies_path).exists():
            print(f"[ERROR] Cookies 文件不存在: {client.cookies_path}")
            return False

        result = client.login()

        if result:
            print("[SUCCESS] 登录成功")
            return True
        else:
            print("[FAILED] 登录失败")
            return False
    except Exception as e:
        print(f"[ERROR] 登录异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transfer():
    """测试转存功能"""
    print("\n" + "=" * 60)
    print("测试：转存分享链接到个人目录")
    print("=" * 60)

    try:
        # 使用测试链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "test-debug-transfer"

        print(f"分享链接: {share_link}")
        print(f"提取码: {extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 先登录
        if not client.login():
            print("[FAILED] 登录失败，无法继续测试")
            return False

        # 转存分享链接
        print(f"开始转存分享链接...")
        result = client.save_share_link(share_link, extraction_code, folder_name)

        if result:
            print(f"[SUCCESS] 分享链接转存成功到 /{folder_name}")
            return True
        else:
            print("[FAILED] 分享链接转存失败")
            return False

    except Exception as e:
        print(f"[FAILED] 转存异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n[DEBUG] 百度网盘转存功能调试")
    print("=" * 60)

    # 设置详细日志
    logger.setLevel('DEBUG')
    for handler in logger.handlers:
        handler.setLevel('DEBUG')

    results = []

    # 测试登录
    results.append(("登录测试", test_login()))

    # 测试转存
    results.append(("转存测试", test_transfer()))

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "[SUCCESS] 通过" if result else "[FAILED] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print("=" * 60)
    print(f"测试通过率: {passed}/{len(results)}")

    return 0 if passed == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())