"""
验证PDF文件格式和质量
"""
import os

def verify_pdf_file(pdf_path):
    """验证PDF文件"""
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF文件不存在: {pdf_path}")
        return False

    size = os.path.getsize(pdf_path)
    print(f'PDF文件信息:')
    print(f'  路径: {os.path.abspath(pdf_path)}')
    print(f'  大小: {size} bytes ({size/1024:.2f} KB)')

    with open(pdf_path, 'rb') as f:
        header = f.read(4)
        f.seek(-100, 2)  # 读取文件末尾
        trailer = f.read()

    # 检查PDF格式
    header_valid = header == b'%PDF'
    trailer_valid = b'%%EOF' in trailer

    print(f'  PDF头: {header}')
    print(f'  格式验证: {"通过" if header_valid else "失败"}')
    print(f'  文件结尾检查: {"通过" if trailer_valid else "失败"}')

    if header_valid and trailer_valid and size > 10000:
        print(f'\n[SUCCESS] 这是真正的PDF文件，可以用Chrome/IE打开!')
        print(f'请用浏览器打开验证: {os.path.abspath(pdf_path)}')
        return True
    else:
        print(f'\n[ERROR] PDF文件可能有问题')
        return False

if __name__ == "__main__":
    pdf_path = 'test_playwright_sample.pdf'
    result = verify_pdf_file(pdf_path)
    print(f"\n最终结果: {'PASS' if result else 'FAIL'}")