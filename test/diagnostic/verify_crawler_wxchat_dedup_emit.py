"""One-shot verification: dedup semantics + _emit_wxchat_result (both paths). ASCII output only."""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import pymysql
from src.config.settings import Settings
from src.wxchat.processor import WeChatArticleProcessor
from src.wxchat.models import ProcessResult

PASS = []
FAIL = []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    # GBK 控制台无法打印 emoji，detail 统一转义为 ASCII
    print(f"[{'OK' if cond else 'FAIL'}] {name} {ascii(detail)}")

# ---- setup ----
settings = Settings()
conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                       password=settings.db_password, database=settings.db_name, charset='utf8mb4')
KEY = 'https://mp.weixin.qq.com/s/10vhWjQ6-Fh3na5RfyfIDg'

with conn.cursor() as cur:
    cur.execute("UPDATE wechat_crawler_article_status SET processed_at=NOW(), pdf_url='/fake/x.pdf', error_message=NULL "
                "WHERE article_key=%s", (KEY,))
conn.commit()

proc = WeChatArticleProcessor(settings, source="crawler")

# ---- 1. dedup read: simulated success row must be seen as processed ----
check("is_article_processed True after simulated success", proc._is_article_processed(KEY))

# ---- 2. process_articles skips the deduped article (fetch patched to only that one) ----
arts, _wt = proc._fetch_articles_from_crawler(None)
target = [a for a in arts if a.get('dedup_key') == KEY]
proc._fetch_articles_from_crawler = lambda days=None: (target, len(target))
result = proc.process_articles(days=None)
check("process_articles skip count", result.skipped_articles == 1 and result.processed_articles == 0
      and result.failed_articles == 0 and result.total_articles == 1,
      f"(total={result.total_articles}, skipped={result.skipped_articles}, "
      f"processed={result.processed_articles}, failed={result.failed_articles})")

# ---- 3. crawler-path _emit_wxchat_result: gate closes (nothing processed/failed) -> no send, exit 0 ----
from src.notification.dingtalk_notifier import DingtalkNotifier
captured = []
DingtalkNotifier.send_notification = lambda self, t, c: captured.append((t, c)) or True

import main as main_module
rc = main_module._emit_wxchat_result(settings, result,
                                     report_title="...", source_label="(crawler)", scope_desc="all pending")
check("gate closed: report NOT sent", len(captured) == 0)
check("exit 0 when no failure", rc == 0, f"(rc={rc})")

# ---- 4a. wewe path: processed=2, failed=1 -> report sent, exit 1 ----
captured.clear()
r_wewe = ProcessResult(total_articles=3, processed_articles=2, failed_articles=1, skipped_articles=0,
                       start_time=datetime(2026, 9, 4, 10, 0, 0), end_time=datetime(2026, 9, 4, 10, 5, 0),
                       errors=["err-one"])
rc = main_module._emit_wxchat_result(settings, r_wewe,
                                     report_title="📊 微信文章处理报告", source_label="", scope_desc="最近3 天")
title, content = captured[0] if captured else ("", "")
check("wewe report sent once", len(captured) == 1)
check("wewe title unchanged", title == "📊 微信文章处理报告", f"(got: {title!r})")
check("wewe content header", content.startswith("## 微信文章处理完成报告\n"))
check("wewe scope text", "最近3 天共 3 篇" in content)
check("wewe error listed", "err-one" in content)
check("exit 1 when failed>0", rc == 1, f"(rc={rc})")

# ---- 4b. crawler path: processed=2, failed=0 -> report sent, exit 0 ----
captured.clear()
r_crw = ProcessResult(total_articles=2, processed_articles=2, failed_articles=0, skipped_articles=5,
                      start_time=datetime(2026, 9, 4, 10, 0, 0), end_time=datetime(2026, 9, 4, 10, 5, 0))
rc = main_module._emit_wxchat_result(settings, r_crw,
                                     report_title="📊 微信文章处理报告（爬虫源）", source_label="（爬虫源）",
                                     scope_desc="全部未处理")
title, content = captured[0] if captured else ("", "")
check("crawler report sent once", len(captured) == 1)
check("crawler title", title == "📊 微信文章处理报告（爬虫源）", f"(got: {title!r})")
check("crawler content header", content.startswith("## 微信文章处理完成报告（爬虫源）\n"))
check("crawler scope text", "全部未处理共 2 篇" in content)
check("crawler exit 0", rc == 0, f"(rc={rc})")

# ---- 5. restore article 110 to real failed state (pending retry) ----
with conn.cursor() as cur:
    cur.execute("UPDATE wechat_crawler_article_status SET processed_at=NULL, pdf_url=NULL, "
                "error_message='主SFTP上传失败' WHERE article_key=%s", (KEY,))
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT processed_at, error_message FROM wechat_crawler_article_status WHERE article_key=%s", (KEY,))
    row = cur.fetchone()
conn.close()
check("row restored to pending-retry", row[0] is None and row[1] == '主SFTP上传失败')

print("=" * 50)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
