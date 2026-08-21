# 微信文章链接钉钉消息类型实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增微信文章链接的钉钉消息类型，支持用户发送微信文章链接自动生成PDF并上传SFTP

**Architecture:** 扩展现有的消息解析和处理器路由架构，复用wxchat PDF生成核心代码，添加微信文章链接识别和处理分支

**Tech Stack:** Python, Playwright, SFTP, 正则表达式, HTTP请求, 钉钉Webhook

---

## 文件结构规划

**创建文件:**
- `src/processor/parsers/wxchat_article_processor.py` - 微信文章链接处理器

**修改文件:**
- `src/feishu/message_parser.py` - 添加微信文章链接识别
- `src/processor/processor_router.py` - 添加wxchat-article处理分支

**复用现有代码:**
- `src/wxchat/processor.py` 中的 `PDFGenerator` 类
- 现有配置项和错误处理机制

---

## Task 1: 扩展MessageParser添加微信文章链接识别

**Files:**
- Modify: `src/feishu/message_parser.py`
- Test: `tests/test_message_parser.py`

- [ ] **Step 1: 在MessageParser类中添加微信文章链接模式**

```python
# 在MessageParser类的顶部添加微信文章链接模式
WXCHAT_ARTICLE_PATTERN = re.compile(
    r'(https://mp\.weixin\.qq\.com/s/[a-zA-Z0-9_-]+)'
)
```

- [ ] **Step 2: 添加微信文章解析方法**

```python
def _parse_wxchat_article(self, content: str, source: str) -> Optional[ParseResult]:
    """
    解析微信文章链接
    
    Args:
        content: 消息内容
        source: 消息来源
        
    Returns:
        ParseResult对象或None
    """
    match = self.WXCHAT_ARTICLE_PATTERN.search(content)
    if not match:
        return None
    
    article_url = match.group(1)
    article_id = article_url.split('/')[-1]
    
    logger.info(f"识别到微信文章链接: {article_url}")
    
    return ParseResult(
        message_type='wxchat-article',
        original_message=content,
        wxchat_article_url=article_url,
        wxchat_article_id=article_id
    )
```

- [ ] **Step 3: 在parse_message方法中添加微信文章解析分支**

```python
# 在parse_message方法中，Priority 3: 微信文章链接（在DingTalk之前）
wxchat_result = self._parse_wxchat_article(content, source)
if wxchat_result:
    return wxchat_result
```

- [ ] **Step 4: 更新ParseResult模型（如果需要新字段）**

检查 `src/feishu/models.py` 中的ParseResult是否包含wxchat相关字段，如果没有则添加：

```python
# 在ParseResult类中添加
wxchat_article_url: Optional[str] = None
wxchat_article_id: Optional[str] = None
```

- [ ] **Step 5: 编写单元测试**

```python
def test_wxchat_article_link_parsing():
    """测试微信文章链接解析"""
    parser = MessageParser()
    
    # 测试标准微信文章链接
    result = parser.parse_message("请看这篇文章：https://mp.weixin.qq.com/s/ABC123XYZ")
    assert result is not None
    assert result.message_type == 'wxchat-article'
    assert result.wxchat_article_url == 'https://mp.weixin.qq.com/s/ABC123XYZ'
    assert result.wxchat_article_id == 'ABC123XYZ'
    
    # 测试包含其他内容的消息
    result2 = parser.parse_message("帮我把这个文章转成PDF https://mp.weixin.qq.com/s/DEF456UVW")
    assert result2 is not None
    assert result2.message_type == 'wxchat-article'
```

- [ ] **Step 6: 运行测试验证功能**

```bash
pytest tests/test_message_parser.py::test_wxchat_article_link_parsing -v
```

预期: PASS

- [ ] **Step 7: 提交代码**

```bash
git add src/feishu/message_parser.py src/feishu/models.py tests/test_message_parser.py
git commit -m "feat: add WeChat article link recognition to MessageParser"
```

---

## Task 2: 创建WxchatArticleProcessor处理器

**Files:**
- Create: `src/processor/parsers/wxchat_article_processor.py`
- Test: `tests/test_wxchat_article_processor.py`

- [ ] **Step 1: 创建处理器文件结构**

