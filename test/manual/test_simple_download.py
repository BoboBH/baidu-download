#!/usr/bin/env python3
"""
测试下载已知存在的PDF文件
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
    print("\n[TEST] 测试下载已知存在的PDF文件")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/3] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 测试下载根目录下的PDF文件
        print(f"\n[2/3] 下载根目录下的PDF文件...")
        remote_path = "/商业银行管理.pdf"
        local_path = "./temp/商业银行管理.pdf"

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 文件下载失败")
            return 1

        # 检查下载的文件
        if Path(local_path).exists():
            file_size = Path(local_path).stat().st_size
            print(f"[SUCCESS] 文件下载成功")
            print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")

            # 验证PDF文件头
            with open(local_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print("[SUCCESS] PDF文件验证通过")
                else:
                    print(f"[WARNING] 文件头不是PDF: {header}")

            print(f"文件位置: {local_path}")
        else:
            print("[FAILED] 文件不存在")
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