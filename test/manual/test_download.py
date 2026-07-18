#!/usr/bin/env python3
"""
测试PDF文件下载功能
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
    print("\n[TEST] 测试PDF文件下载功能")
    print("=" * 60)

    try:
        folder_name = "fixed-test-20240711"

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/3] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 列出PDF文件
        print(f"\n[2/3] 列出PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)

        if not pdf_files:
            print("[FAILED] 没有找到PDF文件")
            return 1

        print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件")
        print(f"测试下载第一个文件: {pdf_files[0]['name']}")

        # 3. 下载第一个PDF文件
        print(f"\n[3/3] 下载PDF文件...")
        test_file = pdf_files[0]
        remote_path = test_file['name']
        local_path = f"./temp/test_{os.path.basename(remote_path)}"

        print(f"远程文件: {remote_path}")
        print(f"本地保存: {local_path}")

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 文件下载失败")
            return 1

        # 检查文件是否真的下载成功
        if Path(local_path).exists():
            file_size = Path(local_path).stat().st_size
            print(f"[SUCCESS] 文件下载成功")
            print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
            print(f"文件路径: {local_path}")

            # 验证文件是否是有效的PDF
            if file_size > 1000:  # 至少1KB
                with open(local_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print("[SUCCESS] 文件格式验证通过 (PDF)")
                    else:
                        print(f"[WARNING] 文件头不是PDF: {header}")
            else:
                print("[WARNING] 文件大小异常小")

        else:
            print("[FAILED] 下载命令成功但文件不存在")
            return 1

        print("\n" + "=" * 60)
        print("[SUCCESS] 下载功能测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())