#!/usr/bin/env python3
"""
模拟process-pending完整流程 - 处理message_id=200

测试流程：
1. 从数据库获取message_id=200的待处理消息
2. 通过ProcessorRouter路由到对应的processor
3. 执行完整的处理流程
4. 观察私信发送的详细日志
"""

import sys
import os
import json
import pymysql
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_database_connection():
    """获取数据库连接"""
    load_dotenv()
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'baidu_download')
    )

def test_process_message_200():
    """测试处理message_id=200的完整流程"""
    print("=" * 80)
    print("模拟 process-pending 完整流程 - Message ID 200")
    print("=" * 80)

    try:
        # 1. 获取message_id=200的消息
        conn = get_database_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, message_hash, original_message, share_link, folder_name,
                   extraction_code, source, message_type, raw_message, file_info,
                   process_status
            FROM message_process_log
            WHERE id = 200
        """)

        result = cursor.fetchone()
        if not result:
            print("[ERROR] 未找到ID=200的记录")
            return False

        # 解包数据库字段
        (message_id, message_hash, original_message, share_link, folder_name,
         extraction_code, source, message_type, raw_message, file_info, process_status) = result

        print(f"\n[DATABASE] 获取到消息:")
        print(f"  ID: {message_id}")
        print(f"  Type: {message_type}")
        print(f"  Folder: {folder_name}")
        print(f"  Status: {process_status}")

        # 2. 检查sender信息
        print(f"\n[SENDER] 检查raw_message中的sender信息:")
        if raw_message:
            try:
                raw_data = json.loads(raw_message)
                sender_staff_id = raw_data.get('sender_staff_id')
                sender_id = raw_data.get('sender_id')
                sender_nick = raw_data.get('sender_nick')

                print(f"  sender_staff_id: {sender_staff_id}")
                print(f"  sender_id: {sender_id}")
                print(f"  sender_nick: {sender_nick}")

                final_sender_id = sender_staff_id or sender_id
                print(f"  最终用于私信的ID: {final_sender_id}")

                if not final_sender_id:
                    print("  [WARNING] 没有sender信息，私信将无法发送")

            except json.JSONDecodeError as e:
                print(f"  [ERROR] Raw Message解析失败: {e}")
        else:
            print("  [WARNING] raw_message为空")

        # 3. 更新状态为processing
        print(f"\n[PROCESS] 开始处理流程:")

        # 关闭数据库连接，让处理器自己管理连接
        conn.close()

        # 4. 导入处理模块
        from src.config.settings import Settings
        from src.processor.processor_router import ProcessorRouter

        settings = Settings()

        # 创建Router（不需要db_repo）
        router = ProcessorRouter(settings)

        print(f"  Router初始化完成")
        print(f"  消息类型: {message_type}")

        # 5. 构造ParseResult
        from src.feishu.models import ParseResult

        parse_result = ParseResult(
            message_type=message_type,
            unique_identifier=message_hash,  # 使用message_hash作为唯一标识
            source=source,
            share_link=share_link,
            extraction_code=extraction_code,
            folder_name=folder_name
        )

        print(f"  ParseResult构造完成")

        # 6. 通过Router处理消息
        print(f"\n[ROUTER] 调用Router处理消息:")
        print("-" * 80)

        router_result = router.process_message(parse_result)

        print("-" * 80)
        print(f"\n[ROUTER_RESULT] 处理结果:")
        print(f"  Success: {router_result.success}")
        if hasattr(router_result, 'upload_files') and router_result.upload_files:
            print(f"  Upload Files: {len(router_result.upload_files)}")
        if hasattr(router_result, 'metadata'):
            print(f"  Metadata: {router_result.metadata}")

        # 7. 模拟发送通知（这是关键测试点）
        print(f"\n[NOTIFICATION] 模拟发送处理结果通知:")
        print("-" * 80)

        # 从raw_message中提取sender信息（与file_transfer_processor相同逻辑）
        sender_id_for_private = None
        sender_nick_for_private = None
        if raw_message:
            try:
                raw_data = json.loads(raw_message)
                sender_id_for_private = raw_data.get('sender_staff_id') or raw_data.get('sender_id')
                sender_nick_for_private = raw_data.get('sender_nick')
                print(f"  [EXTRACT] 从raw_message提取sender信息:")
                print(f"    sender_id_for_private: {sender_id_for_private}")
                print(f"    sender_nick_for_private: {sender_nick_for_private}")
            except Exception as e:
                print(f"    [ERROR] 提取失败: {e}")

        # 构造ProcessResult（模拟file_transfer_processor）
        from src.processor.file_transfer_processor import ProcessResult

        process_result = ProcessResult(
            message_id=message_id,
            folder_name=folder_name or "unknown",
            share_link=share_link or "unknown",
            status="success" if router_result.success else "failed",
            message_type=message_type,
            error_message=None,  # 简化，不使用router_result.error
            processing_time_ms=1000,  # 模拟
            total_files=0,  # 简化
            success_count=0,  # 简化
            failed_count=0,
            skipped_count=0,
            total_size_mb=0.0,
            metadata=router_result.metadata if hasattr(router_result, 'metadata') else None,
            sender_id=sender_id_for_private,
            sender_nick=sender_nick_for_private
        )

        print(f"  [ProcessResult] 构造完成:")
        print(f"    sender_id: {process_result.sender_id}")
        print(f"    sender_nick: {process_result.sender_nick}")
        print(f"    status: {process_result.status}")

        # 8. 测试私信发送（这是关键！）
        print(f"\n[PRIVATE_MESSAGE] 测试私信发送:")
        print("-" * 80)

        if process_result.sender_id:
            print(f"  [HAS_SENDER] 有sender信息，准备发送私信")
            print(f"    Target User ID: {process_result.sender_id}")

            from src.notification.dingtalk_notifier import DingtalkNotifier

            notifier = DingtalkNotifier(settings)

            # 构造通知内容
            title = f"测试处理结果 - {process_result.folder_name}"
            content = f"""## 处理结果测试

**消息ID**: {process_result.message_id}
**类型**: {process_result.message_type}
**状态**: {process_result.status}
**文件夹**: {process_result.folder_name}

**测试目的**: 验证从raw_message提取sender信息后能否成功发送私信
"""

            if process_result.sender_nick:
                content = f"@{process_result.sender_nick} " + content

            print(f"  [SEND] 开始发送私信:")
            print(f"    Title: {title}")
            print(f"    Content长度: {len(content)} 字符")

            # 发送私信
            private_result = notifier.send_private_message(
                user_id=process_result.sender_id,
                title=title,
                content=content
            )

            print(f"  [RESULT] 私信发送结果: {'SUCCESS' if private_result else 'FAILED'}")

        else:
            print(f"  [NO_SENDER] 没有sender信息，跳过私信发送")

        print("-" * 80)
        print(f"\n[SUMMARY] 测试总结:")
        print(f"  原始消息ID: {message_id}")
        print(f"  消息类型: {message_type}")
        print(f"  Router处理: {'成功' if router_result.success else '失败'}")
        print(f"  Sender信息提取: {'成功' if sender_id_for_private else '失败'}")
        print(f"  私信发送: {'会执行' if sender_id_for_private else '不会执行'}")

        return True

    except Exception as e:
        print(f"\n[ERROR] 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_process_message_200()
    sys.exit(0 if success else 1)
