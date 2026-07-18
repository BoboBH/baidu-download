#!/usr/bin/env python3
"""
测试修复后的转存功能
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
    print("\n[TEST] 测试修复后的转存功能")
    print("=" * 60)

    try:
        # 使用原始需求中的链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "fixed-test-20240711"

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

        # 3. 列出PDF文件
        print(f"\n[3/3] 列出PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)

        if pdf_files:
            print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件:")
            for i, file_info in enumerate(pdf_files, 1):
                print(f"  {i}. {file_info['name']} ({file_info['size']} 字节)")
        else:
            print("[INFO] 没有找到PDF文件")
            # 显示所有文件
            print("显示所有文件:")
            all_files_result = client._run_command(['ls', f'/{folder_name}'])
            print(f"所有文件: {all_files_result['stdout']}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 转存功能测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())