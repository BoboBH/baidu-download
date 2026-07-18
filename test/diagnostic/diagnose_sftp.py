#!/usr/bin/env python3
"""
SFTP连接诊断工具
"""

import sys
import socket
import paramiko
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_network_connectivity(host, port, timeout=5):
    """测试网络连接"""
    print(f"\n[Network Connectivity Test]")
    print(f"Target: {host}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"[SUCCESS] Network connection successful - Port {port} is accessible")
            return True
        else:
            print(f"[FAILED] Network connection failed - Error code: {result}")
            return False
    except socket.gaierror:
        print(f"[FAILED] DNS resolution failed - Cannot resolve host: {host}")
        return False
    except Exception as e:
        print(f"[FAILED] Network connection error: {e}")
        return False

def test_ssh_protocol(host, port, username, password, timeout=10):
    """测试SSH协议连接"""
    print(f"\n[SSH Protocol Test]")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {username}")
    print(f"Password: {'*' * len(password)}")

    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 尝试连接
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False
        )

        print("[SUCCESS] SSH connection successful")

        # 测试SFTP子系统
        try:
            sftp = ssh.open_sftp()
            print("[SUCCESS] SFTP subsystem available")

            # 测试目录访问
            try:
                sftp.listdir('/')
                print("[SUCCESS] Can access root directory")
                sftp.close()
                ssh.close()
                return True
            except Exception as e:
                print(f"[WARNING] SFTP permission issue: {e}")
                sftp.close()
                ssh.close()
                return False

        except Exception as e:
            print(f"[FAILED] SFTP subsystem failed: {e}")
            ssh.close()
            return False

    except paramiko.AuthenticationException:
        print("[FAILED] Authentication failed - Username or password incorrect")
        print("\nSuggestions:")
        print("1. Check if username is correct")
        print("2. Check if password is correct")
        print("3. Confirm account is not locked")
        return False
    except paramiko.SSHException as e:
        print(f"[FAILED] SSH protocol error: {e}")
        return False
    except socket.timeout:
        print("[FAILED] Connection timeout - Server response too slow")
        return False
    except Exception as e:
        print(f"[FAILED] Connection error: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("SFTP连接诊断工具")
    print("=" * 60)

    try:
        # 加载配置
        print("\n[配置信息]")
        settings = Settings()
        host = settings.sftp_host
        port = settings.sftp_port
        username = settings.sftp_username
        password = settings.sftp_password

        print(f"SFTP主机: {host}")
        print(f"SFTP端口: {port}")
        print(f"SFTP用户: {username}")
        print(f"SFTP密码: {'*' * len(password)}")
        print(f"SFTP路径: {settings.sftp_remote_path}")

        # 1. 网络连接测试
        if not test_network_connectivity(host, port):
            print("\nSuggestions:")
            print("1. Check if SFTP server is running")
            print("2. Check firewall settings")
            print("3. Confirm IP address and port are correct")
            return 1

        # 2. SSH协议测试
        if not test_ssh_protocol(host, port, username, password):
            print("\nSuggestions:")
            print("1. Verify connection with other SFTP client")
            print("2. Contact SFTP server administrator to confirm account status")
            print("3. Check account permissions and configuration")
            return 1

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed - SFTP connection configured correctly")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[ERROR] Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())