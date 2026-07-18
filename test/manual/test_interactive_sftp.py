#!/usr/bin/env python3
"""
交互式SFTP凭证测试工具
"""

import sys
import paramiko
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_sftp_connection(host, port, username, password):
    """测试SFTP连接"""
    print(f"\nTesting connection to {host}:{port}")
    print(f"Username: {username}")
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
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )

        print("[SUCCESS] SSH connection successful!")

        # 测试SFTP
        try:
            sftp = ssh.open_sftp()
            print("[SUCCESS] SFTP available")

            # 测试目录访问
            try:
                files = sftp.listdir('/')
                print(f"[SUCCESS] Root directory accessible ({len(files)} items)")

                # 显示根目录内容
                print("\nRoot directory contents:")
                for item in files[:10]:  # 只显示前10个
                    print(f"  - {item}")

                sftp.close()
                ssh.close()
                return True

            except Exception as e:
                print(f"[WARNING] Directory access error: {e}")
                sftp.close()
                ssh.close()
                return False

        except Exception as e:
            print(f"[FAILED] SFTP error: {e}")
            ssh.close()
            return False

    except paramiko.AuthenticationException:
        print("[FAILED] Authentication failed - Invalid credentials")
        return False
    except paramiko.SSHException as e:
        print(f"[FAILED] SSH error: {e}")
        return False
    except Exception as e:
        print(f"[FAILED] Connection error: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Interactive SFTP Connection Test")
    print("=" * 60)

    # 默认配置
    default_host = "192.168.0.122"
    default_port = 22
    default_username = "sftp01"

    print(f"\nDefault configuration:")
    print(f"Host: {default_host}")
    print(f"Port: {default_port}")
    print(f"Username: {default_username}")

    # 获取用户输入
    print("\nEnter credentials to test (press Enter to use defaults):")

    host = input(f"Host [{default_host}]: ").strip() or default_host
    port_str = input(f"Port [{default_port}]: ").strip()
    port = int(port_str) if port_str else default_port
    username = input(f"Username [{default_username}]: ").strip() or default_username
    password = input("Password: ").strip()

    if not password:
        print("\n[ERROR] Password cannot be empty")
        return 1

    # 测试连接
    print("\n" + "=" * 60)
    if test_sftp_connection(host, port, username, password):
        print("\n" + "=" * 60)
        print("SUCCESS! Valid credentials found.")
        print("=" * 60)
        print("\nValid credentials:")
        print(f"SFTP_HOST={host}")
        print(f"SFTP_PORT={port}")
        print(f"SFTP_USERNAME={username}")
        print(f"SFTP_PASSWORD={password}")
        print("\nPlease update your .env file with these values.")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAILED - Invalid credentials or connection problem")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())