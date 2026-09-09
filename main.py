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

def ensure_playwright_browsers():
    """确保Playwright浏览器已安装"""
    try:
        import os
        from playwright.sync_api import sync_playwright

        logger.info("检查Playwright浏览器...")

        # 检查是否在PyInstaller环境中运行
        if getattr(sys, 'frozen', False):
            # 在PyInstaller打包的exe中运行
            logger.info("检测到PyInstaller环境，配置浏览器路径...")

            # 设置PLAYWRIGHT_BROWSERS_PATH指向系统浏览器安装路径
            # 这样Playwright可以找到系统安装的浏览器
            system_browsers_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright')
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = system_browsers_path
            logger.info(f"设置浏览器路径: {system_browsers_path}")
            logger.info(f"浏览器目录存在: {os.path.exists(system_browsers_path)}")

        # 尝试启动浏览器来检查是否已安装
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            logger.info("Playwright浏览器已就绪")
            return True
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                logger.warning("Playwright浏览器未找到，请先安装:")
                logger.error("运行命令: playwright install chromium")
                return False
            else:
                logger.error(f"Playwright检查失败: {e}")
                return False

    except ImportError:
        logger.error("Playwright未安装，请先安装: pip install playwright")
        return False
    except Exception as e:
        logger.error(f"Playwright检查异常: {e}")
        return False

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

  微信模式 - 爬虫源文章:
    python main.py --crawler-wxchat
    python main.py --crawler-wxchat --crawler-wxchat-days 7 --verbose
        （回溯天数默认取WXCHAT_CRAWLER_DAYS配置，未配置时3天；0=不限时间窗处理所有未成功文章）
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

    parser.add_argument(
        '--force-reprocess',
        action='store_true',
        help='强制重新处理：跳过去重检查，重新处理所有文件（包括之前成功的）'
    )

    parser.add_argument(
        '--crawler-wxchat',
        dest='crawler_wxchat',
        action='store_true',
        help='微信模式-爬虫源：处理爬虫库微信公众号文章（wechat_crawler_articles），生成PDF并上传（双SFTP，与--wxchat一致）'
    )

    parser.add_argument(
        '--crawler-wxchat-days',
        dest='crawler_wxchat_days',
        type=int,
        default=None,
        help='爬虫源模式：只处理最近N天发布的文章（默认取WXCHAT_CRAWLER_DAYS配置，未配置时3天；0=不限时间窗，处理所有未成功文章）'
    )

    return parser.parse_args()

