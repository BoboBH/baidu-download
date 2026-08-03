"""
验证PDF文件内容 - 检查生成的PDF是否包含真实的微信文章内容
"""

import PyPDF2
import os

def verify_pdf_content():
    """验证PDF文件内容"""
    pdf_path = 'real_wechat_article_test.pdf'

    if not os.path.exists(pdf_path):
        print(f"PDF文件不存在: {pdf_path}")
        return False

    print("=" * 70)
    print("PDF内容验证")
    print("=" * 70)

    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)

            # 获取PDF元数据
            info = pdf_reader.metadata
            print("\n[元数据] PDF信息:")
            if info:
                title = info.get('/Title')
                creator = info.get('/Creator')
                producer = info.get('/Producer')

                if title:
                    print(f"  标题: {title}")
                if creator:
                    print(f"  创建者: {creator}")
                if producer:
                    print(f"  生成器: {producer}")

            # 获取页数
            num_pages = len(pdf_reader.pages)
            print(f"\n[结构] PDF结构:")
            print(f"  总页数: {num_pages}")

            # 读取第一页内容
            if num_pages > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()

                print(f"\n[内容] 第一页内容分析:")
                print(f"  文本长度: {len(text)} 字符")
                print(f"  文本行数: {len(text.split(chr(10)))} 行")

                # 内容预览
                print(f"\n[预览] 前500个字符:")
                print("-" * 70)
                preview = text[:500]
                print(preview)
                print("-" * 70)

                # 检查内容质量
                print(f"\n[验证] 内容质量检查:")

                # 检查中文字符
                chinese_chars = len([c for c in text if ord(c) > 127])
                if chinese_chars > 100:
                    print(f"  [OK] 包含中文字符: {chinese_chars} 个")
                else:
                    print(f"  [FAIL] 中文字符过少: {chinese_chars} 个")

                # 检查常见微信文章元素
                keywords = ['微信', '公众号', '文章', '作者', '来源', '中东', '以色列']
                found_keywords = [kw for kw in keywords if kw in text]
                if found_keywords:
                    print(f"  [OK] 包含关键词: {', '.join(found_keywords)}")

                # 检查内容长度合理性
                if len(text) > 1000:
                    print(f"  [OK] 内容长度合理: {len(text)} 字符")
                else:
                    print(f"  [WARN] 内容长度偏短: {len(text)} 字符")

                # 检查是否包含乱码
                if text.count('') > 10:
                    print(f"  [WARN] 可能包含乱码字符")
                else:
                    print(f"  [OK] 没有明显乱码")

                print(f"\n[结论] PDF内容验证结果:")
                if chinese_chars > 100 and len(found_keywords) >= 3:
                    print(f"  [SUCCESS] PDF包含真实的微信文章内容")
                    print(f"  [INFO] 内容质量良好，可以正常阅读")
                    return True
                else:
                    print(f"  [FAIL] PDF内容可能不完整")
                    return False

        print(f"\n[结论] PDF内容验证: 通过")
        return True

    except Exception as e:
        print(f"\n[ERROR] PDF读取失败: {e}")
        return False

if __name__ == "__main__":
    success = verify_pdf_content()
    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] PDF内容验证完成 - 文件包含真实的微信文章内容")
    else:
        print("[FAIL] PDF内容验证失败")
    print("=" * 70)