#!/usr/bin/env python3
"""测试飞书API连接和消息获取 - 改进版"""

import sys
import json
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.feishu.message_parser import MessageParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_feishu_messages():
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

        logger.info(f"成功获取 {len(messages)} 条消息")

        if messages:
            print(f"\n{'='*60}")
            print(f"飞书消息列表 (共 {len(messages)} 条):")
            print(f"{'='*60}")

            parser = MessageParser()
            valid_messages = []

            for i, msg in enumerate(messages, 1):
                print(f"\n消息 {i}:")
                print(f"  消息ID: {msg.get('message_id', 'N/A')}")

                # 检查原始消息内容
                content = msg.get('content', 'N/A')
                print(f"  原始内容类型: {type(content)}")
                print(f"  原始内容: {content}")

                # 尝试解析JSON
                try:
                    if isinstance(content, str):
                        content_dict = json.loads(content)
                        print(f"  解析后JSON: {content_dict}")
                        text_content = content_dict.get('text', '')
                        print(f"  文本内容: {text_content}")
                    else:
                        text_content = str(content)
                except:
                    text_content = str(content)

                # 尝试解析消息
                try:
                    result = parser.parse_message(text_content)
                    if result:
                        print(f"  [SUCCESS] 解析成功:")
                        print(f"     文件夹名: {result.folder_name}")
                        print(f"     分享链接: {result.share_link}")
                        print(f"     提取码: {result.extraction_code}")
                        valid_messages.append(result)
                    else:
                        print(f"  [FAIL] 解析失败: 格式不匹配")
                        print(f"  期望格式: 'YYMMDD：https://pan.baidu.com/s/...'")
                except Exception as e:
                    print(f"  [ERROR] 解析错误: {str(e)}")

            print(f"\n{'='*60}")
            print(f"可处理的消息: {len(valid_messages)} 条")
            print(f"{'='*60}")

            if valid_messages:
                print("\n可执行 auto 模式测试！")
                return True
            else:
                print("\n没有可处理的消息，请发送测试消息到飞书群")
                print("格式: 260723：https://pan.baidu.com/s/XXXX (提取码)")
                return False
        else:
            print("没有获取到消息")
            return False

    except Exception as e:
        logger.error(f"飞书连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_feishu_messages()
    sys.exit(0 if success else 1)