```python
"""
微信文章链接处理器

处理微信文章链接的PDF生成和SFTP上传。
复用wxchat的PDFGenerator核心代码。
"""
import os
import tempfile
import requests
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup

from src.feishu.models import ParseResult
from src.config.settings import Settings
from src.utils.logger import get_logger
from src.wxchat.processor import PDFGenerator


@dataclass
class DownloadResult:
    """微信文章下载结果"""
    success: bool
    local_path: Optional[str] = None
    file_size: int = 0
    article_title: Optional[str] = None
    account_name: Optional[str] = None
    error: Optional[str] = None
    retryable: bool = False


@dataclass
class ProcessResult:
    """微信文章处理结果"""
    success: bool
    processed_files: List[str]
    article_title: Optional[str] = None
    account_name: Optional[str] = None
    error: Optional[str] = None


class WxchatArticleProcessor:
    """微信文章链接处理器"""
    
    def __init__(self, settings: Settings):
        """
        初始化处理器
        
        Args:
            settings: 配置对象
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.pdf_generator = PDFGenerator(settings)
        self.temp_dir = None
        
    def can_process(self, message_type: str) -> bool:
        """检查是否支持该消息类型"""
        return message_type == 'wxchat-article'
    
    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        从微信文章页面提取元数据
        
        Args:
            parse_result: 解析结果
            
        Returns:
            DownloadResult包含文章标题和公众号名称
        """
        if not parse_result.wxchat_article_url:
            return DownloadResult(
                success=False,
                error="微信文章URL为空"
            )
        
        article_url = parse_result.wxchat_article_url
        self.logger.info(f"正在获取微信文章信息: {article_url}")
        
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix='wxchat_article_')
            
            # 请求文章页面获取元数据
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(article_url, headers=headers, timeout=30)
            if response.status_code != 200:
                return DownloadResult(
                    success=False,
                    error=f"获取文章页面失败: HTTP {response.status_code}",
                    retryable=True if response.status_code >= 500 else False
                )
            
            # 解析HTML获取文章标题和公众号名称
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 获取文章标题
            title_tag = soup.find('meta', property='og:title')
            article_title = title_tag.get('content', '') if title_tag else ''
            
            # 获取公众号名称
            account_tag = soup.find('meta', property='og:site_name')
            account_name = account_tag.get('content', '') if account_tag else ''
            
            if not article_title:
                return DownloadResult(
                    success=False,
                    error="无法从页面提取文章标题"
                )
            
            # 清理文件名
            article_title = self._clean_filename(article_title)
            account_name = self._clean_filename(account_name) if account_name else '未知公众号'
            
            self.logger.info(f"文章信息获取成功 - 标题: {article_title}, 公众号: {account_name}")
            
            return DownloadResult(
                success=True,
                article_title=article_title,
                account_name=account_name
            )
            
        except requests.exceptions.Timeout:
            return DownloadResult(
                success=False,
                error="获取文章页面超时",
                retryable=True
            )
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                success=False,
                error=f"网络请求失败: {str(e)}",
                retryable=True
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"解析文章页面失败: {str(e)}"
            )
    
    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        生成微信文章PDF
        
        Args:
            download_result: 下载结果（包含文章信息）
            parse_result: 原始解析结果
            
        Returns:
            ProcessResult包含生成的PDF文件路径
        """
        if not download_result.success:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=download_result.error
            )
        
        article_id = parse_result.wxchat_article_id
        if not article_id:
            return ProcessResult(
                success=False,
                processed_files=[],
                error="文章ID为空"
            )
        
        # 生成PDF文件名
        filename = f"{download_result.account_name}_{download_result.article_title}.pdf"
        local_path = os.path.join(self.temp_dir, filename)
        
        self.logger.info(f"正在生成PDF: {filename}")
        
        try:
            # 复用wxchat的PDF生成逻辑
            success = self.pdf_generator.generate_pdf(article_id, local_path)
            
            if not success:
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF生成失败"
                )
            
            # 验证文件存在
            if not os.path.exists(local_path):
                return ProcessResult(
                    success=False,
                    processed_files=[],
                    error="PDF文件生成后未找到"
                )
            
            file_size = os.path.getsize(local_path)
            self.logger.info(f"PDF生成成功: {filename} ({file_size / (1024*1024):.2f} MB)")
            
            return ProcessResult(
                success=True,
                processed_files=[local_path],
                article_title=download_result.article_title,
                account_name=download_result.account_name
            )
            
        except Exception as e:
            return ProcessResult(
                success=False,
                processed_files=[],
                error=f"PDF生成异常: {str(e)}"
            )
    
    def get_upload_files(self, process_result: ProcessResult, parse_result: ParseResult) -> List[dict]:
        """
        生成SFTP上传文件列表
        
        Args:
            process_result: 处理结果
            parse_result: 原始解析结果
            
        Returns:
            上传文件列表
        """
        if not process_result.success:
            return []
        
        upload_files = []
        
        for local_path in process_result.processed_files:
            # 生成与wxchat一致的路径结构
            filename = os.path.basename(local_path)
            year_month = datetime.now().strftime('%Y%m')
            
            # 路径: /wxchat/YYYYMM/公众号_文章标题.pdf
            remote_path = f"{self.settings.wxchat_sftp_remote_path}/{year_month}/{filename}"
            
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            
            upload_files.append({
                'local_path': local_path,
                'remote_path': remote_path,
                'size': file_size
            })
            
            self.logger.info(f"准备上传文件: {local_path} -> {remote_path}")
        
        return upload_files
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"清理临时目录失败: {self.temp_dir}, 错误: {e}")
            finally:
                self.temp_dir = None
    
    def _clean_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除或替换不合适的字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\n', '\r', '\t']
        cleaned = filename
        
        for char in illegal_chars:
            cleaned = cleaned.replace(char, '_')
        
        # 移除首尾空格
        cleaned = cleaned.strip()
        
        # 限制长度
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        
        return cleaned if cleaned else 'unknown'
```