def _emit_wxchat_result(settings: Settings, result, report_title: str,
                        source_label: str = "", scope_desc: str = "") -> int:
    """打印微信文章处理统计并发送钉钉报告（--wxchat 与 --crawler-wxchat 共用）

    Args:
        settings: 配置对象
        result: ProcessResult 处理结果
        report_title: 钉钉报告标题
        source_label: 数据源标签（如 "" 或 "（爬虫源）"）
        scope_desc: 处理范围描述（如 "最近3 天" 或 "全部未处理"）

    Returns:
        进程退出码：0=无失败文章，1=有失败文章
    """
    logger.info("=" * 60)
    logger.info(f"微信文章处理完成{source_label}！")
    if result.window_total > 0:
        # 窗口口径：总数含已成功文章，跳过=已成功下载，本次处理=待处理尝试数
        logger.info(f"窗口文章总数: {result.window_total} 篇")
        logger.info(f"本次处理: {result.total_articles} 篇（成功 {result.processed_articles} / 失败 {result.failed_articles}）")
        logger.info(f"跳过(已处理): {result.skipped_articles} 篇")
    else:
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

    # 发送报告到钉钉群
    try:
        from src.notification.dingtalk_notifier import DingtalkNotifier
        notifier = DingtalkNotifier(settings)

        # 构建报告消息
        if result.window_total > 0:
            # 窗口口径：总数含已成功文章，跳过=已成功下载，本次处理=待处理尝试数
            stats_content = f"""### 📈 处理统计
- **窗口文章总数**: {scope_desc}共 {result.window_total} 篇
- **🔨 本次处理**: {result.total_articles} 篇
- **✅ 成功**: {result.processed_articles} 篇
- **❌ 失败**: {result.failed_articles} 篇
- **⏭️ 跳过(已处理)**: {result.skipped_articles} 篇

### ⏱️ 处理时间
"""
        else:
            stats_content = f"""### 📈 处理统计
- **总计文章**: {scope_desc}共 {result.total_articles} 篇
- **✅ 成功处理**: {result.processed_articles} 篇
- **❌ 失败文章**: {result.failed_articles} 篇
- **⏭️ 跳过文章**: {result.skipped_articles} 篇

### ⏱️ 处理时间
"""
        report_content = f"""## 微信文章处理完成报告{source_label}

{stats_content}"""

        if result.start_time and result.end_time:
            duration = (result.end_time - result.start_time).total_seconds()
            start_time_str = result.start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_time_str = result.end_time.strftime('%Y-%m-%d %H:%M:%S')
            report_content += f"- **开始时间**: {start_time_str}\n"
            report_content += f"- **结束时间**: {end_time_str}\n"
            report_content += f"- **处理耗时**: {duration:.2f} 秒\n\n"

        # 添加错误信息（如果有）
        if result.errors:
            total_errors = len(result.errors)
            display_count = min(5, total_errors)
            report_content += f"### ⚠️ 错误信息 ({total_errors} 个)\n"
            for error in result.errors[:display_count]:
                report_content += f"- {error}\n"
            if total_errors > display_count:
                report_content += f"- ... 还有 {total_errors - display_count} 个错误未显示\n"
            report_content += "\n"

        # 添加状态总结
        if result.failed_articles == 0:
            report_content += "### 🎉 处理完成\n所有文章处理成功，无失败！"
        else:
            success_rate = (result.processed_articles / result.total_articles * 100) if result.total_articles > 0 else 0
            report_content += f"### 📋 处理完成\n成功率: {success_rate:.1f}%"

        # 判断是否需要发送报告：有新增文章或有失败文章时才发送
        should_send_report = result.processed_articles > 0 or result.failed_articles > 0

        if should_send_report:
            logger.info("正在发送报告到钉钉群...")
            if notifier.send_notification(report_title, report_content):
                logger.info("✅ 报告已成功发送到钉钉群")
            else:
                logger.warning("⚠️ 钉钉报告发送失败")
        else:
            logger.info("ℹ️ 没有新增文章也没有失败文章，跳过报告发送")

    except ImportError:
        logger.warning("钉钉通知模块未导入，跳过报告发送")
    except Exception as e:
        logger.error(f"发送钉钉报告时出错: {e}")

    return 0 if result.failed_articles == 0 else 1

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

            # 确保Playwright浏览器已安装（重要！）
            if not ensure_playwright_browsers():
                logger.error("Playwright浏览器未就绪，无法处理微信文章")
                logger.error("请手动运行: pip install playwright && playwright install chromium")
                return 1

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
                    # 先同步账号信息，确保账号表是最新的
                    logger.info("同步微信账号信息...")
                    account_sync = WeChatAccountSync(settings)
                    synced_count = account_sync.sync_accounts()
                    logger.info(f"账号同步完成，同步了 {synced_count} 个账号")

                    processor = WeChatArticleProcessor(settings)
                    result = processor.process_articles(days=days)

                    return _emit_wxchat_result(
                        settings, result,
                        report_title="📊 微信文章处理报告",
                        source_label="",
                        scope_desc=f"最近{days} 天"
                    )

                except Exception as e:
                    logger.error(f"微信文章处理失败: {e}", exc_info=True)
                    return 1

        # 微信模式-爬虫源：处理爬虫库微信公众号文章
        if args.crawler_wxchat:
            logger.info("微信模式-爬虫源：开始处理爬虫库微信文章...")

            # 确保Playwright浏览器已安装
            if not ensure_playwright_browsers():
                logger.error("Playwright浏览器未就绪，无法处理微信文章")
                logger.error("请手动运行: pip install playwright && playwright install chromium")
                return 1

            # 回溯天数：CLI > 环境配置 WXCHAT_CRAWLER_DAYS（默认3天）；0=不限时间窗（全部未成功文章）
            days = args.crawler_wxchat_days
            if days is None:
                days = settings.wxchat_crawler_days
            if days < 0 or days > settings.wxchat_max_days:
                logger.error(f"天数必须在 0 到 {settings.wxchat_max_days} 之间（0=不限时间窗，处理所有未成功文章）")
                return 1

            try:
                # 前置检查：状态表 wechat_crawler_article_status 是否已创建（014迁移），
                # 避免取数层吞掉缺表异常后静默按0篇处理
                import pymysql
                conn = pymysql.connect(
                    host=settings.db_host,
                    port=settings.db_port,
                    user=settings.db_user,
                    password=settings.db_password,
                    database=settings.db_name
                )
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM wechat_crawler_article_status LIMIT 1")
                finally:
                    conn.close()

                processor = WeChatArticleProcessor(settings, source="crawler")
                result = processor.process_articles(days=None if days == 0 else days)

                scope_desc = "全部未处理" if days == 0 else f"最近{days} 天"
                return _emit_wxchat_result(
                    settings, result,
                    report_title="📊 微信文章处理报告（爬虫源）",
                    source_label="（爬虫源）",
                    scope_desc=scope_desc
                )

            except Exception as e:
                if "1146" in str(e) or "doesn't exist" in str(e):
                    logger.error(f"状态表 wechat_crawler_article_status 不可用: {e}")
                    logger.error("请先执行迁移: mysql -u root -p test < database/migrations/014_create_wechat_crawler_article_status.sql")
                else:
                    logger.error(f"爬虫源微信文章处理失败: {e}", exc_info=True)
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
            if args.force_reprocess:
                logger.info("🔄 强制重新处理模式已启用：将处理所有文件，包括之前成功的")
            logger.info("处理模式：开始处理待处理消息...")

            with FileTransferProcessor(settings, force_reprocess=args.force_reprocess) as processor:
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
            if args.force_reprocess:
                logger.info("🔄 强制重新处理模式已启用：将处理所有文件，包括之前成功的")
            logger.info("自动模式：开始自动处理飞书消息...")

            # 创建AutoProcessor并执行
            processor: AutoProcessor = AutoProcessor(settings, force_reprocess=args.force_reprocess)
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
        if args.force_reprocess:
            logger.info("🔄 强制重新处理模式已启用：将处理所有文件，包括之前成功的")
        logger.info("开始处理文件传输...")

        with FileProcessor(force_reprocess=args.force_reprocess) as processor:
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
