"""回归：wewe 源单篇走完整管道（ adaptations 后的 wewe 分支）+ 双SFTP + new_wx_article 状态写入。ASCII output only."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from src.config.settings import Settings
from src.wxchat.processor import WeChatArticleProcessor

settings = Settings()
proc = WeChatArticleProcessor(settings)  # wewe source, default

end_date = datetime.now()
start_date = end_date - timedelta(days=30)
arts = proc._fetch_articles_from_wewe(start_date, end_date)
unprocessed = [a for a in arts if not proc._is_article_processed(a.get('id'))]
print(f"wewe window 30d: total={len(arts)} unprocessed={len(unprocessed)}")
assert unprocessed, "no unprocessed wewe article to test"

article = unprocessed[0]
print(f"target: id={article.get('id')}")
print(f"  title      : {article.get('title')}")
print(f"  mp_id      : {article.get('mp_id')}")
print(f"  publish_time: {article.get('publish_time')}")

ok = proc._process_single_article(article)
print(f"RESULT: {'OK' if ok else 'FAILED'}")

# 查状态行
import pymysql
conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                       password=settings.db_password, database=settings.db_name, charset='utf8mb4')
with conn.cursor() as cur:
    cur.execute("SELECT article_id, processed_at, error_message FROM new_wx_article WHERE article_id=%s",
                (article.get('id'),))
    row = cur.fetchone()
conn.close()
print(f"DB new_wx_article: processed_at={row[1]} error={row[2]}")
sys.exit(0 if ok else 1)
