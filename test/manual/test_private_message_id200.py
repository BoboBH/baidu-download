#!/usr/bin/env python3
"""
测试私信功能 - 使用message_id=200的真实数据

测试流程：
1. 从数据库读取message_id=200的完整信息
2. 从raw_message中提取sender信息
3. 调用私信发送接口
4. 观察详细的发送结果和错误信息
"""

import sys
import os
import json
import pymysql
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_database_connection():
    """获取数据库连接"""
    load_dotenv()
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'baidu_download')
    )

def test_private_message_for_id200():
    """测试message_id=200的私信发送"""
    print("=" * 80)
    print("测试私信功能 - Message ID 200")
    print("=" * 80)

    try:
        # 1. 读取message_id=200的完整信息
        conn = get_database_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, message_type, folder_name, process_status, raw_message,
                   share_link, error_message
            FROM message_process_log
            WHERE id = 200
        """)

        result = cursor.fetchone()
        if not result:
            print("[ERROR] 未找到ID=200的记录")
            return False

        message_id, message_type, folder_name, process_status, raw_message, share_link, error_message = result

        print(f"\n[MESSAGE] 消息基本信息:")
        print(f"  ID: {message_id}")
        print(f"  Type: {message_type}")
        print(f"  Folder: {folder_name}")
        print(f"  Status: {process_status}")
        print(f"  Share Link: {share_link}")
        print(f"  Error Message: {error_message}")

        # 2. 解析raw_message提取sender信息
        print(f"\n[SENDER] 提取Sender信息:")
        if raw_message:
            try:
                raw_data = json.loads(raw_message)
                print("  Raw Message JSON内容:")
                for key, value in raw_data.items():
                    if key != 'content':  # 跳过很长的content字段
                        print(f"    {key}: {value}")

                # 提取sender信息 - 使用与代码相同的逻辑
                sender_id_for_private = raw_data.get('sender_staff_id') or raw_data.get('sender_id')
                sender_nick_for_private = raw_data.get('sender_nick')

                print(f"\n  [TARGET] 用于私信的Sender信息:")
                print(f"    sender_staff_id: {raw_data.get('sender_staff_id')}")
                print(f"    sender_id: {raw_data.get('sender_id')}")
                print(f"    sender_nick: {sender_nick_for_private}")
                print(f"    最终使用ID: {sender_id_for_private}")

                if not sender_id_for_private:
                    print("  [ERROR] 没有找到sender信息，无法发送私信")
                    return False

            except json.JSONDecodeError as e:
                print(f"  [ERROR] Raw Message解析失败: {e}")
                return False
        else:
            print("  [ERROR] Raw Message为空")
            return False

        # 3. 准备测试私信内容
        print(f"\n[CONTENT] 准备私信内容:")
        title = "测试私信功能 - ID200处理结果"
        content = f"""## 测试私信通知

**消息ID**: {message_id}
**消息类型**: {message_type}
**文件夹**: {folder_name or 'unknown'}
**状态**: {process_status}

**测试目的**: 验证私信功能是否正常工作
**测试时间**: {os.popen('date').read().strip()}

此消息用于测试message_id=200的私信发送功能。
"""

        if sender_nick_for_private:
            content = f"@{sender_nick_for_private} " + content

        print(f"  Title: {title}")
        print(f"  Content长度: {len(content)} 字符")
        print(f"  Target User ID: {sender_id_for_private}")

        # 4. 调用私信发送接口
        print(f"\n[SEND] 开始发送私信测试:")
        print("-" * 80)

        from src.config.settings import Settings
        from src.notification.dingtalk_notifier import DingtalkNotifier

        settings = Settings()
        notifier = DingtalkNotifier(settings)

        # 发送私信
        result = notifier.send_private_message(
            user_id=sender_id_for_private,
            title=title,
            content=content
        )

        print("-" * 80)
        print(f"\n[RESULT] 测试结果:")
        if result:
            print("  [SUCCESS] 私信发送成功!")
        else:
            print("  [FAILED] 私信发送失败!")

        print(f"\n[SUMMARY] 总结:")
        print(f"  数据库Message ID: {message_id}")
        print(f"  从raw_message提取的sender_id: {sender_id_for_private}")
        print(f"  私信发送结果: {'成功' if result else '失败'}")

        conn.close()
        return result

    except Exception as e:
        print(f"\n[ERROR] 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_private_message_for_id200()
    sys.exit(0 if success else 1)
