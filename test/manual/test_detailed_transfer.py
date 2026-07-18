#!/usr/bin/env python3
"""
详细测试分享链接转存功能，查看完整输出
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
    print("\n[TEST] 详细测试分享链接转存功能")
    print("=" * 60)

    try:
        # 使用原始需求中的链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "detailed-test-20240711"

        print(f"分享链接: {share_link}")
        print(f"提取码: {extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/2] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 详细转存分享链接
        print(f"\n[2/2] 转存分享链接（详细模式）...")
        client.delete_directory(folder_name)

        # 直接运行转存命令并查看详细输出
        command = [client.baidupcs_path, 'share', 'save', share_link, extraction_code, '-p', f'/{folder_name}']
        print(f"执行命令: {' '.join(command)}")

        import subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300
        )

        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        print(f"标准错误:\n{result.stderr}")

        if result.returncode == 0:
            print("[SUCCESS] 转存命令执行成功")

            # 尝试列出网盘根目录看看有什么
            print("\n尝试列出网盘根目录内容...")
            ls_result = client._run_command(['ls', '/'])
            print(f"ls命令输出:\n{ls_result['stdout']}")
            print(f"ls命令错误:\n{ls_result['stderr']}")

        else:
            print("[FAILED] 转存命令执行失败")

        print("\n" + "=" * 60)
        return 0 if result.returncode == 0 else 1

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())