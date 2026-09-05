"""
测试v1.6.7的ZIP文件名解码修复
验证数据库中ID 213, 212, 211的消息处理
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# 设置PYTHONPATH环境变量
os.environ['PYTHONPATH'] = str(project_root)

from src.config.settings import Settings
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
from src.feishu.models import ParseResult
from src.utils.logger import get_logger

try:
    import pymysql
except ImportError:
    print("Warning: pymysql not available, database access will fail")
    pymysql = None

logger = get_logger(__name__)

def test_message_from_db(msg_id):
    """测试数据库中的特定消息"""
    try:
        settings = Settings()

        # 连接数据库获取消息信息
        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        cursor.execute('SELECT id, message_type, raw_message FROM message_process_log WHERE id = %s', (msg_id,))
        result = cursor.fetchone()

        if not result:
            logger.error(f"消息ID {msg_id} 不存在")
            return False

        msg_id, message_type, raw_message = result
        conn.close()

        import json
        raw_data = json.loads(raw_message)

        logger.info(f"=" * 60)
        logger.info(f"Testing message ID {msg_id}: {raw_data.get('file_name')}")
        logger.info(f"Message type: {message_type}")
        logger.info(f"Sender: {raw_data.get('sender_nick')}")

        # 创建ParseResult（使用正确的参数）
        parse_result = ParseResult(
            message_type=message_type,
            unique_identifier=raw_data.get('file_id'),
            source='dingtalk',
            download_code=raw_data.get('download_code'),
            file_name=raw_data.get('file_name'),
            file_id=raw_data.get('file_id'),
            space_id=raw_data.get('space_id'),
            raw_message=raw_message
        )

        # 创建处理器
        processor = DingTalkFileProcessor(settings)

        # 下载文件
        logger.info(f"开始下载文件...")
        download_result = processor.download(parse_result)

        if not download_result.success:
            logger.error(f"❌ 下载失败: {download_result.error}")
            return False

        logger.info(f"✅ 下载成功: {download_result.filename} ({download_result.file_size / (1024*1024):.2f} MB)")

        # 处理文件（解压ZIP）
        logger.info(f"开始处理文件...")
        process_result = processor.process(download_result, parse_result)

        if not process_result.success:
            logger.error(f"❌ 处理失败: {process_result.error}")
            return False

        logger.info(f"✅ 处理成功: 提取了 {len(process_result.processed_files)} 个文件")

        # 显示提取的文件列表
        for i, file_path in enumerate(process_result.processed_files, 1):
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_name = os.path.basename(file_path)
            logger.info(f"  {i}. {file_name} ({file_size / 1024:.1f} KB)")

        # 清理临时文件
        processor.cleanup()

        return True

    except Exception as e:
        logger.error(f"测试消息ID {msg_id} 异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("v1.6.7 ZIP文件名解码修复验证测试")
    print("=" * 60)

    # 测试三个消息ID
    test_ids = [213, 212, 211]  # 2-reports.zip, 4-reports.zip, 3-reports.zip

    results = {}
    for msg_id in test_ids:
        success = test_message_from_db(msg_id)
        results[msg_id] = success
        print()

    # 输出测试结果总结
    print("=" * 60)
    print("Test Results Summary:")
    print("-" * 60)

    for msg_id, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"Message ID {msg_id}: {status}")

    # 判断是否所有测试都通过
    all_success = all(results.values())
    print("-" * 60)
    if all_success:
        print("SUCCESS: All tests passed! v1.6.7 fix verification successful!")
    else:
        print("WARNING: Some tests failed, need further investigation")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
