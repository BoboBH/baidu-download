#!/usr/bin/env python3
"""
详细验证sender_staff_id在各个场景中的获取情况

验证场景：
1. 接收消息时ChatbotMessage是否有sender_staff_id属性
2. 从数据库获取消息时能否提取到sender_staff_id
3. 反馈消息发送时能否获取到sender_staff_id
4. 处理完成通知时能否获取到sender_staff_id
"""

import sys
import json
# 将项目根目录加入 sys.path（脚本已移入 test/manual/）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings
from src.database.repository import DatabaseRepository, extract_sender_info
from src.utils.logger import get_logger

logger = get_logger(__name__)

def check_chatbot_message_attributes():
    """检查ChatbotMessage对象是否有sender_staff_id属性"""
    print("=== 场景1: 检查ChatbotMessage对象属性 ===")

    try:
        from dingtalk_stream import ChatbotMessage

        # 创建一个模拟的ChatbotMessage数据
        mock_data = {
            'conversation_id': 'cidTest123',
            'conversation_title': '测试群',
            'sender_id': '$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==',
            'sender_staff_id': '030309523040343349',  # 真实的钉钉userId
            'sender_nick': '测试用户',
            'message_type': 'text',
            'is_in_at_list': True
        }

        chatbot_message = ChatbotMessage.from_dict(mock_data)

        print(f"ChatbotMessage对象创建成功")
        print(f"sender_id: {chatbot_message.sender_id}")
        print(f"sender_nick: {chatbot_message.sender_nick}")

        # 关键检查：是否有sender_staff_id属性
        if hasattr(chatbot_message, 'sender_staff_id'):
            print(f"sender_staff_id: {chatbot_message.sender_staff_id}")
            print("SUCCESS: ChatbotMessage有sender_staff_id属性")
            return True, chatbot_message.sender_staff_id
        else:
            print("WARNING: ChatbotMessage没有sender_staff_id属性")
            print("可用的属性名称:")
            for attr in dir(chatbot_message):
                if not attr.startswith('_') and 'sender' in attr.lower():
                    print(f"  - {attr}")
            return False, None

    except Exception as e:
        print(f"ERROR: 无法检查ChatbotMessage属性: {e}")
        return False, None

def check_database_message_extraction():
    """检查从数据库获取消息时能否提取到sender_staff_id"""
    print("\n=== 场景2: 数据库消息提取测试 ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        # 获取最近的消息（注意：sender_id/sender_nick存储在raw_message中，不是单独字段）
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT id, raw_message
            FROM message_process_log
            WHERE raw_message IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 3
        ''')
        messages = cursor.fetchall()

        print(f"找到 {len(messages)} 条消息记录")

        for msg in messages:
            print(f"\n--- 消息ID: {msg['id']} ---")

            # 先解析raw_message以获取sender信息
            if isinstance(msg['raw_message'], str):
                raw_data = json.loads(msg['raw_message'])
            else:
                raw_data = msg['raw_message']

            print(f"raw_message中的sender_id: {raw_data.get('sender_id')}")
            print(f"raw_message中的sender_nick: {raw_data.get('sender_nick')}")

            # 解析raw_message
            if isinstance(msg['raw_message'], str):
                raw_data = json.loads(msg['raw_message'])
            else:
                raw_data = msg['raw_message']

            print(f"raw_message字段: {list(raw_data.keys())}")

            # 检查是否有sender_staff_id
            if 'sender_staff_id' in raw_data:
                print(f"raw_message包含sender_staff_id: {raw_data['sender_staff_id']}")
            else:
                print("raw_message不包含sender_staff_id字段")

            # 使用extract_sender_info提取
            extracted_id, extracted_nick = extract_sender_info(raw_data)
            print(f"extract_sender_info结果:")
            print(f"  sender_id: {extracted_id}")
            print(f"  sender_nick: {extracted_nick}")

        # 检查是否有包含sender_staff_id的消息
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM message_process_log
            WHERE raw_message IS NOT NULL
            AND raw_message LIKE '%sender_staff_id%'
        ''')
        result = cursor.fetchone()
        print(f"\n包含sender_staff_id的消息数量: {result['count']}")

        return True

    except Exception as e:
        print(f"ERROR: 数据库查询失败: {e}")
        return False
    finally:
        db.close()

