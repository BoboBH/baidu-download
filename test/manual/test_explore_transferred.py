#!/usr/bin/env python3
"""
探索转存后的目录内容
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
    print("\n[TEST] 探索转存后的目录内容")
    print("=" * 60)

    try:
        folder_name = "fixed-test-20240711"

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/4] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 列出根目录
        print(f"\n[2/4] 列出转存目录: /{folder_name}")
        root_result = client._run_command(['ls', f'/{folder_name}'])
        print(f"根目录内容:\n{root_result['stdout']}")

        # 3. 列出子目录
        if '260709' in root_result['stdout']:
            subfolder = f"/{folder_name}/260709"
            print(f"\n[3/4] 列出子目录: {subfolder}")
            sub_result = client._run_command(['ls', subfolder])
            print(f"子目录内容:\n{sub_result['stdout']}")

            # 检查是否有PDF文件
            if '.pdf' in sub_result['stdout'].lower():
                print("[SUCCESS] 在子目录中找到PDF文件！")

                # 尝试列出所有PDF文件
                print(f"\n[4/4] 查找所有PDF文件...")
                all_files_result = client._run_command(['ls', '-r', f'/{folder_name}'])
                print(f"递归列出所有文件:\n{all_files_result['stdout']}")

                # 解析PDF文件
                pdf_files = []
                for line in all_files_result['stdout'].split('\n'):
                    if '.pdf' in line.lower():
                        print(f"找到PDF文件: {line.strip()}")
                        # 简单的解析逻辑
                        parts = line.split()
                        if len(parts) >= 3:
                            pdf_files.append({
                                'name': f"/{folder_name}/" + parts[-1],
                                'size': 0  # 暂时设为0
                            })

                print(f"共找到 {len(pdf_files)} 个PDF文件")
            else:
                print("[INFO] 子目录中没有PDF文件")
        else:
            print("[INFO] 没有找到260709子目录")

        print("\n" + "=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())