- [ ] **Step 2: 编写单元测试**

```python
def test_wxchat_article_processor_download():
    """测试微信文章信息提取"""
    processor = WxchatArticleProcessor(Settings())
    
    parse_result = ParseResult(
        message_type='wxchat-article',
        wxchat_article_url='https://mp.weixin.qq.com/s/test123',
        wxchat_article_id='test123'
    )
    
    download_result = processor.download(parse_result)
    
    # 注意：这个测试需要真实的微信文章URL，或者使用mock
    # 实际实施时可能需要使用mock响应
    assert download_result is not None

def test_filename_cleaning():
    """测试文件名清理功能"""
    processor = WxchatArticleProcessor(Settings())
    
    # 测试非法字符清理
    cleaned = processor._clean_filename('测试/文件:名称?"<>|*.pdf')
    assert '/' not in cleaned
    assert ':' not in cleaned
    assert cleaned.startswith('测试')
```

- [ ] **Step 3: 运行测试验证基本结构**

```bash
pytest tests/test_wxchat_article_processor.py -v
```

预期: 基本结构测试通过

- [ ] **Step 4: 提交代码**

```bash
git add src/processor/parsers/wxchat_article_processor.py tests/test_wxchat_article_processor.py
git commit -m "feat: create WxchatArticleProcessor with PDF generation"
```

---

## Task 3: 在ProcessorRouter中添加wxchat-article处理分支

**Files:**
- Modify: `src/processor/processor_router.py`
- Test: `tests/test_processor_router.py`

- [ ] **Step 1: 导入WxchatArticleProcessor**

```python
# 在processor_router.py的导入部分添加
from src.processor.parsers.wxchat_article_processor import WxchatArticleProcessor
```

- [ ] **Step 2: 在__init__方法中初始化处理器**

```python
# 在__init__方法中添加
self.wxchat_article_processor = WxchatArticleProcessor(self.settings)
```

- [ ] **Step 3: 在process_message方法中添加路由分支**

```python
# 在process_message方法的路由部分添加（在pdf_link之后）
elif message_type == 'wxchat-article':
    return self._process_wxchat_article(parse_result, start_time)
```

- [ ] **Step 4: 实现_process_wxchat_article方法**

```python
def _process_wxchat_article(self, parse_result: ParseResult, start_time: datetime) -> ProcessResult:
    """处理微信文章链接"""
    logger.info("Routing to WeChat article processor...")
    
    # 1. 下载并获取文章信息
    download_result = self.wxchat_article_processor.download(parse_result)
    
    if not download_result.success:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return ProcessResult(
            success=False,
            message_type='wxchat-article',
            error_message=download_result.error,
            processing_time_ms=processing_time
        )
    
    logger.info(f"微信文章信息获取成功: {download_result.article_title}")
    
    # 2. 生成PDF
    process_result = self.wxchat_article_processor.process(download_result, parse_result)
    
    if not process_result.success:
        self.wxchat_article_processor.cleanup()
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return ProcessResult(
            success=False,
            message_type='wxchat-article',
            error_message=process_result.error,
            processing_time_ms=processing_time
        )
    
    # 3. 生成上传文件列表
    upload_files = self.wxchat_article_processor.get_upload_files(process_result, parse_result)
    logger.info(f"Generated {len(upload_files)} upload files")
    
    # 4. 上传到SFTP
    success_count = 0
    failed_count = 0
    
    if self.enable_sftp:
        for upload_file in upload_files:
            local_path = upload_file['local_path']
            remote_path = upload_file['remote_path']
            
            logger.info(f"Uploading: {local_path} -> {remote_path}")
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            if not self.sftp_client.create_directory(remote_dir):
                logger.error(f"Failed to create remote directory: {remote_dir}")
                failed_count += 1
                continue
            
            # 上传文件
            if self.sftp_client.upload_file(local_path, remote_path):
                logger.info(f"Upload successful: {remote_path}")
                success_count += 1
            else:
                logger.error(f"Upload failed: {remote_path}")
                failed_count += 1
    
    # 5. 清理临时文件
    self.wxchat_article_processor.cleanup()
    
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return ProcessResult(
        success=success_count > 0,
        message_type='wxchat-article',
        total_files=len(upload_files),
        success_count=success_count,
        failed_count=failed_count,
        processing_time_ms=processing_time,
        metadata={
            'article_title': process_result.article_title,
            'account_name': process_result.account_name,
            'article_id': parse_result.wxchat_article_id
        }
    )
```

