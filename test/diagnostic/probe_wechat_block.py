"""Probe what page WeChat actually serves to Playwright under various launch configs. UTF-8 output."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright

URL = 'https://mp.weixin.qq.com/s?__biz=MzE5OTEwMDEwNQ==&mid=2247489542&idx=2&sn=94c4ec7b89574161ffcf4d2006b40b30'
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

configs = [
    # (name, launch_kwargs, headful)
    ("A: chrome-headless-stealth", dict(channel="chrome", headless=True,
                                        args=["--disable-blink-features=AutomationControlled"],
                                        ignore_default_args=["--enable-automation"]), False),
    ("B: chrome-headful-stealth", dict(channel="chrome", headless=False,
                                       args=["--disable-blink-features=AutomationControlled"],
                                       ignore_default_args=["--enable-automation"]), True),
    ("C: edge-headless-stealth", dict(channel="msedge", headless=True,
                                      args=["--disable-blink-features=AutomationControlled"],
                                      ignore_default_args=["--enable-automation"]), False),
]

shot_dir = project_root / "output" / "test_crawler_wxchat"
shot_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    for name, kwargs, headful in configs:
        print("=" * 70)
        print(f"[{name}]")
        try:
            browser = p.chromium.launch(**kwargs)
        except Exception as e:
            print(f"  LAUNCH FAILED: {e}")
            continue
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 900})
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)  # 给跳转/验证流一点时间
            title = page.title()
            wd = page.evaluate("navigator.webdriver")
            ua_seen = page.evaluate("navigator.userAgent")
            text = page.evaluate("document.body ? document.body.innerText.slice(0, 300) : '<no body>'")
            print(f"  title: {title}")
            print(f"  navigator.webdriver: {wd}")
            print(f"  UA seen by page: {ua_seen[:80]}")
            print(f"  body text: {text[:260]}")
            slug = name.split(":")[0].strip().lower()
            page.screenshot(path=str(shot_dir / f"probe_{slug}.png"), full_page=False)
            print(f"  screenshot: {shot_dir / f'probe_{slug}.png'}")
        except Exception as e:
            print(f"  NAV ERROR: {e}")
        finally:
            browser.close()
print("=" * 70)
print("probe done")
