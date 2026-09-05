"""清理假PDF：SFTP上<100KB的成功记录 → 删除两端假文件 + 状态行重置为待处理。ASCII output only."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import pymysql
import paramiko
from src.config.settings import Settings

settings = Settings()
HOST, PORT, USER, PWD = settings.sftp_host, settings.sftp_port, settings.sftp_username, settings.sftp_password

t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PWD)
sftp = paramiko.SFTPClient.from_transport(t)

def external_path(main_rel):
    return main_rel.replace(settings.wxchat_sftp_remote_path, settings.wxchat_external_sftp_folder, 1)

conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                       password=settings.db_password, database=settings.db_name, charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

def clean(table, key_col):
    """扫描表中成功记录，删除假PDF文件并重置状态行，返回处理数"""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {key_col} AS k, title, pdf_url FROM {table} WHERE processed_at IS NOT NULL AND pdf_url IS NOT NULL")
        rows = cur.fetchall()
    n = 0
    for r in rows:
        try:
            size = sftp.stat(r['pdf_url']).st_size
        except FileNotFoundError:
            print(f"  [SKIP] main file missing: {r['pdf_url']}")
            continue
        if size >= 100 * 1024:
            continue
        kb = size // 1024
        ext = external_path(r['pdf_url'])
        print(f"  [FAKE {kb} KB] {r['title'][:40]}")
        # 删除主SFTP与外部SFTP上的假文件
        try:
            sftp.remove(r['pdf_url'])
            print(f"    removed main   : {r['pdf_url']}")
        except FileNotFoundError:
            print(f"    main already gone")
        try:
            sftp.remove(ext)
            print(f"    removed external: {ext}")
        except FileNotFoundError:
            print(f"    external already gone")
        # 重置状态行：待重试、无错误、无退避（下次运行立即扫描）
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {table} SET processed_at=NULL, pdf_url=NULL, error_message=NULL, retry_count=0 "
                        f"WHERE {key_col}=%s", (r['k'],))
        conn.commit()
        n += 1
    return n

print("== crawler_wx_article ==")
n1 = clean('crawler_wx_article', 'article_key')
print(f"reset {n1} crawler rows")
print("== new_wx_article ==")
n2 = clean('new_wx_article', 'article_id')
print(f"reset {n2} wewe rows")

sftp.close(); t.close(); conn.close()
print(f"DONE: {n1 + n2} fake records cleaned")
