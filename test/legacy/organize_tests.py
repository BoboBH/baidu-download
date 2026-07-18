#!/usr/bin/env python3
"""
测试文件组织脚本
将根目录下的测试文件移动到适当的测试目录中
"""

import os
import shutil
from pathlib import Path

def organize_test_files():
    """组织测试文件到适当的目录"""

    # 定义文件映射关系
    file_mappings = {
        # 单元测试 -> test/unit/
        'test_pdf_detection.py': 'test/unit/test_pdf_detection.py',

        # 手动测试 -> test/manual/
        'test_fixed_exe.py': 'test/manual/test_fixed_exe.py',
        'test_settings_fix.py': 'test/manual/test_settings_fix.py',
        'test_sftp_connection.py': 'test/manual/test_sftp_connection.py',
        'test_transfer.py': 'test/manual/test_transfer.py',
        'interactive_sftp_test.py': 'test/manual/test_interactive_sftp.py',

        # 诊断工具 -> tools/
        'diagnose_exe.py': 'tools/diagnose_exe.py',
        'diagnose_sftp.py': 'tools/diagnose_sftp.py',
        'diagnose_transfer_issue.py': 'tools/diagnose_transfer_issue.py',
    }

    # 创建必要的目录
    directories = ['test/unit', 'test/manual', 'tools']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Ensured directory exists: {directory}")

    # 移动文件
    moved_count = 0
    skipped_count = 0

    for source_file, target_file in file_mappings.items():
        if not os.path.exists(source_file):
            print(f"⊘ Skipped (not found): {source_file}")
            skipped_count += 1
            continue

        if os.path.exists(target_file):
            print(f"⊘ Skipped (already exists): {source_file} -> {target_file}")
            skipped_count += 1
            continue

        try:
            shutil.copy2(source_file, target_file)
            print(f"✓ Copied: {source_file} -> {target_file}")
            moved_count += 1
        except Exception as e:
            print(f"✗ Failed to copy {source_file}: {e}")

    print(f"\n{'='*60}")
    print(f"Organization Summary:")
    print(f"  Moved: {moved_count} files")
    print(f"  Skipped: {skipped_count} files")
    print(f"{'='*60}")

    # 显示根目录剩余的测试文件
    print(f"\nRemaining test files in root directory:")
    remaining_files = []
    for file in os.listdir('.'):
        if file.endswith('.py') and (file.startswith('test_') or
                                     file.startswith('diagnose_') or
                                     file.startswith('interactive_')):
            remaining_files.append(file)

    if remaining_files:
        for file in remaining_files:
            print(f"  - {file}")
    else:
        print("  None! All test files have been organized.")

if __name__ == '__main__':
    print("="*60)
    print("测试文件组织脚本")
    print("="*60)
    print()
    organize_test_files()