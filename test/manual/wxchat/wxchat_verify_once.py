"""一次性微信验证：弹出有头浏览器，人工完成"环境异常"验证后cookie存入持久档案。

之后 --wxchat / --crawler-wxchat 的无头浏览器复用该档案即可免验证。
用法: python test/manual/wxchat/wxchat_verify_once.py [--url <文章链接>]
"""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from src.config.settings import Settings
from src.wxchat.processor import PDFGenerator

DEFAULT_URL = 'https://mp.weixin.qq.com/s?__biz=MzE5OTEwMDEwNQ==&mid=2247489542&idx=2&sn=94c4ec7b89574161ffcf4d2006b40b30'

url = DEFAULT_URL
if '--url' in sys.argv:
    url = sys.argv[sys.argv.index('--url') + 1]

settings = Settings()
gen = PDFGenerator(settings)

print("=" * 60)
print("微信反爬一次性验证")
print(f"  验证用URL: {url[:80]}")
print(f"  持久档案: {settings.wxchat_browser_profile}")
print("-" * 60)
print("即将弹出浏览器窗口，请在窗口内完成『环境异常』验证")
print("(点击『去验证』并通过滑块/题目)。通过后本脚本自动检测并退出。")
print("=" * 60)

TIMEOUT_SECONDS = 300
with sync_playwright() as p:
    context = gen._launch_stealth_browser(p, headful=True)
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    start = time.time()
    passed = False
    while time.time() - start < TIMEOUT_SECONDS:
        try:
            body = page.evaluate("document.body ? document.body.innerText : ''")
            has_article = page.query_selector('div.rich_media_content') is not None
            blocked = ('环境异常' in (body or '')) or ('完成验证' in (body or ''))
            if has_article and not blocked:
                passed = True
                break
            if blocked:
                print(f"[{time.strftime('%H:%M:%S')}] 当前仍是验证页，请在浏览器窗口完成验证...")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 页面标题: {page.title()[:50]} (等待文章内容渲染...)")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 检测异常(页面可能在跳转): {e}")
        page.wait_for_timeout(3000)

    context.close()

print("=" * 60)
if passed:
    print("✅ 验证通过！cookie 已写入持久档案，后续批量处理可复用。")
    sys.exit(0)
print(f"❌ {TIMEOUT_SECONDS} 秒内未检测到验证通过，请重试。")
sys.exit(1)
