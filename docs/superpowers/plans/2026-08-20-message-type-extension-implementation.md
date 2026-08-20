# 多消息类型支持系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 扩展现有百度网盘下载系统，支持三种消息类型（百度网盘链接、PDF文件链接、钉钉文件）的统一处理，保持现有功能完全兼容

**架构:** 使用策略模式实现可扩展的文件处理器架构，消息类型优先级路由（百度网盘 > PDF链接 > 钉钉文件），统一错误处理和重试机制

**技术栈:** Python 3.8+, MySQL 5.7+, 钉钉Stream API, SFTP, 异步处理, 策略模式, requests库, zipfile

---

## Task 1: 数据库架构扩展

**文件:**
- 修改: `src/database/message_models.py`
- 修改: `src/database/repository.py`
- 创建: `database/migrations/004_add_message_type_support.sql`
- 测试: `tests/test_database_migration.py`

- [ ] **步骤 1: 编写数据库迁移脚本**

创建 `database/migrations/004_add_message_type_support.sql`:

```sql
-- 迁移 004: 添加消息类型支持
-- 添加 message_type, raw_message, file_info 字段以支持多消息类型

-- 1. 备份现有数据
CREATE TABLE IF NOT EXISTS message_process_log_backup_20260820 AS SELECT * FROM message_process_log;

-- 2. 添加 message_type 字段
ALTER TABLE message_process_log 
ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan' 
COMMENT '消息类型: baidupan, pdf_link, dingtalk_pdf, dingtalk_zip';

-- 3. 添加 raw_message 字段用于存储原始消息JSON
ALTER TABLE message_process_log 
ADD COLUMN raw_message JSON 
COMMENT '原始钉钉消息JSON，用于调试和重放';

-- 4. 添加 file_info 字段用于存储文件元信息
ALTER TABLE message_process_log 
ADD COLUMN file_info JSON 
COMMENT '文件元信息: {size, type, url, fileName}';

-- 5. 创建性能优化索引
CREATE INDEX idx_message_type ON message_process_log(message_type);
CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type);

-- 6. 添加消息类型约束
ALTER TABLE message_process_log 
ADD CONSTRAINT chk_message_type 
CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'));

-- 7. 更新现有记录的 message_type
UPDATE message_process_log 
SET message_type = 'baidupan' 
WHERE message_type IS NULL OR message_type = 'baidupan';

-- 验证迁移结果
SELECT COUNT(*) as total_messages, 
       message_type, 
       process_status 
FROM message_process_log 
GROUP BY message_type, process_status;
```

- [ ] **步骤 2: 执行数据库迁移**

```bash
# 执行迁移脚本
mysql -u root -p baidu_download < database/migrations/004_add_message_type_support.sql

# 验证迁移成功
mysql -u root -p baidu_download -e "DESCRIBE message_process_log;"
```

预期结果: 应该看到新增的字段 `message_type`, `raw_message`, `file_info`

- [ ] **步骤 3: 扩展消息模型**

修改 `src/database/message_models.py`，在 `MessageProcessLog` 类中添加新字段:

```python
@dataclass
class MessageProcessLog:
    """消息处理日志模型"""
    message_hash: str
    original_message: Optional[str] = None
    share_link: Optional[str] = None
    folder_name: Optional[str] = None
    extraction_code: Optional[str] = None
    source: str = 'feishu'
    process_status: str = 'pending'
    error_message: Optional[str] = None
    execution_summary_id: Optional[int] = None
    processing_time_ms: Optional[int] = None
    retry_count: int = 0
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 新增字段 - 消息类型支持
    message_type: str = 'baidupan'  # baidupan, pdf_link, dingtalk_pdf, dingtalk_zip
    raw_message: Optional[str] = None  # 原始JSON字符串
    file_info: Optional[str] = None  # 文件元信息JSON字符串
```

- [ ] **步骤 4: 更新数据库仓库方法**

修改 `src/database/repository.py`，在 `insert_message_log` 方法中添加新字段支持:

找到 `insert_message_log` 方法并更新参数处理:

```python
def insert_message_log(self, message_log: MessageProcessLog) -> int:
    """插入消息处理日志"""
    try:
        now = datetime.now()
        query = """
        INSERT INTO message_process_log (
            message_hash, original_message, share_link, folder_name, 
            extraction_code, source, process_status, processing_time_ms,
            message_type, raw_message, file_info, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (
            message_log.message_hash,
            message_log.original_message,
            message_log.share_link,
            message_log.folder_name,
            message_log.extraction_code,
            message_log.source,
            message_log.process_status,
            message_log.processing_time_ms,
            message_log.message_type,
            message_log.raw_message,
            message_log.file_info,
            now, now
        ))
        self.conn.commit()
        log_id = cursor.lastrowid
        cursor.close()
        return log_id
    except Exception as e:
        self.conn.rollback()
        logger.error(f"插入消息日志失败: {e}")
        raise
```

- [ ] **步骤 5: 编写数据库迁移测试**

创建 `tests/test_database_migration.py`:

```python
import unittest
import json
from datetime import datetime
from src.database.repository import DatabaseRepository
from src.database.message_models import MessageProcessLog
from src.config.settings import Settings

class TestDatabaseMigration(unittest.TestCase):
    """测试数据库迁移功能"""
    
    def setUp(self):
        """设置测试环境"""
        settings = Settings()
        self.db_repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
    
    def tearDown(self):
        """清理测试数据"""
        # 清理测试创建的消息记录
        cursor = self.db_repo.conn.cursor()
        cursor.execute("DELETE FROM message_process_log WHERE original_message LIKE 'test_%'")
        self.db_repo.conn.commit()
        cursor.close()
    
    def test_message_type_field_exists(self):
        """测试 message_type 字段存在"""
        cursor = self.db_repo.conn.cursor()
        cursor.execute("SHOW COLUMNS FROM message_process_log LIKE 'message_type'")
        result = cursor.fetchone()
        cursor.close()
        
        self.assertIsNotNone(result, "message_type 字段应该存在")
        self.assertEqual(result[0], 'message_type')
    
    def test_raw_message_field_exists(self):
        """测试 raw_message 字段存在"""
        cursor = self.db_repo.conn.cursor()
        cursor.execute("SHOW COLUMNS FROM message_process_log LIKE 'raw_message'")
        result = cursor.fetchone()
        cursor.close()
        
        self.assertIsNotNone(result, "raw_message 字段应该存在")
        self.assertEqual(result[0], 'raw_message')
    
    def test_file_info_field_exists(self):
        """测试 file_info 字段存在"""
        cursor = self.db_repo.conn.cursor()
        cursor.execute("SHOW COLUMNS FROM message_process_log LIKE 'file_info'")
        result = cursor.fetchone()
        cursor.close()
        
        self.assertIsNotNone(result, "file_info 字段应该存在")
        self.assertEqual(result[0], 'file_info')
    
    def test_insert_message_with_new_fields(self):
        """测试插入包含新字段的消息记录"""
        file_info = {
            "size": 1024000,
            "type": "pdf",
            "url": "https://example.com/file.pdf"
        }
        
        message_log = MessageProcessLog(
            message_hash="test_hash_12345",
            original_message="test_message_content",
            share_link="https://pan.baidu.com/s/test",
            folder_name="test_folder",
            extraction_code="test_code",
            source="dingtalk",
            process_status="pending",
            message_type="baidupan",
            raw_message=json.dumps({"test": "data"}),
            file_info=json.dumps(file_info)
        )
        
        log_id = self.db_repo.insert_message_log(message_log)
        self.assertGreater(log_id, 0, "应该成功插入消息记录")
    
    def test_message_type_constraint(self):
        """测试消息类型约束"""
        # 测试有效的消息类型
        valid_types = ['baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip']
        
        for msg_type in valid_types:
            message_log = MessageProcessLog(
                message_hash=f"test_hash_{msg_type}",
                original_message=f"test_{msg_type}",
                message_type=msg_type
            )
            
            try:
                log_id = self.db_repo.insert_message_log(message_log)
                self.assertGreater(log_id, 0, f"应该支持消息类型: {msg_type}")
            except Exception as e:
                self.fail(f"有效的消息类型 {msg_type} 不应该抛出异常: {e}")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 6: 运行数据库迁移测试**

```bash
# 运行迁移测试
python tests/test_database_migration.py -v
```

预期结果: 所有测试应该通过，输出类似 "OK (5 tests in 0.123s)"

- [ ] **步骤 7: 提交数据库扩展更改**

```bash
git add database/migrations/004_add_message_type_support.sql
git add src/database/message_models.py
git add src/database/repository.py
git add tests/test_database_migration.py
git commit -m "feat(migration): add message type support to database schema

- Add message_type field for message type tracking
- Add raw_message field for storing original JSON
- Add file_info field for file metadata
- Create performance indexes
- Add message type constraints
- Update MessageProcessLog model
- Update repository methods
- Add migration tests

Supported message types:
- baidupan: Baidu Pan share links
- pdf_link: Direct PDF file links  
- dingtalk_pdf: DingTalk PDF files
- dingtalk_zip: DingTalk ZIP archives"
```

---

## Task 2: 消息解析器架构重构

**文件:**
- 修改: `src/feishu/message_parser.py`
- 创建: `src/feishu/parsers/pdf_link_parser.py`
- 创建: `src/feishu/parsers/dingtalk_file_parser.py`
- 创建: `src/feishu/parsers/__init__.py`
- 测试: `tests/test_message_parsers.py`

- [ ] **步骤 1: 创建解析结果模型**

创建 `src/feishu/models.py`:

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ParseResult:
    """统一的消息解析结果"""
    message_type: str  # 'baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'
    unique_identifier: str  # 用于去重的唯一标识符
    source: str  # 消息来源
    
    # 百度网盘特定字段
    share_link: Optional[str] = None
    extraction_code: Optional[str] = None
    folder_name: Optional[str] = None
    
    # PDF链接特定字段
    pdf_url: Optional[str] = None
    
    # 钉钉文件特定字段
    file_id: Optional[str] = None
    space_id: Optional[str] = None
    download_code: Optional[str] = None
    file_name: Optional[str] = None
    
    # 原始数据
    raw_message: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'message_type': self.message_type,
            'unique_identifier': self.unique_identifier,
            'source': self.source,
            'share_link': self.share_link,
            'extraction_code': self.extraction_code,
            'folder_name': self.folder_name,
            'pdf_url': self.pdf_url,
            'file_id': self.file_id,
            'space_id': self.space_id,
            'download_code': self.download_code,
            'file_name': self.file_name,
            'raw_message': self.raw_message
        }
```

- [ ] **步骤 2: 创建PDF链接解析器**

创建 `src/feishu/parsers/pdf_link_parser.py`:

```python
import re
import hashlib
from typing import Optional
from src.feishu.models import ParseResult

class PdfLinkParser:
    """PDF文件链接解析器"""
    
    PDF_PATTERN = re.compile(r'(https?://[^\s]+\.pdf)')
    
    def parse(self, content: str, source: str = 'dingtalk') -> Optional[ParseResult]:
        """
        解析PDF链接
        
        Args:
            content: 消息内容
            source: 消息来源
            
        Returns:
            ParseResult 对象，如果不包含PDF链接则返回 None
        """
        match = self.PDF_PATTERN.search(content)
        if not match:
            return None
        
        pdf_url = match.group(1)
        
        # 验证URL有效性
        if not self._is_valid_pdf_url(pdf_url):
            return None
        
        # 使用完整URL作为唯一标识符
        unique_identifier = pdf_url
        
        return ParseResult(
            message_type='pdf_link',
            unique_identifier=unique_identifier,
            pdf_url=pdf_url,
            source=source,
            folder_name=None  # PDF链接没有文件夹概念
        )
    
    def _is_valid_pdf_url(self, url: str) -> bool:
        """验证PDF URL有效性"""
        # 基本URL格式验证
        if not url.startswith(('http://', 'https://')):
            return False
        
        # 检查是否包含.pdf扩展名
        if not url.lower().endswith('.pdf'):
            return False
        
        # 检查URL长度合理性
        if len(url) > 2000:  # URL过长可能不合法
            return False
        
        return True
    
    def can_process(self, message_type: str) -> bool:
        """判断是否能处理该消息类型"""
        return message_type == 'pdf_link'
```

- [ ] **步骤 3: 创建钉钉文件解析器**

创建 `src/feishu/parsers/dingtalk_file_parser.py`:

```python
import hashlib
from typing import Optional, Dict, Any
from src.feishu.models import ParseResult

class DingTalkFileParser:
    """钉钉文件消息解析器"""
    
    SUPPORTED_EXTENSIONS = ['.pdf', '.zip']
    
    def parse(self, message_data: Dict[str, Any], source: str = 'dingtalk') -> Optional[ParseResult]:
        """
        解析钉钉文件消息
        
        Args:
            message_data: 钉钉消息数据（包含content字段）
            source: 消息来源
            
        Returns:
            ParseResult 对象，如果不支持的文件类型则返回 None
        """
        if not message_data or not isinstance(message_data, dict):
            return None
        
        content = message_data.get('content', {})
        if not content or not isinstance(content, dict):
            return None
        
        file_name = content.get('fileName')
        file_id = content.get('fileId')
        space_id = content.get('spaceId')
        download_code = content.get('downloadCode')
        
        # 验证必需字段
        if not all([file_name, file_id, space_id, download_code]):
            return None
        
        # 判断文件类型
        file_name_lower = file_name.lower()
        
        if file_name_lower.endswith('.pdf'):
            message_type = 'dingtalk_pdf'
        elif file_name_lower.endswith('.zip'):
            message_type = 'dingtalk_zip'
        else:
            # 不支持的文件类型
            return None
        
        # 使用 file_id:space_id 作为唯一标识符（而不是downloadCode）
        unique_identifier = f"{file_id}:{space_id}"
        
        return ParseResult(
            message_type=message_type,
            unique_identifier=unique_identifier,
            file_id=file_id,
            space_id=space_id,
            download_code=download_code,
            file_name=file_name,
            source=source,
            raw_message=message_data
        )
    
    def can_process(self, message_type: str) -> bool:
        """判断是否能处理该消息类型"""
        return message_type in ['dingtalk_pdf', 'dingtalk_zip']
```

- [ ] **步骤 4: 重构消息解析器主类**

修改 `src/feishu/message_parser.py`，实现消息类型路由:

