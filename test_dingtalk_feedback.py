#!/usr/bin/env python
"""
测试钉钉消息反馈功能

使用方法：
1. 确保 .env 中配置了 DINGTALK_WEBHOOK
2. 运行此脚本：python test_dingtalk_feedback.py
3. 检查钉钉群是否收到测试反馈消息
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.feishu.dingtalk_group_client import MessageHandler


async def test_feedback():
    """测试反馈功能"""
    print("=" * 60)
    print("钉钉消息反馈功能测试")
    print("=" * 60)

    try:
        # 加载配置
        print("\n1. 加载配置...")
        settings = Settings()

        if not settings.dingtalk_webhook:
            print("[错误] DINGTALK_WEBHOOK 未配置")
            print("请在 .env 文件中设置 DINGTALK_WEBHOOK")
            return 1

        print("[成功] 配置加载成功")
        print(f"   Webhook: {settings.dingtalk_webhook[:50]}...")

        # 创建消息处理器
        print("\n2. 创建消息处理器...")
        handler = MessageHandler(settings)

        if not handler.notifier:
            print("[错误] 消息反馈功能未启用")
            print("请检查 DINGTALK_WEBHOOK 配置")
            return 1

        print("[成功] 消息处理器创建成功")
        print("   反馈功能: 已启用")

        # 测试成功消息反馈
        print("\n3. 测试成功消息反馈...")
        await handler.send_feedback(
            conversation_title="测试群",
            message_content="260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg",
            is_valid=True,
            details="已记录: 260723"
        )
        print("[成功] 成功消息反馈已发送")

        # 等待2秒
        await asyncio.sleep(2)

        # 测试失败消息反馈
        print("\n4. 测试失败消息反馈...")
        await handler.send_feedback(
            conversation_title="测试群",
            message_content="这是一条测试消息",
            is_valid=False,
            details="消息不包含百度网盘链接或格式错误"
        )
        print("[成功] 失败消息反馈已发送")

        print("\n" + "=" * 60)
        print("测试完成！")
        print("请检查钉钉群是否收到两条反馈消息：")
        print("1. 收到有效百度网盘链接")
        print("2. 消息格式无效")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"[错误] 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_feedback())
    exit(exit_code)
