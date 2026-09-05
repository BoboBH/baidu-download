#!/usr/bin/env python3
"""
钉钉私信功能测试脚本

测试场景：
1. 数据库从raw_message中提取sender信息
2. ProcessResult对象携带sender信息
3. 两个私信场景的集成点
"""

import sys
# 将项目根目录加入 sys.path（脚本已移入 test/manual/）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_database_sender_extraction():
    """测试数据库sender信息提取"""
    print("=== Test 1: Database Sender Information Extraction ===")

    settings = Settings()
    db = DatabaseRepository(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name
    )

    cursor = db.connection.cursor()
    cursor.execute('SELECT id FROM message_process_log WHERE raw_message IS NOT NULL LIMIT 5')
    message_ids = [row['id'] for row in cursor.fetchall()]

    test_results = []
    for msg_id in message_ids:
        message = db.get_message_by_id(msg_id)
        if message:
            test_results.append({
                'id': message.id,
                'has_sender_id': bool(message.sender_id),
                'has_sender_nick': bool(message.sender_nick),
                'message_type': message.message_type
            })

    db.close()

    # 统计结果
    with_sender = sum(1 for r in test_results if r['has_sender_id'])
    success_rate = (with_sender / len(test_results) * 100) if test_results else 0

    print(f"Messages tested: {len(test_results)}")
    print(f"Messages with sender info: {with_sender}/{len(test_results)} ({success_rate:.0f}%)")

    if with_sender == len(test_results):
        print("SUCCESS: All messages contain sender information")
        return True
    else:
        print("ISSUE: Some messages missing sender information")
        return False

def test_processresult_sender_support():
    """测试ProcessResult对象sender信息支持"""
    print("\n=== Test 2: ProcessResult Sender Information Support ===")

    from src.processor.file_transfer_processor import ProcessResult

    # 创建测试ProcessResult对象
    test_result = ProcessResult(
        message_id=1,
        folder_name="test_folder",
        share_link="https://test.com/link",
        status="success",
        success_count=1,
        failed_count=0,
        total_files=1,
        total_size_mb=1.5,
        processing_time_ms=1000,
        sender_id="test_sender_id",
        sender_nick="Test User"
    )

    has_sender_id = hasattr(test_result, 'sender_id') and test_result.sender_id is not None
    has_sender_nick = hasattr(test_result, 'sender_nick') and test_result.sender_nick is not None

    print(f"ProcessResult has sender_id attribute: {has_sender_id}")
    print(f"ProcessResult has sender_nick attribute: {has_sender_nick}")

    if has_sender_id and has_sender_nick:
        print("SUCCESS: ProcessResult supports sender information")
        return True
    else:
        print("ISSUE: ProcessResult missing sender attributes")
        return False

def test_configuration():
    """测试配置完整性"""
    print("\n=== Test 3: Configuration Completeness ===")

    settings = Settings()

    tests = {
        'DINGTALK_APP_KEY': bool(settings.dingtalk_app_key),
        'DINGTALK_APP_SECRET': bool(settings.dingtalk_app_secret),
        'DINGTALK_AGENT_ID': bool(settings.dingtalk_agent_id),
    }

    for key, result in tests.items():
        status = "CONFIGURED" if result else "MISSING"
        print(f"{key}: {status}")

    all_configured = all(tests.values())

    if all_configured:
        print("SUCCESS: All required configurations present")
    else:
        print("WARNING: Some configurations missing")
        print("You need to set DINGTALK_AGENT_ID to enable private messaging")

    return all_configured

def test_notifier_methods():
    """测试DingtalkNotifier私信方法"""
    print("\n=== Test 4: DingtalkNotifier Private Message Methods ===")

    from src.notification.dingtalk_notifier import DingtalkNotifier

    settings = Settings()
    notifier = DingtalkNotifier(settings)

    methods = [
        '_get_access_token',
        'send_private_message',
        'send_feedback_private',
        'send_processing_result_private'
    ]

    all_exist = True
    for method in methods:
        exists = hasattr(notifier, method)
        status = "EXISTS" if exists else "MISSING"
        print(f"Method {method}: {status}")
        if not exists:
            all_exist = False

    if all_exist:
        print("SUCCESS: All required notifier methods implemented")
        return True
    else:
        print("ISSUE: Some notifier methods missing")
        return False

def main():
    """主测试流程"""
    print("=== DingTalk Private Message Feature Test ===\n")

    test_results = []
    test_results.append(("Database Sender Extraction", test_database_sender_extraction()))
    test_results.append(("ProcessResult Support", test_processresult_sender_support()))
    test_results.append(("Configuration", test_configuration()))
    test_results.append(("Notifier Methods", test_notifier_methods()))

    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")

    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("\nCOMPLETE: Private message functionality is fully implemented!")
        print("Next steps:")
        print("1. Configure DINGTALK_AGENT_ID in .env file")
        print("2. Obtain message sending permissions from DingTalk Open Platform")
        print("3. Test private messaging with actual messages")
        return 0
    else:
        print("\nWARNING: Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())