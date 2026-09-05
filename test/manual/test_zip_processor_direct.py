"""
直接测试ZIP处理器，使用本地文件
"""
import os
import sys
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor, DownloadResult
from src.feishu.models import ParseResult
from src.utils.logger import get_logger

# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s [%(asctime)s] %(message)s')

logger = get_logger(__name__)

def test_zip_file_directly(zip_path):
    """直接处理ZIP文件"""
    try:
        settings = Settings()
        processor = DingTalkFileProcessor(settings)

        print(f"\n{'='*60}")
        print(f"Testing: {os.path.basename(zip_path)}")
        print(f"{'='*60}")

        # 创建一个模拟的下载结果
        import tempfile
        temp_dir = tempfile.mkdtemp()

        download_result = DownloadResult(
            success=True,
            local_path=zip_path,
            filename=os.path.basename(zip_path),
            file_size=os.path.getsize(zip_path),
            temp_dir=temp_dir
        )

        # 创建模拟的ParseResult
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='test_unique_id',
            source='dingtalk',
            file_name=os.path.basename(zip_path),
            download_code='test_code'
        )

        # 处理ZIP文件
        print("Starting ZIP extraction...")
        process_result = processor.process(download_result, parse_result)

        if process_result.success:
            print(f"✅ SUCCESS: Extracted {len(process_result.processed_files)} files")
            for i, file_path in enumerate(process_result.processed_files, 1):
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / 1024
                    file_name = os.path.basename(file_path)
                    print(f"  {i}. {file_name} ({file_size:.1f} KB)")
                else:
                    print(f"  {i}. [FILE NOT FOUND]: {file_path}")
        else:
            print(f"❌ FAILED: {process_result.error}")

        # 清理
        processor.cleanup()
        return process_result.success

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """测试所有ZIP文件"""
    zip_files = [
        "D:\\temp\\zip-file\\2-reports.zip",
        "D:\\temp\\zip-file\\3-reports.zip",
        "D:\\temp\\zip-file\\4-reports.zip"
    ]

    print("ZIP处理器直接测试")
    print("=" * 60)

    results = {}
    for zip_file in zip_files:
        if os.path.exists(zip_file):
            success = test_zip_file_directly(zip_file)
            results[os.path.basename(zip_file)] = success
        else:
            print(f"File not found: {zip_file}")
            results[os.path.basename(zip_file)] = False

    # 总结
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("-" * 60)
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{name}: {status}")

    all_success = all(results.values())
    print("-" * 60)
    if all_success:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
