#!/usr/bin/env python3
"""
DingTalk Webhook Diagnostic Test Script
Test if DingTalk notification configuration works properly
"""

import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.notification.dingtalk_notifier import DingtalkNotifier

def test_webhook():
    """Test DingTalk Webhook configuration"""
    print("=" * 60)
    print("DingTalk Webhook Diagnostic Test")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("1. Loading configuration...")
        settings = Settings()
        webhook = settings.dingtalk_webhook

        if not webhook:
            print("   [ERROR] DINGTALK_WEBHOOK is not configured")
            print("   Please set DINGTALK_WEBHOOK in .env file")
            return False

        print(f"   [OK] Webhook configured: {webhook[:50]}...")

        # Create notifier
        print("\n2. Creating notifier...")
        notifier = DingtalkNotifier(settings)
        print("   [OK] Notifier created successfully")

        # Send test message
        print("\n3. Sending test message...")
        test_title = "[TEST] Webhook Test Message"
        test_content = """## Test Message

This is a test message to verify DingTalk Webhook configuration.

**Test Time**: {}
**Test Purpose**: Verify message feedback function

If you receive this message, the Webhook configuration is correct!
""".format(os.popen("echo %date% %time%").read().strip())

        success = notifier.send_notification(test_title, test_content)

        if success:
            print("   [OK] Test message sent successfully!")
            print("\nPlease check if you received the test message in DingTalk group")
            return True
        else:
            print("   [ERROR] Test message sending failed!")
            print("\nPossible reasons:")
            print("   1. Webhook URL is incorrect")
            print("   2. Network connection issue")
            print("   3. DingTalk server rejected the request")
            return False

    except Exception as e:
        print(f"   [ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_async_feedback():
    """Test async feedback function"""
    print("\n" + "=" * 60)
    print("Async Feedback Function Test")
    print("=" * 60)
    print()

    try:
        import asyncio

        async def test_send_feedback():
            from src.feishu.dingtalk_group_client import MessageHandler
            from src.config.settings import Settings

            settings = Settings()
            handler = MessageHandler(settings)

            print("1. Testing valid message feedback...")
            await handler.send_feedback(
                "Test Group",
                "Test message: 260723:https://pan.baidu.com/s/xxx",
                is_valid=True,
                details="Recorded: Test Folder"
            )

            print("\n2. Testing invalid message feedback...")
            await handler.send_feedback(
                "Test Group",
                "Can you receive message?",
                is_valid=False,
                details="Message does not contain Baidu link or format error"
            )

            print("\n   [OK] Async feedback test completed")
            print("   Please check if you received 2 feedback messages in DingTalk")

        # Run async test
        asyncio.run(test_send_feedback())
        return True

    except Exception as e:
        print(f"   [ERROR] Async test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DingTalk Webhook Diagnostic Tool")
    print()

    # Test basic Webhook
    webhook_ok = test_webhook()

    if webhook_ok:
        print("\n" + "=" * 60)
        input("Press Enter to test async feedback...")
        print("=" * 60)
        test_async_feedback()
    else:
        print("\n" + "=" * 60)
        print("[WARNING] Basic Webhook test failed")
        print("Please fix Webhook configuration before testing async features")
        print("=" * 60)
