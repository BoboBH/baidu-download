# 微信文章PDF生成解决方案

## 问题分析
当前实现存在严重问题：生成的"PDF"文件实际上是纯文本文件，无法用PDF阅读器打开。

## 真正的PDF生成方案

### 方案1: 使用reportlab (推荐)
```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_real_pdf(article_id, url, title, content, output_path):
    """生成真正的PDF文件"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    import os

    # 创建PDF画布
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 设置字体（需要支持中文）
    # 注册中文字体
    # pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))

    # 标题
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height-2*cm, f"WeChat Article: {title}")

    # 文章信息
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height-4*cm, f"Article ID: {article_id}")
    c.drawString(2*cm, height-5*cm, f"URL: {url}")

    # 正文内容
    c.setFont("Helvetica", 9)
    text_y = height-7*cm
    for line in content.split('\n'):
        if text_y < 2*cm:  # 换页
            c.showPage()
            text_y = height-2*cm
        c.drawString(2*cm, text_y, line[:100])  # 限制行长度
        text_y -= 0.5*cm

    c.save()
    return True
```

### 方案2: 使用playwright (完美方案)
```python
from playwright.sync_api import sync_playwright

def generate_pdf_with_playwright(article_id, url, output_path):
    """使用Playwright生成完美PDF"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 访问文章页面
        page.goto(url, wait_until='networkidle')

        # 等待图片加载
        page.wait_for_timeout(5000)

        # 生成真正的PDF
        page.pdf(
            path=output_path,
            format='A4',
            print_background=True,
            margin={'top': '1cm', 'right': '1cm',
                   'bottom': '1cm', 'left': '1cm'}
        )

        browser.close()
        return True
```

### 方案3: 使用weasyprint (HTML转PDF)
```python
from weasyprint import HTML

def generate_pdf_from_html(html_content, output_path):
    """从HTML生成PDF"""
    HTML(string=html_content).write_pdf(output_path)
    return True
```

## 实施建议

1. **立即方案**: 安装并使用reportlab
   ```bash
   pip install reportlab
   ```

2. **长期方案**: 使用playwright生成完美PDF
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **中文字体支持**:
   - 需要下载中文字体文件
   - 配置字体路径
   - 测试中文显示效果

## 当前代码修复

需要替换 `_generate_comprehensive_pdf` 和 `_generate_fallback_pdf` 方法，
使用真正的PDF生成库替代当前的文本生成逻辑。