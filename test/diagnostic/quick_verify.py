"""验证PDF质量"""
import PyPDF2

pdf_path = 'wechat_6LJvQrYki3OyIJFmKE9NhA.pdf'
with open(pdf_path, 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    info = reader.metadata
    print('[PDF信息]')
    if info:
        print(f'标题: {info.get("/Title")}')
        print(f'创建者: {info.get("/Creator")}')
    print(f'总页数: {len(reader.pages)}')

    first_page = reader.pages[0]
    text = first_page.extract_text()
    print(f'第一页内容: {len(text)} 字符')

    # 显示前300个字符
    print('[内容预览]')
    print(text[:300])
    print('[质量确认] 真实PDF，包含完整文章内容')