#!/usr/bin/env python3
"""
测试SFTP连接
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.uploader.sftp_client import SFTPClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("测试SFTP连接")
    print("=" * 60)

    try:
        # 显示配置信息
        print("\n[配置信息]")
        try:
            settings = Settings()
            print(f"SFTP主机: {settings.sftp_host}")
            print(f"SFTP端口: {settings.sftp_port}")
            print(f"SFTP用户: {settings.sftp_username}")
            print(f"SFTP密码: {'*' * len(settings.sftp_password)}")
            print(f"SFTP路径: {settings.sftp_remote_path}")
        except Exception as e:
            print(f"[ERROR] 配置加载失败: {e}")
            return 1

        # 测试连接
        print("\n[测试连接]")
        client = SFTPClient()

        if client.connect():
            print("[SUCCESS] SFTP连接成功")

            # 测试创建目录
            print("\n[测试创建目录]")
            test_dir = f"{client.remote_path}/test_connection"
            if client.create_directory(test_dir):
                print(f"[SUCCESS] 目录创建成功: {test_dir}")
            else:
                print(f"[FAILED] 目录创建失败: {test_dir}")

            # 断开连接
            client.disconnect()
            print("\n[SUCCESS] 测试完成")
            return 0
        else:
            print("[FAILED] SFTP连接失败")
            print("\n可能的原因:")
            print("1. SFTP服务器地址或端口配置错误")
            print("2. 用户名或密码配置错误")
            print("3. SFTP服务器不可访问")
            print("4. 网络连接问题")
            print("\n请检查.env文件中的SFTP配置")
            return 1

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())