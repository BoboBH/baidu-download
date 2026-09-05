"""
Simple ZIP processor test - avoid Unicode issues
"""
import os
import sys
from pathlib import Path

# Setup project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor, DownloadResult
from src.feishu.models import ParseResult

def test_zip_file(zip_path):
    """Test ZIP file processing"""
    try:
        settings = Settings()
        processor = DingTalkFileProcessor(settings)

        # Create temp directory
        import tempfile
        temp_dir = tempfile.mkdtemp()

        download_result = DownloadResult(
            success=True,
            local_path=zip_path,
            filename=os.path.basename(zip_path),
            file_size=os.path.getsize(zip_path),
            temp_dir=temp_dir
        )

        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='test_id',
            source='dingtalk',
            file_name=os.path.basename(zip_path),
            download_code='test_code'
        )

        # Process ZIP
        process_result = processor.process(download_result, parse_result)

        if process_result.success:
            print(f"SUCCESS: {os.path.basename(zip_path)} - {len(process_result.processed_files)} files extracted")

            # Verify files exist
            for file_path in process_result.processed_files:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path) / 1024
                    print(f"  OK: {os.path.basename(file_path)} ({size:.1f} KB)")
                else:
                    print(f"  MISSING: {file_path}")

            success = True
        else:
            print(f"FAILED: {os.path.basename(zip_path)} - {process_result.error}")
            success = False

        # Cleanup
        processor.cleanup()
        return success

    except Exception as e:
        print(f"EXCEPTION: {os.path.basename(zip_path)} - {e}")
        return False

def main():
    """Test all ZIP files"""
    zip_files = [
        "D:\\temp\\zip-file\\2-reports.zip",
        "D:\\temp\\zip-file\\3-reports.zip",
        "D:\\temp\\zip-file\\4-reports.zip"
    ]

    print("ZIP Processor Test")
    print("=" * 50)

    results = {}
    for zip_file in zip_files:
        if os.path.exists(zip_file):
            success = test_zip_file(zip_file)
            results[os.path.basename(zip_file)] = success
        else:
            print(f"NOT FOUND: {zip_file}")
            results[os.path.basename(zip_file)] = False

    # Summary
    print("=" * 50)
    print("Results:")
    for name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"  {name}: {status}")

    all_success = all(results.values())
    print("=" * 50)
    if all_success:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
