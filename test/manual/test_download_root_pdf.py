#!/usr/bin/env python3
"""
测试下载根目录下的PDF文件
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.uploader.sftp_client import SFTPClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("测试下载根目录PDF文件")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 1. 登录
        print("\n[1/4] 登录百度网盘...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 下载根目录下的PDF文件
        print("\n[2/4] 下载商业银行管理.pdf...")
        remote_path = "/商业银行管理.pdf"
        local_path = "./temp/商业银行管理.pdf"

        # 确保temp目录存在
        os.makedirs("./temp", exist_ok=True)

        # 删除已存在的文件
        if Path(local_path).exists():
            os.remove(local_path)
            print("已删除旧的下载文件")

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 下载失败")
            return 1

        # 3. 验证文件下载成功
        print("\n[3/4] 验证下载文件...")
        if not Path(local_path).exists():
            print("[FAILED] 文件不存在")
            return 1

        file_size = Path(local_path).stat().st_size
        print(f"[SUCCESS] 文件下载成功")
        print(f"文件路径: {local_path}")
        print(f"文件大小: {file_size} 字节 ({file_size/1024/1024:.2f} MB)")

        # 4. 测试SFTP上传
        print("\n[4/4] 测试SFTP上传...")
        sftp_client = SFTPClient()

        if sftp_client.connect():
            remote_upload_path = "/sftp01/upload/test/商业银行管理.pdf"
            print(f"上传路径: {remote_upload_path}")

            if sftp_client.upload_file(local_path, remote_upload_path):
                print("[SUCCESS] 上传成功")
                sftp_client.disconnect()

                # 清理本地文件
                os.remove(local_path)
                print("已清理本地临时文件")

                return 0
            else:
                print("[FAILED] 上传失败")
                sftp_client.disconnect()
                return 1
        else:
            print("[FAILED] SFTP连接失败")
            return 1

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())