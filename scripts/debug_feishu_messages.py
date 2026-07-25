#!/usr/bin/env python3
"""深度调试飞书API返回的消息结构"""

import sys
import json
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.feishu.feishu_client import FeishuMessageClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

def debug_feishu_api():
    """深度调试飞书API"""
    try:
        settings = Settings()
        feishu_client = FeishuMessageClient(settings)

        logger.info("获取飞书消息（原始API响应）...")
        messages = feishu_client.get_messages()

        print(f"\n{'='*80}")
        print(f"飞书API原始返回结构分析 (共 {len(messages)} 条消息):")
        print(f"{'='*80}\n")

        for i, msg in enumerate(messages, 1):
            print(f"消息 {i}:")
            print(f"  完整结构:")
            print(json.dumps(msg, indent=2, ensure_ascii=False))

            print(f"\n  关键字段:")
            print(f"    message_id: {msg.get('message_id', 'N/A')}")
            print(f"    msg_type: {msg.get('msg_type', 'N/A')}")
            print(f"    create_time: {msg.get('create_time', 'N/A')}")
            print(f"    update_time: {msg.get('update_time', 'N/A')}")

            # 检查body字段
            if 'body' in msg:
                print(f"    body存在: True")
                body = msg['body']
                print(f"    body内容: {json.dumps(body, indent=4, ensure_ascii=False)}")

                # 检查content字段
                if 'content' in body:
                    content = body['content']
                    print(f"    body.content类型: {type(content)}")
                    print(f"    body.content内容: {content}")

                    # 尝试解析content
                    try:
                        if isinstance(content, str):
                            content_dict = json.loads(content)
                            print(f"    解析后的content: {json.dumps(content_dict, indent=4, ensure_ascii=False)}")

                            # 查找text字段
                            if 'text' in content_dict:
                                print(f"    ✅ 找到text字段: '{content_dict['text']}'")
                    except:
                        print(f"    content解析失败")
            else:
                print(f"    body存在: False")

            # 检查直接content字段
            if 'content' in msg:
                print(f"    直接content: {msg['content']}")

            print(f"\n{'-'*80}\n")

    except Exception as e:
        logger.error(f"调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_feishu_api()