#!/usr/bin/env python3
"""
重新测试登录和下载功能
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
    print("\n[TEST] 重新测试登录和下载功能")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/3] 重新测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 测试下载根目录的PDF
        print(f"\n[2/3] 下载根目录的已知PDF文件...")
        remote_path = "/商业银行管理.pdf"
        local_path = "./download_test/商业银行管理.pdf"

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 文件下载失败")
            return 1

        # 检查下载的文件
        if Path(local_path).exists():
            file_size = Path(local_path).stat().st_size
            print(f"[SUCCESS] 文件下载成功")
            print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
        else:
            print("[FAILED] 文件不存在")
            return 1

        # 3. 测试下载260709目录的PDF
        print(f"\n[3/3] 尝试下载260709目录的PDF...")
        # 列出260709目录中的PDF文件
        list_result = client._run_command(['ls', '/260709'])
        print(f"260709目录列表输出:\n{list_result['stdout']}")
        print(f"错误输出:\n{list_result['stderr']}")

        # 如果能列出文件，尝试下载第一个PDF
        if list_result['returncode'] == 0 and 'pdf' in list_result['stdout'].lower():
            print("找到PDF文件，尝试下载第一个...")
            # 解析第一个PDF文件名
            for line in list_result['stdout'].split('\n'):
                if '.pdf' in line.lower():
                    parts = line.split()
                    if len(parts) >= 4:
                        filename = parts[-1].strip()
                        if filename.lower().endswith('.pdf'):
                            remote_pdf = f"/260709/{filename}"
                            local_pdf = f"./download_test/{filename}"
                            print(f"尝试下载: {remote_pdf}")

                            if client.download_file(remote_pdf, local_pdf):
                                print(f"[SUCCESS] 260709目录PDF下载成功")
                            else:
                                print(f"[FAILED] 260709目录PDF下载失败")
                            break
        else:
            print("[INFO] 无法列出260709目录内容")

        print("\n" + "=" * 60)
        print("[SUCCESS] 测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())