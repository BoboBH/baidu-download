#!/usr/bin/env python3
"""
完整处理message_id=200的测试脚本

测试流程：
1. 从数据库获取message_id=200的消息
2. 调用process_pending_messages处理
3. 观察完整的处理流程：PDF下载、SFTP上传、webhook通知、私信发送
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.settings import Settings
from src.processor.file_transfer_processor import FileTransferProcessor

def test_full_process_id200():
    """完整处理message_id=200"""
    print("=" * 80)
    print("完整处理 message_id=200 - 包括PDF下载、SFTP上传、通知发送")
    print("=" * 80)

    try:
        print("\n[INIT] 初始化处理器...")
        settings = Settings()
        processor = FileTransferProcessor(settings, force_reprocess=True)

        print("[START] 开始处理消息...")
        print("-" * 80)

        # 处理待处理消息（会自动找到id=200的消息）
        result = processor.process_pending_messages()

        print("-" * 80)
        print(f"\n[RESULT] 处理结果:")
        print(f"  总消息数: {result.total_messages}")
        print(f"  成功消息: {result.success_messages}")
        print(f"  失败消息: {result.failed_messages}")
        print(f"  总文件数: {result.total_files}")
        print(f"  成功文件: {result.total_success_files}")
        print(f"  失败文件: {result.total_failed_files}")
        print(f"  总大小: {result.total_size_mb:.2f} MB")
        print(f"  处理时间: {result.processing_time_ms/1000:.2f} 秒")

        print(f"\n[DETAILS] 处理详情:")
        for i, detail in enumerate(result.details, 1):
            print(f"  {i}. Message ID: {detail.message_id}")
            print(f"     Type: {detail.message_type}")
            print(f"     Folder: {detail.folder_name}")
            print(f"     Status: {detail.status}")
            print(f"     Success Count: {detail.success_count}")
            print(f"     Failed Count: {detail.failed_count}")
            print(f"     Sender ID: {detail.sender_id}")
            print(f"     Sender Nick: {detail.sender_nick}")

        print(f"\n[CONCLUSION] 测试完成:")
        if result.total_messages > 0:
            print(f"  ✅ 处理了 {result.total_messages} 条消息")
            print(f"  成功: {result.success_messages}, 失败: {result.failed_messages}")
            print(f"  请检查日志查看webhook通知和私信发送的详细信息")
        else:
            print(f"  ⚠️ 没有找到待处理的消息")

        return result.success_messages > 0

    except Exception as e:
        print(f"\n[ERROR] 处理过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_process_id200()
    sys.exit(0 if success else 1)
