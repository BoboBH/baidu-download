#!/usr/bin/env python3
"""
钉钉反馈消息流程展示和诊断脚本
展示所有相关代码并测试完整的消息发送流程
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.feishu.dingtalk_group_client import MessageHandler

def show_code_structure():
    """展示代码结构"""
    print("=" * 80)
    print("钉钉反馈消息代码结构")
    print("=" * 80)
    print()

    print("1. 消息接收和反馈流程:")
    print("-" * 80)
    print("""
    用户发送 @消息
         ↓
    dingtalk_group_client.py: MessageHandler.process()
         ↓
    解析消息 → MessageParser.parse_message()
         ↓
    判断消息是否有效
         ↓
    发送反馈 → MessageHandler.send_feedback()
         ↓
    钉钉通知器 → DingtalkNotifier.send_notification()
         ↓
    HTTP POST 到钉钉 Webhook API
         ↓
    群里收到反馈消息
    """)

    print()
    print("2. 核心文件:")
    print("-" * 80)
    print("""
    src/feishu/dingtalk_group_client.py
      ├─ MessageHandler.process()      # 处理收到的消息
      ├─ MessageHandler.send_feedback() # 发送反馈消息
      └─ main()                         # 启动钉钉接收服务

    src/notification/dingtalk_notifier.py
      └─ DingtalkNotifier.send_notification() # 实际发送HTTP请求

    src/config/settings.py
      └─ Settings                        # 加载配置(包括WEBHOOK_URL)
    """)

    print()
    print("3. 消息标题格式:")
    print("-" * 80)
    print("""
    成功消息: "feedback: 收到有效百度网盘链接"
    失败消息: "feedback: 消息格式无效"

    所有消息标题都包含 "feedback:" 关键词
    """)

    print()
    print("4. 配置要求:")
    print("-" * 80)
    print("""
    .env 文件需要配置:
    - DINGTALK_APP_KEY       # 接收消息的机器人凭证
    - DINGTALK_APP_SECRET    # 接收消息的机器人凭证
    - DINGTALK_WEBHOOK       # 发送消息的机器人Webhook URL

    钉钉群设置:
    - 需要两个机器人：一个接收(Stream API)，一个发送(Webhook API)
    - Webhook机器人安全设置关键词必须包含 "feedback"
    """)

    print()
    print("5. 常见错误码:")
    print("-" * 80)
    print("""
    errcode=310000: 关键词验证失败
      - 原因: 消息标题不包含机器人配置的关键词
      - 解决: 在机器人设置中添加关键词 "feedback"

    errcode=0: 发送成功
      - 正常情况，消息已发送到群里
    """)

def show_current_config():
    """展示当前配置"""
    print()
    print("=" * 80)
    print("当前配置状态")
    print("=" * 80)
    print()

    try:
        settings = Settings()

        print("✅ 配置加载成功:")
        print(f"  APP_KEY: {settings.dingtalk_app_key[:20]}...")
        print(f"  APP_SECRET: {settings.dingtalk_app_secret[:20]}...")
        print(f"  WEBHOOK: {settings.dingtalk_webhook[:60]}...")
        print()

        if not settings.dingtalk_webhook:
            print("❌ 错误: DINGTALK_WEBHOOK 未配置")
            return False

        return True

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

async def test_feedback_flow():
    """测试完整的反馈消息流程"""
    print()
    print("=" * 80)
    print("测试反馈消息流程")
    print("=" * 80)
    print()

    try:
        settings = Settings()
        handler = MessageHandler(settings)

        print("1️⃣ 测试成功消息反馈...")
        print("-" * 80)
        await handler.send_feedback(
            conversation_title="测试群聊",
            message_content="260723:https://pan.baidu.com/s/test123",
            is_valid=True,
            details="已记录: 测试文件夹"
        )

        print()
        print("2️⃣ 测试失败消息反馈...")
        print("-" * 80)
        await handler.send_feedback(
            conversation_title="测试群聊",
            message_content="这是一个无效消息",
            is_valid=False,
            details="消息不包含百度网盘链接或格式错误"
        )

        print()
        print("3️⃣ 测试完成")
        print("-" * 80)
        print("请检查:")
        print("  1. 是否在钉钉群中收到了上述两条反馈消息")
        print("  2. 控制台输出的详细日志信息")
        print("  3. 如果没有收到，查看错误码和原因")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("钉钉反馈消息诊断工具")
    print()

    # 1. 展示代码结构
    show_code_structure()

    # 2. 展示当前配置
    if not show_current_config():
        print()
        print("请先配置 DINGTALK_WEBHOOK 后再运行此测试")
        return

    # 3. 运行测试
    print()
    input("按 Enter 键开始测试...")
    print()

    asyncio.run(test_feedback_flow())

    print()
    print("=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