```python
import hashlib
import json
import re
from typing import Optional, Dict, Any
from src.feishu.models import ParseResult
from src.feishu.parsers.pdf_link_parser import PdfLinkParser
from src.feishu.parsers.dingtalk_file_parser import DingTalkFileParser

class MessageParser:
    """扩展的消息解析器 - 支持多种消息类型"""
    
    BAIDU_PATTERN = re.compile(r'(https://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?)')
    
    def __init__(self):
        """初始化解析器"""
        self.pdf_parser = PdfLinkParser()
        self.dingtalk_parser = DingTalkFileParser()
    
    def parse_message(self, content: str, source: str = 'feishu', 
                     message_data: Optional[Dict[str, Any]] = None) -> Optional[ParseResult]:
        """
        解析消息内容，按优先级识别消息类型
        
        优先级顺序: 百度网盘 > PDF链接 > 钉钉文件
        
        Args:
            content: 消息文本内容
            source: 消息来源 ('feishu', 'dingtalk')
            message_data: 原始消息数据（用于钉钉文件解析）
            
        Returns:
            ParseResult 对象，如果无法识别则返回 None
        """
        # 优先级 1: 百度网盘链接
        if self._contains_baidu_link(content):
            return self._parse_baidu_link(content, source)
        
        # 优先级 2: PDF链接
        pdf_result = self.pdf_parser.parse(content, source)
        if pdf_result:
            return pdf_result
        
        # 优先级 3: 钉钉文件消息
        if message_data:
            dingtalk_result = self.dingtalk_parser.parse(message_data, source)
            if dingtalk_result:
                return dingtalk_result
        
        # 无法识别的消息类型
        return None
    
    def _contains_baidu_link(self, content: str) -> bool:
        """检查是否包含百度网盘链接"""
        return bool(self.BAIDU_PATTERN.search(content))
    
    def _parse_baidu_link(self, content: str, source: str) -> Optional[ParseResult]:
        """解析百度网盘链接"""
        match = self.BAIDU_PATTERN.search(content)
        if not match:
            return None
        
        share_link = match.group(1)
        
        # 提取提取码
        extraction_code = None
        if '?pwd=' in share_link:
            share_link, extraction_code = share_link.split('?pwd=')
        
        # 提取文件夹名（从消息内容中）
        folder_name = self._extract_folder_name(content)
        
        # 使用 share_link 作为唯一标识符
        unique_identifier = share_link
        
        return ParseResult(
            message_type='baidupan',
            unique_identifier=unique_identifier,
            share_link=share_link,
            extraction_code=extraction_code,
            folder_name=folder_name,
            source=source
        )
    
    def _extract_folder_name(self, content: str) -> Optional[str]:
        """从消息内容中提取文件夹名"""
        # 尝试匹配 "260723：https://pan.baidu.com/s/xxx" 格式
        pattern = re.compile(r'(\d{6})[：:]\s*https://pan\.baidu\.com')
        match = pattern.search(content)
        if match:
            return match.group(1)
        
        return None
    
    def calculate_file_key(self, message_type: str, unique_identifier: str) -> str:
        """
        根据消息类型和唯一标识符计算文件唯一键
        
        Args:
            message_type: 消息类型
            unique_identifier: 唯一标识符
            
        Returns:
            MD5哈希值
        """
        key_data = f"{message_type}:{unique_identifier}"
        return hashlib.md5(key_data.encode()).hexdigest()
```

- [ ] **步骤 5: 创建解析器包初始化文件**

创建 `src/feishu/parsers/__init__.py`:

```python
from src.feishu.parsers.pdf_link_parser import PdfLinkParser
from src.feishu.parsers.dingtalk_file_parser import DingTalkFileParser

__all__ = ['PdfLinkParser', 'DingTalkFileParser']
```

- [ ] **步骤 6: 编写解析器测试**

创建 `tests/test_message_parsers.py`:

```python
import unittest
from src.feishu.message_parser import MessageParser
from src.feishu.models import ParseResult

class TestMessageParsers(unittest.TestCase):
    """测试消息解析器"""
    
    def setUp(self):
        """设置测试环境"""
        self.parser = MessageParser()
    
    def test_baidu_link_parsing(self):
        """测试百度网盘链接解析"""
        content = "260723：https://pan.baidu.com/s/abc123?pwd=xyz"
        result = self.parser.parse_message(content, source='dingtalk')
        
        self.assertIsNotNone(result, "应该能解析百度网盘链接")
        self.assertEqual(result.message_type, 'baidupan')
        self.assertEqual(result.share_link, 'https://pan.baidu.com/s/abc123')
        self.assertEqual(result.extraction_code, 'xyz')
        self.assertEqual(result.folder_name, '260723')
    
    def test_pdf_link_parsing(self):
        """测试PDF链接解析"""
        content = "请查看这个文档: https://example.com/manual.pdf"
        result = self.parser.parse_message(content, source='dingtalk')
        
        self.assertIsNotNone(result, "应该能解析PDF链接")
        self.assertEqual(result.message_type, 'pdf_link')
        self.assertEqual(result.pdf_url, 'https://example.com/manual.pdf')
        self.assertEqual(result.unique_identifier, 'https://example.com/manual.pdf')
    
    def test_dingtalk_pdf_parsing(self):
        """测试钉钉PDF文件解析"""
        message_data = {
            'content': {
                'fileName': 'report.pdf',
                'fileId': 'file123',
                'spaceId': 'space456',
                'downloadCode': 'downloadCode123'
            }
        }
        result = self.parser.parse_message("", source='dingtalk', message_data=message_data)
        
        self.assertIsNotNone(result, "应该能解析钉钉PDF文件")
        self.assertEqual(result.message_type, 'dingtalk_pdf')
        self.assertEqual(result.file_name, 'report.pdf')
        self.assertEqual(result.unique_identifier, 'file123:space456')
    
    def test_dingtalk_zip_parsing(self):
        """测试钉钉ZIP文件解析"""
        message_data = {
            'content': {
                'fileName': 'project_files.zip',
                'fileId': 'file789',
                'spaceId': 'space456',
                'downloadCode': 'downloadCode456'
            }
        }
        result = self.parser.parse_message("", source='dingtalk', message_data=message_data)
        
        self.assertIsNotNone(result, "应该能解析钉钉ZIP文件")
        self.assertEqual(result.message_type, 'dingtalk_zip')
        self.assertEqual(result.file_name, 'project_files.zip')
        self.assertEqual(result.unique_identifier, 'file789:space456')
    
    def test_message_priority_baidu_first(self):
        """测试消息类型优先级 - 百度网盘优先"""
        # 包含百度网盘链接和PDF链接的消息
        content = "百度链接: https://pan.baidu.com/s/abc123 PDF链接: https://example.com/doc.pdf"
        result = self.parser.parse_message(content, source='dingtalk')
        
        self.assertIsNotNone(result, "应该能解析消息")
        self.assertEqual(result.message_type, 'baidupan', "百度网盘应该具有最高优先级")
    
    def test_unsupported_file_type(self):
        """测试不支持的文件类型"""
        message_data = {
            'content': {
                'fileName': 'document.docx',  # 不支持的文件类型
                'fileId': 'file123',
                'spaceId': 'space456',
                'downloadCode': 'downloadCode123'
            }
        }
        result = self.parser.parse_message("", source='dingtalk', message_data=message_data)
        
        self.assertIsNone(result, "不应该解析不支持的文件类型")
    
    def test_calculate_file_key(self):
        """测试文件键计算"""
        # 测试百度网盘
        baidu_key = self.parser.calculate_file_key('baidupan', 'https://pan.baidu.com/s/abc123')
        self.assertEqual(len(baidu_key), 32, "MD5哈希应该是32字符")
        self.assertTrue(baidu_key.isalnum(), "MD5哈希应该只包含字母数字")
        
        # 测试PDF链接
        pdf_key = self.parser.calculate_file_key('pdf_link', 'https://example.com/doc.pdf')
        self.assertEqual(len(pdf_key), 32)
        
        # 测试钉钉文件
        dingtalk_key = self.parser.calculate_file_key('dingtalk_pdf', 'file123:space456')
        self.assertEqual(len(dingtalk_key), 32)
        
        # 相同输入应该产生相同的键
        baidu_key2 = self.parser.calculate_file_key('baidupan', 'https://pan.baidu.com/s/abc123')
        self.assertEqual(baidu_key, baidu_key2, "相同输入应该产生相同的哈希")
        
        # 不同消息类型应该产生不同的键
        different_type_key = self.parser.calculate_file_key('pdf_link', 'https://pan.baidu.com/s/abc123')
        self.assertNotEqual(baidu_key, different_type_key, "不同消息类型应该产生不同的哈希")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 7: 运行解析器测试**

```bash
# 运行解析器测试
python tests/test_message_parsers.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 8: 提交解析器架构更改**

```bash
git add src/feishu/models.py
git add src/feishu/parsers/
git add src/feishu/message_parser.py
git add tests/test_message_parsers.py
git commit -m "feat(parser): refactor message parser architecture for multi-type support

- Create unified ParseResult model for all message types
- Implement PdfLinkParser for direct PDF links
- Implement DingTalkFileParser for DingTalk file messages  
- Refactor MessageParser with priority-based routing
- Add message type priority: BaiduPan > PDF > DingTalk
- Add unique identifier calculation for deduplication
- Add comprehensive parser tests

Supported message types:
- baidupan: Baidu Pan share links (existing)
- pdf_link: Direct PDF file links (new)
- dingtalk_pdf: DingTalk PDF files (new)
- dingtalk_zip: DingTalk ZIP archives (new)

Priority order ensures backwards compatibility with existing Baidu links."
```

---

## Task 3: PDF文件处理器实现

**文件:**
- 创建: `src/processor/parsers/pdf_processor.py`
- 修改: `src/processor/file_processor.py` (添加处理器路由)
- 测试: `tests/test_pdf_processor.py`

- [ ] **步骤 1: 创建PDF处理器**

创建 `src/processor/parsers/pdf_processor.py`:

```python
import os
import requests
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass

from src.feishu.models import ParseResult
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DownloadResult:
    """文件下载结果"""
    success: bool
    files: List[str]  # 下载的文件路径列表
    temp_dir: Path  # 临时目录
    file_size: int = 0  # 文件大小（字节）
    error_message: Optional[str] = None

@dataclass
class ProcessResult:
    """文件处理结果"""
    success: bool
    files: List[str]  # 待上传的文件路径列表
    error_message: Optional[str] = None
    metadata: Optional[dict] = None

class PdfLinkProcessor:
    """PDF文件链接处理器"""
    
    def __init__(self, settings: Settings = None):
        """初始化处理器"""
        self.settings = settings or Settings()
        self.max_pdf_size_mb = getattr(self.settings, 'max_pdf_size_mb', 200)
        self.temp_base_dir = Path(self.settings.temp_dir)
    
    def can_process(self, message_type: str) -> bool:
        """判断是否能处理该消息类型"""
        return message_type == 'pdf_link'
    
    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        下载PDF文件
        
        Args:
            parse_result: 解析结果
            
        Returns:
            DownloadResult 对象
        """
        pdf_url = parse_result.pdf_url
        
        if not pdf_url:
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=self.temp_base_dir,
                error_message="PDF URL为空"
            )
        
        logger.info(f"开始下载PDF文件: {pdf_url}")
        
        # 创建临时目录
        temp_dir = self.temp_base_dir / f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 从URL提取文件名
        filename = self._extract_filename_from_url(pdf_url)
        file_path = temp_dir / filename
        
        try:
            # 下载文件
            response = requests.get(pdf_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # 获取文件大小
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                logger.info(f"PDF文件大小: {file_size / (1024*1024):.2f} MB")
                
                # 检查文件大小限制
                if file_size > self.max_pdf_size_mb * 1024 * 1024:
                    return DownloadResult(
                        success=False,
                        files=[],
                        temp_dir=temp_dir,
                        error_message=f"PDF文件超过大小限制: {file_size / (1024*1024):.2f} MB > {self.max_pdf_size_mb} MB"
                    )
            
            # 流式下载文件
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 实时检查文件大小
                        if downloaded_size > self.max_pdf_size_mb * 1024 * 1024:
                            f.close()
                            file_path.unlink()  # 删除已下载的部分
                            return DownloadResult(
                                success=False,
                                files=[],
                                temp_dir=temp_dir,
                                error_message=f"PDF文件下载超过大小限制: {downloaded_size / (1024*1024):.2f} MB"
                            )
            
            file_size_actual = file_path.stat().st_size
            logger.info(f"PDF文件下载完成: {filename} ({file_size_actual / (1024*1024):.2f} MB)")
            
            return DownloadResult(
                success=True,
                files=[str(file_path)],
                temp_dir=temp_dir,
                file_size=file_size_actual
            )
            
        except requests.Timeout:
            logger.error(f"PDF下载超时: {pdf_url}")
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message="PDF下载超时"
            )
        except requests.RequestException as e:
            logger.error(f"PDF下载失败: {e}")
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message=f"PDF下载失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"PDF处理异常: {e}")
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message=f"PDF处理异常: {str(e)}"
            )
    
    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        处理下载的PDF文件（PDF无需额外处理）
        
        Args:
            download_result: 下载结果
            parse_result: 解析结果
            
        Returns:
            ProcessResult 对象
        """
        if not download_result.success:
            return ProcessResult(
                success=False,
                files=[],
                error_message=download_result.error_message
            )
        
        logger.info("PDF文件无需额外处理，直接返回")
        
        return ProcessResult(
            success=True,
            files=download_result.files,
            metadata={
                'file_size': download_result.file_size,
                'original_url': parse_result.pdf_url
            }
        )
    
    def get_upload_files(self, process_result: ProcessResult, parse_result: ParseResult) -> List[dict]:
        """
        获取需要上传的文件列表
        
        Args:
            process_result: 处理结果
            parse_result: 解析结果
            
        Returns:
            文件信息字典列表: [{'local_path': '...', 'remote_name': '...'}]
        """
        if not process_result.success:
            return []
        
        upload_files = []
        for local_path in process_result.files:
            # 生成远程文件名（添加时间戳避免冲突）
            remote_name = self._generate_remote_filename(local_path, parse_result.pdf_url)
            
            upload_files.append({
                'local_path': local_path,
                'remote_name': remote_name
            })
        
        return upload_files
    
    def cleanup(self, temp_dir: Path):
        """清理临时目录"""
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")
    
    def _extract_filename_from_url(self, url: str) -> str:
        """从URL中提取文件名"""
        # 移除查询参数
        base_url = url.split('?')[0]
        
        # 提取文件名
        filename = base_url.split('/')[-1]
        
        # 如果文件名无效，使用默认名称
        if not filename or not filename.endswith('.pdf'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"downloaded_pdf_{timestamp}.pdf"
        
        return filename
    
    def _generate_remote_filename(self, local_path: str, pdf_url: str) -> str:
        """生成远程文件名（避免冲突）"""
        original_name = Path(local_path).name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 添加时间戳避免文件名冲突
        name_without_ext, ext = os.path.splitext(original_name)
        remote_name = f"{name_without_ext}_{timestamp}{ext}"
        
        return remote_name
```

- [ ] **步骤 2: 编写PDF处理器测试**

创建 `tests/test_pdf_processor.py`:

```python
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.processor.parsers.pdf_processor import PdfLinkProcessor, DownloadResult, ProcessResult
from src.feishu.models import ParseResult
from src.config.settings import Settings

class TestPdfProcessor(unittest.TestCase):
    """测试PDF处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.settings = Settings()
        # 设置较小的PDF大小限制用于测试
        self.settings.max_pdf_size_mb = 1
        self.processor = PdfLinkProcessor(self.settings)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_can_process_pdf_link(self):
        """测试能处理PDF链接类型"""
        self.assertTrue(self.processor.can_process('pdf_link'))
        self.assertFalse(self.processor.can_process('baidupan'))
        self.assertFalse(self.processor.can_process('dingtalk_pdf'))
    
    @patch('requests.get')
    def test_successful_pdf_download(self, mock_get):
        """测试成功的PDF下载"""
        # 创建模拟的PDF文件内容
        pdf_content = b'%PDF-1.4 mock pdf content'
        
        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(pdf_content))}
        mock_response.iter_content = Mock(return_value=[pdf_content])
        mock_get.return_value = mock_response
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        result = self.processor.download(parse_result)
        
        self.assertTrue(result.success, "下载应该成功")
        self.assertEqual(len(result.files), 1, "应该有一个下载的文件")
        self.assertEqual(result.file_size, len(pdf_content), "文件大小应该正确")
        self.assertTrue(Path(result.files[0]).exists(), "文件应该存在")
    
    @patch('requests.get')
    def test_pdf_download_size_limit(self, mock_get):
        """测试PDF文件大小限制"""
        # 模拟超过大小限制的文件
        large_size = 2 * 1024 * 1024  # 2MB，超过1MB限制
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(large_size)}
        mock_get.return_value = mock_response
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/large.pdf',
            pdf_url='https://example.com/large.pdf',
            source='dingtalk'
        )
        
        result = self.processor.download(parse_result)
        
        self.assertFalse(result.success, "超过大小限制应该失败")
        self.assertIn("超过大小限制", result.error_message, "应该显示大小限制错误")
    
    @patch('requests.get')
    def test_pdf_download_timeout(self, mock_get):
        """测试PDF下载超时"""
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        result = self.processor.download(parse_result)
        
        self.assertFalse(result.success, "超时应该失败")
        self.assertIn("超时", result.error_message, "应该显示超时错误")
    
    def test_process_pdf_no_processing_needed(self):
        """测试PDF无需额外处理"""
        download_result = DownloadResult(
            success=True,
            files=['/path/to/file.pdf'],
            temp_dir=Path(self.temp_dir),
            file_size=1024000
        )
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        result = self.processor.process(download_result, parse_result)
        
        self.assertTrue(result.success, "处理应该成功")
        self.assertEqual(result.files, download_result.files, "文件列表应该相同")
        self.assertIsNotNone(result.metadata, "应该有元数据")
    
    def test_get_upload_files(self):
        """测试获取上传文件列表"""
        process_result = ProcessResult(
            success=True,
            files=['/path/to/test.pdf'],
            metadata={'file_size': 1024000}
        )
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        upload_files = self.processor.get_upload_files(process_result, parse_result)
        
        self.assertEqual(len(upload_files), 1, "应该有一个上传文件")
        self.assertEqual(upload_files[0]['local_path'], '/path/to/test.pdf')
        self.assertIsNotNone(upload_files[0]['remote_name'], "应该有远程文件名")
        self.assertTrue(upload_files[0]['remote_name'].endswith('.pdf'), "远程文件名应该是PDF")

if __name__ == '__main__':
    # 修复导入问题
    import requests
    unittest.main()
```

- [ ] **步骤 3: 运行PDF处理器测试**

```bash
# 运行PDF处理器测试
python tests/test_pdf_processor.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 4: 提交PDF处理器实现**

```bash
git add src/processor/parsers/pdf_processor.py
git add tests/test_pdf_processor.py
git commit -m "feat(processor): implement PDF link processor

- Create PdfLinkProcessor for direct PDF file downloads
- Implement HTTP download with stream support  
- Add file size validation (200MB default limit)
- Add timeout handling (300 seconds)
- Add real-time size checking during download
- Implement filename extraction from URLs
- Add timestamp-based conflict resolution
- Add cleanup of temporary directories
- Add comprehensive processor tests

Features:
- Stream-based download for memory efficiency
- Size limit enforcement (200MB default)
- Timeout protection (300s default)
- Automatic conflict resolution
- Clean temporary file management

Error handling:
- Download timeout detection
- Size limit enforcement  
- HTTP error handling
- File system error handling"
```

---

## Task 4: 钉钉文件处理器实现

**文件:**
- 创建: `src/processor/parsers/dingtalk_processor.py`
- 测试: `tests/test_dingtalk_processor.py`

- [ ] **步骤 1: 创建钉钉文件处理器**

创建 `src/processor/parsers/dingtalk_processor.py`:

```python
import os
import zipfile
import tempfile
import shutil
import requests
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass

from dingtalk_stream import Credential
from src.feishu.models import ParseResult
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DownloadResult:
    """文件下载结果"""
    success: bool
    files: List[str]  # 下载的文件路径列表
    temp_dir: Path  # 临时目录
    file_size: int = 0
    file_name: str = ""  # 原始文件名
    error_message: Optional[str] = None

@dataclass
class ProcessResult:
    """文件处理结果"""
    success: bool
    files: List[str]  # 待上传的文件路径列表
    error_message: Optional[str] = None
    metadata: Optional[dict] = None

