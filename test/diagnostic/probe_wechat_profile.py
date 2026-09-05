"""Probe E: same persistent profile, headless vs headful article visit. UTF-8 output."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.config.settings import Settings
from src.wxchat.processor import PDFGenerator

ARTICLE = 'https://mp.weixin.qq.com/s?__biz=MzE5OTEwMDEwNQ==&mid=2247489542&idx=2&sn=94c4ec7b89574161ffcf4d2006b40b30'

settings = Settings()
gen = PDFGenerator(settings)

with sync_playwright() as p:
    # ---- 1) 无头 + 档案 ----
    ctx = gen._launch_stealth_browser(p)  # headless
    names = [c['name'] for c in ctx.cookies()]
    print(f"[headless] profile cookies ({len(names)}): {names}")
    page = ctx.new_page()
    page.goto(ARTICLE, wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(5000)
    body = page.evaluate("document.body ? document.body.innerText : ''")
    print(f"[headless] rich_media_content={page.query_selector('div.rich_media_content') is not None} "
          f"blocked={'环境异常' in body}")
    ctx.close()

    # ---- 2) 有头 + 同一档案 ----
    ctx2 = gen._launch_stealth_browser(p, headful=True)
    page2 = ctx2.new_page()
    page2.goto(ARTICLE, wait_until='domcontentloaded', timeout=45000)
    page2.wait_for_timeout(5000)
    body2 = page2.evaluate("document.body ? document.body.innerText : ''")
    print(f"[headful ] rich_media_content={page2.query_selector('div.rich_media_content') is not None} "
          f"blocked={'环境异常' in body2}")
    ctx2.close()
print("probe E done")
