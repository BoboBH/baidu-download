"""
测试Playwright PDF生成功能
"""

import tempfile
import os
from playwright.sync_api import sync_playwright

def test_pdf_generation():
    """测试基本的PDF生成功能"""
    print("开始测试Playwright PDF生成...")

    # 创建临时PDF文件
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        output_path = tmp_file.name

    try:
        print(f"正在生成PDF到: {output_path}")

        with sync_playwright() as p:
            print("启动Chromium浏览器...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("访问测试页面...")
            # 使用一个简单的测试页面
            page.goto("https://example.com", wait_until='networkidle')

            print("等待页面加载完成...")
            page.wait_for_timeout(2000)

            print("生成PDF...")
            page.pdf(
                path=output_path,
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )

            browser.close()
            print("浏览器已关闭")

        # 检查生成的文件
        file_size = os.path.getsize(output_path)
        print(f"[SUCCESS] PDF生成成功！")
        print(f"   文件路径: {output_path}")
        print(f"   文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")

        # 验证PDF文件格式
        with open(output_path, 'rb') as f:
            header = f.read(4)
            if header == b'%PDF':
                print("[SUCCESS] PDF文件格式验证通过！")
                print(f"[SUCCESS] 文件可以用浏览器打开: {output_path}")

                # 复制到项目目录供用户验证
                import shutil
                project_file = "d:/git/baidu-download/test_playwright_sample.pdf"
                shutil.copy(output_path, project_file)
                print(f"[INFO] 已复制文件到项目目录: {project_file}")
                print("你可以用Chrome或IE打开这个文件验证PDF格式")

                return True
            else:
                print(f"[ERROR] PDF文件格式错误: {header}")
                return False

    except Exception as e:
        print(f"[ERROR] PDF生成失败: {e}")
        return False

if __name__ == "__main__":
    success = test_pdf_generation()
    if success:
        print("\n[SUCCESS] Playwright PDF生成测试成功！")
    else:
        print("\n[ERROR] Playwright PDF生成测试失败！")