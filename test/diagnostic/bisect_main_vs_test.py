# -*- coding: utf-8 -*-
"""
二分定位 main.py 与测试脚本的行为差异（2026-09-05）

背景：main.py 运行必被微信拦，测试脚本/探针必通过，处理代码同一条路径。
main.py 独有步骤 = ensure_playwright_browsers()（裸 chromium launch+close 预检）。

本脚本在同一进程内逐轮开关各环节，全部走真实的 PDFGenerator 流程：
  Round C0: 无预检（对照组，= 测试脚本环境）
  Round A : 仅 driver start/stop（with sync_playwright()，不启浏览器）
  Round B : driver start/stop + 裸 chromium launch/close（= main.py 完整预检）
  Round C1: 再次无预检（确认时间漂移）

每轮都用 _generate_pdf_with_playwright 真实流程访问同一篇文章。
输出 PASS(真实PDF) / BLOCK(拦截页) 逐轮对照。
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from playwright.sync_api import sync_playwright

from src.config.settings import Settings
from src.wxchat.processor import PDFGenerator

# 文章30（中金中报业绩总结）——main.py 10:58 被拦 / 探针 11:00 通过，状态未知，适合做对照
URL = ('https://mp.weixin.qq.com/s?__biz=MzI3MDMzMjg0MA=='
       '&mid=2247857036&idx=3&sn=882e842861d25422da64dee22472fd3a')
# 文章110（冠南固收，短链）——今天多次成功，已知干净
URL_CLEAN = 'https://mp.weixin.qq.com/s/10vhWjQ6-Fh3na5RfyfIDg'

# 命令行第1个参数可指定URL（默认测文章30）
if len(sys.argv) > 1:
    URL = sys.argv[1]
    print(f"[参数] 使用指定URL: {URL[:70]}...")


def round_bare_launch_only():
    """完整复刻 main.py ensure_playwright_browsers：driver start/stop + 裸 chromium"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
    print("  [预检] 裸 chromium launch+close 完成（=main.py）")


def round_driver_only():
    """只做 driver start/stop，不启动任何浏览器"""
    with sync_playwright():
        pass
    print("  [预检] 仅 driver start/stop 完成")


def run_processor_flow(tag: str):
    """真实处理器流程访问文章，返回 PASS/BLOCK + 证据"""
    gen = PDFGenerator(Settings())
    gen.image_wait_time = 2  # 缩短图片等待，加快实验节奏（不影响拦截判定，拦截在前5秒）
    tmp = os.path.join(tempfile.gettempdir(), f"bisect_{tag}.pdf")
    try:
        ok = gen._generate_pdf_with_playwright(URL, tmp)
        if ok and os.path.exists(tmp):
            size = os.path.getsize(tmp)
            print(f"  [结果] PASS — 真实PDF {size/1024:.0f} KB")
        elif getattr(gen, 'last_page_blocked', False):
            print(f"  [结果] BLOCK — 微信拦截页（早期检测命中）")
        else:
            print(f"  [结果] FAIL(非拦截) — ok={ok}, blocked={getattr(gen, 'last_page_blocked', None)}")
    finally:
        gen.close_browser()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


if __name__ == '__main__':
    print("=" * 60)
    print("二分实验：定位 main.py 独有步骤是否为拦截诱因")
    print(f"目标URL: {URL[:80]}...")
    print("=" * 60)

    rounds = [
        ("C0 对照(无预检)", None),
    ]
    if os.getenv('BISECT_FULL'):
        rounds += [
            ("A 仅driver", round_driver_only),
            ("B 完整预检(裸chromium)", round_bare_launch_only),
            ("C1 对照(无预检)", None),
        ]
    for tag, pre in rounds:
        print("-" * 60)
        print(f"▶ Round {tag}")
        if pre:
            try:
                pre()
            except Exception as e:
                print(f"  [预检失败] {e}")
        run_processor_flow(tag.split()[0])
    print("=" * 60)
    print("实验结束。若 B 轮 BLOCK 而 C 轮 PASS → 裸chromium预检是诱因")
