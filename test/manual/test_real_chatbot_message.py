#!/usr/bin/env python3
"""
实际运行时ChatbotMessage属性检查

在实际运行环境中检查ChatbotMessage对象
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def check_real_chatbot_message():
    """检查真实的ChatbotMessage"""
    print("=== 实际运行时ChatbotMessage检查 ===")

    try:
        from dingtalk_stream import ChatbotMessage

        # 基于用户日志的真实数据
        real_data = {
            'conversationId': 'cidCdq7DXpNepxSGvjYesVuY7VbY3/CBS6JB+KFBTlbe+4=',
            'conversationTitle': '测试群',
            'senderId': '$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==',
            'senderNick': '黄齐仁',
            'senderStaffId': '030309523040343349',
            'messageType': 'text',
            'isInAtList': True,
            'content': {'content': 'https://mp.weixin.qq.com/s/5-csRltLRZpWqQbMZ4qdXg'}
        }

        chatbot_message = ChatbotMessage.from_dict(real_data)

        print("✅ ChatbotMessage创建成功")

        # 检查关键属性
        print("\n关键属性值:")
        print(f"  sender_id: {chatbot_message.sender_id}")
        print(f"  sender_staff_id: {getattr(chatbot_message, 'sender_staff_id', 'NOT_FOUND')}")
        print(f"  sender_nick: {chatbot_message.sender_nick}")

        # 测试实际运行的逻辑
        print("\n实际运行逻辑测试:")

        # 模拟发送反馈时的逻辑
        sender_for_private = None
        if hasattr(chatbot_message, 'sender_staff_id') and chatbot_message.sender_staff_id:
            sender_for_private = chatbot_message.sender_staff_id
            print(f"  ✅ 私信将使用: {sender_for_private} (sender_staff_id)")
        else:
            sender_for_private = chatbot_message.sender_id if hasattr(chatbot_message, 'sender_id') else None
            print(f"  ❌ 私信将使用: {sender_for_private} (sender_id)")

        # 检查属性类型
        print("\n属性类型检查:")
        print(f"  type(sender_id): {type(chatbot_message.sender_id)}")
        if hasattr(chatbot_message, 'sender_staff_id'):
            print(f"  type(sender_staff_id): {type(chatbot_message.sender_staff_id)}")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(check_real_chatbot_message())
