#!/usr/bin/env python3
"""
测试修复后的 EXE 程序
"""
import subprocess
import os
from pathlib import Path

print("🧪 测试修复后的 baidu-download.exe")
print("=" * 60)

# 检查文件
exe_path = Path("release/dist/baidu-download.exe")
env_path = Path("release/dist/.env")
baidupcs_path = Path("release/dist/BaiduPCS-Go.exe")

print(f"📁 主程序: {exe_path.exists()} ({exe_path.stat().st_size / (1024*1024):.1f} MB)")
print(f"📁 配置文件: {env_path.exists()}")
print(f"📁 百度工具: {baidupcs_path.exists()} ({baidupcs_path.stat().st_size / (1024*1024):.1f} MB)")

# 读取配置
if env_path.exists():
    print("\n📝 .env 配置:")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'BAIDUPCS_GO_PATH' in line or 'BAIDU_COOKIES_PATH' in line:
                print(f"  {line.strip()}")

# 测试命令
test_command = [
    str(exe_path),
    "--link=https://pan.baidu.com/s/1Fi2LAxr441x57Kk4B6ws2Q",
    "--code=0409",
    "--folder=260710"
]

print(f"\n🚀 测试命令:")
print(f"  cd release/dist && {exe_path.name} --link=... --code=0409 --folder=260710")

print("\n📋 测试步骤:")
print("  1. 程序应该使用 ./BaiduPCS-Go.exe (相对路径)")
print("  2. 程序应该成功登录百度账号")
print("  3. 程序应该成功转存分享链接到 /260710 目录")
print("  4. 程序应该列出转存的 PDF 文件")

print("\n⚠️  如果程序仍然调用 d:\\tools\\BaiduPCS-Go，说明修复失败")
print("✅  如果程序使用 release\\dist\\BaiduPCS-Go.exe，说明修复成功")

print("\n" + "=" * 60)
print("请在 release/dist 目录下运行以下命令进行实际测试:")
print("cd release/dist")
print("./baidu-download.exe --link=https://pan.baidu.com/s/1Fi2LAxr441x57Kk4B6ws2Q --code=0409 --folder=260710")