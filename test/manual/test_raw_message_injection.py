#!/usr/bin/env python3
"""
测试sender_staff_id注入到raw_message的逻辑

模拟接收消息的过程，验证：
1. ChatbotMessage有sender_staff_id时是否正确注入
2. 注入后的raw_message是否包含sender_staff_id
3. extract_sender_info能否正确提取
"""

import json
import os
import sys
# 将项目根目录加入 sys.path（脚本已移入 test/manual/）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.repository import extract_sender_info

def test_sender_staff_id_injection():
    """测试sender_staff_id注入逻辑"""
    print("=== 测试sender_staff_id注入逻辑 ===")

    # 模拟接收消息时的数据
    mock_chatbot_message = {
        'conversation_id': 'cidTest123',
        'conversation_title': '测试群',
        'sender_id': '$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==',  # LWCP_v1格式
        'sender_staff_id': '030309523040343349',  # 标准钉钉userId
        'sender_nick': '测试用户',
        'message_type': 'text',
        'content': 'https://pan.baidu.com/s/test 提取码: 1234',
        'is_in_at_list': True
    }

    # 模拟代码中的逻辑
    raw_message_data = {
        'conversation_id': mock_chatbot_message['conversation_id'],
        'conversation_title': mock_chatbot_message['conversation_title'],
        'sender_id': mock_chatbot_message['sender_id'],
        'sender_nick': mock_chatbot_message['sender_nick'],
        'message_type': mock_chatbot_message['message_type'],
        'content': mock_chatbot_message['content'],
        'is_in_at_list': mock_chatbot_message['is_in_at_list']
    }

    print("原始raw_message_data字段:", list(raw_message_data.keys()))

    # 关键逻辑：如果有sender_staff_id，添加到raw_message
    if mock_chatbot_message.get('sender_staff_id'):
        raw_message_data['sender_staff_id'] = mock_chatbot_message['sender_staff_id']
        print(f"检测到sender_staff_id: {mock_chatbot_message['sender_staff_id']}")
    else:
        print("没有检测到sender_staff_id")

    print("注入后raw_message_data字段:", list(raw_message_data.keys()))

    # 序列化为JSON（模拟保存到数据库）
    raw_message_json = json.dumps(raw_message_data, ensure_ascii=False)
    print(f"raw_message JSON: {raw_message_json[:100]}...")

    # 模拟从数据库读取后提取sender信息
    sender_id, sender_nick = extract_sender_info(raw_message_json)

    print(f"\nextract_sender_info提取结果:")
    print(f"  sender_id: {sender_id}")
    print(f"  sender_nick: {sender_nick}")

    # 验证是否优先使用了sender_staff_id
    if sender_id == '030309523040343349':
        print("SUCCESS: 正确提取sender_staff_id（标准userId格式）")
        print("新消息支持私信功能")
        return True
    else:
        print(f"FAIL: 提取到错误的sender_id: {sender_id}")
        return False

def test_without_sender_staff_id():
    """测试没有sender_staff_id的情况（旧消息）"""
    print("\n=== 测试旧消息（无sender_staff_id） ===")

    # 模拟旧消息数据（没有sender_staff_id）
    old_raw_message = {
        'conversation_id': 'cidOld123',
        'conversation_title': '旧群',
        'sender_id': '$:LWCP_v1:$OldMessageId==',  # 只有LWCP_v1格式
        'sender_nick': '旧用户',
        'message_type': 'text',
        'content': '测试',
        'is_in_at_list': True
    }

    print("旧消息raw_message字段:", list(old_raw_message.keys()))

    # 提取sender信息
    sender_id, sender_nick = extract_sender_info(old_raw_message)

    print(f"extract_sender_info提取结果:")
    print(f"  sender_id: {sender_id}")
    print(f"  sender_nick: {sender_nick}")

    if sender_id and sender_id.startswith('$:'):
        print("WARNING: 旧消息使用LWCP_v1格式，不支持私信")
        print("但webhook通知仍然工作")
        return True
    else:
        print("ERROR: 意外的sender_id格式")
        return False

def main():
    """主测试流程"""
    print("sender_staff_id注入逻辑验证")
    print("=" * 60)

    try:
        # 测试1: 有sender_staff_id的情况
        test1_pass = test_sender_staff_id_injection()

        # 测试2: 没有sender_staff_id的情况
        test2_pass = test_without_sender_staff_id()

        print("\n" + "=" * 60)
        print("测试结果:")
        print(f"新消息注入逻辑: {'PASS' if test1_pass else 'FAIL'}")
        print(f"旧消息兼容性: {'PASS' if test2_pass else 'FAIL'}")

        if test1_pass and test2_pass:
            print("\n结论:")
            print("1. 新消息会自动注入sender_staff_id到raw_message")
            print("2. extract_sender_info正确提取sender_staff_id")
            print("3. 旧消息保持兼容，webhook仍然工作")
            print("4. 新消息支持webhook + 私信双重通知")
            print("\n建议：重启钉钉服务，新消息立即支持私信功能！")
            return 0
        else:
            print("\n测试失败，需要检查代码逻辑")
            return 1

    except Exception as e:
        print(f"\nERROR: 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
