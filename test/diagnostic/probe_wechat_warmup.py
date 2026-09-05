"""Probe D: warm-up homepage visit first (seed cookies into persistent profile), then article. UTF-8 output."""
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
    context = gen._launch_stealth_browser(p)  # 无头 + 持久档案 + 拟真参数
    page = context.new_page()

    print("[1] warm-up: visit mp.weixin.qq.com homepage...")
    page.goto('https://mp.weixin.qq.com/', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(4000)
    cookies = context.cookies()
    print(f"    cookies after homepage: {len(cookies)} -> {[c['name'] for c in cookies][:10]}")

    print("[2] visit article with seeded cookies...")
    page.goto(ARTICLE, wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(6000)
    body = page.evaluate("document.body ? document.body.innerText : ''")
    has_article = page.query_selector('div.rich_media_content') is not None
    print(f"    title: {page.title()[:60]}")
    print(f"    rich_media_content: {has_article}")
    print(f"    blocked: {'环境异常' in body}")
    print(f"    body head: {body[:150]!r}")
    page.screenshot(path=str(project_root / 'output' / 'test_crawler_wxchat' / 'probe_d_warmup.png'))
    context.close()
print("probe D done")
