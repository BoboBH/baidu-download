#!/usr/bin/env python3
"""测试飞书API连接和消息获取"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_feishu():
    """测试飞书连接和消息获取"""
    try:
        settings = Settings()
        logger.info("开始测试飞书连接...")

        # 创建飞书客户端
        feishu_client = FeishuMessageClient(settings)
        logger.info(f"飞书客户端创建成功")

        # 获取消息
        logger.info(f"获取最近 {settings.feishu_hours_limit} 小时的消息...")
        messages = feishu_client.get_messages()

        logger.info(f"✅ 成功获取 {len(messages)} 条消息")

        if messages:
            print("\n" + "="*60)
            print("飞书消息列表:")
            print("="*60)

            parser = MessageParser()

            for i, msg in enumerate(messages, 1):
                print(f"\n消息 {i}:")
                print(f"  消息ID: {msg.get('message_id', 'N/A')}")
                print(f"  内容: {msg.get('content', 'N/A')}")

                # 尝试解析消息
                try:
                    result = parser.parse_message(msg.get('content', ''))
                    if result:
                        print(f"  ✅ 解析成功:")
                        print(f"     文件夹名: {result.folder_name}")
                        print(f"     分享链接: {result.share_link}")
                        print(f"     提取码: {result.code}")
                    else:
                        print(f"  ❌ 解析失败: 格式不匹配")
                except Exception as e:
                    print(f"  ❌ 解析错误: {e}")

            return messages
        else:
            print("❌ 没有获取到消息")
            print("\n请确保:")
            print("1. 飞书群中有消息")
            print("2. 消息格式正确: 'YYMMDD：https://pan.baidu.com/s/...'")
            print("3. FEISHU_HOURS_LIMIT 设置合适的时间范围")
            return []

    except Exception as e:
        logger.error(f"❌ 飞书连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    messages = test_feishu()