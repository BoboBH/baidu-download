#!/usr/bin/env python3
"""
测试包含PDF文件的分享链接
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
    print("\n[TEST] 测试包含PDF文件的分享链接")
    print("=" * 60)

    try:
        # 使用已知包含PDF文件的分享链接
        share_link = "https://pan.baidu.com/s/1Q5VQREw8S1zvvuC9_cJEsQ"
        extraction_code = ""  # 这个链接没有提取码
        folder_name = "pdf-test-20240711"

        print(f"分享链接: {share_link}")
        print(f"提取码: {'(无)' if not extraction_code else extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/4] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 转存分享链接
        print(f"\n[2/4] 转存分享链接...")
        client.delete_directory(folder_name)

        if not client.save_share_link(share_link, extraction_code, folder_name):
            print("[FAILED] 分享链接转存失败")
            return 1
        print(f"[SUCCESS] 分享链接转存成功到 /{folder_name}")

        # 3. 查看目录内容
        print(f"\n[3/4] 查看目录内容...")
        list_result = client._run_command(['ls', f'/{folder_name}'])
        print(f"目录内容:\n{list_result['stdout']}")

        # 4. 列出PDF文件
        print(f"\n[4/4] 列出PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)

        if pdf_files:
            print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件:")
            for i, file_info in enumerate(pdf_files, 1):
                print(f"  {i}. {file_info['name']} ({file_info['size']} 字节)")
        else:
            print("[INFO] 没有找到PDF文件")

        print("\n" + "=" * 60)
        print("[SUCCESS] 测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())