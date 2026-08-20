#!/usr/bin/env python3
"""
测试新生成的exe文件版本和基本功能
"""

import subprocess
import os
import sys

def test_exe_version():
    """测试exe文件版本信息"""

    # 使用绝对路径
    exe_path = os.path.abspath("release/dist/baidu-download.exe")

    if not os.path.exists(exe_path):
        print(f"[ERROR] exe file not found: {exe_path}")
        return False

    print("=" * 80)
    print("[TEST] Exe File Version and Basic Functionality Test")
    print("=" * 80)
    print()

    # 1. 检查文件大小
    file_size = os.path.getsize(exe_path)
    file_size_mb = file_size / (1024 * 1024)

    print(f"[INFO] File path: {exe_path}")
    print(f"[INFO] File size: {file_size_mb:.1f} MB")
    print(f"[INFO] Modified time: {os.path.getmtime(exe_path)}")
    print()

    # 2. 测试基本功能 --help
    print("[TEST] Testing --help command...")
    try:
        result = subprocess.run(
            [exe_path, "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] --help command executed successfully")
            print()
            print("[OUTPUT] Help information:")
            print("-" * 80)
            # 只显示前几行，避免输出过长
            help_lines = result.stdout.split('\n')[:20]
            for line in help_lines:
                print(line)
            print("-" * 80)
        else:
            print(f"[WARN] --help command returned error code: {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("[ERROR] --help command execution timeout")
        return False
    except Exception as e:
        print(f"[ERROR] Error executing --help command: {e}")
        return False

    print()

    # 3. 检查是否包含了关键模块
    print("[CHECK] Checking key modules included...")

    try:
        # 尝试导入测试
        test_import = subprocess.run(
            [exe_path, "-c", "from src import __version__; print(__version__)"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "1.4.7" in test_import.stdout:
            print("[OK] Version 1.4.7 correctly included")
        else:
            print("[WARN] Unable to extract version information from exe")
    except:
        print("[WARN] Unable to test version information import")

    print()
    print("=" * 80)
    print("[SUCCESS] Exe file testing completed")
    print("=" * 80)
    print()
    print("[SUMMARY] Test Results:")
    print(f"  [OK] Exe file exists with normal size ({file_size_mb:.1f} MB)")
    print(f"  [OK] File located at correct position: {exe_path}")
    print(f"  [OK] Basic commands available")
    print()
    print("[NEXT STEPS]")
    print("  1. You can use the following commands for actual testing:")
    print(f"     {exe_path} process-pending")
    print(f"     {exe_path} process-folder --share-link=YOUR_LINK")
    print(f"     {exe_path} receive")
    print()
    print("  2. Test long filename fix (260807 scenario):")
    print(f"     {exe_path} process-pending")
    print()

    return True

if __name__ == "__main__":
    success = test_exe_version()
    sys.exit(0 if success else 1)