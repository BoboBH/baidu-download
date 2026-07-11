#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境验证脚本
验证系统所需的所有依赖和配置是否正确
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 设置标准输出编码为UTF-8，避免Windows下GBK编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    if version >= (3, 8):
        print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("  需要Python 3.8或更高版本")
        return False

def check_module(module_name, package_name=None):
    """检查Python模块是否已安装"""
    if package_name is None:
        package_name = module_name

    try:
        __import__(module_name)
        print(f"✓ {package_name} 已安装")
        return True
    except ImportError:
        print(f"✗ {package_name} 未安装")
        print(f"  请运行: pip install {package_name}")
        return False

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    path = Path(file_path)
    if path.exists():
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description} 不存在: {file_path}")
        return False

def check_env_file():
    """检查环境配置文件"""
    env_file = Path('.env')
    if env_file.exists():
        print("✓ 环境配置文件 .env 存在")

        # 检查必需的配置项
        from dotenv import load_dotenv
        load_dotenv()

        required_vars = [
            ('BAIDUPCS_GO_PATH', 'BaiduPCS-Go路径'),
            ('SFTP_HOST', 'SFTP主机'),
            ('SFTP_USERNAME', 'SFTP用户名'),
            ('DB_HOST', '数据库主机'),
            ('DB_USER', '数据库用户'),
            ('DB_PASSWORD', '数据库密码')
        ]

        all_present = True
        for var, desc in required_vars:
            if os.getenv(var):
                print(f"  ✓ {desc} ({var}) 已配置")
            else:
                print(f"  ✗ {desc} ({var}) 未配置")
                all_present = False

        return all_present
    else:
        print("✗ 环境配置文件 .env 不存在")
        print("  请复制 .env.example 到 .env 并填写配置")
        return False

def check_database_connection():
    """检查数据库连接"""
    try:
        import pymysql
        from dotenv import load_dotenv

        load_dotenv()

        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            charset='utf8mb4'
        )

        connection.close()
        print("✓ 数据库连接正常")
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("环境验证脚本")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    # 检查Python版本
    results.append(check_python_version())

    # 检查Python模块
    print("\n检查Python模块...")
    modules = [
        ('paramiko', 'paramiko'),
        ('pymysql', 'pymysql'),
        ('dotenv', 'python-dotenv'),
        ('colorama', 'colorama')
    ]

    for module, package in modules:
        results.append(check_module(module, package))

    # 检查配置文件
    print("\n检查配置文件...")
    results.append(check_env_file())

    # 检查BaiduPCS-Go
    print("\n检查外部工具...")
    from dotenv import load_dotenv
    load_dotenv()
    baidupcs_path = os.getenv('BAIDUPCS_GO_PATH', '')
    if baidupcs_path:
        results.append(check_file_exists(baidupcs_path, 'BaiduPCS-Go'))
    else:
        print("✗ BaiduPCS-Go路径未配置")
        results.append(False)

    # 检查数据库连接
    print("\n检查数据库连接...")
    results.append(check_database_connection())

    # 检查必要目录
    print("\n检查目录结构...")
    directories = ['src', 'test', 'middle', 'logs', 'temp']
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 目录 {directory} 已就绪")

    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"验证通过: {passed}/{total} 项检查通过")
        print("环境配置完整，可以正常运行程序")
        return 0
    else:
        print(f"验证失败: {passed}/{total} 项检查通过")
        print("请解决上述问题后再运行程序")
        return 1

if __name__ == '__main__':
    sys.exit(main())