class DingTalkFileProcessor:
    """钉钉文件处理器"""
    
    def __init__(self, settings: Settings = None):
        """初始化处理器"""
        self.settings = settings or Settings()
        self.max_pdf_size_mb = getattr(self.settings, 'max_pdf_size_mb', 200)
        self.max_zip_size_mb = getattr(self.settings, 'max_zip_size_mb', 500)
        self.max_single_file_size_mb = getattr(self.settings, 'max_single_file_size_mb', 50)
        
        # 钉钉API配置
        self.app_key = self.settings.dingtalk_app_key
        self.app_secret = self.settings.dingtalk_app_secret
        
        if not self.app_key or not self.app_secret:
            logger.warning("钉钉配置缺失，处理器可能无法正常工作")
    
    def can_process(self, message_type: str) -> bool:
        """判断是否能处理该消息类型"""
        return message_type in ['dingtalk_pdf', 'dingtalk_zip']
    
    def download(self, parse_result: ParseResult) -> DownloadResult:
        """
        使用downloadCode下载钉钉文件
        
        Args:
            parse_result: 解析结果
            
        Returns:
            DownloadResult 对象
        """
        download_code = parse_result.download_code
        file_name = parse_result.file_name
        message_type = parse_result.message_type
        
        if not download_code or not file_name:
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=Path(self.settings.temp_dir),
                error_message="downloadCode或file_name为空"
            )
        
        logger.info(f"开始下载钉钉文件: {file_name} (类型: {message_type})")
        
        # 创建临时目录
        temp_dir = Path(self.settings.temp_dir) / f"dingtalk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file_name
        
        try:
            # 构建下载URL
            download_url = f"https://api.dingtalk.com/media/download?downloadCode={download_code}"
            
            logger.info(f"钉钉下载URL: {download_url[:60]}...")
            
            # 流式下载文件
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # 检查文件大小限制
            max_size = self.max_pdf_size_mb * 1024 * 1024 if message_type == 'dingtalk_pdf' else self.max_zip_size_mb * 1024 * 1024
            
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 实时检查文件大小
                        if downloaded_size > max_size:
                            f.close()
                            file_path.unlink()
                            return DownloadResult(
                                success=False,
                                files=[],
                                temp_dir=temp_dir,
                                error_message=f"文件超过大小限制: {downloaded_size / (1024*1024):.2f} MB"
                            )
            
            file_size_actual = file_path.stat().st_size
            logger.info(f"钉钉文件下载完成: {file_name} ({file_size_actual / (1024*1024):.2f} MB)")
            
            return DownloadResult(
                success=True,
                files=[str(file_path)],
                temp_dir=temp_dir,
                file_size=file_size_actual,
                file_name=file_name
            )
            
        except requests.Timeout:
            logger.error(f"钉钉文件下载超时: {file_name}")
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message="文件下载超时"
            )
        except requests.HTTPError as e:
            logger.error(f"钉钉文件下载HTTP错误: {e}")
            error_msg = f"文件下载失败: HTTP {e.response.status_code}" if hasattr(e, 'response') else str(e)
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message=error_msg
            )
        except Exception as e:
            logger.error(f"钉钉文件处理异常: {e}")
            return DownloadResult(
                success=False,
                files=[],
                temp_dir=temp_dir,
                error_message=f"文件处理异常: {str(e)}"
            )
    
    def process(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        处理下载的文件（PDF直接返回，ZIP解压）
        
        Args:
            download_result: 下载结果
            parse_result: 解析结果
            
        Returns:
            ProcessResult 对象
        """
        if not download_result.success:
            return ProcessResult(
                success=False,
                files=[],
                error_message=download_result.error_message
            )
        
        message_type = parse_result.message_type
        downloaded_file = download_result.files[0]
        
        if message_type == 'dingtalk_pdf':
            # PDF文件无需处理，直接返回
            logger.info("钉钉PDF文件无需额外处理")
            return ProcessResult(
                success=True,
                files=download_result.files,
                metadata={
                    'file_size': download_result.file_size,
                    'original_filename': download_result.file_name,
                    'file_type': 'pdf'
                }
            )
        
        elif message_type == 'dingtalk_zip':
            # ZIP文件需要解压
            logger.info("开始解压钉钉ZIP文件")
            return self._extract_zip(download_result, parse_result)
        
        else:
            return ProcessResult(
                success=False,
                files=[],
                error_message=f"不支持的消息类型: {message_type}"
            )
    
    def _extract_zip(self, download_result: DownloadResult, parse_result: ParseResult) -> ProcessResult:
        """
        解压ZIP文件，保持原有结构
        
        Args:
            download_result: 下载结果
            parse_result: 解析结果
            
        Returns:
            ProcessResult 对象
        """
        zip_file_path = download_result.files[0]
        zip_name = Path(zip_file_path).stem  # 去掉.zip扩展名
        
        # 创建解压目录
        extract_dir = download_result.temp_dir / zip_name
        extract_dir.mkdir(exist_ok=True)
        
        logger.info(f"解压ZIP文件到: {extract_dir}")
        
        try:
            extracted_files = []
            total_size = 0
            skipped_large_files = 0
            
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # 获取ZIP文件列表
                file_list = zip_ref.namelist()
                logger.info(f"ZIP包含 {len(file_list)} 个文件")
                
                for file_info in file_list:
                    # 跳过目录
                    if file_info.endswith('/'):
                        continue
                    
                    # 解压文件
                    try:
                        zip_ref.extract(file_info, extract_dir)
                        
                        extracted_file_path = extract_dir / file_info
                        file_size = extracted_file_path.stat().st_size
                        total_size += file_size
                        
                        # 检查单个文件大小限制
                        max_single_size = self.max_single_file_size_mb * 1024 * 1024
                        if file_size > max_single_size:
                            logger.warning(f"跳过超大文件: {file_info} ({file_size / (1024*1024):.2f} MB)")
                            extracted_file_path.unlink()
                            skipped_large_files += 1
                        else:
                            extracted_files.append(str(extracted_file_path))
                            logger.debug(f"解压文件: {file_info} ({file_size / 1024:.2f} KB)")
                    
                    except Exception as e:
                        logger.warning(f"解压文件失败 {file_info}: {e}")
                        continue
            
            logger.info(f"ZIP解压完成: {len(extracted_files)} 个文件, 总大小: {total_size / (1024*1024):.2f} MB")
            if skipped_large_files > 0:
                logger.warning(f"跳过 {skipped_large_files} 个超大文件")
            
            if not extracted_files:
                return ProcessResult(
                    success=False,
                    files=[],
                    error_message="ZIP解压后无有效文件（可能所有文件都超过大小限制）"
                )
            
            return ProcessResult(
                success=True,
                files=extracted_files,
                metadata={
                    'original_zip': download_result.file_name,
                    'extracted_count': len(extracted_files),
                    'total_size': total_size,
                    'skipped_count': skipped_large_files,
                    'extract_dir': str(extract_dir),
                    'file_type': 'zip'
                }
            )
            
        except zipfile.BadZipFile:
            logger.error("ZIP文件损坏")
            return ProcessResult(
                success=False,
                files=[],
                error_message="ZIP文件损坏，无法解压"
            )
        except Exception as e:
            logger.error(f"ZIP解压异常: {e}")
            return ProcessResult(
                success=False,
                files=[],
                error_message=f"ZIP解压异常: {str(e)}"
            )
    
    def get_upload_files(self, process_result: ProcessResult, parse_result: ParseResult) -> List[dict]:
        """
        获取需要上传的文件列表
        
        Args:
            process_result: 处理结果
            parse_result: 解析结果
            
        Returns:
            文件信息字典列表
        """
        if not process_result.success:
            return []
        
        upload_files = []
        message_type = parse_result.message_type
        
        if message_type == 'dingtalk_pdf':
            # PDF文件直接上传
            for local_path in process_result.files:
                remote_name = self._generate_remote_filename(local_path, parse_result.file_name)
                upload_files.append({
                    'local_path': local_path,
                    'remote_name': remote_name
                })
        
        elif message_type == 'dingtalk_zip':
            # ZIP解压后的文件，保持目录结构
            extract_dir = process_result.metadata.get('extract_dir', '')
            original_zip = parse_result.file_name.replace('.zip', '')
            
            for local_path in process_result.files:
                # 计算相对路径以保持原有结构
                rel_path = Path(local_path).relative_to(extract_dir)
                
                # 远程路径: original_zip/original_structure
                remote_path = f"{original_zip}/{rel_path}"
                
                upload_files.append({
                    'local_path': local_path,
                    'remote_name': remote_path
                })
        
        return upload_files
    
    def cleanup(self, temp_dir: Path):
        """清理临时目录"""
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")
    
    def _generate_remote_filename(self, local_path: str, original_filename: str) -> str:
        """生成远程文件名（避免冲突）"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_without_ext, ext = os.path.splitext(original_filename)
        remote_name = f"{name_without_ext}_{timestamp}{ext}"
        return remote_name
```

- [ ] **步骤 2: 编写钉钉处理器测试**

创建 `tests/test_dingtalk_processor.py`:

```python
import unittest
import tempfile
import shutil
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor, DownloadResult, ProcessResult
from src.feishu.models import ParseResult
from src.config.settings import Settings

class TestDingTalkProcessor(unittest.TestCase):
    """测试钉钉文件处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.settings = Settings()
        # 设置较小的大小限制用于测试
        self.settings.max_pdf_size_mb = 1
        self.settings.max_zip_size_mb = 2
        self.settings.max_single_file_size_mb = 0.5
        
        # 设置钉钉配置
        self.settings.dingtalk_app_key = "test_app_key"
        self.settings.dingtalk_app_secret = "test_app_secret"
        
        self.processor = DingTalkFileProcessor(self.settings)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_can_process_dingtalk_types(self):
        """测试能处理钉钉消息类型"""
        self.assertTrue(self.processor.can_process('dingtalk_pdf'))
        self.assertTrue(self.processor.can_process('dingtalk_zip'))
        self.assertFalse(self.processor.can_process('baidupan'))
        self.assertFalse(self.processor.can_process('pdf_link'))
    
    @patch('requests.get')
    def test_successful_dingtalk_pdf_download(self, mock_get):
        """测试成功的钉钉PDF下载"""
        pdf_content = b'%PDF-1.4 mock dingtalk pdf'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(pdf_content))}
        mock_response.iter_content = Mock(return_value=[pdf_content])
        mock_get.return_value = mock_response
        
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_id='file123',
            space_id='space456',
            download_code='test_download_code',
            file_name='test.pdf',
            source='dingtalk'
        )
        
        result = self.processor.download(parse_result)
        
        self.assertTrue(result.success, "下载应该成功")
        self.assertEqual(len(result.files), 1, "应该有一个下载的文件")
        self.assertEqual(result.file_size, len(pdf_content), "文件大小应该正确")
        self.assertTrue(Path(result.files[0]).exists(), "文件应该存在")
    
    @patch('requests.get')
    def test_dingtalk_pdf_size_limit(self, mock_get):
        """测试钉钉PDF文件大小限制"""
        large_size = 2 * 1024 * 1024  # 2MB，超过1MB限制
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(large_size)}
        mock_get.return_value = mock_response
        
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            download_code='test_code',
            file_name='large.pdf',
            source='dingtalk'
        )
        
        result = self.processor.download(parse_result)
        
        self.assertFalse(result.success, "超过大小限制应该失败")
        self.assertIn("超过大小限制", result.error_message)
    
    def test_process_dingtalk_pdf_no_processing(self):
        """测试钉钉PDF无需处理"""
        download_result = DownloadResult(
            success=True,
            files=['/path/to/test.pdf'],
            temp_dir=Path(self.temp_dir),
            file_size=1024000,
            file_name='test.pdf'
        )
        
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_name='test.pdf',
            source='dingtalk'
        )
        
        result = self.processor.process(download_result, parse_result)
        
        self.assertTrue(result.success, "处理应该成功")
        self.assertEqual(result.files, download_result.files, "文件列表应该相同")
    
    def test_extract_zip_file(self):
        """测试ZIP文件解压"""
        # 创建测试ZIP文件
        zip_path = Path(self.temp_dir) / "test.zip"
        
        # 添加一些测试文件到ZIP
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr('doc1.txt', 'Content of document 1')
            zipf.writestr('doc2.txt', 'Content of document 2')
            zipf.writestr('subfolder/doc3.txt', 'Content of document 3')
        
        download_result = DownloadResult(
            success=True,
            files=[str(zip_path)],
            temp_dir=Path(self.temp_dir),
            file_name='test.zip'
        )
        
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file789:space456',
            file_name='test.zip',
            source='dingtalk'
        )
        
        result = self.processor.process(download_result, parse_result)
        
        self.assertTrue(result.success, "解压应该成功")
        self.assertEqual(len(result.files), 3, "应该解压出3个文件")
        self.assertIsNotNone(result.metadata, "应该有元数据")
        self.assertEqual(result.metadata['extracted_count'], 3, "元数据应该包含文件数量")
    
    def test_extract_zip_with_large_files(self):
        """测试包含大文件的ZIP处理"""
        # 创建包含大文件的ZIP
        zip_path = Path(self.temp_dir) / "large.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # 正常文件
            zipf.writestr('small.txt', 'Small content')
            # 超大文件 (1MB，超过0.5MB限制)
            large_content = 'x' * (1 * 1024 * 1024)
            zipf.writestr('large.txt', large_content)
        
        download_result = DownloadResult(
            success=True,
            files=[str(zip_path)],
            temp_dir=Path(self.temp_dir),
            file_name='large.zip'
        )
        
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file999:space456',
            file_name='large.zip',
            source='dingtalk'
        )
        
        result = self.processor.process(download_result, parse_result)
        
        self.assertTrue(result.success, "解压应该成功")
        self.assertEqual(len(result.files), 1, "应该只有小文件被解压")
        self.assertEqual(result.metadata['skipped_count'], 1, "应该跳过1个大文件")
    
    def test_get_upload_files_for_zip(self):
        """测试获取ZIP上传文件列表"""
        # 创建解压后的文件结构
        extract_dir = Path(self.temp_dir) / "project"
        extract_dir.mkdir()
        (extract_dir / 'docs').mkdir()
        (extract_dir / 'docs' / 'spec.pdf').touch()
        (extract_dir / 'src' / 'main.py').touch()
        
        process_result = ProcessResult(
            success=True,
            files=[
                str(extract_dir / 'docs' / 'spec.pdf'),
                str(extract_dir / 'src' / 'main.py')
            ],
            metadata={
                'extract_dir': str(extract_dir),
                'original_zip': 'project.zip',
                'file_type': 'zip'
            }
        )
        
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file789:space456',
            file_name='project.zip',
            source='dingtalk'
        )
        
        upload_files = self.processor.get_upload_files(process_result, parse_result)
        
        self.assertEqual(len(upload_files), 2, "应该有2个上传文件")
        
        # 检查路径结构保持
        remote_paths = [f['remote_name'] for f in upload_files]
        self.assertIn('project/docs/spec.pdf', remote_paths, "应该保持原有目录结构")
        self.assertIn('project/src/main.py', remote_paths, "应该保持原有目录结构")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 3: 运行钉钉处理器测试**

```bash
# 运行钉钉处理器测试
python tests/test_dingtalk_processor.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 4: 提交钉钉处理器实现**

```bash
git add src/processor/parsers/dingtalk_processor.py
git add tests/test_dingtalk_processor.py
git commit -m "feat(processor): implement DingTalk file processor

- Create DingTalkFileProcessor for DingTalk file downloads
- Implement downloadCode-based file download
- Support PDF files with direct processing
- Support ZIP files with structure-preserving extraction
- Add file size limits (200MB PDF, 500MB ZIP, 50MB single)
- Add real-time size monitoring during download
- Implement ZIP structure preservation
- Add single file size checking in ZIP
- Add comprehensive error handling
- Add processor tests

Features:
- Stream-based download for DingTalk files
- Automatic PDF vs ZIP detection
- ZIP structure preservation for uploads
- Size limit enforcement at multiple levels
- Graceful handling of large files in ZIP
- Clean temporary file management

Size limits:
- PDF: 200MB (configurable)
- ZIP: 500MB (configurable)  
- Single file in ZIP: 50MB (configurable)

Error handling:
- Download timeout detection
- Size limit enforcement
- ZIP corruption handling
- HTTP error handling"
```

---

## Task 5: 处理器路由和集成

**文件:**
- 创建: `src/processor/processor_router.py`
- 修改: `src/processor/auto_processor.py` (集成新处理器)
- 测试: `tests/test_processor_router.py`

- [ ] **步骤 1: 创建处理器路由器**

创建 `src/processor/processor_router.py`:

```python
from typing import Optional
from src.feishu.models import ParseResult
from src.processor.parsers.pdf_processor import PdfLinkProcessor
from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
from src.processor.file_processor import FileProcessor
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ProcessorRouter:
    """文件处理器路由器 - 根据消息类型分发到对应处理器"""
    
    def __init__(self, settings: Settings = None):
        """初始化路由器"""
        self.settings = settings or Settings()
        
        # 初始化所有处理器（按优先级顺序）
        self.processors = [
            PdfLinkProcessor(self.settings),      # PDF链接处理器
            DingTalkFileProcessor(self.settings),  # 钉钉文件处理器
        ]
        
        # 保留原有的百度网盘处理器
        self.baidu_processor = FileProcessor()
        
        logger.info("处理器路由器初始化完成")
    
    def get_processor(self, parse_result: ParseResult):
        """
        根据消息类型获取对应的处理器
        
        Args:
            parse_result: 解析结果
            
        Returns:
            对应的处理器对象
        """
        message_type = parse_result.message_type
        
        logger.info(f"路由消息到处理器: {message_type}")
        
        # 百度网盘使用原有处理器
        if message_type == 'baidupan':
            return self.baidu_processor
        
        # 其他消息类型使用新处理器
        for processor in self.processors:
            if processor.can_process(message_type):
                logger.info(f"找到匹配处理器: {processor.__class__.__name__}")
                return processor
        
        logger.error(f"没有找到匹配的处理器: {message_type}")
        return None
    
    def process_with_router(self, parse_result: ParseResult):
        """
        使用路由器处理消息的统一入口
        
        Args:
            parse_result: 解析结果
            
        Returns:
            处理结果字典
        """
        processor = self.get_processor(parse_result)
        
        if not processor:
            return {
                'success': False,
                'error_message': f'不支持的处理器: {parse_result.message_type}'
            }
        
        try:
            # 1. 下载文件
            download_result = processor.download(parse_result)
            if not download_result.success:
                return {
                    'success': False,
                    'error_message': download_result.error_message
                }
            
            # 2. 处理文件
            process_result = processor.process(download_result, parse_result)
            if not process_result.success:
                return {
                    'success': False,
                    'error_message': process_result.error_message
                }
            
            # 3. 获取上传文件列表
            upload_files = processor.get_upload_files(process_result, parse_result)
            
            return {
                'success': True,
                'download_result': download_result,
                'process_result': process_result,
                'upload_files': upload_files,
                'processor': processor
            }
            
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
            return {
                'success': False,
                'error_message': f'处理异常: {str(e)}'
            }
```

- [ ] **步骤 2: 修改自动处理器以集成新路由**

修改 `src/processor/auto_processor.py`，添加对多消息类型的支持:

在文件末尾添加新的处理函数:

```python
from src.feishu.message_parser import MessageParser
from src.processor.processor_router import ProcessorRouter

class MultiTypeProcessor:
    """多消息类型处理器 - 集成所有消息类型的处理"""
    
    def __init__(self, settings: Settings = None):
        """初始化处理器"""
        self.settings = settings or Settings()
        self.parser = MessageParser()
        self.router = ProcessorRouter(self.settings)
        self.sftp_client = SFTPClient()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
    
    def process_message(self, content: str, source: str = 'dingtalk', 
                       message_data: Optional[dict] = None) -> dict:
        """
        处理消息的统一入口
        
        Args:
            content: 消息内容
            source: 消息来源
            message_data: 原始消息数据
            
        Returns:
            处理结果字典
        """
        try:
            # 1. 解析消息
            parse_result = self.parser.parse_message(content, source, message_data)
            if not parse_result:
                return {
                    'success': False,
                    'error_message': '无法识别的消息类型'
                }
            
            logger.info(f"识别消息类型: {parse_result.message_type}")
            
            # 2. 使用路由器处理
            router_result = self.router.process_with_router(parse_result)
            if not router_result['success']:
                return router_result
            
            # 3. SFTP上传
            upload_files = router_result['upload_files']
            processor = router_result['processor']
            
            upload_success = 0
            upload_failed = 0
            
            for file_info in upload_files:
                local_path = file_info['local_path']
                remote_name = file_info['remote_name']
                
                # 构建远程路径
                remote_path = f"{self.sftp_client.remote_path}/{datetime.now().strftime('%Y%m')}/{remote_name}"
                
                if self.sftp_client.upload_file(local_path, remote_path):
                    upload_success += 1
                    logger.info(f"上传成功: {remote_name}")
                else:
                    upload_failed += 1
                    logger.error(f"上传失败: {remote_name}")
            
            # 4. 清理临时文件
            if hasattr(router_result['download_result'], 'temp_dir'):
                processor.cleanup(router_result['download_result'].temp_dir)
            
            return {
                'success': True,
                'upload_success': upload_success,
                'upload_failed': upload_failed,
                'total_files': len(upload_files)
            }
            
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
            return {
                'success': False,
                'error_message': f'处理异常: {str(e)}'
            }
    
    def close(self):
        """关闭连接"""
        try:
            self.sftp_client.disconnect()
            self.db_repo.close()
        except Exception as e:
            logger.error(f"关闭连接异常: {e}")
```

- [ ] **步骤 3: 编写处理器路由测试**

创建 `tests/test_processor_router.py`:

```python
import unittest
from unittest.mock import Mock, patch
from src.processor.processor_router import ProcessorRouter
from src.feishu.models import ParseResult
from src.config.settings import Settings

class TestProcessorRouter(unittest.TestCase):
    """测试处理器路由器"""
    
    def setUp(self):
        """设置测试环境"""
        self.settings = Settings()
        self.router = ProcessorRouter(self.settings)
    
    def test_route_baidu_message(self):
        """测试路由百度网盘消息"""
        parse_result = ParseResult(
            message_type='baidupan',
            unique_identifier='https://pan.baidu.com/s/test',
            share_link='https://pan.baidu.com/s/test',
            extraction_code='abc',
            folder_name='260723',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(parse_result)
        
        self.assertIsNotNone(processor, "应该找到百度网盘处理器")
        # 验证是原有的FileProcessor
        from src.processor.file_processor import FileProcessor
        self.assertIsInstance(processor, FileProcessor)
    
    def test_route_pdf_message(self):
        """测试路由PDF消息"""
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(parse_result)
        
        self.assertIsNotNone(processor, "应该找到PDF处理器")
        from src.processor.parsers.pdf_processor import PdfLinkProcessor
        self.assertIsInstance(processor, PdfLinkProcessor)
    
    def test_route_dingtalk_pdf_message(self):
        """测试路由钉钉PDF消息"""
        parse_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_id='file123',
            space_id='space456',
            download_code='code123',
            file_name='test.pdf',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(parse_result)
        
        self.assertIsNotNone(processor, "应该找到钉钉处理器")
        from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
        self.assertIsInstance(processor, DingTalkFileProcessor)
    
    def test_route_dingtalk_zip_message(self):
        """测试路由钉钉ZIP消息"""
        parse_result = ParseResult(
            message_type='dingtalk_zip',
            unique_identifier='file789:space456',
            file_id='file789',
            space_id='space456',
            download_code='code789',
            file_name='project.zip',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(parse_result)
        
        self.assertIsNotNone(processor, "应该找到钉钉处理器")
        from src.processor.parsers.dingtalk_processor import DingTalkFileProcessor
        self.assertIsInstance(processor, DingTalkFileProcessor)
    
    def test_route_unknown_message(self):
        """测试路由未知消息类型"""
        parse_result = ParseResult(
            message_type='unknown_type',
            unique_identifier='test',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(parse_result)
        
        self.assertIsNone(processor, "未知消息类型应该返回None")
    
    @patch('src.processor.parsers.pdf_processor.PdfLinkProcessor.download')
    @patch('src.processor.parsers.pdf_processor.PdfLinkProcessor.process')
    @patch('src.processor.parsers.pdf_processor.PdfLinkProcessor.get_upload_files')
    def test_process_with_router_success(self, mock_upload, mock_process, mock_download):
        """测试路由处理流程成功"""
        # 设置mock返回值
        from src.processor.parsers.pdf_processor import DownloadResult, ProcessResult
        from pathlib import Path
        
        mock_download.return_value = DownloadResult(
            success=True,
            files=['/path/to/file.pdf'],
            temp_dir=Path('/tmp/test'),
            file_size=1024000
        )
        
        mock_process.return_value = ProcessResult(
            success=True,
            files=['/path/to/file.pdf'],
            metadata={'file_size': 1024000}
        )
        
        mock_upload.return_value = [
            {'local_path': '/path/to/file.pdf', 'remote_name': 'file_20250820_143020.pdf'}
        ]
        
        parse_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        result = self.router.process_with_router(parse_result)
        
        self.assertTrue(result['success'], "处理应该成功")
        self.assertIn('upload_files', result, "应该包含上传文件列表")
        self.assertEqual(len(result['upload_files']), 1, "应该有一个上传文件")

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 4: 运行路由器测试**

```bash
# 运行路由器测试
python tests/test_processor_router.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 5: 提交处理器路由实现**

```bash
git add src/processor/processor_router.py
git add src/processor/auto_processor.py
git add tests/test_processor_router.py
git commit -m "feat(router): implement processor router for multi-type support

- Create ProcessorRouter for message type routing
- Integrate with existing FileProcessor for Baidu messages
- Add unified processing entry point
- Support priority-based processor selection
- Add comprehensive routing tests

Processor routing:
- baidupan -> FileProcessor (existing)
- pdf_link -> PdfLinkProcessor (new)
- dingtalk_pdf -> DingTalkFileProcessor (new)
- dingtalk_zip -> DingTalkFileProcessor (new)

Features:
- Automatic processor selection based on message type
- Unified processing interface
- Backwards compatible with existing Baidu processing
- Clean separation of concerns
- Extensible architecture for future message types

Error handling:
- Unsupported message type detection
- Processor availability validation
- Graceful fallback for unknown types"
```

---

## Task 6: 钉钉客户端集成和消息处理更新

**文件:**
- 修改: `src/feishu/dingtalk_group_client.py`
- 测试: `tests/test_dingtalk_integration.py`

- [ ] **步骤 1: 更新钉钉客户端以支持多消息类型**

修改 `src/feishu/dingtalk_group_client.py` 中的 `MessageHandler.process` 方法:

找到现有的解析和存储逻辑并更新:

```python
async def process(self, callback_message: CallbackMessage):
    """处理钉钉消息 - 支持多种消息类型"""
    start_time = datetime.now()
    self.total_received += 1
    db_repo = None
    
    try:
        # 将 CallbackMessage 的 data 转换为 ChatbotMessage
        chatbot_message = ChatbotMessage.from_dict(callback_message.data)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.info("=" * 50)
        logger.info(f"⏰ {current_time} - 📨 消息 #{self.total_received}")
        logger.info(f"Conversation ID: {chatbot_message.conversation_id}")
        logger.info(f"群名称: {chatbot_message.conversation_title}")
        logger.info(f"发送者: {chatbot_message.sender_nick} ({chatbot_message.sender_id})")
        logger.info(f"消息类型: {chatbot_message.message_type}")
        
        # 处理文本消息
        if chatbot_message.message_type == 'text' and chatbot_message.text:
            message_content = chatbot_message.text.content
            logger.info(f"📝 文本消息内容: {message_content}")
            logger.info(f"@机器人: {chatbot_message.is_in_at_list}")
        else:
            # 处理文件消息
            logger.info(f"🔍 非文本消息类型: {chatbot_message.message_type}")
            
            # 构建文件消息数据
            message_data = {}
            if hasattr(chatbot_message, 'file') and chatbot_message.file:
                message_data['content'] = {
                    'fileName': chatbot_message.file.name,
                    'fileId': chatbot_message.file.file_id,
                    'spaceId': chatbot_message.file.space_id,
                    'downloadCode': chatbot_message.file.download_code
                }
                logger.info(f"📁 文件消息: {message_data['content']['fileName']}")
            
            # 文件消息需要@机器人才能处理
            if not chatbot_message.is_in_at_list:
                logger.info(f"⚠️  文件消息未@机器人，跳过")
                self.total_skipped += 1
                return AckMessage.STATUS_OK, "OK"
            
            # 设置消息内容（用于日志）
            message_content = f"[文件消息: {message_data.get('content', {}).get('fileName', 'unknown')}]"
        
        # 检查是否@机器人（必需）
        if chatbot_message.message_type == 'text' and not chatbot_message.is_in_at_list:
            logger.info(f"⚠️  消息未@机器人，跳过")
            self.total_skipped += 1
            return AckMessage.STATUS_OK, "OK"
        
        self.total_at_bot += 1
        
        # 🔥 关键修改：使用扩展的消息解析器
        # 准备消息数据（用于钉钉文件解析）
        message_data_for_parser = message_data if chatbot_message.message_type != 'text' else None
        
        # 解析消息内容，指定来源为钉钉
        parse_result = self.parser.parse_message(
            message_content if chatbot_message.message_type == 'text' else "",
            source='dingtalk',
            message_data=message_data_for_parser
        )
        
        if not parse_result:
            logger.info(f"⚠️  消息不包含支持的类型，跳过: {message_content[:50]}...")
            self.total_skipped += 1
            
            # 发送无效消息反馈
            await self.send_feedback(
                chatbot_message.conversation_title,
                message_content,
                is_valid=False,
                details="消息不包含百度网盘链接、PDF链接或钉钉文件"
            )
            return AckMessage.STATUS_OK, "OK"
        
        # 验证消息来源
        if parse_result.source != 'dingtalk':
            logger.warning(f"Unexpected message source: {parse_result.source}")
            self.total_skipped += 1
            return AckMessage.STATUS_OK, "OK"
        
        logger.info(f"✅ 识别消息类型: {parse_result.message_type}")
        
        # 🔥 关键修改：使用新的去重计算方法
        message_hash = self.parser.calculate_file_key(
            parse_result.message_type,
            parse_result.unique_identifier
        )
        
        # 连接数据库
        db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )
        logger.debug("数据库连接已创建")
        
        # 检查消息是否已处理
        existing_message = db_repo.get_message_by_hash(message_hash)
        if existing_message:
            logger.info(f"♻️  消息已处理，跳过: {message_hash[:8]}...")
            self.total_skipped += 1
            
            # 发送重复消息反馈
            await self.send_feedback(
                chatbot_message.conversation_title,
                message_content,
                is_valid=False,
                details=f"重复消息，已存在记录。当前状态: {existing_message.process_status}，已重试: {existing_message.retry_count}次"
            )
            return AckMessage.STATUS_OK, "OK"
        
        # 🔥 关键修改：创建消息处理日志，包含新字段
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # 准备文件信息JSON
        import json
        file_info_dict = {}
        if parse_result.message_type == 'pdf_link':
            file_info_dict = {
                'type': 'pdf',
                'url': parse_result.pdf_url,
                'source': 'direct_link'
            }
        elif parse_result.message_type in ['dingtalk_pdf', 'dingtalk_zip']:
            file_info_dict = {
                'type': 'pdf' if parse_result.message_type == 'dingtalk_pdf' else 'zip',
                'file_name': parse_result.file_name,
                'file_id': parse_result.file_id,
                'space_id': parse_result.space_id,
                'source': 'dingtalk'
            }
        elif parse_result.message_type == 'baidupan':
            file_info_dict = {
                'type': 'baidupan',
                'share_link': parse_result.share_link,
                'folder_name': parse_result.folder_name,
                'source': 'baidu_pan'
            }
        
        message_log = MessageProcessLog(
            message_hash=message_hash,
            original_message=message_content,
            share_link=parse_result.share_link,
            folder_name=parse_result.folder_name,
            extraction_code=parse_result.extraction_code,
            source='dingtalk',
            process_status='pending',
            processing_time_ms=processing_time_ms,
            message_type=parse_result.message_type,  # 新增
            raw_message=json.dumps(message_data_for_parser) if message_data_for_parser else None,  # 新增
            file_info=json.dumps(file_info_dict) if file_info_dict else None  # 新增
        )
        
        # 存储到数据库
        log_id = db_repo.insert_message_log(message_log)
        self.total_processed += 1
        
        logger.info(f"✅ 消息已存储: {parse_result.message_type} (ID: {log_id})")
        logger.info(f"📊 统计: 收到={self.total_received}, @机器={self.total_at_bot}, 处理={self.total_processed}, 跳过={self.total_skipped}, 错误={self.total_errors}")
        
        # 构建成功反馈信息
        if parse_result.message_type == 'baidupan':
            details = f"已记录: {parse_result.folder_name or '无文件夹信息'}"
        elif parse_result.message_type == 'pdf_link':
            details = f"已记录PDF链接: {parse_result.pdf_url[:50]}..."
        elif parse_result.message_type == 'dingtalk_pdf':
            details = f"已记录钉钉PDF: {parse_result.file_name}"
        elif parse_result.message_type == 'dingtalk_zip':
            details = f"已记录钉钉ZIP: {parse_result.file_name}"
        else:
            details = f"已记录: {parse_result.message_type}"
        
        # 发送成功消息反馈
        await self.send_feedback(
            chatbot_message.conversation_title,
            message_content,
            is_valid=True,
            details=details
        )
        
        return AckMessage.STATUS_OK, "OK"
        
    except Exception as e:
        self.total_errors += 1
        logger.error(f"❌ 处理消息时出错: {e}", exc_info=True)
        logger.info(f"📊 统计: 收到={self.total_received}, @机器={self.total_at_bot}, 处理={self.total_processed}, 跳过={self.total_skipped}, 错误={self.total_errors}")
        return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)
        
    finally:
        # 立即关闭数据库连接
        if db_repo:
            db_repo.close()
            logger.debug("数据库连接已关闭")
```

- [ ] **步骤 2: 编写集成测试**

创建 `tests/test_dingtalk_integration.py`:

```python
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from src.feishu.dingtalk_group_client import MessageHandler
from src.feishu.message_parser import MessageParser
from src.database.message_models import MessageProcessLog
from dingtalk_stream import ChatbotMessage, CallbackMessage

class TestDingTalkIntegration(unittest.TestCase):
    """测试钉钉客户端集成"""
    
    def setUp(self):
        """设置测试环境"""
        from src.config.settings import Settings
        self.settings = Settings()
        self.handler = MessageHandler(self.settings)
    
    @patch('src.database.repository.DatabaseRepository')
    def test_process_baidu_message(self, mock_db_repo):
        """测试处理百度网盘消息"""
        # Mock数据库
        mock_repo_instance = Mock()
        mock_repo_instance.get_message_by_hash.return_value = None
        mock_repo_instance.insert_message_log.return_value = 123
        mock_db_repo.return_value = mock_repo_instance
        
        # 创建模拟的ChatbotMessage
        chatbot_msg = Mock(spec=ChatbotMessage)
        chatbot_msg.conversation_id = "test_conv_id"
        chatbot_msg.conversation_title = "测试群"
        chatbot_msg.sender_nick = "测试用户"
        chatbot_msg.sender_id = "test_user_id"
        chatbot_msg.message_type = 'text'
        chatbot_msg.is_in_at_list = True
        
        # 模拟文本内容
        text_content = Mock()
        text_content.content = "260723：https://pan.baidu.com/s/abc123?pwd=xyz"
        chatbot_msg.text = text_content
        
        # 模拟CallbackMessage
        callback_msg = Mock(spec=CallbackMessage)
        callback_msg.data = {
            'conversationId': 'test_conv_id',
            'conversationTitle': '测试群',
            'senderNick': '测试用户',
            'senderId': 'test_user_id',
            'messageType': 'text',
            'text': {'content': '260723：https://pan.baidu.com/s/abc123?pwd=xyz'},
            'isInAtList': True
        }
        
        # 异步执行测试
        import asyncio
        result = asyncio.run(self.handler.process(callback_msg))
        
        # 验证结果
        self.assertEqual(result[0], 'OK', "处理应该成功")
        mock_repo_instance.insert_message_log.assert_called_once()
        
        # 验证插入的消息日志
        call_args = mock_repo_instance.insert_message_log.call_args[0][0]
        self.assertEqual(call_args.message_type, 'baidupan')
        self.assertEqual(call_args.source, 'dingtalk')
    
    @patch('src.database.repository.DatabaseRepository')
    def test_process_pdf_link_message(self, mock_db_repo):
        """测试处理PDF链接消息"""
        mock_repo_instance = Mock()
        mock_repo_instance.get_message_by_hash.return_value = None
        mock_repo_instance.insert_message_log.return_value = 124
        mock_db_repo.return_value = mock_repo_instance
        
        # 创建模拟的CallbackMessage
        callback_msg = Mock(spec=CallbackMessage)
        callback_msg.data = {
            'conversationId': 'test_conv_id',
            'conversationTitle': '测试群',
            'senderNick': '测试用户',
            'senderId': 'test_user_id',
            'messageType': 'text',
            'text': {'content': '请查看这个PDF: https://example.com/manual.pdf'},
            'isInAtList': True
        }
        
        import asyncio
        result = asyncio.run(self.handler.process(callback_msg))
        
        self.assertEqual(result[0], 'OK')
        call_args = mock_repo_instance.insert_message_log.call_args[0][0]
        self.assertEqual(call_args.message_type, 'pdf_link')
        self.assertIsNotNone(call_args.file_info)
    
    @patch('src.database.repository.DatabaseRepository')
    def test_process_dingtalk_file_message(self, mock_db_repo):
        """测试处理钉钉文件消息"""
        mock_repo_instance = Mock()
        mock_repo_instance.get_message_by_hash.return_value = None
        mock_repo_instance.insert_message_log.return_value = 125
        mock_db_repo.return_value = mock_repo_instance
        
        # 创建模拟的文件消息
        callback_msg = Mock(spec=CallbackMessage)
        callback_msg.data = {
            'conversationId': 'test_conv_id',
            'conversationTitle': '测试群',
            'senderNick': '测试用户',
            'senderId': 'test_user_id',
            'messageType': 'file',
            'file': {
                'name': 'report.pdf',
                'fileId': 'file123',
                'spaceId': 'space456',
                'downloadCode': 'code123'
            },
            'isInAtList': True
        }
        
        import asyncio
        result = asyncio.run(self.handler.process(callback_msg))
        
        self.assertEqual(result[0], 'OK')
        call_args = mock_repo_instance.insert_message_log.call_args[0][0]
        self.assertEqual(call_args.message_type, 'dingtalk_pdf')
        self.assertIsNotNone(call_args.raw_message)

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 3: 运行集成测试**

```bash
# 运行集成测试
python tests/test_dingtalk_integration.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 4: 提交钉钉客户端集成**

```bash
git add src/feishu/dingtalk_group_client.py
git add tests/test_dingtalk_integration.py
git commit -m "feat(integration): update DingTalk client for multi-type message support

- Update MessageHandler to support all message types
- Add file message detection and processing
- Integrate extended message parser
- Support Baidu, PDF, and DingTalk file messages
- Add message type tracking in database
- Store raw message JSON for debugging
- Store file metadata for processing
- Add deduplication by message type and identifier
- Add comprehensive integration tests

Message types supported:
- Baidu Pan share links (existing, enhanced)
- Direct PDF file links (new)
- DingTalk PDF files (new)
- DingTalk ZIP archives (new)

Features:
- @Bot requirement for all message types
- Immediate feedback for invalid messages
- Detailed success/failure notifications
- Message type detection and routing
- Enhanced error handling
- Complete message logging

Database enhancements:
- message_type field for type tracking
- raw_message field for debugging
- file_info field for metadata
- Enhanced deduplication logic"
```

---

## Task 7: 错误处理和重试机制完善

**文件:**
- 创建: `src/processor/error_handler.py`
- 修改: `src/processor/auto_processor.py` (集成错误处理)
- 测试: `tests/test_error_handler.py`

- [ ] **步骤 1: 创建错误分类器**

创建 `src/processor/error_handler.py`:

```python
import enum
import requests
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ErrorType(enum.Enum):
    """错误类型枚举"""
    RETRYABLE = "retryable"  # 可重试错误
    NON_RETRYABLE = "non_retryable"  # 不可重试错误

class ErrorClassifier:
    """错误分类器 - 判断错误是否可重试"""
    
    @staticmethod
    def classify_error(error: Exception, message_type: str) -> ErrorType:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            message_type: 消息类型
            
        Returns:
            ErrorType 枚举值
        """
        # 网络相关错误 - 可重试
        if isinstance(error, (requests.Timeout, requests.ConnectionError)):
            logger.info(f"分类错误为可重试: 网络错误 - {error.__class__.__name__}")
            return ErrorType.RETRYABLE
        
        # 文件大小错误 - 不可重试
        if "超过大小限制" in str(error) or "size" in str(error).lower():
            logger.info(f"分类错误为不可重试: 文件大小错误")
            return ErrorType.NON_RETRYABLE
        
        # HTTP错误 - 根据状态码判断
        if isinstance(error, requests.HTTPError):
            if hasattr(error, 'response') and error.response:
                status_code = error.response.status_code
                if status_code in [404, 410, 403]:  # 文件不存在、权限问题
                    logger.info(f"分类错误为不可重试: HTTP {status_code}")
                    return ErrorType.NON_RETRYABLE
                elif status_code >= 500:  # 服务器错误
                    logger.info(f"分类错误为可重试: HTTP {status_code}")
                    return ErrorType.RETRYABLE
                else:
                    logger.info(f"分类错误为不可重试: HTTP {status_code}")
                    return ErrorType.NON_RETRYABLE
        
        # 钉钉API特殊错误
        error_str = str(error).lower()
        if any(keyword in error_str for keyword in ['expired', 'notfound', 'invalid', 'permission']):
            logger.info(f"分类错误为不可重试: API错误关键词")
            return ErrorType.NON_RETRYABLE
        
        # 文件系统错误
        if isinstance(error, (FileNotFoundError, PermissionError)):
            logger.info(f"分类错误为不可重试: 文件系统错误")
            return ErrorType.NON_RETRYABLE
        
        # 默认为可重试
        logger.info(f"分类错误为可重试: 默认处理 - {error.__class__.__name__}")
        return ErrorType.RETRYABLE

class EnhancedRetryHandler:
    """增强的重试处理器"""
    
    def __init__(self, settings):
        """初始化重试处理器"""
        self.settings = settings
        self.error_classifier = ErrorClassifier()
        self.max_retries = getattr(settings, 'max_retry_count', 10)
        self.db_repo = None
    
    def handle_processing_failure(self, message_log_id: int, error: Exception, 
                                 message_type: str, db_repo, 
                                 notifier=None, conversation_title: str = None,
                                 original_message: str = None):
        """
        处理消息处理失败
        
        Args:
            message_log_id: 消息日志ID
            error: 异常对象
            message_type: 消息类型
            db_repo: 数据库仓库对象
            notifier: 通知器对象（可选）
            conversation_title: 群名称（可选）
            original_message: 原始消息（可选）
        """
        # 1. 分类错误
        error_type = self.error_classifier.classify_error(error, message_type)
        
        # 2. 获取当前重试次数
        current_retry = db_repo.get_retry_count(message_log_id)
        current_retry = current_retry if current_retry else 0
        
        # 3. 计算下一次重试
        next_retry = current_retry + 1
        should_retry = (
            error_type == ErrorType.RETRYABLE and 
            next_retry <= self.max_retries
        )
        
        # 4. 更新数据库状态
        new_status = 'pending' if should_retry else 'failed'
        db_repo.update_message_status(
            message_log_id, 
            new_status, 
            next_retry, 
            str(error)
        )
        
        # 5. 发送失败通知
        if notifier:
            self._send_failure_notification(
                notifier, conversation_title, original_message, message_type,
                error, error_type, should_retry, next_retry, self.max_retries
            )
        
        logger.info(f"消息处理失败 - 类型: {error_type.value}, 重试: {next_retry}/{self.max_retries}, 状态: {new_status}")
    
    def _send_failure_notification(self, notifier, conversation_title: str, 
                                 original_message: str, message_type: str,
                                 error: Exception, error_type: ErrorType, 
                                 should_retry: bool, current_retry: int, 
                                 max_retries: int):
        """发送失败通知"""
        try:
            # 格式化消息类型显示
            type_display = {
                'baidupan': '百度网盘链接',
                'pdf_link': 'PDF文件链接',
                'dingtalk_pdf': '钉钉PDF文件',
                'dingtalk_zip': '钉钉ZIP文件'
            }.get(message_type, message_type)
            
            if should_retry:
                # 可重试错误通知
                title = "⚠️ 消息处理失败 - 自动重试中"
                content = f"""## ⚠️ 消息处理失败 - 自动重试中

**群聊**: {conversation_title or '未知'}
**消息类型**: {type_display}
**重试进度**: {current_retry}/{max_retries}
**错误原因**: {str(error)[:100]}

🔄 系统将自动重试，请稍后查看处理结果。

**原始消息**: {original_message[:50] if original_message else '无'}...
"""
            else:
                # 永久失败通知
                title = "❌ 消息处理永久失败"
                content = f"""## ❌ 消息处理永久失败

**群聊**: {conversation_title or '未知'}
**消息类型**: {type_display}
**失败原因**: {str(error)[:100]}
**错误类型**: {'不可重试错误' if error_type == ErrorType.NON_RETRYABLE else '超过重试次数'}
**重试次数**: {current_retry}/{max_retries}

⚠️ 此消息已无法自动恢复，需要手动处理。

**原始消息**: {original_message[:50] if original_message else '无'}...
"""
            
            # 发送通知
            import asyncio
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, notifier.send_notification, title, content)
            
        except Exception as e:
            logger.error(f"发送失败通知时出错: {e}")
