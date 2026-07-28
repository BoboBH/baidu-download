# 微信公众号文章处理 - 技术方案分析

## 🔍 wewe-rss API分析

### 基于wewe-rss的获取方式

**1. wewe-rss REST API（推荐）**
- wewe-rss通常提供REST API接口
- 可以获取订阅的公众号列表和文章列表
- 支持按时间范围、公众号筛选

**预期API端点：**
```
GET /api/accounts          # 获取订阅的公众号列表
GET /api/articles          # 获取文章列表
GET /api/articles/:id       # 获取单篇文章详情
```

**2. 数据库直接访问（备选）**
- wewe-rss使用SQLite数据库存储文章
- 可以直接查询数据库获取文章
- 需要了解wewe-rss的数据库schema

---

## 🖨️ HTML转PDF技术方案

### 方案对比分析

#### 方案1: wkhtmltopdf（推荐）

**优点：**
- ✅ 支持复杂的HTML和CSS
- ✅ 渲染效果好，接近浏览器显示
- ✅ 支持JavaScript执行
- ✅ 可以处理微信公众号的富文本
- ✅ 开源免费

**缺点：**
- ⚠️ 需要安装外部依赖
- ⚠️ 相对较慢（但质量好）

**使用示例：**
```python
import subprocess

def html_to_pdf(html_content, output_path):
    # 将HTML写入临时文件
    with open('temp.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 转换为PDF
    cmd = f'wkhtmltopdf temp.html {output_path}'
    subprocess.run(cmd, shell=True, check=True)
```

#### 方案2: Playwright + PDF

**优点：**
- ✅ 真实浏览器渲染
- ✅ 支持复杂的动态内容
- ✅ 可以执行JavaScript
- ✅ 支持截图和PDF导出

**缺点：**
- ⚠️ 依赖较大（需要浏览器）
- ⚠️ 资源消耗较多

**使用示例：**
```python
from playwright.sync_api import sync_playwright

def html_to_pdf_playwright(url, output_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.pdf(path=output_path)
        browser.close()
```

#### 方案3: WeasyPrint

**优点：**
- ✅ 纯Python实现
- ✅ 支持CSS3
- ✅ 不需要外部依赖

**缺点：**
- ⚠️ 对复杂HTML支持有限
- ⚠️ 渲染效果可能不如浏览器

#### 方案4: Headless Chrome

**优点：**
- ✅ Chrome真实渲染
- ✅ 支持最新的Web标准
- ✅ 可以处理动态内容

**缺点：**
- ⚠️ 需要安装Chrome
- ⚠️ 资源占用较大

---

## 🎯 推荐技术方案

### 方案选择：wkhtmltopdf（主要） + Playwright（备用）

**主要使用 wkhtmltopdf 的原因：**
1. **质量优先** - 微信公众号文章排版复杂，需要高质量渲染
2. **成本可控** - 相对轻量，易于部署
3. **稳定性好** - 成熟工具，社区支持好

**Playwright作为备选：**
1. 处理特殊情况下wkhtmltopf无法渲染的内容
2. 处理需要JavaScript执行的动态内容

---

## 🛠️ 完整实现架构

### 系统架构设计

```
┌─────────────────────────────────────────────────┐
│              微信公众号文章处理系统              │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
   ┌────▼─────┐                   ┌────▼─────┐
   │ 数据获取  │                   │ 文章处理  │
   └────┬─────┘                   └────┬─────┘
        │                               │
   ┌────▼─────────┐           ┌──────────▼────────┐
   │ wewe-rss API │           │ PDF转换引擎      │
   └────┬─────────┘           └──────┬───────────┘
        │                          │
   ┌────▼──────┐            ┌─────▼─────┐
   │ 文章存储  │            │ 文件管理  │
   └────┬─────┘            └─────┬─────┘
        │                          │
   ┌────▼───────────┐      ┌────▼──────┐
   │ wx_account表  │      │ SFTP上传  │
   │ wx_article表   │      └─────┬──────┘
   └────────────────┘            │
                            ┌────▼──────┐
                            │ 存储状态  │
                            │ 更新pdf_url│
                            └───────────┘
```

### 核心组件设计

**1. WefClient (wef-rss API客户端)**
```python
class WefClient:
    """wewe-rss API客户端"""
    def get_accounts() -> List[Account]
    def get_articles(account_id: str) -> List[Article]
    def get_article_detail(article_id: str) -> Article
```

**2. ArticleProcessor (文章处理器)**
```python
class ArticleProcessor:
    """文章内容处理器"""
    def process_content(html: str) -> str
    def extract_metadata(html: str) -> Dict
    def clean_content(content: str) -> str
```

