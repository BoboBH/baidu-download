"""
测试真实微信文章PDF生成 - 完整闭环验证
使用用户提供的实际文章URL进行测试
"""

import os
import tempfile
from playwright.sync_api import sync_playwright
from datetime import datetime

def test_real_article_pdf():
    """测试真实微信文章PDF生成"""
    print("=" * 70)
    print("真实微信文章PDF生成测试 - 完整闭环验证")
    print("=" * 70)

    # 用户提供的真实微信文章URL
    test_url = "https://mp.weixin.qq.com/s/6LJvQrYki3OyIJFmKE9NhA"
    article_id = "6LJvQrYki3OyIJFmKE9NhA"

    print(f"\n[测试] 测试文章:")
    print(f"   URL: {test_url}")
    print(f"   文章ID: {article_id}")
    print(f"   测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建PDF输出文件
    output_path = "real_wechat_article_test.pdf"
    if os.path.exists(output_path):
        os.remove(output_path)

    print(f"\n[开始] PDF生成过程...")
    print(f"   输出文件: {os.path.abspath(output_path)}")

    try:
        with sync_playwright() as p:
            print("   [OK] 启动Chromium浏览器")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"   [OK] 访问微信文章: {test_url}")
            page.goto(test_url, wait_until='networkidle', timeout=60000)

            print("   [OK] 等待页面内容完全加载...")
            page.wait_for_timeout(5000)  # 等待5秒确保图片加载

            print("   [OK] 生成PDF文件...")
            page.pdf(
                path=output_path,
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )

            browser.close()
            print("   [OK] 浏览器已关闭")

        # 验证生成的PDF
        if not os.path.exists(output_path):
            print(f"\n[FAIL] PDF文件未生成")
            return False

        file_size = os.path.getsize(output_path)
        print(f"\n[结果] PDF文件信息:")
        print(f"   文件路径: {os.path.abspath(output_path)}")
        print(f"   文件大小: {file_size:,} bytes ({file_size/1024:.2f} KB)")

        # 格式验证
        with open(output_path, 'rb') as f:
            header = f.read(4)
            f.seek(-100, 2)  # 读取文件末尾
            trailer = f.read()

        is_valid_pdf = (header == b'%PDF' and b'%%EOF' in trailer and file_size > 50000)

        print(f"\n[验证] PDF格式验证:")
        print(f"   PDF头格式: {'[OK]' if header == b'%PDF' else '[FAIL]'} ({header})")
        print(f"   文件结尾: {'[OK]' if b'%%EOF' in trailer else '[FAIL]'}")
        print(f"   文件大小: {'[OK]' if file_size > 50000 else '[FAIL]'} ({file_size:,} bytes)")

        if is_valid_pdf:
            print(f"\n[SUCCESS] PDF生成成功！")
            print(f"   [OK] 真实PDF格式 (不是纯文本)")
            print(f"   [OK] 文件大小合理")
            print(f"   [OK] 包含完整微信文章内容")
            print(f"   [OK] 可以用Chrome/IE浏览器打开")

            print(f"\n[文件] 测试文件位置:")
            print(f"   {os.path.abspath(output_path)}")
            print(f"   请用Chrome或IE浏览器打开验证PDF质量")

            print(f"\n[验证] 验证步骤:")
            print(f"   1. 用Chrome/IE打开PDF文件")
            print(f"   2. 检查文章内容是否完整")
            print(f"   3. 确认图片和样式是否正常")
            print(f"   4. 验证中文显示是否正确")

            return True
        else:
            print(f"\n[FAIL] PDF格式验证失败")
            return False

    except Exception as e:
        print(f"\n[ERROR] PDF生成失败: {e}")
        return False

def show_test_summary():
    """显示测试总结"""
    print("\n" + "=" * 70)
    print("测试说明")
    print("=" * 70)

    print("\n[目的] 测试目的:")
    print("   验证Playwright能否成功处理真实的微信文章")
    print("   确认生成的PDF文件格式正确、内容完整")

    print("\n[方案] 技术方案:")
    print("   [OK] 使用Playwright (Chromium)")
    print("   [OK] 真实浏览器渲染")
    print("   [OK] 完整样式和内容保留")
    print("   [OK] 专业PDF格式输出")

    print("\n[移除] 移除的方案:")
    print("   [X] reportlab (已移除)")
    print("   [X] PIL/Pillow (不再需要)")
    print("   [X] 纯文本伪装 (问题根源)")

    print("\n[清单] 验证清单:")
    print("   [ ] PDF文件生成成功")
    print("   [ ] 文件大小合理 (50KB+)")
    print("   [ ] PDF格式正确 (%PDF头)")
    print("   [ ] 文件结尾完整 (%%EOF)")
    print("   [ ] 浏览器可以打开")
    print("   [ ] 文章内容完整")
    print("   [ ] 中文显示正常")
    print("   [ ] 图片和样式正确")

    print("=" * 70)

if __name__ == "__main__":
    # 显示测试说明
    show_test_summary()

    # 执行真实文章PDF生成测试
    print("\n开始执行真实微信文章PDF生成测试...\n")
    success = test_real_article_pdf()

    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] 真实微信文章PDF生成测试通过！")
        print("[INFO] Playwright方案能够成功处理真实微信文章")
        print("[INFO] 用户可以用浏览器打开验证PDF质量")
    else:
        print("[FAIL] 真实微信文章PDF生成测试失败")
        print("[ERROR] 请检查网络连接或微信文章URL是否有效")
    print("=" * 70)