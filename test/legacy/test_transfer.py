#!/usr/bin/env python3
"""
分享链接转存功能测试工具
用于诊断 sharelink -> personalfolder 功能问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.config.settings import Settings

def test_baidu_client_initialization():
    """测试1: BaiduClient 初始化"""
    print("=" * 60)
    print("测试1: BaiduClient 初始化")
    print("=" * 60)

    try:
        client = BaiduClient()
        print(f"[OK] BaiduClient 初始化成功")
        print(f"     BaiduPCS-Go 路径: {client.baidupcs_path}")
        print(f"     Cookie 路径: {client.cookies_path}")
        print(f"     临时目录: {client.temp_dir}")
        return True, client
    except Exception as e:
        print(f"[FAILED] BaiduClient 初始化失败: {e}")
        return False, None

def test_baidupcs_go_commands(client):
    """测试2: BaiduPCS-Go 基本命令"""
    print("\n" + "=" * 60)
    print("测试2: BaiduPCS-Go 基本命令测试")
    print("=" * 60)

    tests = [
        ('当前目录', ['cd', '/']),
        ('列出文件', ['ls', '/']),
        ('用户信息', ['who'])
    ]

    results = []
    for test_name, command in tests:
        try:
            result = client._run_command(command)
            if result['returncode'] == 0:
                print(f"[OK] {test_name} - 成功")
                results.append(True)
            else:
                print(f"[FAILED] {test_name} - 失败")
                print(f"         错误: {result['stderr']}")
                results.append(False)
        except Exception as e:
            print(f"[ERROR] {test_name} - 异常: {e}")
            results.append(False)

    return all(results)

def test_transfer_command(client):
    """测试3: 分享链接转存命令"""
    print("\n" + "=" * 60)
    print("测试3: 分享链接转存命令测试")
    print("=" * 60)

    # 测试用的分享链接（使用一个公开的测试链接）
    test_link = "https://pan.baidu.com/s/1VYzSl7465sdrQXe8GT5RdQ"
    test_code = "704e"
    test_folder = "test_transfer_folder"

    print(f"测试链接: {test_link}")
    print(f"提取码: {test_code}")
    print(f"目标目录: {test_folder}")

    try:
        # 先清理可能存在的测试目录
        print("\n[1/3] 清理可能存在的测试目录...")
        client.delete_directory(test_folder)

        # 切换到根目录
        print("[2/3] 切换到根目录...")
        client._run_command(['cd', '/'])

        # 执行转存命令
        print("[3/3] 执行转存命令...")
        success = client.save_share_link(test_link, test_code, test_folder)

        if success:
            print(f"[OK] 转存成功")

            # 验证转存结果
            print("\n验证转存结果...")
            result = client._run_command(['ls', f'/{test_folder}'])
            if result['returncode'] == 0:
                print(f"[OK] 目标目录创建成功")
                print(f"     目录内容:\n{result['stdout']}")
                return True
            else:
                print(f"[FAILED] 目标目录未找到或为空")
                return False
        else:
            print(f"[FAILED] 转存失败")
            return False

    except Exception as e:
        print(f"[ERROR] 转存测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_login_status(client):
    """测试4: 登录状态检查"""
    print("\n" + "=" * 60)
    print("测试4: 登录状态检查")
    print("=" * 60)

    try:
        result = client._run_command(['who'])
        if result['returncode'] == 0:
            print(f"[OK] 登录状态检查成功")
            print(f"     用户信息:\n{result['stdout']}")
            return True
        else:
            print(f"[FAILED] 登录状态检查失败")
            print(f"         错误: {result['stderr']}")
            return False
    except Exception as e:
        print(f"[ERROR] 登录状态检查异常: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("分享链接转存功能诊断工具")
    print("=" * 60)

    results = []

    # 测试1: 初始化
    success, client = test_baidu_client_initialization()
    results.append(success)

    if not success or client is None:
        print("\n[FAILED] 无法继续测试，BaiduClient 初始化失败")
        return 1

    # 测试2: 基本命令
    results.append(test_baidupcs_go_commands(client))

    # 测试3: 登录状态
    results.append(test_login_status(client))

    # 测试4: 转存功能 (可选，有风险)
    print("\n" + "=" * 60)
    print("是否执行转存功能测试？")
    print("注意: 这将在您的百度网盘中创建测试目录")
    choice = input("继续测试？(y/N): ").strip().lower()

    if choice == 'y':
        results.append(test_transfer_command(client))
    else:
        print("[SKIP] 跳过转存功能测试")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    test_names = [
        "BaiduClient 初始化",
        "BaiduPCS-Go 基本命令",
        "登录状态检查",
        "分享链接转存"
    ]

    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "[OK]" if result else "[FAILED]"
        print(f"{status} {name}")

    print("\n" + "=" * 60)

    if all(results):
        print("[SUCCESS] 所有测试通过")
        return 0
    else:
        print("[FAILED] 部分测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())
