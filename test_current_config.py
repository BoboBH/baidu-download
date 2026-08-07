#!/usr/bin/env python3
"""
钉钉消息配置诊断脚本 - 帮助用户理解为什么没收到反馈消息
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.notification.dingtalk_notifier import DingtalkNotifier

def diagnose_config():
    """诊断当前配置"""
    print("=" * 80)
    print("钉钉消息配置诊断")
    print("=" * 80)
    print()

    # 加载配置
    settings = Settings()

    print("1. Current Configuration:")
    print("-" * 80)

    # 检查钉钉配置
    print(f"DingTalk App Key: {settings.dingtalk_app_key[:20]}...")
    print(f"DingTalk App Secret: {settings.dingtalk_app_secret[:20]}...")
    print(f"DingTalk Webhook: {settings.dingtalk_webhook[:60]}...")
    print()

    print("2. Configuration Explanation:")
    print("-" * 80)
    print("App Key + App Secret = Message Receiving Bot (Stream API)")
    print("  - This bot receives @messages from the group")
    print("  - DingTalk Group -> Smart Group Assistant -> Add Bot -> Custom")
    print()
    print("Webhook URL = Message Sending Bot (Webhook API)")
    print("  - This bot sends feedback messages to the group")
    print("  - DingTalk Group -> Smart Group Assistant -> Add Bot -> Custom")
    print("  - Must set security keyword: 'feedback'")
    print()

    print("3. Test Sending Feedback Message:")
    print("-" * 80)

    if not settings.dingtalk_webhook:
        print("ERROR: DINGTALK_WEBHOOK is not configured!")
        print("   Please set DINGTALK_WEBHOOK in .env file")
        return

    try:
        # 创建通知器
        notifier = DingtalkNotifier(settings)

        # 发送测试消息
        title = "feedback: Test Feedback Message"
        content = """## Test Feedback Message

This is a test message from Baidu Download System.

**Time**: {}
**Purpose**: Verify feedback message function

If you can see this message, the Webhook configuration is correct!

---

**Current configured bot types**:
- Message receiving bot: Stream API (App Key + Secret)
- Message sending bot: Webhook API (requires keyword: feedback)

**Tips**:
- If you only receive test message but not other feedback, your DingTalk bot keyword setting is incorrect
- Please add keyword in bot settings: "feedback"
""".format(os.popen("echo %date% %time%").read().strip())

        print("Sending test message...")
        print(f"   Title: {title}")
        print()

        success = notifier.send_notification(title, content)

        if success:
            print("SUCCESS: Test message sent successfully!")
            print()
            print("Check steps:")
            print("   1. Look for test message in DingTalk group")
            print("   2. If you see test message, Webhook bot is configured correctly")
            print("   3. If you see test message but not previous feedback messages,")
            print("      it's because message titles need to include keyword 'feedback'")
            print()
            print("Solution:")
            print("   In DingTalk bot security settings:")
            print("   - Add keyword: feedback")
            print("   - Or turn off keyword verification")
            print("   - Or switch to signature verification")
        else:
            print("ERROR: Test message sending failed!")
            print()
            print("Possible reasons:")
            print("   1. Webhook URL is incorrect")
            print("   2. Network connection issue")
            print("   3. DingTalk server rejected the request")

    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("4. Message Title Format:")
    print("-" * 80)
    print("Success message: 'feedback: Received valid Baidu link'")
    print("Failure message: 'feedback: Invalid message format'")
    print()
    print("所有消息标题都包含 'feedback:' 关键词以满足钉钉安全要求")
    print()

    print("=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_config()
