"""
测试exe文件中的PDF生成功能（包含PIL支持）
"""
import sys
import os
from datetime import datetime

def test_pdf_generation():
    """测试PDF生成功能"""
    print("=" * 60)
    print("测试PDF生成功能（包含PIL支持）")
    print("=" * 60)

    # 测试PIL导入
    print("\n[1/4] 测试PIL导入...")
    try:
        import PIL
        print(f"  [OK] PIL版本: {PIL.__version__}")
    except ImportError as e:
        print(f"  [FAIL] PIL导入失败: {e}")
        return False

    # 测试PIL.Image导入
    print("\n[2/4] 测试PIL.Image导入...")
    try:
        from PIL import Image
        print(f"  [OK] PIL.Image导入成功")
    except ImportError as e:
        print(f"  [FAIL] PIL.Image导入失败: {e}")
        return False

    # 测试reportlab导入
    print("\n[3/4] 测试reportlab导入...")
    try:
        import reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        print(f"  [OK] reportlab版本: {reportlab.__version__}")
        print(f"  [OK] reportlab PDF模块导入成功")
    except ImportError as e:
        print(f"  [FAIL] reportlab导入失败: {e}")
        return False

    # 测试实际PDF生成
    print("\n[4/4] 测试实际PDF生成...")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm

        # 创建测试PDF
        test_pdf_path = "test_pil_support.pdf"
        c = canvas.Canvas(test_pdf_path, pagesize=A4)
        width, height = A4

        # 添加测试内容
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height-2*cm, "PIL Support Test - PDF Generation")

        c.setFont("Helvetica", 12)
        c.drawString(2*cm, height-4*cm, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(2*cm, height-5*cm, "PIL/Pillow: OK")
        c.drawString(2*cm, height-6*cm, "reportlab: OK")
        c.drawString(2*cm, height-7*cm, "PDF Generation: SUCCESS")

        c.save()

        # 验证文件
        if os.path.exists(test_pdf_path):
            file_size = os.path.getsize(test_pdf_path)
            with open(test_pdf_path, 'rb') as f:
                header = f.read(4)

            is_valid = (header == b'%PDF' and file_size > 1000)
            print(f"  [OK] PDF文件生成成功")
            print(f"  [OK] 文件大小: {file_size} bytes")
            print(f"  [OK] PDF头: {header}")
            print(f"  [OK] 格式验证: {'PASS' if is_valid else 'FAIL'}")

            if is_valid:
                print(f"\n[SUCCESS] PIL支持测试完全通过！")
                print(f"测试PDF文件: {os.path.abspath(test_pdf_path)}")
                return True
            else:
                print(f"\n[FAIL] PDF格式验证失败")
                return False
        else:
            print(f"  [FAIL] PDF文件未生成")
            return False

    except Exception as e:
        print(f"  [FAIL] PDF生成失败: {e}")
        return False

if __name__ == "__main__":
    success = test_pdf_generation()
    print("\n" + "=" * 60)
    if success:
        print("PIL支持测试通过 - exe文件包含完整的PDF生成功能")
    else:
        print("PIL支持测试失败 - 请检查打包配置")
    print("=" * 60)
    sys.exit(0 if success else 1)