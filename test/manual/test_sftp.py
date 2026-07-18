#!/usr/bin/env python3
"""
测试SFTP连接和上传功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.uploader.sftp_client import SFTPClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("\n[TEST] 测试SFTP连接和上传功能")
    print("=" * 60)

    try:
        # 1. 测试SFTP客户端初始化
        print("\n[1/4] 测试SFTP客户端初始化...")
        try:
            sftp_client = SFTPClient()
            print("[SUCCESS] SFTP客户端初始化成功")
            print(f"SFTP服务器: {sftp_client.host}:{sftp_client.port}")
            print(f"用户名: {sftp_client.username}")
            print(f"远程路径: {sftp_client.remote_path}")
        except Exception as e:
            print(f"[FAILED] SFTP客户端初始化失败: {e}")
            return 1

        # 2. 测试SFTP连接
        print(f"\n[2/4] 测试SFTP连接...")
        if not sftp_client.connect():
            print("[FAILED] SFTP连接失败")
            print("请检查以下配置:")
            print("1. SFTP服务器地址和端口是否正确")
            print("2. 用户名和密码是否正确")
            print("3. 网络连接是否正常")
            print("4. SFTP服务器是否运行中")
            return 1
        print("[SUCCESS] SFTP连接成功")

        # 3. 测试创建目录
        print(f"\n[3/4] 测试创建远程目录...")
        test_dir = f"{sftp_client.remote_path}/test_upload_20240711"
        if sftp_client.create_directory(test_dir):
            print(f"[SUCCESS] 远程目录创建成功: {test_dir}")
        else:
            print(f"[FAILED] 远程目录创建失败: {test_dir}")
            sftp_client.disconnect()
            return 1

        # 4. 测试上传文件
        print(f"\n[4/4] 测试上传PDF文件...")
        # 使用之前下载的PDF文件进行测试
        test_file = "./download_test/商业银行管理.pdf"

        if not Path(test_file).exists():
            print(f"[INFO] 测试文件不存在，尝试使用其他文件...")
            # 检查temp目录中是否有文件
            temp_files = list(Path("temp").glob("*")) if Path("temp").exists() else []
            if temp_files:
                test_file = str(temp_files[0])
                print(f"[INFO] 使用文件: {test_file}")
            else:
                print("[FAILED] 没有可用的测试文件")
                sftp_client.disconnect()
                return 1

        print(f"本地文件: {test_file}")
        remote_file = f"{test_dir}/test_upload.pdf"

        if not sftp_client.upload_file(test_file, remote_file):
            print(f"[FAILED] 文件上传失败: {remote_file}")
            sftp_client.disconnect()
            return 1

        # 检查上传的文件大小
        file_size = Path(test_file).stat().st_size
        print(f"[SUCCESS] 文件上传成功")
        print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
        print(f"远程路径: {remote_file}")

        # 断开连接
        sftp_client.disconnect()
        print("\n" + "=" * 60)
        print("[SUCCESS] SFTP功能测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())