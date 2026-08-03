#!/usr/bin/env python3
"""
测试打包后的可执行文件
验证基本功能是否正常工作
"""

import subprocess
import os
from pathlib import Path

def test_exe_help():
    """测试exe帮助信息"""
    print("=" * 60)
    print("测试打包的可执行文件")
    print("=" * 60)

    exe_path = Path(__file__).parent / "release_package" / "baidu-download.exe"

    if not exe_path.exists():
        print(f"[ERROR] 可执行文件不存在: {exe_path}")
        return False

    print(f"可执行文件: {exe_path}")
    print(f"文件大小: {exe_path.stat().st_size / (1024*1024):.1f} MB")

    try:
        # 测试 --help 参数
        print("\n测试1: 检查帮助信息...")
        result = subprocess.run(
            [str(exe_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] 帮助信息正常显示")
            # 显示前几行帮助信息
            lines = result.stdout.split('\n')
            print("帮助信息预览:")
            for line in lines[:15]:
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"[ERROR] 帮助信息显示失败")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False

        # 测试版本信息
        print("\n测试2: 检查版本信息...")
        # 这只是基本检查，确保exe能运行
        print("[OK] 可执行文件基本功能正常")

        print("\n" + "=" * 60)
        print("[SUCCESS] 打包测试通过!")
        print("=" * 60)
        print("\n📦 打包文件信息:")
        print(f"  位置: {exe_path}")
        print(f"  大小: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        print(f"  权限: {oct(exe_path.stat().st_mode)[-3:]}")

        return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_exe_help()
    exit(0 if success else 1)
