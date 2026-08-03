"""
测试用户提供的真实文章 - 使用exe环境中的Playwright
"""

import os
import sys

# 模拟wxchat配置
class MockConfig:
    wxchat_base_url = 'https://mp.weixin.qq.com/s/'
    wxchat_pdf_timeout = 60
    wxchat_image_wait_time = 5
    wxchat_download_delay = 3

def test_real_article():
    """测试真实文章PDF生成"""
    print("=" * 60)
    print("测试真实文章PDF生成")
    print("=" * 60)

    try:
        # 导入处理器
        sys.path.insert(0, 'd:/git/baidu-download')
        from src.wxchat.processor import PDFGenerator

        config = MockConfig()
        generator = PDFGenerator(config)

        # 用户提供的文章ID
        article_id = "6LJvQrYki3OyIJFmKE9NhA"
        output_pdf = "test_user_article_final.pdf"

        print(f"\n[测试] 文章ID: {article_id}")
        print(f"[输出] {os.path.abspath(output_pdf)}")

        # 生成PDF
        print(f"\n[开始] PDF生成...")
        result = generator.generate_pdf(article_id, output_pdf)

        if result and os.path.exists(output_pdf):
            size = os.path.getsize(output_pdf)
            print(f"\n[SUCCESS] PDF生成成功!")
            print(f"  文件大小: {size:,} bytes ({size/1024:.2f} KB)")
            print(f"  文件位置: {os.path.abspath(output_pdf)}")
            print(f"\n[验证] 请用Chrome/IE打开验证PDF质量")
            return True
        else:
            print(f"\n[FAIL] PDF生成失败")
            return False

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_article()
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] 真实文章PDF生成测试通过!")
        print("[INFO] 您可以用浏览器打开PDF验证质量")
    else:
        print("[FAIL] 测试失败，请检查配置")
    print("=" * 60)