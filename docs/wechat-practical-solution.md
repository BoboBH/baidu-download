# 微信公众号文章处理 - 实际技术方案

## 🔍 wewe-rss API 测试结果分析

### 测试发现

**❌ 传统REST API不可用**
- 没有找到标准的 `/api/accounts`、`/api/articles` 等端点
- `/dash` 端点返回的是前端SPA应用
- 后端API可能通过不同的方式访问

**✅ wewe-rss 服务正常运行**
- 服务在 http://localhost:4000 正常运行
- 前端是React单页应用
- 数据通过JavaScript动态加载

---

## 🎯 实际技术方案

### 方案A: 数据库直接访问（推荐）

**原理：**
- wewe-rss 使用SQLite数据库存储数据
- 可以直接访问数据库获取文章信息
- 绕过API，直接从源头获取数据

**实现步骤：**
1. 定位wefe-rss数据库文件位置
2. 分析数据库schema结构
3. 创建数据访问层
4. 实现文章获取和处理逻辑

**优点：**
- ✅ 完全控制数据获取
- ✅ 不受API变更影响
- ✅ 可以获取完整的文章数据
- ✅ 性能更好

**缺点：**
- ⚠️ 需要了解数据库结构
- ⚠️ 数据库文件可能被锁定

### 方案B: 浏览器自动化（备选）

**原理：**
- 使用Playwright/Selenium控制浏览器
- 自动登录wefe-rss并导航到文章页面
- 提取文章内容和元数据

**实现步骤：**
1. 启动无头浏览器
2. 自动登录wefe-rss
3. 导航到文章列表页面
4. 逐个获取文章内容

**优点：**
- ✅ 可以获取前端显示的所有数据
- ✅ 不需要了解数据库结构
- ✅ 可以处理需要认证的页面

**缺点：**
- ⚠️ 速度较慢
- ⚠️ 资源消耗大
- ⚠️ 可能受页面结构变化影响

### 方案C: wewe-rss API逆向（复杂）

**原理：**
- 通过浏览器开发者工具分析API请求
- 识别真正的API端点和参数
- 模拟前端请求获取数据

**实现步骤：**
1. 打开浏览器开发者工具
2. 在wefe-rss中操作并观察网络请求
3. 识别API端点和参数格式
4. 实现API客户端

**优点：**
- ✅ 使用官方API方式
- ✅ 数据格式标准化

**缺点：**
- ⚠️ API可能随时变化
- ⚠️ 需要认证token
- ⚠️ 复杂度较高

---

## 🖨️ HTML转PDF 技术方案（更新）

### 推荐方案对比

| 方案 | 难度 | 质量 | 速度 | 推荐度 |
|------|------|------|------|--------|
| **wkhtmltopdf** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Playwright** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **WeasyPrint** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **pdfkit** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

### 具体实现方案

#### 方案1: wkhtmltopdf（最推荐）

**安装：**
```bash
# Windows
choco install wkhtmltopdf

# 或下载 standalone版本
# https://wkhtmltopdf.org/downloads.html
```

**Python实现：**
```python
import subprocess
import os

class PDFConverter:
    def convert_html_to_pdf(self, html_content, output_path):
        """将HTML内容转换为PDF"""
        # 保存HTML到临时文件
        temp_html = "temp_article.html"
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        try:
            # wkhtmltopdf命令
            cmd = [
                'wkhtmltopdf',
                temp_html,
                output_path,
                '--page-size', 'A4',
                '--margin-top', '0.75cm',
                '--margin-bottom', '0.75cm',
                '--margin-left', '0.75cm',
                '--margin-right', '0.75cm',
                '--encoding', 'UTF-8',
                '--enable-local-file-access'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                return True, output_path
            else:
                return False, result.stderr
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_html):
                os.remove(temp_html)
```

#### 方案2: Playwright（备选）

**安装：**
```bash
pip install playwright
playwright install chromium
```

**Python实现：**
```python
from playwright.sync_api import sync_playwright

class PDFConverterPlaywright:
    def convert_url_to_pdf(self, url, output_path):
        """直接将URL转换为PDF"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')
            page.pdf(path=output_path, format='A4')
            browser.close()
            return True, output_path
```

---

## 🛠️ 完整实现架构（基于数据库访问）

### 系统架构

```
┌─────────────────────────────────────────────────┐
│              微信公众号文章处理系统              │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
   ┌────▼───────┐                   ┌────▼──────┐
   │ 数据获取层  │                   │ 文件处理层  │
   └────┬───────┘                   └────┬──────┘
        │                               │
   ┌────▼─────────────┐         ┌─────▼───────┐
   │ wewe-rss数据库访问 │         │ PDF转换引擎  │
   │ (SQLite/PostgreSQL)│         │ (wkhtmltopdf) │
   └────┬─────────────┘         └─────┬───────┘
        │                            │
   ┌────▼──────────┐            ┌────▼────────┐
   │ 文章数据提取  │            │ 文件管理    │
   └────┬──────────┘            └────┬────────┘
        │                            │
   ┌────▼──────────┐            ┌────▼──────┐
   │ wx_article存储 │            │ SFTP上传   │
   └─────────────────┘            └─────────────┘
```

