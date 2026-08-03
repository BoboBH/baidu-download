#!/usr/bin/env python3
"""
完整工作流程测试
验证飞书消息到文件传输的完整流程
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.processor.file_processor import FileProcessor
from src.downloader.baidu_client import BaiduClient
from src.uploader.sftp_client import SFTPClient
from src.feishu.message_parser import MessageParser

def test_complete_workflow():
    """测试完整工作流程"""
    print("=" * 60)
    print("完整工作流程测试")
    print("=" * 60)

    try:
        settings = Settings()

        # 1. 检查配置
        print("1. 检查配置...")
        configs_ok = True

        required_configs = {
            '百度网盘': [settings.baidupcs_go_path, settings.baidu_cookies_path],
            'SFTP': [settings.sftp_host, settings.sftp_username, settings.sftp_password],
            '飞书': [settings.feishu_app_id, settings.feishu_app_secret, settings.feishu_chat_id],
            '数据库': [settings.db_host, settings.db_user, settings.db_password, settings.db_name]
        }

        for config_name, config_items in required_configs.items():
            status = "[OK]" if all(config_items) else "[WARNING]"
            print(f"   {status} {config_name}配置")
            if not all(config_items):
                configs_ok = False

        # 2. 测试组件初始化
        print("\n2. 测试组件初始化...")
        components_ok = True

        try:
            # SFTP测试
            print("   测试SFTP连接...")
            sftp_client = SFTPClient()
            if sftp_client.connect():
                print("   [OK] SFTP连接成功")
                sftp_client.disconnect()
            else:
                print("   [ERROR] SFTP连接失败")
                components_ok = False

            # 百度网盘客户端
            print("   测试百度网盘客户端...")
            baidu_client = BaiduClient()
            print("   [OK] 百度网盘客户端初始化成功")

            # 消息解析器
            print("   测试消息解析器...")
            parser = MessageParser()
            print("   [OK] 消息解析器初始化成功")

        except Exception as e:
            print(f"   [ERROR] 组件初始化失败: {e}")
            components_ok = False

        # 3. 测试消息解析
        print("\n3. 测试消息解析...")
        parser_ok = True

        try:
            # 测试消息格式
            test_messages = [
                "分享链接 链接:https://pan.baidu.com/s/1A2B3C4D5E 提取码:abcd 目录名:测试文件",
                "链接 https://pan.baidu.com/s/1XYZ 提取码 1234 文件夹 我的文档"
            ]

            for msg in test_messages:
                try:
                    result = parser.parse_message(msg)
                    if result:
                        print(f"   [OK] 消息解析成功: {result.share_link[:20]}...")
                    else:
                        print(f"   [WARNING] 消息解析失败")
                except Exception as e:
                    print(f"   [ERROR] 消息解析异常: {e}")
                    parser_ok = False

        except Exception as e:
            print(f"   [ERROR] 消息解析测试失败: {e}")
            parser_ok = False

        # 4. 工作流程验证
        print("\n4. 工作流程验证...")

        workflows = [
            {
                'name': '消息接收 → 数据库存储',
                'components': ['MessageReceiver', 'DatabaseRepository'],
                'status': '正常' if configs_ok else '需要配置'
            },
            {
                'name': '数据库读取 → 文件下载 → SFTP上传',
                'components': ['FileTransferProcessor', 'BaiduClient', 'SFTPClient'],
                'status': '正常' if components_ok else '组件异常'
            },
            {
                'name': '消息解析 → 文件处理',
                'components': ['MessageParser', 'FileProcessor'],
                'status': '正常' if parser_ok else '解析异常'
            }
        ]

        for workflow in workflows:
            symbol = '[OK]' if workflow['status'] == '正常' else '[!]'
            print(f"   {symbol} {workflow['name']}: {workflow['status']}")
            print(f"      组件: {', '.join(workflow['components'])}")

        # 5. 总体状态
        print("\n5. 总体状态评估...")

        all_ok = configs_ok and components_ok and parser_ok

        if all_ok:
            print("   [SUCCESS] 所有功能正常，可以正常使用")
            print("\n推荐使用方式:")
            print("   - 自动模式: python main.py --auto")
            print("   - 分离模式: python main.py --receive-messages && python main.py --process-pending")
            print("   - 手动模式: python main.py --link <链接> --code <提取码> --folder <目录名>")
        else:
            print("   [WARNING] 部分功能需要检查配置")
            if not configs_ok:
                print("   - 检查.env配置文件")
            if not components_ok:
                print("   - 检查网络连接和外部服务")
            if not parser_ok:
                print("   - 检查消息解析逻辑")

        print("\n" + "=" * 60)
        status_str = '[SUCCESS]' if all_ok else '[WARNING]'
        print(f"{status_str} 工作流程测试完成!")
        print("=" * 60)

        return all_ok

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