- [ ] **Step 5: 在close方法中添加清理逻辑（如果需要）**

```python
# 在close方法中确保处理器清理完成
if hasattr(self, 'wxchat_article_processor'):
    self.wxchat_article_processor.cleanup()
```

- [ ] **Step 6: 编写集成测试**

```python
def test_wxchat_article_routing():
    """测试微信文章链接路由"""
    router = ProcessorRouter(enable_sftp=False)
    
    parse_result = ParseResult(
        message_type='wxchat-article',
        wxchat_article_url='https://mp.weixin.qq.com/s/test123',
        wxchat_article_id='test123'
    )
    
    # 注意：这个测试需要mock外部依赖
    # 实际实施时需要适当调整
    result = router.process_message(parse_result)
    
    assert result is not None
    assert result.message_type == 'wxchat-article'
```

- [ ] **Step 7: 运行测试验证路由功能**

```bash
pytest tests/test_processor_router.py::test_wxchat_article_routing -v
```

预期: 路由测试通过

- [ ] **Step 8: 提交代码**

```bash
git add src/processor/processor_router.py tests/test_processor_router.py
git commit -m "feat: add wxchat-article processing route to ProcessorRouter"
```

---

## Task 4: 集成钉钉反馈通知

**Files:**
- Modify: `src/feishu/dingtalk_group_client.py` 或相关反馈模块
- Modify: `src/processor/auto_processor.py`

- [ ] **Step 1: 检查现有钉钉反馈机制**

```bash
# 查看现有的钉钉反馈实现
grep -r "dingtalk.*feedback\|钉钉.*反馈" src/
```

- [ ] **Step 2: 扩展消息反馈逻辑（如果需要）**

```python
# 在相关的反馈处理器中添加wxchat-article支持
def send_wxchat_article_feedback(self, result: ProcessResult, parse_result: ParseResult):
    """发送微信文章处理反馈"""
    
    if result.success:
        # 成功消息
        article_title = result.metadata.get('article_title', '未知文章')
        account_name = result.metadata.get('account_name', '未知公众号')
        
        message = f"""✅ 微信文章处理成功
文章: {account_name}_{article_title}.pdf
文章ID: {parse_result.wxchat_article_id}
已上传到: /wxchat/"""
        
    else:
        # 失败消息
        error_msg = result.error_message or "未知错误"
        article_url = parse_result.wxchat_article_url or "未知链接"
        
        message = f"""❌ 微信文章处理失败
链接: {article_url}
错误: {error_msg}
"""
    
    self.send_text_message(message)
```

- [ ] **Step 3: 集成到AutoProcessor中**

```python
# 在AutoProcessor中添加wxchat-article反馈调用
if result.message_type == 'wxchat-article':
    self.dingtalk_client.send_wxchat_article_feedback(result, parse_result)
```

- [ ] **Step 4: 测试钉钉反馈功能**

手动测试或使用mock验证钉钉消息发送

- [ ] **Step 5: 提交代码**

```bash
git add src/feishu/dingtalk_group_client.py src/processor/auto_processor.py
git commit -m "feat: add DingTalk feedback for wxchat-article processing"
```

---

## Task 5: 完善错误处理和重试机制

**Files:**
- Modify: `src/processor/parsers/wxchat_article_processor.py`
- Modify: `src/database/repository.py` (数据库重试逻辑)

- [ ] **Step 1: 完善DownloadResult中的retryable逻辑**

确保所有错误都正确设置了retryable标志

