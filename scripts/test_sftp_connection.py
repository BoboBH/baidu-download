#!/usr/bin/env python3
"""测试SFTP连接"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.uploader.sftp_client import SFTPClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_sftp():
    """测试SFTP连接"""
    try:
        print("开始测试SFTP连接...")

        client = SFTPClient()
        print(f"SFTP配置: {client.host}:{client.port}")
        print(f"用户: {client.username}")
        print(f"远程路径: {client.remote_path}")

        result = client.connect()
        if result:
            print("SFTP连接测试: SUCCESS")
            client.disconnect()
            return True
        else:
            print("SFTP连接测试: FAILED")
            return False

    except Exception as e:
        print(f"SFTP连接测试: ERROR - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sftp()
    sys.exit(0 if success else 1)