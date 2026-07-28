#!/usr/bin/env python3
"""
百度网盘PDF文件自动传输系统主程序
"""

import sys
import argparse
import asyncio
from src.processor.file_processor import FileProcessor
from src.processor.auto_processor import AutoProcessor
from src.processor.message_receiver import MessageReceiver
from src.processor.file_transfer_processor import FileTransferProcessor
from src.config.settings import ConfigError, Settings
from src.utils.logger import get_logger
from src.wxchat.processor import WeChatAccountSync, WeChatArticleProcessor

logger = get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='百度网盘PDF文件自动传输系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  手动模式:
    python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
    python main.py -l "分享链接" -c "提取码" -f "目录名" --verbose

  自动模式（一站式）:
    python main.py --auto
    python main.py --auto --config "/path/to/config.env" --verbose

  分离模式 - 接收消息:
    python main.py --receive-messages
    python main.py --receive-messages --verbose

  分离模式 - 处理待处理消息:
    python main.py --process-pending
    python main.py --process-pending --verbose

  分离模式 - 组合使用（推荐）:
    # 步骤1: 接收飞书消息
    python main.py --receive-messages
    # 步骤2: 处理待处理消息
    python main.py --process-pending

  钉钉服务模式（常驻进程）:
    python main.py --dingtalk-service
    python main.py --dingtalk-service --verbose

  微信模式 - 处理文章:
    python main.py --wxchat
    python main.py --wxchat --wxchat-days 7 --verbose

  微信模式 - 同步账号:
    python main.py --wxchat --wxchat-sync-accounts
        '''
    )

    parser.add_argument(
        '--link', '-l',
        required=False,
        help='百度网盘分享链接（手动模式必需）'
    )

    parser.add_argument(
        '--code', '-c',
        required=False,
        help='分享链接提取码（手动模式必需）'
    )

    parser.add_argument(
        '--folder', '-f',
        required=False,
        help='目标目录名称（手动模式必需）'
    )

    parser.add_argument(
        '--config',
        help='配置文件路径（默认为.env）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅测试配置，不实际执行下载和上传'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动模式：从飞书获取消息并自动处理（不需要手动指定链接、提取码和目录名）'
    )

    parser.add_argument(
        '--receive-messages',
        action='store_true',
        help='接收模式：专职收取飞书消息，解析并记录到数据库（状态为待处理）'
    )

    parser.add_argument(
        '--process-pending',
        action='store_true',
        help='处理模式：专职从数据库获取待处理消息，执行下载和上传'
    )

    parser.add_argument(
        '--dingtalk-service',
        action='store_true',
        help='启动钉钉消息接收服务（常驻进程）'
    )

    parser.add_argument(
        '--source',
        choices=['feishu', 'dingtalk'],
        default='feishu',
        help='消息来源平台（feishu或dingtalk，默认为feishu）'
    )

    parser.add_argument(
        '--wxchat', '--wechat',
        dest='wxchat',
        action='store_true',
        help='微信模式：处理微信公众号文章，生成PDF并上传'
    )

    parser.add_argument(
        '--wxchat-days',
        type=int,
        default=3,
        help='微信模式：处理最近几天的文章（默认3天）'
    )

    parser.add_argument(
        '--wxchat-sync-accounts',
        action='store_true',
        help='微信模式：仅同步微信公众号账号信息'
    )

    return parser.parse_args()

def main() -> int:
    """主函数"""
    try:
        # 解析命令行参数
        args: argparse.Namespace = parse_arguments()

        # 设置日志级别
        if args.verbose:
            logger.setLevel('DEBUG')
            for handler in logger.handlers:
                handler.setLevel('DEBUG')
            logger.info("Verbose mode enabled")

        logger.info("=" * 60)
        logger.info("百度网盘PDF文件自动传输系统启动")
        logger.info("=" * 60)

        # 验证配置
        logger.info("验证配置...")
        settings: Settings
        if args.config:
            settings = Settings(args.config)
        else:
            settings = Settings()

        logger.info("配置验证通过")

        # 钉钉服务模式：启动钉钉消息接收常驻服务
        if args.dingtalk_service:
            logger.info("启动钉钉消息接收服务...")

            # 验证钉钉配置
            if not settings.dingtalk_app_key or not settings.dingtalk_app_secret:
                logger.error("DINGTALK_APP_KEY and DINGTALK_APP_SECRET must be set in .env file")
                return 1

            # 启动钉钉服务
            from src.feishu.dingtalk_group_client import main as dingtalk_main

            print("=" * 60)
            print("DingTalk Message Receiver Service")
            print("=" * 60)
            print(f"App Key: {settings.dingtalk_app_key}")
            print(f"Database: {settings.db_name}")
            print("消息要求: 必须@机器人")
            print("Supported format: 260723：https://pan.baidu.com/s/xxx")
            print("Press Ctrl+C to stop the service")
            print("=" * 60)

            # 运行钉钉服务（使用默认设置）
            exit_code = asyncio.run(dingtalk_main())
            return exit_code

        # 微信模式：处理微信公众号文章
        if args.wxchat or args.wxchat_sync_accounts:
            logger.info("微信模式：开始处理微信公众号功能...")

            # 仅验证微信数据库配置（不需要检查WXCHAT_ENABLED开关）
            if not settings.wxchat_wewe_db_host or not settings.wxchat_wewe_db_name:
                logger.error("WXCHAT_WEWE_DB_HOST and WXCHAT_WEWE_DB_NAME must be set in .env file")
                return 1

            # 账号同步模式
            if args.wxchat_sync_accounts:
                logger.info("微信模式 - 账号同步：开始同步微信公众号账号...")

                try:
                    account_sync = WeChatAccountSync(settings)
                    synced_count = account_sync.sync_accounts()

                    logger.info("=" * 60)
                    logger.info("微信账号同步完成！")
                    logger.info(f"同步账号数: {synced_count} 个")
                    logger.info("=" * 60)

                    return 0  # 成功同步，即使账号数为0也不是错误

                except Exception as e:
                    logger.error(f"微信账号同步失败: {e}", exc_info=True)
                    return 1

            # 文章处理模式
            if args.wxchat:
                days = args.wxchat_days
                logger.info(f"微信模式 - 文章处理：开始处理最近 {days} 天的文章...")

                # 验证天数参数
                if days < 1 or days > settings.wxchat_max_days:
                    logger.error(f"天数必须在 1 到 {settings.wxchat_max_days} 之间")
                    return 1

                try:
                    processor = WeChatArticleProcessor(settings)
                    result = processor.process_articles(days=days)

                    logger.info("=" * 60)
                    logger.info("微信文章处理完成！")
                    logger.info(f"总计文章: {result.total_articles} 篇")
                    logger.info(f"成功处理: {result.processed_articles} 篇")
                    logger.info(f"失败文章: {result.failed_articles} 篇")
                    logger.info(f"跳过文章: {result.skipped_articles} 篇")

                    if result.start_time and result.end_time:
                        duration = (result.end_time - result.start_time).total_seconds()
                        logger.info(f"处理耗时: {duration:.2f} 秒")

                    if result.errors:
                        total_errors = len(result.errors)
                        display_count = min(5, total_errors)
                        logger.warning(f"错误信息: {total_errors} 个 (显示前 {display_count} 个)")
                        for error in result.errors[:display_count]:
                            logger.warning(f"  - {error}")
                        if total_errors > display_count:
                            logger.warning(f"  ... 还有 {total_errors - display_count} 个错误未显示")

                    logger.info("=" * 60)

                    return 0 if result.failed_articles == 0 else 1

                except Exception as e:
                    logger.error(f"微信文章处理失败: {e}", exc_info=True)
                    return 1

        # 接收模式：专职接收飞书消息
        if args.receive_messages:
            logger.info(f"接收模式：开始接收{args.source}消息...")

            with MessageReceiver(settings, source=args.source) as receiver:
                result = receiver.receive_messages()

                logger.info("=" * 60)
                logger.info("飞书消息接收完成！")
                logger.info(f"总计接收: {result.total_messages} 条消息")
                logger.info(f"新增消息: {result.new_messages} 条")
                logger.info(f"重复消息: {result.duplicate_messages} 条")
                # 计算过滤消息数量（重复 + 无法解析）
                filtered_count = result.duplicate_messages + len(result.details[0].get('filtered_messages', []))
                logger.info(f"过滤消息: {filtered_count} 条 (重复/无法解析)")
                logger.info(f"处理耗时: {result.processing_time_ms / 1000:.2f} 秒")
                logger.info("=" * 60)

                return 0 if result.failed_messages == 0 else 1

        # 处理模式：专职处理待处理消息
        if args.process_pending:
            logger.info("处理模式：开始处理待处理消息...")

            with FileTransferProcessor(settings) as processor:
                result = processor.process_pending_messages()

                logger.info("=" * 60)
                logger.info("文件处理完成！")
                logger.info(f"处理消息数: {result.total_messages} 条")
                logger.info(f"成功消息: {result.success_messages} 条")
                logger.info(f"失败消息: {result.failed_messages} 条")
                logger.info(f"总文件数: {result.total_files} 个")
                logger.info(f"成功文件: {result.total_success_files} 个")
                logger.info(f"失败文件: {result.total_failed_files} 个")
                logger.info(f"总大小: {result.total_size_mb:.2f} MB")
                logger.info(f"处理耗时: {result.processing_time_ms / 1000:.2f} 秒")
                logger.info("=" * 60)

                return 0 if result.failed_messages == 0 else 1

        # 自动模式处理（保留原有的一站式功能）
        if args.auto:
            logger.info("自动模式：开始自动处理飞书消息...")

            # 创建AutoProcessor并执行
            processor: AutoProcessor = AutoProcessor(settings)
            exit_code: int = processor.process_messages()

            return exit_code

        # 手动模式：验证必需参数
        if not args.link or not args.code or not args.folder:
            logger.error("手动模式需要提供 --link, --code, 和 --folder 参数")
            logger.error("使用 --auto 参数启用自动模式，或提供所有必需的手动参数")
            return 1

        logger.info(f"分享链接: {args.link}")
        logger.info(f"提取码: {args.code}")
        logger.info(f"目录名: {args.folder}")

        # 如果是dry-run模式，只验证配置
        if args.dry_run:
            logger.info("Dry-run模式：配置验证完成，不执行实际操作")
            return 0

        # 创建处理器并执行
        logger.info("开始处理文件传输...")

        with FileProcessor() as processor:
            summary = processor.process_files(
                share_link=args.link,
                code=args.code,
                folder_name=args.folder
            )

            if summary:
                logger.info("=" * 60)
                logger.info("处理完成！")
                logger.info(f"总文件数: {summary.total_files}")
                logger.info(f"成功: {summary.success_count}")
                logger.info(f"失败: {summary.failed_count}")
                logger.info(f"跳过: {summary.skipped_count}")
                if summary.total_size:
                    logger.info(f"总大小: {summary.total_size / 1024 / 1024:.2f} MB")
                if summary.start_time and summary.end_time:
                    duration = (summary.end_time - summary.start_time).total_seconds()
                    logger.info(f"总耗时: {duration:.2f} 秒")
                logger.info("=" * 60)
                return 0
            else:
                logger.error("处理失败")
                return 1

    except ConfigError as e:
        logger.error(f"配置错误: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
