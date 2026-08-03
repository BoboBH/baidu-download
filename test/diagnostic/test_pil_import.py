"""
测试exe文件中是否包含PIL/Pillow库
"""
import sys

def test_pil_import():
    """测试PIL导入"""
    print("开始测试PIL/Pillow模块导入...")

    try:
        import PIL
        print(f"[OK] PIL模块导入成功: {PIL.__version__}")
    except ImportError as e:
        print(f"[FAIL] PIL模块导入失败: {e}")
        return False

    try:
        from PIL import Image
        print(f"[OK] PIL.Image导入成功")
    except ImportError as e:
        print(f"[FAIL] PIL.Image导入失败: {e}")
        return False

    try:
        import reportlab
        print(f"[OK] reportlab模块导入成功: {reportlab.__version__}")
    except ImportError as e:
        print(f"[FAIL] reportlab模块导入失败: {e}")
        return False

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        print(f"[OK] reportlab PDF模块导入成功")
    except ImportError as e:
        print(f"[FAIL] reportlab PDF模块导入失败: {e}")
        return False

    try:
        import playwright
        print(f"[OK] playwright模块导入成功")
    except ImportError as e:
        print(f"[FAIL] playwright模块导入失败: {e}")
        return False

    print("\n[SUCCESS] 所有PDF生成相关模块导入成功！")
    return True

if __name__ == "__main__":
    success = test_pil_import()
    sys.exit(0 if success else 1)