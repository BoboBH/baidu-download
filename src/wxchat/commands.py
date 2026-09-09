"""
微信公众号文章处理CLI命令定义
"""

import click
import logging
from src.config.settings import Settings
from src.utils.logger import get_file_handler
from src.wxchat.processor import WeChatAccountSync, WeChatArticleProcessor

logger = logging.getLogger(__name__)


def register_commands(cli: click.Group):
    """
    注册微信文章处理相关命令

    Args:
        cli: Click命令组对象
    """

    @cli.command('wxchat')
    @click.option('--days', default=3, help='处理最近几天的文章（默认3天）')
    @click.option('--sync-accounts', is_flag=True, help='仅同步账号信息')
    @click.pass_context
    def wxchat_command(ctx, days, sync_accounts):
        """
        处理微信公众号文章

        从wewe_rss数据库获取文章，转换为PDF，上传到SFTP服务器

        示例:
            python main.py wxchat                    # 处理最近3天文章
            python main.py wxchat --days 7          # 处理最近7天文章
            python main.py wxchat --sync-accounts    # 仅同步账号信息
        """
        try:
            # 加载配置
            config = Settings()

            if not config.wxchat_enabled:
                click.echo("错误: 微信文章处理功能未启用，请在.env中设置WXCHAT_ENABLED=true")
                return

            # 配置日志（文件按天+按大小滚动，最多保留7天，单文件不超过50MB）
            logging.basicConfig(
                level=getattr(logging, config.log_level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    get_file_handler(config.log_file),
                    logging.StreamHandler()
                ]
            )

            click.echo("🚀 微信公众号文章处理系统")
            click.echo("=" * 50)

            if sync_accounts:
                # 仅同步账号信息
                click.echo("📋 开始同步微信账号信息...")

                syncer = WeChatAccountSync(config)
                count = syncer.sync_accounts()

                click.echo(f"✅ 账号同步完成，共同步 {count} 个账号")

            else:
                # 处理文章
                click.echo(f"📰 开始处理最近 {days} 天的文章...")

                processor = WeChatArticleProcessor(config)
                result = processor.process_articles(days)

                # 显示处理结果
                click.echo("\n📊 处理结果统计:")
                click.echo(f"  总文章数: {result.total_articles}")
                click.echo(f"  处理成功: {result.processed_articles}")
                click.echo(f"  处理失败: {result.failed_articles}")
                click.echo(f"  跳过处理: {result.skipped_articles}")

                if result.start_time and result.end_time:
                    duration = (result.end_time - result.start_time).total_seconds()
                    click.echo(f"  处理时长: {duration:.2f} 秒")

                if result.errors:
                    click.echo(f"\n⚠️  错误信息:")
                    for error in result.errors[:5]:  # 只显示前5个错误
                        click.echo(f"  - {error}")

                click.echo("\n✅ 文章处理完成!")

        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            click.echo(f"❌ 执行失败: {e}")
            raise click.ClickException(str(e))
