"""
独立微信文章PDF生成器
不依赖数据库，可以直接处理单个文章URL
"""

import os
import sys
from playwright.sync_api import sync_playwright

def generate_single_pdf(article_url, output_pdf="single_article.pdf"):
    """
    生成单个微信文章PDF

    Args:
        article_url: 微信文章URL，如 https://mp.weixin.qq.com/s/XXXXXX
        output_pdf: 输出PDF文件名
    """
    print("=" * 60)
    print("独立微信文章PDF生成器")
    print("=" * 60)

    print(f"\n文章URL: {article_url}")
    print(f"输出PDF: {output_pdf}")

    try:
        print(f"\n[1/4] 启动Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"[2/4] 访问文章页面...")
            page.goto(article_url, wait_until='networkidle', timeout=60000)

            print(f"[3/4] 等待内容加载...")
            page.wait_for_timeout(5000)

            print(f"[4/4] 生成PDF文件...")
            page.pdf(
                path=output_pdf,
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )

            browser.close()

        # 验证结果
        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"\n[SUCCESS] PDF生成成功!")
            print(f"  文件: {os.path.abspath(output_pdf)}")
            print(f"  大小: {file_size:,} bytes ({file_size/1024:.2f} KB)")
            print(f"\n请用Chrome/IE打开验证PDF质量")
            return True
        else:
            print(f"\n[FAIL] PDF文件未生成")
            return False

    except Exception as e:
        print(f"\n[ERROR] 处理失败: {e}")
        return False

if __name__ == "__main__":
    # 您的文章URL
    your_url = "https://mp.weixin.qq.com/s/6LJvQrYki3OyIJFmKE9NhA"

    # 支持命令行参数
    if len(sys.argv) > 1:
        url = sys.argv[1]
        if len(sys.argv) > 2:
            output = sys.argv[2]
        else:
            # 从URL生成文件名
            article_id = url.split('/s/')[-1].split('?')[0]
            output = f"{article_id}.pdf"
    else:
        url = your_url
        output = "6LJvQrYki3OyIJFmKE9NhA.pdf"

    print("[用法]")
    print(f"python {os.path.basename(__file__)} <文章URL> [输出文件名]")
    print(f"示例: python {os.path.basename(__file__)} {your_url}")
    print()

    success = generate_single_pdf(url, output)

    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] PDF生成完成，请验证文件质量")
    else:
        print("[FAIL] 请检查网络连接或文章URL")
    print("=" * 60)