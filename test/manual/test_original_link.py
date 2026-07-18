#!/usr/bin/env python3
"""
测试原始需求中的分享链接
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("\n[TEST] 测试原始需求分享链接")
    print("=" * 60)

    try:
        # 使用原始需求中的链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "test-original-20240711"

        print(f"分享链接: {share_link}")
        print(f"提取码: {extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/3] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 转存分享链接
        print(f"\n[2/3] 转存分享链接...")
        client.delete_directory(folder_name)

        if not client.save_share_link(share_link, extraction_code, folder_name):
            print("[FAILED] 分享链接转存失败")
            return 1
        print(f"[SUCCESS] 分享链接转存成功到 /{folder_name}")

        # 3. 查看转存后的目录内容
        print(f"\n[3/3] 查看目录内容...")
        result = client._run_command(['ls', f'/{folder_name}'])
        print(f"目录内容:\n{result['stdout']}")

        if result['stderr'] and 'file name is invalid' not in result['stderr']:
            print(f"错误信息: {result['stderr']}")

        print("\n" + "=" * 60)
        print("[INFO] 测试完成，请检查上面的目录内容")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())