#!/usr/bin/env python3
"""
诊断现有 EXE 的问题
"""
import subprocess
import os
from pathlib import Path

print("🔍 诊断现有 baidu-download.exe 的问题")
print("=" * 60)

# 检查现有文件
exe_path = Path("release/dist/baidu-download.exe")
env_path = Path("release/dist/.env")
baidupcs_path = Path("release/dist/BaiduPCS-Go.exe")

print(f"📁 EXE 文件: {exe_path.exists()}")
print(f"📁 ENV 文件: {env_path.exists()}")
print(f"📁 BaiduPCS-Go 文件: {baidupcs_path.exists()}")

if env_path.exists():
    print("\n📝 .env 文件内容:")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'BAIDUPCS_GO_PATH' in line or 'BAIDU_COOKIES_PATH' in line:
                print(f"  {line.strip()}")

# 检查源代码
print("\n📝 检查源代码中的路径处理:")
settings_path = Path("src/config/settings.py")
if settings_path.exists():
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "get_executable_dir()" in content:
            print("  ✅ 源代码包含 get_executable_dir() 调用")
        else:
            print("  ❌ 源代码缺少 get_executable_dir() 调用")

        # 检查 BaiduPCS-Go 路径处理
        if "baidupcs_go_path = str(baidupcs_path)" in content:
            print("  ✅ 源代码包含路径转换逻辑")
        else:
            print("  ❌ 源代码缺少路径转换逻辑")

print("\n🔧 需要重新编译并打包")
