#!/usr/bin/env python3
"""
专门测试下载和清理功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("\n[TEST] 测试下载和清理功能")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 1. 登录
        print("\n[1/5] 登录百度网盘...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 测试下载单个文件
        print(f"\n[2/5] 测试下载文件...")
        remote_file = "/商业银行管理.pdf"
        local_file = "./temp/test_cleanup.pdf"

        print(f"远程文件: {remote_file}")
        print(f"本地文件: {local_file}")

        # 确保temp目录存在
        Path("temp").mkdir(exist_ok=True)

        if not client.download_file(remote_file, local_file):
            print("[FAILED] 文件下载失败")
            return 1

        # 检查下载的文件
        if Path(local_file).exists():
            file_size = Path(local_file).stat().st_size
            print(f"[SUCCESS] 文件下载成功")
            print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
        else:
            print("[FAILED] 文件不存在")
            return 1

        # 3. 验证PDF文件
        print(f"\n[3/5] 验证PDF文件...")
        try:
            with open(local_file, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print("[SUCCESS] PDF文件验证通过")
                else:
                    print(f"[WARNING] 文件头: {header}")
        except Exception as e:
            print(f"[ERROR] PDF验证失败: {e}")

        # 4. 检查BaiduPCS-Go默认下载目录
        print(f"\n[4/5] 检查BaiduPCS-Go默认下载目录...")
        download_dir = Path("download")
        if download_dir.exists():
            files = list(download_dir.glob("*"))
            print(f"默认下载目录中有 {len(files)} 个文件:")
            for file in files:
                print(f"  - {file.name} ({file.stat().st_size} 字节)")
        else:
            print("[INFO] 默认下载目录不存在")

        # 5. 测试文件删除功能
        print(f"\n[5/5] 测试文件删除功能...")
        try:
            if Path(local_file).exists():
                os.remove(local_file)
                print(f"[SUCCESS] 文件删除成功: {local_file}")
            else:
                print("[INFO] 文件已经被删除")

        except Exception as e:
            print(f"[ERROR] 删除文件失败: {e}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 下载和清理功能测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())