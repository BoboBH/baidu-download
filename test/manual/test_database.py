#!/usr/bin/env python3
"""
测试数据库连接和操作功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.database.repository import DatabaseRepository
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("\n[TEST] 测试数据库连接和操作功能")
    print("=" * 60)

    try:
        # 1. 显示数据库配置信息（隐藏密码）
        print("\n[1/4] 检查数据库配置...")
        try:
            settings = Settings()
            print(f"[SUCCESS] 配置加载成功")
            print(f"数据库主机: {settings.db_host}")
            print(f"数据库端口: {settings.db_port}")
            print(f"数据库名称: {settings.db_name}")
            print(f"数据库用户: {settings.db_user}")
            print(f"数据库密码: {'*' * (len(settings.db_password)//2)}{settings.db_password[-2:] if len(settings.db_password) > 4 else '****'}")
        except Exception as e:
            print(f"[FAILED] 配置加载失败: {e}")
            return 1

        # 2. 测试数据库连接
        print(f"\n[2/4] 测试数据库连接...")
        try:
            db_repo = DatabaseRepository(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name
            )
            print("[SUCCESS] 数据库连接成功")
        except Exception as e:
            print(f"[FAILED] 数据库连接失败: {e}")
            print("请检查以下配置:")
            print("1. MySQL服务是否运行")
            print("2. 主机地址和端口是否正确")
            print("3. 用户名和密码是否正确")
            print("4. 数据库是否已创建")
            print("5. 是否已执行数据库初始化脚本")
            return 1

        # 3. 测试插入操作
        print(f"\n[3/4] 测试插入文件传输日志...")
        from src.database.models import FileTransferLog
        from datetime import datetime

        test_log = FileTransferLog(
            share_link="https://pan.baidu.com/s/test123",
            extraction_code="test123",
            folder_name="test_folder",
            file_name="test.pdf",
            file_path="/test/test.pdf",
            transfer_status="pending",
            start_time=datetime.now(),
            file_size=1024000
        )

        try:
            log_id = db_repo.insert_file_log(test_log)
            print(f"[SUCCESS] 插入文件日志成功，ID: {log_id}")
        except Exception as e:
            print(f"[FAILED] 插入文件日志失败: {e}")
            db_repo.close()
            return 1

        # 4. 测试更新操作
        print(f"\n[4/4] 测试更新文件状态...")
        try:
            db_repo.update_file_status(
                file_id=log_id,
                status="success",
                download_time=datetime.now(),
                upload_time=datetime.now()
            )
            print("[SUCCESS] 更新文件状态成功")
        except Exception as e:
            print(f"[FAILED] 更新文件状态失败: {e}")
            db_repo.close()
            return 1

        # 查询插入的记录进行验证
        print(f"\n[验证] 查询插入的记录...")
        try:
            logs = db_repo.get_file_logs_by_link("https://pan.baidu.com/s/test123")
            if logs:
                print(f"[SUCCESS] 查询到 {len(logs)} 条记录")
                for log in logs:
                    print(f"  - ID: {log.id}, 文件: {log.file_name}, 状态: {log.transfer_status}")
            else:
                print("[WARNING] 没有查询到记录")
        except Exception as e:
            print(f"[WARNING] 查询操作失败: {e}")

        db_repo.close()
        print("\n" + "=" * 60)
        print("[SUCCESS] 数据库功能测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())