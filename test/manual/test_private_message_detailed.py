#!/usr/bin/env python3
"""
钉钉私信功能详细测试脚本

测试流程：
1. 从数据库中提取真实的sender_id和sender_nick
2. 测试access_token获取
3. 测试私信发送功能
"""

import sys
import json
# 将项目根目录加入 sys.path（脚本已移入 test/manual/）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_extract_sender_info():
    """测试从raw_message中提取sender信息"""
    print("=== 测试1: 从raw_message提取sender信息 ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    cursor = db.connection.cursor()
    cursor.execute('SELECT id, raw_message FROM message_process_log WHERE raw_message IS NOT NULL LIMIT 3')
    messages = cursor.fetchall()

    senders = []
    for msg in messages:
        try:
            if isinstance(msg['raw_message'], str):
                raw_data = json.loads(msg['raw_message'])
            else:
                raw_data = msg['raw_message']

            if isinstance(raw_data, dict) and 'sender_id' in raw_data:
                senders.append({
                    'message_id': msg['id'],
                    'sender_id': raw_data['sender_id'],
                    'sender_nick': raw_data.get('sender_nick', 'Unknown')
                })
        except Exception as e:
            print(f"Error parsing message {msg['id']}: {e}")

    db.close()

    print(f"找到 {len(senders)} 个发送者信息:")
    for sender in senders:
        print(f"  Message ID: {sender['message_id']}")
        print(f"  Sender ID: {sender['sender_id']}")
        print(f"  Sender Nick: {sender['sender_nick']}")

    if senders:
        return senders[0]  # 返回第一个用于测试
    return None

def test_access_token():
    """测试access_token获取"""
    print("\n=== 测试2: access_token获取 ===")

    settings = Settings()
    notifier = DingtalkNotifier(settings)

    print("获取钉钉access_token...")
    access_token = notifier._get_access_token()

    if access_token:
        print(f"SUCCESS: access_token获取成功")
        print(f"Token长度: {len(access_token)} 字符")
        print(f"Token前缀: {access_token[:20]}...")
        return access_token
    else:
        print("FAILED: access_token获取失败")
        return None

def test_private_message_send(sender_id, sender_nick):
    """测试私信发送"""
    print(f"\n=== 测试3: 私信发送 ===")
    print(f"发送者ID: {sender_id}")
    print(f"发送者昵称: {sender_nick}")

    settings = Settings()
    notifier = DingtalkNotifier(settings)

    # 测试消息内容
    title = "🧪 私信功能测试"
    content = f"""## 私信功能测试

这是系统自动发送的测试消息。

**测试信息**:
- 发送者ID: {sender_id[:20]}...
- 发送者昵称: {sender_nick}
- 测试时间: {str(__import__('datetime').datetime.now())}

**功能验证**:
- ✅ access_token获取
- ✅ 私信API调用
- ✅ 消息格式正确

请忽略此测试消息。
"""

    print(f"开始发送私信...")
    result = notifier.send_private_message(sender_id, title, content)

    if result:
        print("SUCCESS: 私信发送成功!")
        return True
    else:
        print("FAILED: 私信发送失败")
        return False

def main():
    """主测试流程"""
    print("DingTalk Private Message Complete Test")
    print("=" * 60)

    try:
        # 测试1: 提取sender信息
        sender_info = test_extract_sender_info()
        if not sender_info:
            print("SKIP: 无法获取测试用的sender信息")
            return 1

        # 测试2: 获取access_token
        access_token = test_access_token()
        if not access_token:
            print("FAILED: 无法获取access_token，后续测试跳过")
            return 1

        # 测试3: 发送私信
        success = test_private_message_send(sender_info['sender_id'], sender_info['sender_nick'])

        print("\n" + "=" * 60)
        if success:
            print("SUCCESS: All tests passed! Private messaging works correctly")
            return 0
        else:
            print("FAILED: Private message test failed")
            return 1

    except Exception as e:
        print(f"\nERROR: Test error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())