### 核心模块设计

#### 1. 数据库访问层
```python
class WefDatabaseClient:
    """wefe-rss数据库客户端"""
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
    
    def get_accounts(self) -> List[Dict]:
        """获取公众号列表"""
        
    def get_articles(self, account_id: str) -> List[Dict]:
        """获取文章列表"""
        
    def get_article_detail(self, article_id: str) -> Dict:
        """获取文章详情"""
```

#### 2. 文章处理器
```python
class ArticleProcessor:
    """文章内容处理器"""
    def process_html_content(self, html: str) -> str:
        """处理HTML内容，移除广告和无关元素"""
        
    def extract_metadata(self, article: Dict) -> Dict:
        """提取文章元数据"""
```

#### 3. PDF转换器
```python
class PDFConverter:
    """PDF转换器（wkhtmltopdf实现）"""
    def convert_html_to_pdf(self, html_content: str, output_path: str):
        """HTML转PDF"""
        
    def convert_url_to_pdf(self, url: str, output_path: str):
        """直接从URL转PDF"""
```

#### 4. SFTP上传器
```python
class WechatSFTPUploader:
    """微信文章SFTP上传器"""
    def upload_pdf(self, pdf_path: str) -> str:
        """上传PDF并返回URL"""
```

---

## 📊 完整数据流程

### 1. 文章获取流程
```
wefe-rss数据库 → 提取文章数据 → 检查url_md5 → 
存储到wx_article表 → 标记为'pending'
```

### 2. PDF转换流程
```
从数据库获取文章 → 清理HTML内容 → wkhtmltopdf转换 → 
保存本地文件 → 更新pdf_path字段
```

### 3. SFTP上传流程
```
本地PDF文件 → SFTP上传 → 生成远程URL → 
更新pdf_url字段 → 标记为'completed'
```

---

## ⚙️ 配置文件设计

### .env 新增配置

```bash
# wewe-rss数据库配置
WEWE_RSS_DB_PATH=C:\path\to\wefe-rss\data.db
WEWE_RSS_DB_TYPE=sqlite
# 或PostgreSQL
# WEWE_RSS_DB_HOST=localhost
# WEWE_RSS_DB_PORT=5432
# WEWE_RSS_DB_NAME=wefe_rss
# WEWE_RSS_DB_USER=wefe_rss
# WEWE_RSS_DB_PASSWORD=password

# PDF转换配置
PDF_CONVERTER=wkhtmltopdf
WKHTMLTOPDF_PATH=C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe

# PDF质量设置
PDF_QUALITY=high
PDF_PAGE_SIZE=A4
PDF_MARGIN_TOP=0.75cm
PDF_MARGIN_BOTTOM=0.75cm

# 微信文章处理配置
WECHAT_AUTO_PROCESS=true
WECHAT_BATCH_SIZE=10
WECHAT_PROCESS_INTERVAL=3600
WECHAT_PDF_SFTP_PATH=/wechat_articles

# 文章过滤配置
WECHAT_ACCOUNT_FILTER=研讯社,中金研报
WECHAT_DATE_RANGE_DAYS=7
```

---

## 🚀 实现步骤

### 阶段1: 数据库访问（基础）
1. 定位wefe-rss数据库文件
2. 分析数据库schema
3. 实现数据库访问客户端
4. 测试数据读取

### 阶段2: 数据处理（核心）
1. 实现文章数据提取
2. 实现HTML内容清理
3. 存储到wx_article表
4. 实现去重机制

### 阶段3: PDF转换（关键）
1. 安装和配置wkhtmltopdf
2. 实现HTML转PDF功能
3. 添加错误处理和重试
4. 优化PDF质量

### 阶段4: 集成部署（完整）
1. 集成现有SFTP上传功能
2. 实现自动化流程
3. 添加定时任务
4. 部署和监控

---

## 🔍 下一步行动

### 立即可做的：

**1. 定位wefe-rss数据库文件**
```bash
# 常见位置
C:\Users\<username>\AppData\Local\wefe-rss\
C:\Program Files\wefe-rss\
当前项目目录下
```

**2. 测试数据库访问**
```bash
# 我可以帮你创建一个测试脚本来分析数据库结构
python test_scripts/test_wef_database.py
```

**3. 安装PDF转换工具**
```bash
# 测试wkhtmltopdf安装
choco install wkhtmltopdf
```

### 建议的实现顺序：

**第一步：数据库访问** - 先确认能获取数据  
**第二步：基础处理** - 处理单篇文章  
**第三步：PDF转换** - 实现HTML转PDF  
**第四步：完整集成** - 端到端流程

---

## 💡 需要确认的信息

**关于wefe-rss：**
1. wefe-rss的数据库文件位置？
2. 数据库的表结构和字段？
3. 文章数据在哪个表中？

**关于PDF转换：**
1. 优先考虑PDF质量还是速度？
2. 是否需要保留原文格式和图片？
3. PDF文件的大致大小限制？

**关于文章处理：**
1. 需要处理哪些公众号？
2. 文章的时间范围？
3. 是否需要全自动化还是半自动化？

**请告诉我这些信息，我来帮你实现具体功能！** 🎯