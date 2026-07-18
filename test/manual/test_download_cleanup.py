#!/usr/bin/env python3
"""
测试BaiduPCS-Go下载文件选择和清理机制
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("\n[TEST] 测试BaiduPCS-Go文件选择和清理机制")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 1. 登录
        print("\n[1/6] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 查看当前工作目录
        print(f"\n[2/6] 查看当前工作目录...")
        pwd_result = client._run_command(['pwd'])
        print(f"当前工作目录: {pwd_result['stdout'].strip()}")

        # 3. 列出根目录内容
        print(f"\n[3/6] 列出根目录内容...")
        ls_result = client._run_command(['ls', '/'])
        print(f"根目录内容:\n{ls_result['stdout']}")

        # 4. 尝试下载商业银行管理.pdf
        print(f"\n[4/6] 测试下载商业银行管理.pdf...")

        # 创建下载目录
        download_dir = Path("./download_test")
        download_dir.mkdir(parents=True, exist_ok=True)

        # 使用绝对路径下载
        remote_file = "/商业银行管理.pdf"

        print(f"下载命令: download {remote_file} --save")
        download_result = client._run_command(['download', remote_file, '--save'])

        print(f"下载返回码: {download_result['returncode']}")
        print(f"下载输出:\n{download_result['stdout']}")
        print(f"下载错误:\n{download_result['stderr']}")

        # 检查是否下载成功
        # BaiduPCS-Go默认下载到程序所在目录的download/目录
        default_download_dir = Path("./download")
        if default_download_dir.exists():
            downloaded_files = list(default_download_dir.glob("*"))
            print(f"默认下载目录中有 {len(downloaded_files)} 个文件:")
            for file in downloaded_files[:5]:
                print(f"  - {file.name} ({file.stat().st_size} 字节)")

            if downloaded_files:
                print(f"[SUCCESS] 文件已下载到默认目录")
                # 移动文件到我们指定的目录
                for file in downloaded_files:
                    target = download_dir / file.name
                    file.rename(target)
                    print(f"移动文件: {file.name} -> {target.name}")
            else:
                print("[FAILED] 默认下载目录中没有文件")
        else:
            print("[INFO] 默认下载目录不存在")

        # 5. 测试文件清理功能
        print(f"\n[5/6] 测试文件清理功能...")
        if downloaded_files:
            for file in downloaded_files:
                try:
                    if file.exists():
                        file.unlink()
                        print(f"[SUCCESS] 删除文件: {file.name}")
                except Exception as e:
                    print(f"[FAILED] 删除文件失败: {e}")

        # 6. 测试目录清理
        print(f"\n[6/6] 测试目录清理...")
        try:
            if default_download_dir.exists():
                for file in default_download_dir.glob("*"):
                    file.unlink()
                default_download_dir.rmdir()
                print("[SUCCESS] 清理下载目录")
        except Exception as e:
            print(f"[INFO] 清理下载目录: {e}")

        print("\n" + "=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())