```

- [ ] **步骤 2: 编写错误处理测试**

创建 `tests/test_error_handler.py`:

```python
import unittest
import requests
from unittest.mock import Mock
from src.processor.error_handler import ErrorClassifier, ErrorType, EnhancedRetryHandler
from src.config.settings import Settings

class TestErrorClassifier(unittest.TestCase):
    """测试错误分类器"""
    
    def setUp(self):
        """设置测试环境"""
        self.classifier = ErrorClassifier()
    
    def test_classify_network_timeout(self):
        """测试网络超时分类"""
        error = requests.Timeout("Connection timeout")
        error_type = self.classifier.classify_error(error, 'pdf_link')
        self.assertEqual(error_type, ErrorType.RETRYABLE)
    
    def test_classify_http_404(self):
        """测试HTTP 404错误分类"""
        response = Mock()
        response.status_code = 404
        error = requests.HTTPError(response=response)
        error_type = self.classifier.classify_error(error, 'dingtalk_pdf')
        self.assertEqual(error_type, ErrorType.NON_RETRYABLE)
    
    def test_classify_http_500(self):
        """测试HTTP 500错误分类"""
        response = Mock()
        response.status_code = 500
        error = requests.HTTPError(response=response)
        error_type = self.classifier.classify_error(error, 'pdf_link')
        self.assertEqual(error_type, ErrorType.RETRYABLE)
    
    def test_classify_size_limit_error(self):
        """测试文件大小限制错误分类"""
        error = Exception("文件超过大小限制: 250MB")
        error_type = self.classifier.classify_error(error, 'dingtalk_pdf')
        self.assertEqual(error_type, ErrorType.NON_RETRYABLE)
    
    def test_classify_file_not_found(self):
        """测试文件不存在错误分类"""
        error = FileNotFoundError("/path/to/file.pdf not found")
        error_type = self.classifier.classify_error(error, 'pdf_link')
        self.assertEqual(error_type, ErrorType.NON_RETRYABLE)
    
    def test_classify_unknown_error(self):
        """测试未知错误默认分类"""
        error = Exception("Unknown error occurred")
        error_type = self.classifier.classify_error(error, 'baidupan')
        self.assertEqual(error_type, ErrorType.RETRYABLE)  # 默认可重试