**3. PDFConverter (PDF转换器)**
```python
class PDFConverter:
    """HTML到PDF转换器"""
    def convert_html_to_pdf(html: str, output_path: str)
    def convert_url_to_pdf(url: str, output_path: str)
```

**4. WechatArticleManager (微信文章管理器)**
```python
class WechatArticleManager:
    """微信文章管理器"""
    def fetch_and_store_articles()
    def convert_to_pdf(article_id: int)
    def upload_to_sftp(article_id: int)
```

---

## 📊 数据流程

### 1. 文章获取流程

```
wewe-rss API → 解析文章 → 存储到wx_article表
     ↓
检查url_md5避免重复 → 更新数据库状态
```

### 2. PDF转换流程

```
从数据库获取文章 → HTML内容清理 → PDF生成 → 保存本地 → 更新pdf_path
```

### 3. SFTP上传流程

```
本地PDF文件 → SFTP上传 → 获取远程URL → 更新pdf_url字段 → 标记处理完成
```

---

## ⚙️ 配置要求

### 新增配置项

```bash
# wewe-rss配置
WEWE_RSS_API_URL=http://localhost:4000
WEWE_RSS_API_KEY=your_api_key

# PDF转换配置
PDF_CONVERTER=wkhtmltopdf  # wkhtmltopdf 或 playwright
WKHTMLTOPDF_PATH=/path/to/wkhtmltopdf
PLAYWRIGHT_PATH=/path/to/playwright

# 微信文章处理配置
WECHAT_ARTICLE_AUTO_PROCESS=true
WECHAT_ARTICLE_BATCH_SIZE=10
WECHAT_PDF_QUALITY=high
WECHAT_PDF_PAGE_SIZE=A4

# SFTP配置（已有）
SFTP_HOST=your_sftp_host
SFTP_REMOTE_PATH=/wechat_articles
```

---

## 🚀 实现步骤

### 阶段1: 数据获取（基础）
1. 创建 WefClient 类
2. 实现公众号列表获取
3. 实现文章列表获取
4. 存储到数据库

### 阶段2: PDF转换（核心）
1. 安装 wkhtmltopdf
2. 实现 HTML 内容清理
3. 实现PDF转换功能
4. 添加错误处理

### 阶段3: 文件上传（集成）
1. 集成现有SFTP上传功能
2. 实现批量上传
3. 更新数据库记录
4. 添加状态跟踪

### 阶段4: 自动化（完整）
1. 实现定时任务
2. 添加监控和日志
3. 错误重试机制
4. 性能优化

---

## 💡 关键技术点

### 1. 去重机制
```python
# 使用url_md5避免重复文章
url_md5 = hashlib.md5(article_url.encode()).hexdigest()
if db.get_article_by_url(url_md5):
    return "文章已存在"
```

### 2. HTML内容清理
```python
def clean_html(html: str) -> str:
    """清理微信公众号HTML内容"""
    # 移除广告、导航等无关元素
    # 保留正文、图片、表格等核心内容
    # 转换相对路径为绝对路径
    return cleaned_html
```

### 3. PDF质量控制
```python
# 设置PDF转换参数
pdf_options = {
    'page_size': 'A4',
    'margin_top': '0.75cm',
    'margin_bottom': '0.75cm',
    'encoding': 'UTF-8',
    'enable_local_file_access': True
}
```

### 4. 批量处理优化
```python
# 限制单次处理数量，避免内存溢出
BATCH_SIZE = 10

# 分批处理文章
for i in range(0, len(articles), BATCH_SIZE):
    batch = articles[i:i+BATCH_SIZE]
    process_articles(batch)
```

---

## 📋 目录结构设计

```
src/
├── weixin/
│   ├── __init__.py
│   ├── wef_client.py          # wewe-rss API客户端
│   ├── article_processor.py   # 文章处理器
│   ├── pdf_converter.py       # PDF转换器
│   ├── wechat_manager.py      # 微信文章管理器
│   └── models.py              # 微信数据模型
├── processor/
│   └── wechat_processor.py    # 微信文章处理主流程
├── database/
│   ├── models.py              # 更新：添加微信表模型
│   └── repository.py         # 更新：添加微信表操作
└── utils/
    └── html_cleaner.py        # HTML内容清理工具
```

---

## 🎯 下一步行动

你希望我：

1. **先测试wewe-rss API** - 我帮你写一个测试脚本验证API可用性
2. **开始实现基础功能** - 从数据获取开始逐步实现
3. **设计完整架构** - 详细的类设计和接口定义
4. **创建原型演示** - 快速搭建一个可演示的版本

**基于你的反馈，我来帮你实现具体的功能！** 🚀