"""
直接处理用户提供的微信文章URL
不依赖数据库，直接生成PDF
"""

import os
import sys
from playwright.sync_api import sync_playwright

def process_single_article(article_url, output_filename=None):
    """直接处理单个微信文章URL"""
    print("=" * 60)
    print("直接处理微信文章PDF生成")
    print("=" * 60)

    if not output_filename:
        # 从URL提取文章ID
        if '/s/' in article_url:
            article_id = article_url.split('/s/')[-1].split('?')[0]
            output_filename = f"wechat_{article_id}.pdf"
        else:
            output_filename = "wechat_article.pdf"

    print(f"\n[文章] URL: {article_url}")
    print(f"[输出] {output_filename}")

    try:
        print(f"\n[开始] 使用Playwright生成PDF...")

        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"[访问] 正在访问文章...")
            page.goto(article_url, wait_until='networkidle', timeout=60000)

            print(f"[等待] 等待图片和内容加载...")
            page.wait_for_timeout(5000)

            print(f"[生成] 正在生成PDF...")
            page.pdf(
                path=output_filename,
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )

            browser.close()

        # 验证生成的PDF
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            print(f"\n[SUCCESS] PDF生成成功!")
            print(f"  文件: {os.path.abspath(output_filename)}")
            print(f"  大小: {file_size:,} bytes ({file_size/1024:.2f} KB)")
            print(f"\n[提示] 您可以用Chrome/IE打开这个PDF文件")
            return True
        else:
            print(f"\n[FAIL] PDF文件未生成")
            return False

    except Exception as e:
        print(f"\n[ERROR] 处理失败: {e}")
        return False

if __name__ == "__main__":
    import sys

    # 您的文章URL
    your_article_url = "https://mp.weixin.qq.com/s/6LJvQrYki3OyIJFmKE9NhA"

    print("[使用方法]")
    print("1. 直接运行本脚本处理您的文章")
    print("2. 或者修改下面的your_article_url变量")
    print("3. 或者作为命令行参数传入")
    print()

    # 检查命令行参数
    if len(sys.argv) > 1:
        article_url = sys.argv[1]
    else:
        article_url = your_article_url
        print(f"[默认] 使用您的文章: {article_url}")

    success = process_single_article(article_url)

    print("\n" + "=" * 60)
    if success:
        print("[完成] PDF生成完成，请验证文件质量")
    else:
        print("[失败] 请检查网络连接或文章URL")
    print("=" * 60)