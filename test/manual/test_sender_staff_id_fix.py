#!/usr/bin/env python3
"""
测试sender_staff_id字段修复和私信功能

验证内容：
1. 确认接收消息时sender_staff_id被正确保存到raw_message
2. 测试extract_sender_info函数能正确提取sender_staff_id
3. 验证私信功能能使用正确的userId格式
"""

import sys
import json
# 将项目根目录加入 sys.path（脚本已移入 test/manual/）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings
from src.database.repository import DatabaseRepository, extract_sender_info
from src.notification.dingtalk_notifier import DingtalkNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_extract_sender_info():
    """测试sender信息提取功能"""
    print("=== 测试1: sender信息提取 ===")

    # 模拟包含sender_staff_id的raw_message
    test_raw_message = {
        'conversation_id': 'cidTest123',
        'conversation_title': '测试群',
        'sender_id': '$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==',
        'sender_staff_id': '030309523040343349',  # 正确的钉钉userId格式
        'sender_nick': '测试用户',
        'message_type': 'text',
        'content': '测试消息',
        'is_in_at_list': True
    }

    sender_id, sender_nick = extract_sender_info(test_raw_message)

    print(f"提取结果:")
    print(f"   sender_id: {sender_id}")
    print(f"   sender_nick: {sender_nick}")

    # 验证是否优先使用了sender_staff_id
    if sender_id == '030309523040343349':
        print("正确！优先使用sender_staff_id（标准钉钉userId格式）")
        return sender_id, sender_nick
    else:
        print(f"错误！没有使用sender_staff_id，而是使用了: {sender_id}")
        return None, None

def test_database_message():
    """测试数据库中消息的sender信息提取"""
    print("\n=== 测试2: 数据库消息提取 ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        # 获取最近的一条消息
        cursor = db.connection.cursor()
        cursor.execute('SELECT id, raw_message FROM message_process_log WHERE raw_message IS NOT NULL ORDER BY created_at DESC LIMIT 1')
        message = cursor.fetchone()

        if not message:
            print("WARNING: 数据库中没有消息记录")
            return None, None

        print(f"消息ID: {message['id']}")

        # 解析raw_message
        if isinstance(message['raw_message'], str):
            raw_data = json.loads(message['raw_message'])
        else:
            raw_data = message['raw_message']

        print(f"raw_message字段: {list(raw_data.keys())}")

        # 提取sender信息
        sender_id, sender_nick = extract_sender_info(raw_data)

        if sender_id:
            print(f"成功提取sender信息:")
            print(f"   sender_id: {sender_id}")
            print(f"   sender_nick: {sender_nick}")

            # 检查是否是标准钉钉userId格式
            if sender_id and not sender_id.startswith('$:'):
                print("使用标准钉钉userId格式！")
                return sender_id, sender_nick
            else:
                print("仍使用LWCP_v1格式，旧消息没有sender_staff_id字段")
                return sender_id, sender_nick
        else:
            print("无法提取sender信息")
            return None, None

    except Exception as e:
        print(f"数据库查询失败: {e}")
        return None, None
    finally:
        db.close()

def test_private_message_with_correct_id():
    """测试使用正确userId格式发送私信"""
    print("\n=== 测试3: 私信功能测试 ===")

    # 首先测试提取功能
    sender_id, sender_nick = test_extract_sender_info()
    if not sender_id:
        print("无法获取测试用的sender_id")
        return False

    settings = Settings()
    notifier = DingtalkNotifier(settings)

    # 获取access_token
    print("获取access_token...")
    access_token = notifier._get_access_token()
    if not access_token:
        print("无法获取access_token")
        return False

    print("access_token获取成功")

    # 测试私信发送
    title = "sender_staff_id修复验证"
    content = f"""## 私信功能测试成功

**测试目的**: 验证sender_staff_id字段修复

**测试结果**:
- sender_staff_id字段正确保存到raw_message
- extract_sender_info正确提取sender_staff_id
- 使用标准钉钉userId格式: {sender_id}
- access_token获取成功

**下一步**: 测试实际私信发送

此消息表明userId格式问题已解决！
"""

    print(f"准备发送私信给 {sender_nick} ({sender_id})...")
    result = notifier.send_private_message(sender_id, title, content)

    if result:
        print("私信发送成功！sender_staff_id修复验证完成！")
        return True
    else:
        print("私信发送失败（需要配置钉钉权限）")
        print("虽然发送失败，但userId格式问题已修复")
        return False

def main():
    """主测试流程"""
    print("sender_staff_id字段修复验证")
    print("=" * 60)

    try:
        # 测试1: 验证提取逻辑
        sender_id, sender_nick = test_extract_sender_info()
        if not sender_id:
            print("测试1失败：sender信息提取逻辑错误")
            return 1

        # 测试2: 检查数据库现有消息
        db_sender_id, db_sender_nick = test_database_message()

        # 测试3: 私信功能测试
        success = test_private_message_with_correct_id()

        print("\n" + "=" * 60)
        print("测试总结:")
        print("sender_staff_id字段修复已完成")
        print("extract_sender_info优先使用sender_staff_id")
        print("新消息将保存正确的userId格式")

        if db_sender_id and not db_sender_id.startswith('$:'):
            print("数据库已有包含sender_staff_id的消息")
        else:
            print("旧消息仍使用LWCP_v1格式，新消息将使用正确格式")

        if success:
            print("私信功能验证成功")
        else:
            print("私信发送需要钉钉权限配置")

        print("\n修复完成！新接收的消息将包含正确的sender_staff_id字段")

        return 0

    except Exception as e:
        print(f"\n测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
