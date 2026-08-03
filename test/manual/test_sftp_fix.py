#!/usr/bin/env python3
"""
测试SFTP连接修复
验证host key verification问题是否已解决
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.uploader.sftp_client import SFTPClient
from src.config.settings import Settings

def test_sftp_connection():
    """测试SFTP连接"""
    print("=" * 60)
    print("测试SFTP连接修复")
    print("=" * 60)

    try:
        # 使用.env配置
        print("1. 创建SFTP客户端...")
        client = SFTPClient()

        print(f"2. 尝试连接到 {client.host}:{client.port}...")
        if client.connect():
            print("[OK] SFTP连接成功!")

            # 测试基本操作
            print("3. 测试基本操作...")
            print(f"   远程路径: {client.remote_path}")

            # 断开连接
            client.disconnect()
            print("4. 断开连接成功")

            print("=" * 60)
            print("[SUCCESS] 所有测试通过!")
            print("=" * 60)
            return True
        else:
            print("[FAILED] SFTP连接失败")
            print("=" * 60)
            return False

    except Exception as e:
        print(f"[ERROR] 测试过程中发生错误: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_sftp_connection()
    sys.exit(0 if success else 1)
