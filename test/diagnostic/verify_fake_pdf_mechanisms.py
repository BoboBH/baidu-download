"""Verify: retry_count upsert semantics, backoff fetch filter, fake-PDF detection, circuit breaker. ASCII output only."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import pymysql
from src.config.settings import Settings
from src.wxchat.processor import WeChatArticleProcessor

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'OK' if cond else 'FAIL'}] {name} {ascii(detail)}")

settings = Settings()
proc = WeChatArticleProcessor(settings, source="crawler")
conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                       password=settings.db_password, database=settings.db_name, charset='utf8mb4')

SCRATCH_KEY = 'test_retry_scratch_key'
SCRATCH_ART = {'id': 999999, 'account_name': 'scratch'}

def row_of(key):
    conn.commit()  # 结束当前事务，避免 REPEATABLE_READ 快照读到旧数据
    with conn.cursor() as cur:
        cur.execute("SELECT processed_at, retry_count FROM crawler_wx_article WHERE article_key=%s", (key,))
        return cur.fetchone()

# ---- 1. retry_count increments on failure, resets on success ----
proc._update_article_status(SCRATCH_KEY, 999, 't', '2026-09-04', None, 'err1', article=SCRATCH_ART)
proc._update_article_status(SCRATCH_KEY, 999, 't', '2026-09-04', None, 'err2', article=SCRATCH_ART)
r = row_of(SCRATCH_KEY)
check("two failures -> retry_count=2, pending", r[0] is None and r[1] == 2, f"row={r}")
proc._update_article_status(SCRATCH_KEY, 999, 't', '2026-09-04', '/x.pdf', None, article=SCRATCH_ART)
r = row_of(SCRATCH_KEY)
check("success -> retry_count=0, processed", r[0] is not None and r[1] == 0, f"row={r}")

# ---- 2. backoff filter in crawler fetch ----
with conn.cursor() as cur:
    cur.execute("""SELECT a.dedup_key FROM wechat_crawler_articles a
                   LEFT JOIN crawler_wx_article s ON s.article_key = a.dedup_key COLLATE utf8mb4_0900_ai_ci
                   WHERE s.article_key IS NULL AND a.url IS NOT NULL AND a.url != ''
                   ORDER BY a.id LIMIT 1""")
    free_key = cur.fetchone()[0]
with conn.cursor() as cur:
    cur.execute("""INSERT INTO crawler_wx_article (article_key, crawler_article_id, account_id, title,
                   error_message, processed_at, retry_count, updated_at)
                   VALUES (%s, 888888, 1, 'backoff-test', 'err', NULL, 2, NOW())""", (free_key,))
conn.commit()
arts = proc._fetch_articles_from_crawler(None)
in_list = any(a.get('dedup_key') == free_key for a in arts)
check("failed(2x, just now) article EXCLUDED by backoff", not in_list, f"fetch={len(arts)}")
with conn.cursor() as cur:
    cur.execute("UPDATE crawler_wx_article SET updated_at = NOW() - INTERVAL 3 HOUR WHERE article_key=%s", (free_key,))
conn.commit()
arts = proc._fetch_articles_from_crawler(None)
in_list = any(a.get('dedup_key') == free_key for a in arts)
check("same article after 3h (2*20min=40min elapsed) INCLUDED", in_list, f"fetch={len(arts)}")

# cleanup scratch rows
with conn.cursor() as cur:
    cur.execute("DELETE FROM crawler_wx_article WHERE article_key IN (%s, %s)", (SCRATCH_KEY, free_key))
conn.commit()
conn.close()

# ---- 3. fake-PDF detection (single attempt per run; retries happen across runs via backoff) ----
captured = {}
proc2 = WeChatArticleProcessor(settings, source="crawler")
proc2._update_article_status = lambda *a, **k: captured.update(err=a[5])
def fake_gen(url, out):
    with open(out, 'wb') as f:
        f.write(b'%PDF-1.4 tiny' + b'\0' * 500)
    return True
proc2.pdf_generator.generate_pdf_from_url = fake_gen
art = {'id': 'scratch-det', 'dedup_key': 'scratch-det', 'url': 'https://x', 'title': 'det-test',
       'account_id': 1, 'account_name': 'a', 'publish_date': '2026-09-04'}
ok = proc2._process_single_article(art)
check("tiny PDF -> failure", ok is False)
check("error mentions fake PDF", '假PDF' in (captured.get('err') or ''), f"err={captured.get('err')}")
check("last_pdf_blocked=True", proc2.last_pdf_blocked is True)

# ---- 4. circuit breaker: 6 consecutive blocked articles abort run ----
proc3 = WeChatArticleProcessor(settings, source="crawler")
calls = {'n': 0}
def blocked(self, article):
    calls['n'] += 1
    self.last_pdf_blocked = True
    return False
WeChatArticleProcessor._process_single_article = blocked
proc3._fetch_articles_from_crawler = lambda days=None: [{'dedup_key': f'k{i}'} for i in range(6)]
proc3._is_article_processed = lambda key: False
res = proc3.process_articles(days=None)
check("circuit breaker aborts after 5 (6th untouched)", res.failed_articles == 5 and calls['n'] == 5,
      f"failed={res.failed_articles} calls={calls['n']}")
check("abort message recorded", any('中止' in e for e in res.errors), f"errors={res.errors}")

print("=" * 50)
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
