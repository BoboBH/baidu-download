#!/usr/bin/env python3
"""
调试ChatbotMessage的实际属性

检查真实的ChatbotMessage对象是否有sender_staff_id属性
"""

import sys
from dingtalk_stream import ChatbotMessage

def main():
    print("=== 调试ChatbotMessage属性 ===")

    # 创建模拟数据（基于用户提供的日志）
    mock_data = {
        'conversationId': 'cidCdq7DXpNepxSGvjYesVuY7VbY3/CBS6JB+KFBTlbe+4=',
        'conversationTitle': '测试群',
        'senderId': '$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==',
        'senderNick': '黄齐仁',
        'senderStaffId': '030309523040343349',
        'messageType': 'text',
        'isInAtList': True,
        'content': 'https://mp.weixin.qq.com/s/5-csRltLRZpWqQbMZ4qdXg'
    }

    print("模拟数据:")
    for key, value in mock_data.items():
        print(f"  {key}: {value}")

    # 创建ChatbotMessage对象
    try:
        chatbot_message = ChatbotMessage.from_dict(mock_data)
        print("\nChatbotMessage对象创建成功")

        # 检查所有属性
        print("\nChatbotMessage属性检查:")
        for attr in dir(chatbot_message):
            if not attr.startswith('_') and not callable(getattr(chatbot_message, attr)):
                try:
                    value = getattr(chatbot_message, attr)
                    if value is not None and 'sender' in attr.lower():
                        print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: [Error: {e}]")

        # 关键检查：是否有sender_staff_id属性
        print("\n关键属性检查:")
        if hasattr(chatbot_message, 'sender_staff_id'):
            print(f"  sender_staff_id属性: {chatbot_message.sender_staff_id}")
        else:
            print("  sender_staff_id属性: 不存在")

        if hasattr(chatbot_message, 'sender_id'):
            print(f"  sender_id属性: {chatbot_message.sender_id}")

        # 测试优先逻辑
        print("\n优先逻辑测试:")
        sender_for_feedback = None
        if hasattr(chatbot_message, 'sender_staff_id') and chatbot_message.sender_staff_id:
            sender_for_feedback = chatbot_message.sender_staff_id
            print(f"  优先使用sender_staff_id: {sender_for_feedback}")
        else:
            sender_for_feedback = chatbot_message.sender_id if hasattr(chatbot_message, 'sender_id') else None
            print(f"  回退使用sender_id: {sender_for_feedback}")

        # 检查实际字段名
        print("\n字段名检查:")
        print("  可能的字段名: senderStaffId, sender_staff_id, senderId, sender_id")

        # 尝试不同的属性名
        possible_attrs = ['senderStaffId', 'sender_staff_id', 'senderId', 'sender_id']
        for attr in possible_attrs:
            if hasattr(chatbot_message, attr):
                value = getattr(chatbot_message, attr)
                print(f"  {attr}: {value}")

        return 0

    except Exception as e:
        print(f"\nERROR: ChatbotMessage创建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