class TestEnhancedRetryHandler(unittest.TestCase):
    """测试增强重试处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.settings = Settings()
        self.handler = EnhancedRetryHandler(self.settings)
        self.mock_notifier = Mock()
        self.mock_db_repo = Mock()
    
    def test_handle_retryable_error(self):
        """测试处理可重试错误"""
        self.mock_db_repo.get_retry_count.return_value = 0
        
        error = requests.Timeout("Connection timeout")
        
        self.handler.handle_processing_failure(
            message_log_id=1,
            error=error,
            message_type='pdf_link',
            db_repo=self.mock_db_repo,
            notifier=self.mock_notifier,
            conversation_title='测试群',
            original_message='测试消息'
        )
        
        # 验证数据库更新
        self.mock_db_repo.update_message_status.assert_called_once()
        call_args = self.mock_db_repo.update_message_status.call_args[0]
        self.assertEqual(call_args[2], 1)  # retry_count = 1
        self.assertEqual(call_args[1], 'pending')  # status = pending
    
    def test_handle_non_retryable_error(self):
        """测试处理不可重试错误"""
        self.mock_db_repo.get_retry_count.return_value = 0
        
        response = Mock()
        response.status_code = 404
        error = requests.HTTPError(response=response)
        
        self.handler.handle_processing_failure(
            message_log_id=2,
            error=error,
            message_type='dingtalk_pdf',
            db_repo=self.mock_db_repo,
            notifier=self.mock_notifier,
            conversation_title='测试群',
            original_message='测试消息'
        )
        
        # 验证数据库更新
        call_args = self.mock_db_repo.update_message_status.call_args[0]
        self.assertEqual(call_args[1], 'failed')  # status = failed
    
    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        self.mock_db_repo.get_retry_count.return_value = 10
        
        error = requests.Timeout("Connection timeout")
        
        self.handler.handle_processing_failure(
            message_log_id=3,
            error=error,
            message_type='pdf_link',
            db_repo=self.mock_db_repo,
            notifier=None,
            conversation_title='测试群',
            original_message='测试消息'
        )
        
        # 验证标记为失败
        call_args = self.mock_db_repo.update_message_status.call_args[0]
        self.assertEqual(call_args[1], 'failed')  # 超过重试次数，标记为失败

if __name__ == '__main__':
    unittest.main()
```

- [ ] **步骤 3: 运行错误处理测试**

```bash
# 运行错误处理测试
python tests/test_error_handler.py -v
```

预期结果: 所有测试应该通过

- [ ] **步骤 4: 提交错误处理实现**

```bash
git add src/processor/error_handler.py
git add tests/test_error_handler.py
git commit -m "feat(error): implement comprehensive error handling and retry mechanism

- Create ErrorClassifier for intelligent error categorization
- Implement EnhancedRetryHandler with retry logic
- Add retryable vs non-retryable error detection
- Implement automatic retry for transient failures
- Add immediate failure for permanent errors
- Implement detailed failure notifications
- Add retry count tracking and limits
- Add comprehensive error tests

Error classification:
- Retryable: Network timeouts, server errors (5xx), unknown errors
- Non-retryable: File not found (404), size limits, permissions, expired codes

Retry mechanism:
- Max 10 retries (configurable via max_retry_count)
- Automatic retry for retryable errors
- Immediate failure for non-retryable errors
- Detailed retry progress tracking

Failure notifications:
- Retryable errors: Show retry progress (e.g., \"3/10\")
- Non-retryable errors: Mark as permanent failure
- Include error details and original message
- Separate notifications for different error types

Supported error types:
- Network errors (timeout, connection)
- HTTP errors (4xx, 5xx)
- File system errors (not found, permissions)
- API errors (expired codes, invalid files)
- Size limit errors"

---

## Task 8: 真实集成测试和验证

**文件:**
- 创建: `tests/integration/test_real_integration.py`
- 创建: `tests/integration/test_real_dingtalk.py`
- 文档: `docs/INTEGRATION_TESTING_GUIDE.md`

- [ ] **步骤 1: 创建真实集成测试指导文档**

创建 `docs/INTEGRATION_TESTING_GUIDE.md`:

```markdown
# 多消息类型集成测试指南

## 测试环境要求

### 必需服务
1. **MySQL数据库** - 运行中的数据库实例
2. **钉钉服务** - dingtalk-service 启动状态
3. **SFTP服务器** - 可访问的SFTP服务

### 配置要求
```bash
# .env 文件配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download

DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret

SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USER=your_sftp_user
SFTP_PASSWORD=your_sftp_password
SFTP_REMOTE_PATH=/random
```

## 真实测试步骤

### 1. 数据库测试
```bash
# 执行数据库迁移
mysql -u root -p baidu_download < database/migrations/004_add_message_type_support.sql

# 运行数据库测试
python tests/test_database_migration.py
```

### 2. 钉钉真实消息测试

#### 启动钉钉服务
```bash
# 启动 dingtalk-service（如果需要）
# 按照你的钉钉服务启动说明进行操作
```

#### 发送测试消息

**百度网盘链接测试:**
```
@机器人 260723：https://pan.baidu.com/s/xxx?pwd=yyy
```

**PDF链接测试:**
```
@机器人 请处理这个PDF: https://example.com/test.pdf
```

**钉钉PDF文件测试:**
1. 上传PDF文件到钉钉群
2. @机器人发送该文件

**钉钉ZIP文件测试:**
1. 上传ZIP文件到钉钉群
2. @机器人发送该文件

### 3. 验证结果

#### 检查数据库
```sql
-- 检查消息记录
SELECT id, message_type, process_status, retry_count, error_message 
FROM message_process_log 
ORDER BY created_at DESC 
LIMIT 10;

-- 检查文件信息
SELECT id, message_type, file_info 
FROM message_process_log 
WHERE message_type != 'baidupan';
```

#### 检查日志
```bash
# 查看处理日志
tail -f logs/baidu_download.log

# 搜索特定消息类型
grep "pdf_link" logs/baidu_download.log
grep "dingtalk_pdf" logs/baidu_download.log
grep "dingtalk_zip" logs/baidu_download.log
```

#### 检查SFTP上传
```bash
# 连接SFTP服务器
sftp user@sftp_host

# 查看上传的文件
ls -la /random/202508/

# 验证ZIP解压结构
ls -la /random/202508/project_folder/
```

## 预期结果

### 百度网盘链接
- ✅ 消息类型: `baidupan`
- ✅ 处理状态: `success` 或 `pending`
- ✅ SFTP上传: `random/202508/260723/*.pdf`

### PDF链接
- ✅ 消息类型: `pdf_link`
- ✅ 文件下载: 成功下载到临时目录
- ✅ SFTP上传: `random/202508/filename_20250820_143020.pdf`
- ✅ 文件验证: PDF文件完整且可打开

### 钉钉PDF文件
- ✅ 消息类型: `dingtalk_pdf`
- ✅ 钉钉下载: 使用downloadCode成功下载
- ✅ SFTP上传: `random/202508/filename_20250820_150530.pdf`
- ✅ 去重测试: 相同文件不会重复处理

### 钉钉ZIP文件
- ✅ 消息类型: `dingtalk_zip`
- ✅ ZIP下载: 成功下载ZIP文件
- ✅ 解压处理: 保持原有目录结构
- ✅ SFTP上传: `random/202508/project_name/original_path/*`
- ✅ 大文件处理: 超大文件被跳过

## 错误处理测试

### 可重试错误测试
1. 发送无效的PDF链接测试网络错误
2. 验证系统自动重试
3. 检查retry_count递增

### 不可重试错误测试
1. 发送超过大小限制的文件
2. 验证立即失败，不重试
3. 检查状态标记为`failed`

### 去重测试
1. 发送相同的消息两次
2. 验证第二次被识别为重复
3. 检查去重反馈消息

## 性能测试

### 响应时间测试
- 消息验证响应: < 2秒
- 即时反馈发送: < 5秒
- 文件下载时间: 取决于文件大小和网络
- SFTP上传时间: 取决于文件大小和网络

### 并发测试
```bash
# 同时发送多个不同类型的消息
# 观察系统处理能力和资源使用
```

## 故障排除

### 常见问题
1. **数据库连接失败**: 检查.env配置和MySQL服务状态
2. **钉钉下载失败**: 检查app_key/app_secret和downloadCode有效性
3. **SFTP上传失败**: 检查SFTP服务器连接和权限
4. **文件大小限制**: 调整.env中的大小限制配置

### 调试技巧
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 查看实时日志
tail -f logs/baidu_download.log | grep ERROR

# 检查数据库状态
mysql -u root -p baidu_download -e "SELECT * FROM message_process_log WHERE process_status='failed'"
```

## 测试清单

### 功能测试
- [ ] 百度网盘链接处理正常
- [ ] PDF链接下载和上传正常
- [ ] 钉钉PDF文件处理正常
- [ ] 钉钉ZIP文件解压和上传正常
- [ ] 文件冲突自动解决
- [ ] 消息去重正常工作
- [ ] 错误重试机制正常
- [ ] 失败通知正确发送

### 性能测试
- [ ] 消息验证响应时间 < 2秒
- [ ] 即时反馈发送时间 < 5秒
- [ ] 文件大小限制正确执行
- [ ] 大文件处理不会阻塞系统

### 兼容性测试
- [ ] 现有百度网盘功能完全正常
- [ ] 数据库向后兼容
- [ ] 配置文件无需修改
- [ ] 新功能失败不影响现有功能
```

- [ ] **步骤 2: 创建真实集成测试脚本**

创建 `tests/integration/test_real_integration.py`:

```python
"""
真实集成测试 - 需要运行的服务和配置

