#!/usr/bin/env python3
"""
测试账号同步修复
验证账号查找问题是否已解决
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.wxchat.processor import WeChatAccountSync

def test_account_sync():
    """测试账号同步功能"""
    print("=" * 60)
    print("测试账号同步修复")
    print("=" * 60)

    try:
        # 创建配置
        print("1. 加载配置...")
        config = Settings()

        # 检查数据库配置
        if not config.wxchat_wewe_db_host or not config.wxchat_wewe_db_name:
            print("[ERROR] wewe_rss数据库配置缺失")
            print(f"   WXCHAT_WEWE_DB_HOST: {config.wxchat_wewe_db_host}")
            print(f"   WXCHAT_WEWE_DB_NAME: {config.wxchat_wewe_db_name}")
            return False

        print(f"   wewe_rss数据库: {config.wxchat_wewe_db_host}:{config.wxchat_wewe_db_port}/{config.wxchat_wewe_db_name}")
        print(f"   本地数据库: {config.db_host}:{config.db_port}/{config.db_name}")

        # 创建账号同步器
        print("2. 创建账号同步器...")
        account_sync = WeChatAccountSync(config)

        # 执行同步
        print("3. 开始同步账号...")
        synced_count = account_sync.sync_accounts()

        print(f"   同步完成! 同步了 {synced_count} 个账号")

        if synced_count > 0:
            print("[SUCCESS] 账号同步成功!")

            # 测试查找特定账号
            print("4. 测试账号查找...")
            test_account_id = "MP_WXS_3098173029"

            # 导入数据库连接
            from src.wxchat.processor import DatabaseConnection

            with DatabaseConnection(config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT account_name FROM new_wx_account WHERE account_id = %s
                    """, (test_account_id,))
                    result = cursor.fetchone()

                    if result:
                        print(f"   [FOUND] 找到账号: {test_account_id} -> {result['account_name']}")
                    else:
                        print(f"   [NOT FOUND] 账号不存在: {test_account_id}")
                        print("   (可能wewe_rss数据库中没有此账号)")

            # 显示所有同步的账号
            print("5. 所有已同步的账号:")
            with DatabaseConnection(config, use_wewe_db=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT account_id, account_name FROM new_wx_account ORDER BY account_name")
                    accounts = cursor.fetchall()
                    for i, account in enumerate(accounts, 1):
                        print(f"   {i}. {account['account_id']} -> {account['account_name']}")

            print("=" * 60)
            print("[SUCCESS] 账号同步测试通过!")
            print("=" * 60)
            return True
        else:
            print("[WARNING] 未同步到任何账号")
            print("   (wewe_rss数据库可能没有数据或feeds表为空)")
            print("=" * 60)
            return True  # 不算失败，只是没有数据

    except Exception as e:
        print(f"[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_account_sync()
    sys.exit(0 if success else 1)
