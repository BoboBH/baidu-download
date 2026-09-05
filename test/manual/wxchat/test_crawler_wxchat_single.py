"""
单篇/小批量验证 --crawler-wxchat 爬虫源处理流程

从 test 库 wechat_crawler_articles 取文章，走 WeChatArticleProcessor(source="crawler")
完整流程：URL直连生成PDF -> 主SFTP + 外部SFTP双上传 -> crawler_wx_article 状态写入。
与 main.py --crawler-wxchat 唯一区别是不经过 main 的参数分发与钉钉报告。

用法:
  # 单篇生成PDF但不真正上传、不写状态表（PDF副本输出到 output/test_crawler_wxchat/）
  python test/manual/wxchat/test_crawler_wxchat_single.py --limit 1 --skip-upload

  # 按URL片段定位单篇，全链路验证（真实双SFTP上传+状态写入）
  python test/manual/wxchat/test_crawler_wxchat_single.py --url "__biz=MzA3MDM3NjE5Nw=="

  # 小批量全链路
  python test/manual/wxchat/test_crawler_wxchat_single.py --limit 2

  # 组合：最近7天内发布的第1篇，跳过上传
  python test/manual/wxchat/test_crawler_wxchat_single.py --limit 1 --days 7 --skip-upload
"""

import argparse
import shutil
import sys
from pathlib import Path

# Windows GBK控制台兜底：文章标题常含 /emoji，避免打印时UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录到Python路径（test/manual/wxchat/ 下需上溯3级）
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.wxchat import processor as wxchat_processor_module
from src.wxchat.processor import WeChatArticleProcessor
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# skip-upload 模式下 PDF 副本的本地输出目录
OUTPUT_DIR = project_root / "output" / "test_crawler_wxchat"


class FakeSFTPClient:
    """替代真实 SFTPClient：不上传，仅把PDF副本保存到本地供人工检查"""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def upload_file(self, local_path, remote_path):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUTPUT_DIR / Path(remote_path).name
        shutil.copyfile(local_path, dest)
        print(f"[SKIP-UPLOAD] PDF副本已保存: {dest}")
        print(f"[SKIP-UPLOAD] 模拟远程路径: {remote_path}")
        return True


def apply_skip_upload(processor: WeChatArticleProcessor):
    """跳过真实上传与状态写入：避免测试数据污染 crawler_wx_article 去重表"""
    wxchat_processor_module.SFTPClient = FakeSFTPClient
    processor._upload_to_external_sftp = lambda *args, **kwargs: True

    def fake_update_status(*args, **kwargs):
        print(f"[SKIP-UPLOAD] 跳过状态写入: article_key={args[0]}")

    processor._update_article_status = fake_update_status
    print(f"[SKIP-UPLOAD] 已启用：不连接SFTP、不写 crawler_wx_article，PDF副本在 {OUTPUT_DIR}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="crawler-wxchat 单篇/小批量验证脚本")
    parser.add_argument('--limit', type=int, default=1,
                        help='最多处理几篇文章（默认1，0表示不限制）')
    parser.add_argument('--url', default=None,
                        help='按URL片段过滤（子串匹配，取第一篇匹配的）')
    parser.add_argument('--days', type=int, default=None,
                        help='只取最近N天发布的文章（默认不限）')
    parser.add_argument('--skip-upload', action='store_true',
                        help='不真实上传SFTP、不写状态表，PDF副本保存到本地')
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    print("crawler-wxchat 单篇验证")
    print("=" * 50)

    settings = Settings()
    processor = WeChatArticleProcessor(settings, source="crawler")

    # 取数（与 main.py --crawler-wxchat 同一入口）
    articles = processor._fetch_articles_from_crawler(args.days)
    print(f"取到候选文章: {len(articles)} 篇 (days={args.days})")

    if args.url:
        articles = [a for a in articles if args.url in (a.get('url') or '')]
        print(f"按URL片段过滤后: {len(articles)} 篇 (匹配: {args.url})")

    if args.limit and args.limit > 0:
        articles = articles[:args.limit]

    if not articles:
        print("[WARN] 没有符合条件的文章，退出")
        return 0

    if args.skip_upload:
        apply_skip_upload(processor)

    success_count = 0
    for idx, article in enumerate(articles, 1):
        print("-" * 50)
        print(f"[{idx}/{len(articles)}] id={article.get('id')} "
              f"dedup_key={article.get('dedup_key')}")
        print(f"  标题: {article.get('title')}")
        print(f"  公众号: {article.get('account_name')} (account_id={article.get('account_id')})")
        print(f"  发布日期: {article.get('publish_date')}")

        article_key = article.get('dedup_key') or article.get('id')
        if processor._is_article_processed(article_key):
            print(f"  [WARN] 该文章在状态表中已成功处理过，本次将覆盖状态记录")

        try:
            ok = processor._process_single_article(article)
        except Exception as e:
            logger.error(f"处理异常: {e}", exc_info=True)
            ok = False

        print(f"  结果: {'[OK] 成功' if ok else '[FAIL] 失败'}")
        if ok:
            success_count += 1

    print("=" * 50)
    print(f"完成: {success_count}/{len(articles)} 篇成功")
    return 0 if success_count == len(articles) else 1


if __name__ == "__main__":
    sys.exit(main())