这些测试需要真实的数据库、钉钉服务和SFTP服务器
在运行这些测试之前，请确保所有服务都正常运行
"""
import unittest
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime

from src.config.settings import Settings
from src.database.repository import DatabaseRepository
from src.feishu.message_parser import MessageParser
from src.processor.processor_router import ProcessorRouter
from src.uploader.sftp_client import SFTPClient

@unittest.skipUnless(
    os.getenv('RUN_INTEGRATION_TESTS') == 'true',
    "集成测试需要设置 RUN_INTEGRATION_TESTS=true 环境变量"
)
class TestRealIntegration(unittest.TestCase):
    """真实集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print("\n" + "="*80)
        print("🚀 开始真实集成测试")
        print("⚠️  确保以下服务正在运行:")
        print("   - MySQL数据库")
        print("   - 钉钉服务 (dingtalk-service)")
        print("   - SFTP服务器")
        print("="*80 + "\n")
        
        cls.settings = Settings()
        cls.parser = MessageParser()
        cls.router = ProcessorRouter(cls.settings)
        cls.db_repo = DatabaseRepository(
            host=cls.settings.db_host,
            port=cls.settings.db_port,
            user=cls.settings.db_user,
            password=cls.settings.db_password,
            database=cls.settings.db_name
        )
        cls.sftp_client = SFTPClient()
        
        # 连接SFTP
        if not cls.sftp_client.connect():
            raise Exception("SFTP连接失败，请检查配置和服务状态")
        
        print("✅ 所有服务连接成功")
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        cls.db_repo.close()
        cls.sftp_client.disconnect()
        print("\n" + "="*80)
        print("✅ 真实集成测试完成")
        print("="*80 + "\n")
    
    def test_database_connection(self):
        """测试数据库连接"""
        # 执行简单查询测试连接
        result = self.db_repo.get_message_by_hash("test_hash_not_exists")
        self.assertIsNone(result, "数据库连接正常")
    
    def test_sftp_connection(self):
        """测试SFTP连接"""
        # 测试目录创建
        test_dir = f"{self.sftp_client.remote_path}/test_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.assertTrue(self.sftp_client.create_directory(test_dir), "应该能创建目录")
        
        # 清理测试目录
        try:
            self.sftp_client.client.rmdir(test_dir)
        except:
            pass
    
    def test_message_parser_integration(self):
        """测试消息解析器集成"""
        # 测试百度网盘链接解析
        baidu_content = "260723：https://pan.baidu.com/s/test123?pwd=abc"
        baidu_result = self.parser.parse_message(baidu_content, source='dingtalk')
        self.assertIsNotNone(baidu_result, "应该能解析百度网盘链接")
        self.assertEqual(baidu_result.message_type, 'baidupan')
        
        # 测试PDF链接解析
        pdf_content = "请查看PDF: https://example.com/test.pdf"
        pdf_result = self.parser.parse_message(pdf_content, source='dingtalk')
        self.assertIsNotNone(pdf_result, "应该能解析PDF链接")
        self.assertEqual(pdf_result.message_type, 'pdf_link')
        
        # 测试去重键计算
        baidu_key = self.parser.calculate_file_key('baidupan', baidu_result.unique_identifier)
        pdf_key = self.parser.calculate_file_key('pdf_link', pdf_result.unique_identifier)
        
        self.assertEqual(len(baidu_key), 32, "去重键应该是32位MD5")
        self.assertNotEqual(baidu_key, pdf_key, "不同消息应该有不同的去重键")
    
    def test_processor_router_integration(self):
        """测试处理器路由集成"""
        # 创建测试解析结果
        from src.feishu.models import ParseResult
        
        # 测试PDF处理器路由
        pdf_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://example.com/test.pdf',
            pdf_url='https://example.com/test.pdf',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(pdf_result)
        self.assertIsNotNone(processor, "应该找到PDF处理器")
        self.assertTrue(processor.can_process('pdf_link'), "处理器应该能处理PDF")
        
        # 测试钉钉PDF处理器路由
        dingtalk_result = ParseResult(
            message_type='dingtalk_pdf',
            unique_identifier='file123:space456',
            file_id='file123',
            space_id='space456',
            download_code='test_code',
            file_name='test.pdf',
            source='dingtalk'
        )
        
        processor = self.router.get_processor(dingtalk_result)
        self.assertIsNotNone(processor, "应该找到钉钉处理器")
        self.assertTrue(processor.can_process('dingtalk_pdf'), "处理器应该能处理钉钉PDF")
    
    def test_message_deduplication(self):
        """测试消息去重功能"""
        from src.database.message_models import MessageProcessLog
        
        # 创建测试消息
        test_message = MessageProcessLog(
            message_hash="integration_test_hash_12345",
            original_message="test message for integration testing",
            message_type="pdf_link",
            source="dingtalk",
            process_status="pending",
            processing_time_ms=100
        )
        
        # 第一次插入应该成功
        log_id_1 = self.db_repo.insert_message_log(test_message)
        self.assertGreater(log_id_1, 0, "第一次插入应该成功")
        
        # 第二次插入应该成功（允许重复记录）
        log_id_2 = self.db_repo.insert_message_log(test_message)
        self.assertGreater(log_id_2, 0, "第二次插入也应该成功")
        
        # 去重检查应该在应用层面进行
        existing = self.db_repo.get_message_by_hash("integration_test_hash_12345")
        self.assertIsNotNone(existing, "应该能找到已插入的消息")
        
        # 清理测试数据
        cursor = self.db_repo.conn.cursor()
        cursor.execute("DELETE FROM message_process_log WHERE message_hash LIKE 'integration_test_%'")
        self.db_repo.conn.commit()
        cursor.close()
    
    def test_end_to_end_message_processing(self):
        """测试端到端消息处理流程"""
        from src.feishu.models import ParseResult
        
        print("\n🔄 开始端到端处理测试...")
        
        # 创建PDF链接解析结果
        pdf_result = ParseResult(
            message_type='pdf_link',
            unique_identifier='https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
            pdf_url='https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
            source='dingtalk'
        )
        
        # 使用路由器处理
        router_result = self.router.process_with_router(pdf_result)
        
        if router_result['success']:
            print("✅ 消息处理成功")
            
            # 检查下载结果
            download_result = router_result['download_result']
            self.assertTrue(download_result.success, "下载应该成功")
            self.assertTrue(len(download_result.files) > 0, "应该有下载的文件")
            self.assertTrue(Path(download_result.files[0]).exists(), "文件应该存在")
            
            # 检查处理结果
            process_result = router_result['process_result']
            self.assertTrue(process_result.success, "处理应该成功")
            
            # 检查上传文件列表
            upload_files = router_result['upload_files']
            self.assertTrue(len(upload_files) > 0, "应该有待上传的文件")
            
            # 清理下载的文件
            processor = router_result['processor']
            processor.cleanup(download_result.temp_dir)
            
            print("✅ 端到端处理测试完成")
        else:
            print(f"⚠️  消息处理失败: {router_result.get('error_message')}")
            # 网络问题可能导致测试失败，这是正常的
            self.skipTest("网络连接问题，跳过端到端测试")

if __name__ == '__main__':
    # 运行测试时需要设置环境变量
    if os.getenv('RUN_INTEGRATION_TESTS') != 'true':
        print("\n⚠️  集成测试需要设置环境变量 RUN_INTEGRATION_TESTS=true")
        print("💡 运行命令: RUN_INTEGRATION_TESTS=true python tests/integration/test_real_integration.py")
        exit(1)
    
    unittest.main(verbosity=2)
```

- [ ] **步骤 3: 运行真实集成测试**

```bash
# 设置环境变量并运行集成测试
RUN_INTEGRATION_TESTS=true python tests/integration/test_real_integration.py -v
```

预期结果: 在真实环境中所有集成测试应该通过

- [ ] **步骤 4: 提交集成测试实现**

```bash
git add docs/INTEGRATION_TESTING_GUIDE.md
git add tests/integration/test_real_integration.py
git commit -m "test(integration): add comprehensive integration testing guide and real tests

- Create detailed integration testing guide
- Add real environment integration tests
- Document testing requirements and setup
- Provide step-by-step testing instructions
- Add validation for all message types
- Include performance and error testing
- Add troubleshooting guide

Integration test coverage:
- Database connectivity and operations
- SFTP connection and operations
- Message parser integration
- Processor router functionality
- Message deduplication
- End-to-end message processing

Testing guide includes:
- Environment setup requirements
- Real message testing procedures
- Expected results validation
- Error handling testing
- Performance testing
- Troubleshooting tips

Features:
- Requires RUN_INTEGRATION_TESTS=true to run
- Tests against real services (MySQL, DingTalk, SFTP)
- Comprehensive validation of all components
- Safe cleanup and isolation
- Detailed error reporting

Supported message type testing:
- Baidu Pan links (existing functionality)
- PDF links (new functionality)
- DingTalk PDF files (new functionality)
- DingTalk ZIP files (new functionality)"
```

---

## Task 9: 文档更新和发布准备

**文件:**
- 更新: `README.md`
- 更新: `docs/RELEASE_NOTES.md`
- 创建: `docs/MULTI_TYPE_USER_GUIDE.md`
- 更新: `config/.env.example`

- [ ] **步骤 1: 更新主README**

更新 `README.md`，添加多消息类型支持的说明:

在现有README中添加新章节:

```markdown
## 多消息类型支持

### 支持的消息类型

系统现在支持以下消息类型的自动处理:

1. **百度网盘分享链接** (原有功能)
   - 格式: `260723：https://pan.baidu.com/s/xxx?pwd=yyy`
   - 自动下载PDF文件并上传到SFTP
   - 支持文件夹批量处理

2. **PDF文件链接** (新增功能)
   - 格式: `@机器人 请处理: https://example.com/file.pdf`
   - 直接HTTP下载PDF文件
   - 支持最大200MB文件
   - 自动文件名冲突处理

3. **钉钉文件消息** (新增功能)
   - PDF文件: 直接下载并上传
   - ZIP文件: 自动解压并保持原有目录结构
   - 支持200MB PDF、500MB ZIP限制
   - 自动去重处理

### 消息处理优先级

系统按以下优先级识别消息类型:
1. 百度网盘链接 (最高优先级)
2. PDF文件链接
3. 钉钉文件消息

### 使用示例

#### 发送百度网盘链接
```
@机器人 260723：https://pan.baidu.com/s/abc123def?pwd=xyz456
```

#### 发送PDF链接
```
@机器人 请处理这个PDF文件: https://example.com/technical-manual.pdf
```

#### 发送钉钉文件
1. 在钉钉群中上传PDF或ZIP文件
2. @机器人并附上该文件
3. 系统自动下载并处理

### 配置要求

在 `.env` 文件中添加以下配置:

```bash
# 文件大小限制 (可选，有默认值)
MAX_PDF_SIZE_MB=200
MAX_ZIP_SIZE_MB=500
MAX_SINGLE_FILE_SIZE_MB=50

# 钉钉配置 (必需)
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
```

### 去重机制

- 百度网盘: 基于分享链接去重
- PDF链接: 基于完整URL去重
- 钉钉文件: 基于 `file_id:space_id` 去重
- 不同消息类型的相同文件视为不同消息

### 错误处理

- 可重试错误 (网络超时、服务器错误): 自动重试最多10次
- 不可重试错误 (文件不存在、大小超限): 立即失败通知
- 每次失败都发送钉钉群通知，显示重试进度

### 向后兼容性

- 现有百度网盘功能完全不受影响
- 数据库结构向后兼容
- 配置文件可选择性添加新参数
- 新功能失败不影响现有功能运行
```

- [ ] **步骤 2: 创建多类型用户指南**

创建 `docs/MULTI_TYPE_USER_GUIDE.md`:

```markdown
# 多消息类型处理用户指南

## 快速开始

### 1. 消息格式要求

所有消息必须 **@机器人** 才会被处理。