- [ ] **Step 2: 集成数据库重试机制**

```python
# 确保wxchat-article消息类型支持重试
# 检查数据库记录逻辑是否支持新的消息类型
```

- [ ] **Step 3: 添加日志记录**

```python
# 在关键步骤添加详细日志
self.logger.info(f"开始处理微信文章: {article_id}")
self.logger.debug(f"文章标题: {article_title}, 公众号: {account_name}")
self.logger.info(f"PDF生成完成: {local_path}")
```

- [ ] **Step 4: 提交代码**

```bash
git add src/processor/parsers/wxchat_article_processor.py
git commit -m "feat: improve error handling and retry logic for wxchat-article"
```

---

## Task 6: 编写文档和测试用例

**Files:**
- Create: `docs/active/wxchat-article-usage.md`
- Modify: `README.md` 或相关文档

- [ ] **Step 1: 编写用户使用指南**

```markdown
# 微信文章链接处理功能

## 使用方法

1. 在钉钉群中@机器人，发送微信文章链接
2. 机器人会自动识别并处理
3. 处理完成后会发送钉钉反馈通知

## 支持的链接格式

- 标准格式: `https://mp.weixin.qq.com/s/[article_id]`
- 示例: `https://mp.weixin.qq.com/s/ABC123XYZ`

## 文件命名

PDF文件命名格式: `公众号名称_文章标题.pdf`
```

- [ ] **Step 2: 更新相关文档**

- [ ] **Step 3: 编写完整测试套件**

```python
# 创建完整的集成测试
def test_wxchat_article_complete_flow():
    """测试完整的微信文章处理流程"""
    pass
```

- [ ] **Step 4: 提交文档和测试**

```bash
git add docs/active/wxchat-article-usage.md README.md tests/
git commit -m "docs: add wxchat-article usage guide and complete test suite"
```

---

## Task 7: 性能优化和验证

**Files:**
- Modify: `src/processor/parsers/wxchat_article_processor.py`

- [ ] **Step 1: 优化HTTP请求性能**

```python
# 添加请求超时和重试配置
# 优化BeautifulSoup解析性能
```

- [ ] **Step 2: 添加缓存机制（如果需要）**

```python
# 考虑添加文章元数据缓存
# 避免重复请求同一篇文章
```

- [ ] **Step 3: 进行性能测试**

```bash
# 测试多个微信文章同时处理的情况
# 验证并发处理能力
```

- [ ] **Step 4: 提交优化代码**

```bash
git add src/processor/parsers/wxchat_article_processor.py
git commit -m "perf: optimize wxchat-article processing performance"
```

---

## Task 8: 最终集成测试和部署准备

**Files:**
- Various

- [ ] **Step 1: 进行端到端测试**

使用真实的微信文章链接进行完整流程测试

- [ ] **Step 2: 验证SFTP上传路径**

确认文件上传到正确的 `/wxchat/YYYYMM/` 路径

- [ ] **Step 3: 测试钉钉反馈通知**

验证成功和失败场景的钉钉通知

- [ ] **Step 4: 检查数据库记录**

确认message_process_log表正确记录处理过程

- [ ] **Step 5: 准备发布说明**

```markdown
# 版本更新说明

## 新功能
- 新增微信文章链接处理功能
- 支持钉钉消息中发送微信文章链接自动生成PDF
- 文件命名使用文章标题，与wxchat保持一致
- SFTP上传路径与wxchat保持一致: /wxchat/YYYYMM/

## 使用方法
在钉钉群中@机器人发送微信文章链接即可

## 技术细节
- 复用现有wxchat PDF生成核心代码
- 扩展MessageParser识别微信文章链接
- 新增WxchatArticleProcessor处理器
```

- [ ] **Step 6: 最终代码提交和准备发布**

```bash
git commit -m "release: complete wxchat-article feature implementation"
```

---

## 实施检查清单

### 功能完整性
- [ ] 微信文章链接正确识别
- [ ] PDF生成成功
- [ ] SFTP上传到正确路径
- [ ] 文件命名使用文章标题
- [ ] 钉钉反馈通知工作正常

### 代码质量
- [ ] 所有测试通过
- [ ] 错误处理完善
- [ ] 日志记录详细
- [ ] 代码复用良好
- [ ] 向后兼容性保持

### 部署准备
- [ ] 文档完整
- [ ] 配置正确
- [ ] 测试充分
- [ ] 性能达标
- [ ] 发布说明准备

---

**实施计划版本:** 1.0
**创建日期:** 2026-08-21
**预计工期:** 中等复杂度，建议分步实施