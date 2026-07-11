#!/usr/bin/env python3
"""
百度网盘PDF文件自动传输系统主程序
"""

import sys
import argparse
from pathlib import Path
from src.processor.file_processor import FileProcessor
from src.config.settings import ConfigError
from src.utils.logger import get_logger

logger = get_logger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='百度网盘PDF文件自动传输系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
  python main.py -l "分享链接" -c "提取码" -f "目录名" --verbose
        '''
    )

    parser.add_argument(
        '--link', '-l',
        required=True,
        help='百度网盘分享链接'
    )

    parser.add_argument(
        '--code', '-c',
        required=True,
        help='分享链接提取码'
    )

    parser.add_argument(
        '--folder', '-f',
        required=True,
        help='目标目录名称'
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

    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 设置日志级别
        if args.verbose:
            logger.info("Verbose mode enabled")

        logger.info("=" * 60)
        logger.info("百度网盘PDF文件自动传输系统启动")
        logger.info("=" * 60)

        # 验证配置
        logger.info("验证配置...")
        if args.config:
            from src.config.settings import Settings
            settings = Settings(args.config)
        else:
            from src.config.settings import Settings
            settings = Settings()

        logger.info("配置验证通过")
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
