"""去重验证：已成功文章重跑 process_articles 应 skipped，不重传、不报告。ASCII output only."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.wxchat.processor import WeChatArticleProcessor
from src.notification.dingtalk_notifier import DingtalkNotifier

KEY = 'https://mp.weixin.qq.com/s/10vhWjQ6-Fh3na5RfyfIDg'

settings = Settings()
proc = WeChatArticleProcessor(settings, source="crawler")

target = [a for a in proc._fetch_articles_from_crawler(None) if a.get('dedup_key') == KEY]
assert len(target) == 1, f"target article not found, got {len(target)}"

# 关键：把过滤后的取数挂回 processor，否则 process_articles 会取全部文章
proc._fetch_articles_from_crawler = lambda days=None: target

# 拦截：若去重失效会走到 _process_single_article，这里直接判失败
proc._process_single_article = lambda article: (_ for _ in ()).throw(
    AssertionError("dedup failed: article reached processing"))

captured = []
DingtalkNotifier.send_notification = lambda self, t, c: captured.append((t, c)) or True

import main as main_module
result = proc.process_articles(days=None)
rc = main_module._emit_wxchat_result(settings, result,
                                     report_title="📊 微信文章处理报告（爬虫源）",
                                     source_label="（爬虫源）", scope_desc="全部未处理")

ok = (result.total_articles == 1 and result.skipped_articles == 1
      and result.processed_articles == 0 and result.failed_articles == 0
      and len(captured) == 0 and rc == 0)
print(f"RESULT: total={result.total_articles} skipped={result.skipped_articles} "
      f"processed={result.processed_articles} failed={result.failed_articles} "
      f"reports_sent={len(captured)} rc={rc}")
print("DEDUP OK" if ok else "DEDUP FAILED")
sys.exit(0 if ok else 1)
