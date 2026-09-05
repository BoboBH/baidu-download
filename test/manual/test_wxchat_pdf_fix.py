"""
测试wxchat PDF生成功能修复
验证浏览器路径动态检测是否正确工作
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.wxchat.processor import PDFGenerator
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_browser_path_detection():
    """测试浏览器路径检测逻辑"""
    print("=== 测试浏览器路径检测 ===")

    # 模拟不同的用户环境
    test_users = ['SZ02', 'bobo', 'Default']

    for test_user in test_users:
        print(f"\n测试用户: {test_user}")

        # 模拟环境变量
        os.environ['USERPROFILE'] = f'C:\\Users\\{test_user}'

        # 模拟路径检测逻辑
        user_profile = os.environ.get('USERPROFILE', 'C:\\Users\\Default')

        possible_paths = [
            # 当前用户的Playwright浏览器
            os.path.join(user_profile, 'AppData', 'Local', 'ms-playwright', 'chromium-1140', 'chrome-win', 'chrome.exe'),
            # 默认用户路径
            r"C:\Users\Default\AppData\Local\ms-playwright\chromium-1140\chrome-win\chrome.exe",
            # 系统程序路径中的Chrome（如果安装了）
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        print(f"  USERPROFILE: {user_profile}")
        print(f"  检测到的路径:")

        found_path = None
        for path in possible_paths:
            exists = os.path.exists(path)
            print(f"    {path}")
            print(f"      存在: {exists}")
            if exists and not found_path:
                found_path = path

        if found_path:
            print(f"  [OK] 找到浏览器: {found_path}")
        else:
            print(f"  [WARN] 未找到系统浏览器，将使用Playwright自带浏览器")

def test_pdf_generation_simple():
    """简单的PDF生成测试（使用真实文章ID）"""
    print("\n\n=== 测试PDF生成 ===")

    try:
        # 加载配置
        settings = Settings()
        logger.info(f"配置加载成功")

        # 创建PDF生成器
        pdf_gen = PDFGenerator(settings)
        logger.info(f"PDF生成器创建成功")

        # 测试文章ID（从错误日志中的真实文章）
        test_article_id = "uhco9Jp0sLbAlzYh_GMIiQ"

        # 创建临时输出路径
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"test_wxchat_{test_article_id}.pdf")

        print(f"测试文章ID: {test_article_id}")
        print(f"输出路径: {output_path}")

        # 生成PDF
        success = pdf_gen.generate_pdf(test_article_id, output_path)

        if success:
            file_size = os.path.getsize(output_path)
            print(f"[OK] PDF生成成功！文件大小: {file_size} bytes ({file_size/1024:.2f} KB)")
            print(f"文件路径: {output_path}")

            # 清理测试文件
            try:
                os.remove(output_path)
                print("测试文件已清理")
            except:
                print("测试文件清理失败，请手动删除")
        else:
            print(f"[FAIL] PDF生成失败")

        return success

    except Exception as e:
        logger.error(f"PDF生成测试异常: {e}")
        print(f"[FAIL] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("wxchat PDF生成功能修复测试")
    print("=" * 50)

    # 测试路径检测
    test_browser_path_detection()

    # 测试PDF生成（可选，需要网络和真实环境）
    print("\n是否要进行实际PDF生成测试？")
    print("注意：这会下载真实微信文章并生成PDF，需要网络连接")
    user_input = input("输入 'y' 继续，其他键跳过: ").strip().lower()

    if user_input == 'y':
        test_pdf_generation_simple()
    else:
        print("跳过实际PDF生成测试")

    print("\n" + "=" * 50)
    print("测试完成！")

if __name__ == "__main__":
    main()