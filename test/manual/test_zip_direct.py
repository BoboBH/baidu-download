"""
直接测试ZIP文件编码检测逻辑
避免每次都从数据库下载
"""

import os
import zipfile
import sys
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.utils.filename_handler import FilenameHandler

def test_zip_encoding_detection(zip_file_path):
    """测试单个ZIP文件的编码检测"""
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(zip_file_path)}")
    print(f"{'='*60}")

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            print(f"ZIP contains {len(zip_ref.filelist)} files\n")

            for file_info_obj in zip_ref.filelist[:3]:  # 只看前3个文件
                try:
                    print(f"Raw ZIP filename: {repr(file_info_obj.filename)}")
                except UnicodeEncodeError:
                    print(f"Raw ZIP filename: [Contains unprintable characters]")

                # 使用项目的编码检测逻辑
                wrong_decoded_name = file_info_obj.filename
                filename_bytes = wrong_decoded_name.encode('cp437')

                # 测试各种编码
                encodings_to_try = [
                    ('gbk', 'GBK (简体中文)'),
                    ('gb2312', 'GB2312 (简体中文)'),
                    ('gb18030', 'GB18030 (中文)'),
                    ('utf-8', 'UTF-8 (国际通用)'),
                    ('shift_jis', 'Shift JIS (日文)'),
                    ('euc-kr', 'EUC-KR (韩文)'),
                    ('big5', 'Big5 (繁体中文)'),
                ]

                print("Testing encodings:")
                for encoding, description in encodings_to_try:
                    try:
                        decoded_name = filename_bytes.decode(encoding)
                        print(f"  {encoding:12} -> {decoded_name[:60]}...")
                    except UnicodeDecodeError as e:
                        print(f"  {encoding:12} -> ❌ DecodeError")

                # 使用项目的filename handler
                handler = FilenameHandler()
                clean_name = handler.sanitize_filename(wrong_decoded_name)
                print(f"Cleaned filename: {clean_name}")
                print("-" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """测试所有ZIP文件"""
    zip_files = [
        "D:\\temp\\zip-file\\2-reports.zip",
        "D:\\temp\\zip-file\\3-reports.zip",
        "D:\\temp\\zip-file\\4-reports.zip"
    ]

    print("ZIP文件编码检测测试")
    print("=" * 60)

    for zip_file in zip_files:
        if os.path.exists(zip_file):
            test_zip_encoding_detection(zip_file)
        else:
            print(f"File not found: {zip_file}")

if __name__ == "__main__":
    main()
