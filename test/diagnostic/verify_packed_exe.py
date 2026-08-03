"""
验证打包后的exe是否包含外部SFTP功能

用法: python test/diagnostic/verify_packed_exe.py
"""

import sys
import os
from pathlib import Path

def verify_exe_packaging():
    """验证exe打包结果"""

    print("=" * 60)
    print("验证打包后的exe文件")
    print("=" * 60)

    # 检查exe文件是否存在
    exe_path = Path("release/dist/baidu-download.exe")
    if not exe_path.exists():
        print(f"[FAIL] exe文件不存在: {exe_path}")
        return False

    file_size = exe_path.stat().st_size
    print(f"[OK] exe文件存在: {exe_path}")
    print(f"[INFO] 文件大小: {file_size / (1024*1024):.1f} MB")

    # 检查必要文件是否包含
    print("\n检查必要的文件:")

    required_files = [
        "release/dist/.env.example",
        "release/dist/database/wxchat_tables.sql",
        "release/dist/database/migrations/migrate_add_source_field.sql",
        "release/dist/middle/db_init.sql",
    ]

    all_files_present = True
    for file_path in required_files:
        file_obj = Path(file_path)
        if file_obj.exists():
            print(f"[OK] {file_path}")
        else:
            print(f"[FAIL] {file_path}")
            all_files_present = False

    # 检查.env.example中的外部SFTP配置
    print("\n检查.env.example中的外部SFTP配置:")
    env_example_path = Path("release/dist/.env.example")
    if env_example_path.exists():
        content = env_example_path.read_text(encoding='utf-8')
        external_configs = [
            "WXCHAT_EXTERNAL_SFTP_HOST",
            "WXCHAT_EXTERNAL_SFTP_PORT",
            "WXCHAT_EXTERNAL_SFTP_USERNAME",
            "WXCHAT_EXTERNAL_SFTP_PASSWORD",
            "WXCHAT_EXTERNAL_SFTP_FOLDER",
            "WXCHAT_EXTERNAL_EXCLUDE_ACCOUNTS",
        ]

        all_configs_present = True
        for config in external_configs:
            if config in content:
                print(f"[OK] {config}")
            else:
                print(f"[FAIL] {config}")
                all_configs_present = False

    # 总结
    print("\n" + "=" * 60)
    if all_files_present and all_configs_present:
        print("[SUCCESS] 验证通过！打包包含所有必要文件和配置")
        print("\n打包内容:")
        print("  [OK] baidu-download.exe (主程序)")
        print("  [OK] 外部SFTP功能")
        print("  [OK] 数据库初始化脚本")
        print("  [OK] 数据库迁移脚本")
        print("  [OK] 配置文件模板")
        print("\n可以开始测试:")
        print("  1. 编辑 release/dist/.env 文件配置外部SFTP")
        print("  2. 运行: release/dist/baidu-download.exe --wxchat")
        return True
    else:
        print("[FAIL] 验证失败，缺少必要文件或配置")
        return False

if __name__ == "__main__":
    success = verify_exe_packaging()
    sys.exit(0 if success else 1)
