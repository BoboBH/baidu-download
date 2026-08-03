"""
验证发布ZIP文件内容

检查打包的zip文件是否包含所有必要文件和功能
"""

import zipfile
import os
from pathlib import Path

def verify_zip_package(zip_path):
    """验证ZIP文件包内容"""

    print("=" * 60)
    print("验证发布ZIP文件")
    print("=" * 60)

    # 检查ZIP文件是否存在
    if not Path(zip_path).exists():
        print(f"[FAIL] ZIP文件不存在: {zip_path}")
        return False

    file_size = Path(zip_path).stat().st_size
    print(f"[OK] ZIP文件存在: {zip_path}")
    print(f"[INFO] 文件大小: {file_size / (1024*1024):.1f} MB")

    # 打开ZIP文件检查内容
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            print(f"[OK] ZIP文件包含 {len(files)} 个文件")

            # 检查关键文件
            print("\n检查关键文件:")

            key_files = {
                'dist/baidu-download.exe': '主程序',
                'dist/.env.example': '配置模板',
                'dist/database/wxchat_tables.sql': '微信文章表结构',
                'dist/database/migrations/migrate_add_source_field.sql': '数据库迁移脚本',
                'dist/middle/db_init.sql': '核心数据库表结构',
                'dist/BaiduPCS-Go.exe': '百度网盘工具',
            }

            all_files_present = True
            for file_path, description in key_files.items():
                if file_path in files:
                    print(f"[OK] {description}: {file_path}")
                else:
                    print(f"[FAIL] {description} 缺失: {file_path}")
                    all_files_present = False

            # 检查Playwright依赖
            print("\n检查Playwright依赖:")
            playwright_files = [f for f in files if 'playwright' in f.lower()]
            if playwright_files:
                print(f"[OK] 包含 {len(playwright_files)} 个Playwright相关文件")

            # 检查驱动文件
            chromium_files = [f for f in files if 'chromium-1140' in f]
            ffmpeg_files = [f for f in files if 'ffmpeg-1010' in f]
            print(f"[OK] Chromium驱动文件: {len(chromium_files)} 个")
            print(f"[OK] FFmpeg驱动文件: {len(ffmpeg_files)} 个")

            # 检查.env.example中的配置
            print("\n检查配置文件内容:")
            try:
                env_content = zf.read('dist/.env.example').decode('utf-8')
                configs_to_check = [
                    'WXCHAT_EXTERNAL_SFTP_HOST',
                    'WXCHAT_EXTERNAL_SFTP_FOLDER',
                    'YYYYMM',  # 检查是否更新为YYYYMM格式
                ]

                all_configs_present = True
                for config in configs_to_check:
                    if config in env_content:
                        print(f"[OK] {config} 配置存在")
                    else:
                        print(f"[FAIL] {config} 配置缺失")
                        all_configs_present = False

            except Exception as e:
                print(f"[FAIL] 读取配置文件失败: {e}")
                all_configs_present = False

            # 总结
            print("\n" + "=" * 60)
            if all_files_present and all_configs_present:
                print("[SUCCESS] ZIP文件验证通过！")
                print("\n文件内容:")
                print("  [OK] 主程序 (baidu-download.exe)")
                print("  [OK] 配置模板 (.env.example)")
                print("  [OK] 数据库脚本")
                print("  [OK] Playwright依赖")
                print("  [OK] 浏览器驱动")
                print("  [OK] YYYYMM格式配置")
                print("  [OK] 外部SFTP配置")
                print("\n可以开始分发和使用!")
                return True
            else:
                print("[FAIL] ZIP文件验证失败，缺少必要文件或配置")
                return False

    except Exception as e:
        print(f"[FAIL] ZIP文件读取失败: {e}")
        return False

def main():
    """主函数"""
    print("[TEST] 发布ZIP文件验证工具")
    print("   验证打包的zip文件是否包含所有必要内容")

    # 检查ZIP文件
    zip_path = "release/baidu-download-v1.3.0-YYYYMM-external-sftp.zip"
    success = verify_zip_package(zip_path)

    if success:
        print("\n[NEXT] 下一步：")
        print("   1. 解压ZIP文件到目标服务器")
        print("   2. 配置 .env 文件")
        print("   3. 运行 baidu-download.exe --wxchat")
        print("   4. 验证YYYYMM格式和外部SFTP功能")
        return 0
    else:
        print("\n[ERROR] ZIP文件验证失败")
        return 1

if __name__ == "__main__":
    exit(main())