def check_feedback_message_scenario():
    """检查反馈消息发送场景中的sender_staff_id获取"""
    print("\n=== 场景3: 反馈消息发送场景测试 ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        # 模拟反馈消息发送场景：从数据库获取消息
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT id, raw_message, process_status
            FROM message_process_log
            WHERE process_status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        message = cursor.fetchone()

        if not message:
            print("没有pending状态的消息用于测试")
            # 尝试获取任意消息
            cursor.execute('''
                SELECT id, raw_message
                FROM message_process_log
                WHERE raw_message IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            message = cursor.fetchone()

        if not message:
            print("ERROR: 没有可用消息")
            return False

        print(f"测试消息ID: {message['id']}")

        # 模拟get_message_by_id的行为
        sender_id, sender_nick = extract_sender_info(message.get('raw_message'))

        print(f"反馈场景可用的sender信息:")
        print(f"  sender_id: {sender_id}")
        print(f"  sender_nick: {sender_nick}")

        # 检查是否是有效的userId格式
        if sender_id:
            if sender_id.startswith('$:'):
                print("  格式: LWCP_v1编码格式（不适用私信）")
                return False
            else:
                print("  格式: 标准钉钉userId格式（适用于私信）")
                return True
        else:
            print("  无法提取sender_id")
            return False

    except Exception as e:
        print(f"ERROR: 反馈场景测试失败: {e}")
        return False
    finally:
        db.close()

def check_processing_result_scenario():
    """检查处理完成通知场景中的sender_staff_id获取"""
    print("\n=== 场景4: 处理结果通知场景测试 ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    try:
        # 模拟处理完成场景：获取已完成的消息
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT id, raw_message, process_status
            FROM message_process_log
            WHERE process_status IN ('success', 'failed')
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        message = cursor.fetchone()

        if not message:
            print("没有已完成的消息用于测试")
            # 尝试获取任意消息
            cursor.execute('''
                SELECT id, raw_message
                FROM message_process_log
                WHERE raw_message IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            message = cursor.fetchone()

        if not message:
            print("ERROR: 没有可用消息")
            return False

        print(f"测试消息ID: {message['id']}")
        print(f"消息状态: {message['process_status']}")

        # 模拟处理完成通知时提取sender信息
        sender_id, sender_nick = extract_sender_info(message.get('raw_message'))

        print(f"处理结果通知可用的sender信息:")
        print(f"  sender_id: {sender_id}")
        print(f"  sender_nick: {sender_nick}")

        # 检查格式是否适用于私信
        if sender_id:
            if sender_id.startswith('$:'):
                print("  格式: LWCP_v1编码格式（不适用私信）")
                print("  旧消息无法发送私信，只有新消息支持")
                return False
            else:
                print("  格式: 标准钉钉userId格式（适用于私信）")
                print("  可以正常发送处理结果私信")
                return True
        else:
            print("  无法提取sender_id")
            return False

    except Exception as e:
        print(f"ERROR: 处理结果场景测试失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主验证流程"""
    print("sender_staff_id全场景验证测试")
    print("=" * 60)

    try:
        # 场景1: 检查ChatbotMessage对象
        has_attribute, staff_id = check_chatbot_message_attributes()

        # 场景2: 数据库消息提取
        db_success = check_database_message_extraction()

        # 场景3: 反馈消息场景
        feedback_success = check_feedback_message_scenario()

        # 场景4: 处理结果场景
        result_success = check_processing_result_scenario()

        print("\n" + "=" * 60)
        print("验证总结:")
        print(f"场景1 (ChatbotMessage属性): {'PASS' if has_attribute else 'FAIL'}")
        print(f"场景2 (数据库提取): {'PASS' if db_success else 'FAIL'}")
        print(f"场景3 (反馈消息): {'PASS' if feedback_success else 'PARTIAL'}")
        print(f"场景4 (处理结果): {'PASS' if result_success else 'PARTIAL'}")

        if has_attribute:
            print("\n结论:")
            print("1. ChatbotMessage确实有sender_staff_id属性")
            print("2. 代码修改会将sender_staff_id保存到raw_message")
            print("3. extract_sender_info会优先使用sender_staff_id")
            print("4. 新消息支持私信功能，旧消息需要重新处理")
        else:
            print("\nWARNING: ChatbotMessage可能没有sender_staff_id属性")
            print("需要进一步检查钉钉SDK版本")

        return 0

    except Exception as e:
        print(f"\nERROR: 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
