#!/usr/bin/env python3
"""
测试下载和上传功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.downloader.baidu_client import BaiduClient
from src.uploader.sftp_client import SFTPClient
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_download_functionality():
    """测试下载功能"""
    print("=" * 60)
    print("测试1: 百度网盘下载功能")
    print("=" * 60)

    try:
        client = BaiduClient()

        # 登录
        print("[1/4] 登录百度网盘...")
        if not client.login():
            print("[FAILED] 登录失败")
            return False
        print("[SUCCESS] 登录成功")

        # 转存分享链接
        print("\n[2/4] 转存分享链接...")
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        code = "0409"
        folder_name = "test-download-upload"

        # 删除旧目录
        client.delete_directory(folder_name)

        if not client.save_share_link(share_link, code, folder_name):
            print("[FAILED] 转存失败")
            return False
        print("[SUCCESS] 转存成功")

        # 列出PDF文件
        print("\n[3/4] 列出PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)
        if not pdf_files:
            print("[FAILED] 没有找到PDF文件")
            return False
        print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件")

        # 下载第一个文件
        print("\n[4/4] 下载第一个PDF文件...")
        test_file = pdf_files[0]
        remote_path = test_file['name']
        local_path = f"./temp/{os.path.basename(remote_path)}"

        print(f"下载文件: {remote_path}")
        print(f"保存到: {local_path}")

        if not client.download_file(remote_path, local_path):
            print("[FAILED] 下载失败")
            return False

        # 验证文件存在
        if not Path(local_path).exists():
            print("[FAILED] 文件不存在")
            return False

        file_size = Path(local_path).stat().st_size
        print(f"[SUCCESS] 下载成功，文件大小: {file_size} 字节")
        return True

    except Exception as e:
        print(f"[ERROR] 下载测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_upload_functionality():
    """测试上传功能"""
    print("\n" + "=" * 60)
    print("测试2: SFTP上传功能")
    print("=" * 60)

    try:
        # 检查是否有下载的文件可以上传
        temp_dir = Path("./temp")
        pdf_files = list(temp_dir.glob("*.pdf"))

        if not pdf_files:
            print("[WARNING] 没有找到可上传的文件")
            print("请先运行下载测试")
            return False

        # 使用第一个PDF文件进行测试
        test_file = pdf_files[0]
        print(f"准备上传文件: {test_file}")

        client = SFTPClient()

        # 连接SFTP
        print("\n[1/3] 连接SFTP服务器...")
        if not client.connect():
            print("[FAILED] SFTP连接失败")
            return False
        print("[SUCCESS] SFTP连接成功")

        # 上传文件
        print("\n[2/3] 上传文件...")
        remote_path = f"/sftp01/upload/test/{test_file.name}"

        if not client.upload_file(str(test_file), remote_path):
            print("[FAILED] 上传失败")
            return False
        print(f"[SUCCESS] 上传成功: {remote_path}")

        # 断开连接
        print("\n[3/3] 断开连接...")
        client.disconnect()
        print("[SUCCESS] 测试完成")

        return True

    except Exception as e:
        print(f"[ERROR] 上传测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cleanup_functionality():
    """测试清理功能"""
    print("\n" + "=" * 60)
    print("测试3: 临时文件清理功能")
    print("=" * 60)

    try:
        temp_dir = Path("./temp")

        # 列出当前临时文件
        pdf_files = list(temp_dir.glob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个临时PDF文件")

        if pdf_files:
            print("\n清理临时文件...")
            for file in pdf_files:
                file.unlink()
                print(f"已删除: {file.name}")

        print("[SUCCESS] 临时文件清理完成")
        return True

    except Exception as e:
        print(f"[ERROR] 清理测试异常: {e}")
        return False

def main():
    """主函数"""
    print("\n[TEST] 下载和上传功能测试")
    print("=" * 60)

    results = []

    # 测试1: 下载功能
    results.append(("下载功能", test_download_functionality()))

    # 测试2: 上传功能
    results.append(("上传功能", test_upload_functionality()))

    # 测试3: 清理功能
    results.append(("清理功能", test_cleanup_functionality()))

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "[SUCCESS] 通过" if result else "[FAILED] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print("=" * 60)
    print(f"测试通过率: {passed}/{len(results)}")

    return 0 if passed == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())