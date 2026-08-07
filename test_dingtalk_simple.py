#!/usr/bin/env python3
"""
Simple DingTalk Feedback Message Test
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.feishu.dingtalk_group_client import MessageHandler

def main():
    print("=" * 80)
    print("DingTalk Feedback Message Diagnostic Test")
    print("=" * 80)
    print()

    # Show current configuration
    print("1. Current Configuration:")
    print("-" * 80)
    try:
        settings = Settings()
        print(f"APP_KEY: {settings.dingtalk_app_key[:20]}...")
        print(f"APP_SECRET: {settings.dingtalk_app_secret[:20]}...")
        print(f"WEBHOOK: {settings.dingtalk_webhook[:60]}...")

        if not settings.dingtalk_webhook:
            print("ERROR: DINGTALK_WEBHOOK is not configured")
            return

        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Configuration load failed: {e}")
        return

    print()

    # Test feedback flow
    print("2. Testing Feedback Message Flow:")
    print("-" * 80)

    async def test_feedback():
        handler = MessageHandler(settings)

        print("Testing success message feedback...")
        await handler.send_feedback(
            conversation_title="Test Group",
            message_content="260723:https://pan.baidu.com/s/test123",
            is_valid=True,
            details="Recorded: Test Folder"
        )

        print()
        print("Testing failure message feedback...")
        await handler.send_feedback(
            conversation_title="Test Group",
            message_content="Invalid message",
            is_valid=False,
            details="Message does not contain Baidu link or format error"
        )

    asyncio.run(test_feedback())

    print()
    print("3. Code Flow Summary:")
    print("-" * 80)
    print("""
    User sends @message
         ↓
    dingtalk_group_client.py: MessageHandler.process()
         ↓
    Parse message → MessageParser.parse_message()
         ↓
    Check if message is valid
         ↓
    Send feedback → MessageHandler.send_feedback()
         ↓
    DingtalkNotifier.send_notification()
         ↓
    HTTP POST to DingTalk Webhook API
         ↓
    Group receives feedback message
    """)

    print()
    print("4. Key Files:")
    print("-" * 80)
    print("""
    src/feishu/dingtalk_group_client.py
      - MessageHandler.process()      # Process received messages
      - MessageHandler.send_feedback() # Send feedback messages
      - main()                         # Start DingTalk service

    src/notification/dingtalk_notifier.py
      - DingtalkNotifier.send_notification() # Actual HTTP request
    """)

    print()
    print("5. Message Titles:")
    print("-" * 80)
    print("""
    Success: "feedback: Received valid Baidu link"
    Failure: "feedback: Invalid message format"

    All message titles contain "feedback:" keyword
    """)

    print()
    print("6. Configuration Requirements:")
    print("-" * 80)
    print("""
    .env file:
    - DINGTALK_APP_KEY       # Message receiving bot credentials
    - DINGTALK_APP_SECRET    # Message receiving bot credentials
    - DINGTALK_WEBHOOK       # Message sending bot webhook URL

    DingTalk group settings:
    - Need two bots: one for receiving (Stream API), one for sending (Webhook API)
    - Webhook bot security keyword must include "feedback"
    """)

    print()
    print("7. Common Error Codes:")
    print("-" * 80)
    print("""
    errcode=310000: Keyword verification failed
      - Reason: Message title doesn't contain configured keyword
      - Solution: Add keyword "feedback" in bot settings

    errcode=0: Send success
      - Normal case, message sent to group
    """)

    print()
    print("8. Next Steps:")
    print("-" * 80)
    print("""
    1. Check the detailed logs above for error codes
    2. Verify if you received the test messages in DingTalk group
    3. If errcode=310000, modify bot keyword settings
    4. If no error but no message received, check if webhook bot is in the group
    """)

    print()
    print("=" * 80)
    print("Diagnostic Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
