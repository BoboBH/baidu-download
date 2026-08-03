"""
快速测试Playwright浏览器是否安装
"""

import sys
import subprocess

def check_and_install_playwright():
    """检查并安装Playwright浏览器"""

    print("=" * 60)
    print("Playwright浏览器检查工具")
    print("=" * 60)

    # 1. 检查playwright是否安装
    try:
        import playwright
        print("[OK] Playwright已安装")
    except ImportError:
        print("[FAIL] Playwright未安装")
        print("请运行: pip install playwright")
        return False

    # 2. 检查浏览器是否可用
    try:
        from playwright.sync_api import sync_playwright
        print("[OK] Playwright模块导入成功")

        # 尝试启动浏览器
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            print("[OK] Playwright浏览器已就绪")
            print("=" * 60)
            print("[SUCCESS] Playwright完全可用！")
            return True
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                print("[WARN] Playwright浏览器未安装")
                print("正在自动安装浏览器...")
                print("这可能需要几分钟时间...")

                try:
                    result = subprocess.run(
                        ['playwright', 'install', 'chromium'],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )

                    if result.returncode == 0:
                        print("[OK] Playwright浏览器安装成功")

                        # 验证安装
                        try:
                            with sync_playwright() as p:
                                browser = p.chromium.launch(headless=True)
                                browser.close()
                            print("[OK] 浏览器验证成功")
                            print("=" * 60)
                            print("[SUCCESS] Playwright安装完成！")
                            return True
                        except:
                            print("[WARN] 浏览器验证失败")
                    else:
                        print(f"[FAIL] 安装失败: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    print("[FAIL] 安装超时")
                    return False
                except Exception as install_error:
                    print(f"[FAIL] 安装异常: {install_error}")
                    return False
            else:
                print(f"[FAIL] 浏览器检查失败: {e}")
                return False

    except Exception as e:
        print(f"[FAIL] Playwright导入失败: {e}")
        return False

if __name__ == "__main__":
    success = check_and_install_playwright()

    if success:
        print("\n现在可以正常使用:")
        print("  python main.py --wxchat")
        print("  baidu-download.exe --wxchat")
    else:
        print("\n请手动安装:")
        print("  pip install playwright")
        print("  playwright install chromium")

    sys.exit(0 if success else 1)