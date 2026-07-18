#!/usr/bin/env python3
"""
使用用户提供的分享链接测试完整流程
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
    print("\n[TEST] 使用用户提供的分享链接测试完整流程")
    print("=" * 60)

    try:
        # 用户提供的分享链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "user-test-20240711"

        print(f"分享链接: {share_link}")
        print(f"提取码: {extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 1. 测试登录
        print("\n[1/5] 测试登录...")
        if not client.login():
            print("[FAILED] 登录失败")
            return 1
        print("[SUCCESS] 登录成功")

        # 2. 清理并转存分享链接
        print(f"\n[2/5] 转存分享链接到网盘...")
        client.delete_directory(folder_name)

        if not client.save_share_link(share_link, extraction_code, folder_name):
            print("[FAILED] 分享链接转存失败")
            return 1
        print(f"[SUCCESS] 分享链接转存成功到 /{folder_name}")

        # 3. 查看转存后的目录结构
        print(f"\n[3/5] 查看转存后的目录结构...")
        structure_result = client._run_command(['ls', f'/{folder_name}'])
        print(f"顶层目录结构:\n{structure_result['stdout']}")

        # 4. 列出PDF文件
        print(f"\n[4/5] 查找PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)

        if pdf_files:
            print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件:")
            for i, file_info in enumerate(pdf_files[:5], 1):  # 只显示前5个
                print(f"  {i}. {file_info['name']} ({file_info['size']} 字节)")
            if len(pdf_files) > 5:
                print(f"  ... 还有 {len(pdf_files) - 5} 个文件")
        else:
            print("[INFO] 没有找到PDF文件")
            return 0

        # 5. 测试下载第一个PDF文件
        print(f"\n[5/5] 测试下载PDF文件...")
        test_file = pdf_files[0]
        remote_path = test_file['name']
        local_path = f"./temp/{os.path.basename(remote_path)}"

        print(f"下载文件: {remote_path}")
        print(f"保存到: {local_path}")

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 文件下载失败")
            # 显示下载命令的详细输出
            download_result = client._run_command(['download', '--save', './temp/', remote_path])
            print(f"下载命令输出: {download_result['stdout']}")
            print(f"下载命令错误: {download_result['stderr']}")
            return 1

        # 检查下载的文件
        if Path(local_path).exists():
            file_size = Path(local_path).stat().st_size
            print(f"[SUCCESS] 文件下载成功")
            print(f"文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")

            # 验证PDF文件头
            if file_size > 1000:
                with open(local_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print("[SUCCESS] PDF文件验证通过")
                    else:
                        print(f"[WARNING] 文件头: {header}")
        else:
            print("[FAILED] 下载命令成功但文件不存在")
            return 1

        print("\n" + "=" * 60)
        print("[SUCCESS] 完整流程测试成功！")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())