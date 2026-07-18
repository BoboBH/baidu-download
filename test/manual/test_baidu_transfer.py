#!/usr/bin/env python3
"""
测试百度网盘分享链接转存功能
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

def test_baidu_login():
    """测试百度网盘登录"""
    print("=" * 60)
    print("测试1: 百度网盘登录")
    print("=" * 60)

    try:
        client = BaiduClient()
        result = client.login()

        if result:
            print("[SUCCESS] 登录成功")
            return True
        else:
            print("[FAILED] 登录失败")
            return False
    except Exception as e:
        print(f"[ERROR] 登录异常: {e}")
        return False

def test_save_share_link():
    """测试转存分享链接"""
    print("\n" + "=" * 60)
    print("测试2: 转存分享链接到百度网盘")
    print("=" * 60)

    try:
        # 使用原始需求中的测试链接
        share_link = "https://pan.baidu.com/s/1ir_5mHA5jNIHAstbyEZN-g"
        extraction_code = "0409"
        folder_name = "test-transfer-20240711"

        print(f"分享链接: {share_link}")
        print(f"提取码: {extraction_code}")
        print(f"目标目录: {folder_name}")

        client = BaiduClient()

        # 先登录
        if not client.login():
            print("[FAILED] 登录失败，无法继续测试")
            return False

        # 删除可能存在的旧目录
        print(f"清理旧目录: /{folder_name}")
        client.delete_directory(folder_name)

        # 转存分享链接
        print(f"开始转存分享链接...")
        result = client.save_share_link(share_link, extraction_code, folder_name)

        if result:
            print(f"[SUCCESS] 分享链接转存成功到 /{folder_name}")
            return True
        else:
            print("[FAILED] 分享链接转存失败")
            return False

    except Exception as e:
        print(f"[FAILED] 转存异常: {e}")
        return False

def test_list_pdf_files():
    """测试列出PDF文件"""
    print("\n" + "=" * 60)
    print("测试3: 列出目录中的PDF文件")
    print("=" * 60)

    try:
        folder_name = "test-transfer-20240711"

        client = BaiduClient()

        # 先登录
        if not client.login():
            print("[FAILED] 登录失败，无法继续测试")
            return False

        # 列出PDF文件
        print(f"列出 /{folder_name} 中的PDF文件...")
        pdf_files = client.list_pdf_files(folder_name)

        if pdf_files:
            print(f"[SUCCESS] 找到 {len(pdf_files)} 个PDF文件:")
            for i, file_info in enumerate(pdf_files, 1):
                print(f"  {i}. {file_info['name']} ({file_info['size']} 字节)")
            return True
        else:
            print("[FAILED] 没有找到PDF文件")
            return False

    except Exception as e:
        print(f"[FAILED] 列出文件异常: {e}")
        return False

def test_download_file():
    """测试下载文件"""
    print("\n" + "=" * 60)
    print("测试4: 下载PDF文件到本地")
    print("=" * 60)

    try:
        folder_name = "test-transfer-20240711"

        client = BaiduClient()

        # 先登录
        if not client.login():
            print("[FAILED] 登录失败，无法继续测试")
            return False

        # 获取PDF文件列表
        pdf_files = client.list_pdf_files(folder_name)

        if not pdf_files:
            print("[FAILED] 没有可下载的PDF文件")
            return False

        # 下载第一个PDF文件
        test_file = pdf_files[0]
        remote_path = test_file['name']
        local_path = f"./temp/test_download_{os.path.basename(remote_path)}"

        print(f"下载文件: {remote_path}")
        print(f"保存到: {local_path}")

        result = client.download_file(remote_path, local_path)

        if result:
            # 检查文件是否真的下载成功
            if Path(local_path).exists():
                file_size = Path(local_path).stat().st_size
                print(f"[SUCCESS] 文件下载成功，大小: {file_size} 字节")
                return True
            else:
                print("[FAILED] 下载命令成功但文件不存在")
                return False
        else:
            print("[FAILED] 文件下载失败")
            return False

    except Exception as e:
        print(f"[FAILED] 下载异常: {e}")
        return False

def main():
    """主函数"""
    print("\n[TEST] 百度网盘功能测试开始")
    print("=" * 60)

    results = []

    # 测试1: 登录
    results.append(("登录测试", test_baidu_login()))

    # 测试2: 转存分享链接
    results.append(("转存分享链接", test_save_share_link()))

    # 测试3: 列出PDF文件
    results.append(("列出PDF文件", test_list_pdf_files()))

    # 测试4: 下载文件
    results.append(("下载文件", test_download_file()))

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