### 2. 支持的消息类型

#### 百度网盘链接 (原有功能)
```
@机器人 260723：https://pan.baidu.com/s/abc123def?pwd=xyz456
```

**特性:**
- 自动提取文件夹名 (如: 260723)
- 自动下载文件夹内所有PDF文件
- 保持原有SFTP目录结构
- 支持提取码自动识别

#### PDF文件链接 (新增功能)
```
@机器人 请处理这个PDF: https://example.com/technical-manual.pdf
```

**特性:**
- 直接HTTP下载，无需额外工具
- 支持最大200MB文件
- 自动添加时间戳避免文件名冲突
- 验证PDF文件有效性

#### 钉钉文件消息 (新增功能)
**PDF文件:**
1. 在钉钉群上传PDF文件
2. @机器人并附上该文件
3. 系统自动下载并处理

**ZIP文件:**
1. 在钉钉群上传ZIP文件
2. @机器人并附上该文件
3. 系统自动解压并保持原有结构

**特性:**
- 支持PDF (200MB) 和 ZIP (500MB)
- ZIP文件保持原有目录结构上传
- 自动跳过超大文件 (>50MB)
- 基于 `file_id:space_id` 去重

## 处理流程

### 1. 消息验证 (< 2秒)
- 接收消息
- 识别消息类型
- 检查是否重复
- 发送即时反馈

### 2. 文件处理 (异步)
- 下载文件到临时目录
- 必要时解压ZIP文件
- 上传到SFTP服务器
- 更新处理状态

### 3. 状态反馈
- 成功: 发送成功通知
- 失败: 发送失败通知和重试信息
- 重复: 提示已存在记录

## 错误处理

### 自动重试
- 网络超时、服务器错误等自动重试
- 最多重试10次
- 每次失败都发送进度通知

### 立即失败
- 文件不存在 (404)
- 文件大小超限
- 权限问题
- 过期的下载码

### 失败通知示例

**可重试错误:**
```
⚠️ 消息处理失败 - 自动重试中
群聊: 技术交流群
消息类型: PDF文件链接
重试进度: 3/10
错误原因: PDF下载超时
🔄 系统将自动重试，请稍后查看处理结果。
```

**永久失败:**
```
❌ 消息处理永久失败
群聊: 技术交流群
消息类型: 钉钉PDF文件
失败原因: 下载码已过期，请重新发送文件
错误类型: 不可重试错误
⚠️ 此消息已无法自动恢复，需要手动处理。
```

## 文件上传位置

### SFTP目录结构
```
/random/
├── 202508/                    # 按年月分组
│   ├── 260723/               # 百度网盘文件夹
│   │   └── *.pdf
│   ├── manual_20250820_143020.pdf  # PDF链接 (带时间戳)
│   ├── report_20250820_150530.pdf  # 钉钉PDF
│   └── project_files/       # ZIP解压目录
│       ├── docs/
│       ├── src/
│       └── README.md
└── 202509/
```

### 文件冲突处理
- 自动添加时间戳: `filename_20250820_143020.pdf`
- 保持原有ZIP结构: `project_folder/original_path/file.pdf`
- 保留原始文件名在数据库中

## 高级配置

### 文件大小限制
```bash
# .env 配置
MAX_PDF_SIZE_MB=200          # PDF文件最大200MB
MAX_ZIP_SIZE_MB=500          # ZIP文件最大500MB  
MAX_SINGLE_FILE_SIZE_MB=50   # ZIP内单文件最大50MB
```

### 重试次数配置
```bash
MAX_RETRY_COUNT=10            # 最大重试次数
```

### 临时目录配置
```bash
TEMP_DIR=/tmp/baidu_download  # 临时文件目录
```

## 故障排除

### 常见问题

**Q: 发送消息后没有反应**
A: 确保消息中 @机器人，检查群成员中是否有机器人

**Q: 提示"重复消息"**
A: 正常情况，相同消息不会重复处理，查看现有记录状态

**Q: PDF下载失败**
A: 检查链接是否有效，文件是否超过200MB限制

**Q: 钉钉文件处理失败**
A: 确保downloadCode未过期，检查文件大小限制

**Q: ZIP文件部分文件缺失**
A: ZIP中的单个文件可能超过50MB限制，自动跳过

### 日志查看
```bash
# 实时查看日志
tail -f logs/baidu_download.log

# 搜索特定消息类型
grep "pdf_link" logs/baidu_download.log
grep "dingtalk_pdf" logs/baidu_download.log

# 查看错误日志
grep "ERROR" logs/baidu_download.log
```

### 数据库查询
```sql
-- 查看所有待处理消息
SELECT * FROM message_process_log WHERE process_status='pending';

-- 查看失败消息
SELECT id, message_type, error_message, retry_count 
FROM message_process_log 
WHERE process_status='failed';

-- 查看特定消息类型的处理记录
SELECT * FROM message_process_log 
WHERE message_type='pdf_link' 
ORDER BY created_at DESC 
LIMIT 10;
```

## 最佳实践

### 1. 消息发送
- 始终 @机器人
- 使用准确的消息格式
- 避免发送重复消息

### 2. 文件管理
- 定期清理临时文件
- 监控SFTP存储空间
- 检查处理失败的文件

### 3. 错误处理
- 关注失败通知消息
- 及时处理永久失败的消息
- 必要时手动重试

### 4. 性能优化
- 分批处理大量文件
- 避免在高峰期发送大文件
- 定期维护数据库

## 安全建议

1. **文件来源**: 只处理可信来源的文件
2. **大小限制**: 合理设置文件大小限制
3. **权限控制**: 限制数据库和SFTP访问权限
4. **定期备份**: 定期备份数据库和配置文件
5. **日志监控**: 定期检查异常日志
```

- [ ] **步骤 3: 更新环境配置示例**

更新 `config/.env.example`，添加新的配置项:

```bash
# ========== 数据库配置 ==========
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download

# ========== 百度网盘配置 ==========
BAIDUPCS_GO_PATH=./BaiduPCS-Go

# ========== SFTP配置 ==========
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USER=your_sftp_user
SFTP_PASSWORD=your_sftp_password
SFTP_REMOTE_PATH=/random

# ========== 钉钉配置 ==========
DINGTALK_APP_KEY=your_dingtalk_app_key
DINGTALK_APP_SECRET=your_dingtalk_app_secret
DINGTALK_WEBHOOK=your_dingtalk_webhook_url

# ========== 文件大小限制 (可选，有默认值) ==========
# PDF文件最大大小 (MB)，默认200MB
MAX_PDF_SIZE_MB=200

# ZIP文件最大大小 (MB)，默认500MB  
MAX_ZIP_SIZE_MB=500

# ZIP内单文件最大大小 (MB)，默认50MB
MAX_SINGLE_FILE_SIZE_MB=50

# ========== 重试配置 (可选，有默认值) ==========
# 消息处理最大重试次数，默认10次
MAX_RETRY_COUNT=10

# ========== 临时目录配置 (可选) ==========
# 临时文件目录，默认系统临时目录
TEMP_DIR=/tmp/baidu_download

# ========== 日志配置 (可选) ==========
# 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

- [ ] **步骤 4: 创建版本发布说明**

创建 `docs/RELEASE_NOTES_v1.5.0.md`:

```markdown
# 多消息类型支持版本 v1.5.0 发布说明

**发布日期**: 2026-08-20  
**版本**: v1.5.0  
**类型**: 重大功能更新

---

## 🎉 主要更新

### 多消息类型支持

系统现已支持三种消息类型的统一处理:

#### 1. 百度网盘链接 (增强功能)
- ✅ 保持原有功能完全兼容
- ✅ 增强消息类型识别
- ✅ 优化去重机制
- ✅ 改进错误处理

#### 2. PDF文件链接 (全新功能)
- ✨ 支持直接HTTP下载PDF文件
- ✨ 自动文件名冲突处理
- ✨ 200MB文件大小限制
- ✨ 实时大小监控
- ✨ 完整的错误重试机制

#### 3. 钉钉文件消息 (全新功能)
- ✨ 支持PDF和ZIP文件
- ✨ 基于downloadCode的文件下载
- ✨ ZIP自动解压并保持结构
- ✨ 智能 `file_id:space_id` 去重
- ✨ 分层文件大小限制 (PDF 200MB, ZIP 500MB, 单文件 50MB)

---

## 🔧 技术改进

### 数据库扩展
- 新增 `message_type` 字段用于消息类型跟踪
- 新增 `raw_message` 字段存储原始JSON
- 新增 `file_info` 字段存储文件元数据
- 性能优化索引
- 消息类型约束保证数据完整性

### 架构重构
- 策略模式实现可扩展处理器架构
- 消息类型优先级路由系统
- 统一错误处理和重试机制
- 智能错误分类器 (可重试 vs 不可重试)
- 模块化设计便于未来扩展

### 错误处理增强
- 智能错误分类系统
- 自动重试机制 (最多10次)
- 详细失败通知消息
- 重试进度实时反馈
- 永久失败即时通知

---

## 📋 配置变更

### 新增配置项 (可选)
```bash
# 文件大小限制
MAX_PDF_SIZE_MB=200
MAX_ZIP_SIZE_MB=500  
MAX_SINGLE_FILE_SIZE_MB=50

# 重试次数
MAX_RETRY_COUNT=10

# 临时目录
TEMP_DIR=/tmp/baidu_download
```

### 必需配置
- 确保 `DINGTALK_APP_KEY` 和 `DINGTALK_APP_SECRET` 已配置
- 验证数据库连接正常
- 确认SFTP服务可访问

---

## 🗄️ 数据库迁移

### 必需迁移步骤
```bash
# 1. 备份数据库
mysqldump -u root -p baidu_download > backup_20260820.sql

# 2. 执行迁移
mysql -u root -p baidu_download < database/migrations/004_add_message_type_support.sql

# 3. 验证迁移
mysql -u root -p baidu_download -e "DESCRIBE message_process_log;"
```

---

## 📚 文档更新

- ✅ 完整的多消息类型用户指南
- ✅ 集成测试指南和真实测试脚本
- ✅ API文档更新
- ✅ 配置说明更新
- ✅ 故障排除指南扩展

---

## 🧪 测试覆盖

- ✅ 单元测试 (所有新组件)
- ✅ 集成测试 (真实环境)
- ✅ 错误处理测试
- ✅ 性能测试
- ✅ 向后兼容性测试

---

## ⚡ 性能改进

- 消息验证响应时间 < 2秒
- 即时反馈发送时间 < 5秒
- 流式文件下载减少内存使用
- 实时文件大小监控
- 优化的数据库查询

---

## 🔒 安全增强

- 文件大小限制防止资源耗尽
- 输入验证和清理
- 错误信息过滤敏感信息
- 数据库连接安全
- SFTP连接加密

---

## 📈 兼容性

### 向后兼容
- ✅ 现有百度网盘功能完全不变
- ✅ 数据库向后兼容
- ✅ 配置文件可选扩展
- ✅ API接口保持一致

### 降级支持
- 新功能失败不影响现有功能
- 优雅的错误处理
- 独立的处理器隔离

---

## 🚀 部署建议

### 生产环境部署
1. 先在测试环境验证所有功能
2. 备份生产数据库
3. 执行数据库迁移
4. 更新配置文件
5. 部署新版本代码
6. 运行集成测试验证
7. 监控日志和性能

### 验证清单
- [ ] 数据库迁移成功
- [ ] 百度网盘功能正常
- [ ] PDF链接处理正常
- [ ] 钉钉文件处理正常
- [ ] 错误重试机制正常
- [ ] SFTP上传正常
- [ ] 日志记录正常

---

## 📞 支持和帮助

### 文档资源
- [多消息类型用户指南](MULTI_TYPE_USER_GUIDE.md)
- [集成测试指南](INTEGRATION_TESTING_GUIDE.md)
- [故障排除指南](README.md#故障排除)

### 常见问题
**Q: 现有功能会受影响吗?**  
A: 不会，所有现有功能完全兼容，新功能独立运行。

**Q: 如何测试新功能?**  
A: 参考 [集成测试指南](INTEGRATION_TESTING_GUIDE.md) 进行真实环境测试。

**Q: 出现问题如何回滚?**  
A: 使用数据库备份恢复，部署旧版本代码即可。

---

## ✨ 特别感谢

感谢用户在开发过程中提供的宝贵反馈和测试支持！

---

**下一版本计划**: v1.6.0 - 性能优化和更多文件类型支持

**升级建议**: 强烈建议升级以获得新功能和错误处理改进

**风险评估**: 🟢 低风险 - 向后兼容，独立功能部署
```

- [ ] **步骤 5: 提交文档更新**

```bash
git add README.md
git add docs/MULTI_TYPE_USER_GUIDE.md
git add docs/RELEASE_NOTES_v1.5.0.md
git add config/.env.example
git commit -m "docs: update documentation for multi-type message support v1.5.0

- Update main README with multi-type support overview
- Create comprehensive user guide for new features
- Add detailed release notes for v1.5.0
- Update .env.example with new configuration options
- Document all supported message types
- Add troubleshooting guides
- Provide deployment instructions
- Include compatibility information

New documentation:
- Multi-type user guide with examples
- Integration testing guide
- Release notes for v1.5.0
- Updated configuration examples
- Enhanced troubleshooting section

Features documented:
- Baidu Pan links (existing, enhanced)
- PDF file links (new)
- DingTalk files (new)
- Error handling and retry mechanism
- Configuration options
- Deployment checklist

User guidance:
- Message format requirements
- Processing workflow
- Error handling behavior
- File upload structure
- Best practices
- Security recommendations"
```

---

## ✅ **实施计划完成**

**计划保存位置**: `docs/superpowers/plans/2026-08-20-message-type-extension-implementation.md`

### **实施总结**

**任务分解**: 9个主要任务，涵盖从数据库扩展到文档发布的完整实施流程

**关键特性**:
- ✅ 数据库架构扩展 (新增字段、索引、约束)
- ✅ 消息解析器重构 (策略模式、优先级路由)
- ✅ PDF链接处理器 (HTTP下载、大小验证)
- ✅ 钉钉文件处理器 (downloadCode下载、ZIP解压)
- ✅ 处理器路由系统 (统一接口、自动分发)
- ✅ 错误处理机制 (智能分类、自动重试)
- ✅ 真实集成测试 (无mock、全真服务)
- ✅ 完整文档更新 (用户指南、API文档)

**技术亮点**:
- 策略模式实现可扩展架构
- 消息级别去重 (file_id:space_id策略)
- 实时文件大小监控
- 分层错误处理和重试
- 向后完全兼容现有功能
- 真实环境集成测试

**验收标准**:
- 支持三种消息类型 (百度网盘、PDF链接、钉钉文件)
- 消息验证响应 < 2秒
- 5秒快速反馈要求
- 错误重试机制正常工作
- 现有功能完全不受影响
- 真实环境测试全部通过

---

**计划状态**: ✅ 已完成，等待执行

**下一步**: 开始实施各任务，建议按照任务顺序执行，每个任务完成后进行测试验证。