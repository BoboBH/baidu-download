#!/usr/bin/env python3
"""
Quick test to check if the current exe has the new logging code
"""

import subprocess
import os

def test_exe_has_new_code():
    """Test if exe has new feedback logging code"""

    exe_path = r"d:\git\baidu-download\release\dist\baidu-download.exe"

    if not os.path.exists(exe_path):
        print(f"ERROR: {exe_path} does not exist")
        return False

    print("Checking exe file...")
    print(f"Path: {exe_path}")
    print(f"Size: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
    print()

    # Try to get version info
    try:
        result = subprocess.run(
            ["powershell", "Get-Item", exe_path, "|", "Select-Object", "Name", "Length", "LastWriteTime"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("File info:")
        print(result.stdout)
    except Exception as e:
        print(f"Cannot get file info: {e}")

    print()
    print("=" * 60)
    print("IMPORTANT: You need to RESTART the service!")
    print("=" * 60)
    print()
    print("Steps:")
    print("1. Stop the current running service (Ctrl+C)")
    print("2. Run the exe again:")
    print("   cd release")
    print("   baidu-download.exe --dingtalk-service")
    print("3. Send a test message in DingTalk")
    print("4. Check if you see detailed feedback logs")
    print()
    print("The new logs should show:")
    print("- 🎯 准备发送反馈消息...")
    print("- 📱 群聊: ...")
    print("- 📝 反馈标题: feedback: ...")
    print("- 📤 准备发送钉钉消息...")
    print("- 📡 HTTP 状态码: ...")

if __name__ == "__main__":
    test_exe_has_new_code()
