#!/usr/bin/env python3
"""
测试外部SFTP功能
验证custom_config参数支持
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.uploader.sftp_client import SFTPClient
from src.config.settings import Settings

def test_external_sftp():
    """测试外部SFTP配置功能"""
    print("=" * 60)
    print("测试外部SFTP配置功能")
    print("=" * 60)

    try:
        # 加载配置
        settings = Settings()

        # 测试默认配置
        print("1. 测试默认SFTP配置...")
        default_client = SFTPClient()
        print(f"   主机: {default_client.host}:{default_client.port}")
        print(f"   用户: {default_client.username}")
        print(f"   远程路径: {default_client.remote_path}")

        # 测试自定义配置
        if settings.wxchat_external_sftp_host:
            print("2. 测试外部SFTP配置...")

            external_config = {
                'host': settings.wxchat_external_sftp_host,
                'port': settings.wxchat_external_sftp_port,
                'username': settings.wxchat_external_sftp_username,
                'password': settings.wxchat_external_sftp_password,
                'remote_path': settings.wxchat_external_sftp_folder
            }

            external_client = SFTPClient(custom_config=external_config)
            print(f"   外部主机: {external_client.host}:{external_client.port}")
            print(f"   外部用户: {external_client.username}")
            print(f"   外部路径: {external_client.remote_path}")

            # 测试连接
            print("3. 测试外部SFTP连接...")
            if external_client.connect():
                print("✅ 外部SFTP连接成功!")
                external_client.disconnect()

                print("=" * 60)
                print("[SUCCESS] 外部SFTP配置测试通过!")
                print("=" * 60)
                return True
            else:
                print("❌ 外部SFTP连接失败")
                print("=" * 60)
                return False
        else:
            print("2. 外部SFTP未配置，跳过测试")
            print("=" * 60)
            print("[SUCCESS] 默认配置测试通过!")
            print("=" * 60)
            return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_external_sftp()
    sys.exit(0 if success else 1)
