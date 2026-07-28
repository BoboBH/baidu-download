# 微信公众号文章PDF转换上传功能设计文档

**创建日期**: 2026-07-28
**状态**: 设计完成，待审核
**版本**: 1.0

## 1. 概述

### 1.1 功能描述
实现一个微信公众号文章处理系统，从wewe_rss数据库获取文章，使用Playwright浏览器转换为PDF，上传到SFTP服务器，并记录处理状态到test数据库。

### 1.2 核心目标
- 自动化处理微信公众号文章，生成PDF并归档到SFTP服务器
- 提供账号同步、文章去重、历史查询等功能
- 实现反限流措施，确保稳定运行
- 支持错误处理和自动重试机制

## 2. 架构设计

### 2.1 轻量级集成架构
采用复用现有架构的方式，最小化新增代码：

```
main.py (新增wxchat命令)
  └── src/wxchat/
      ├── __init__.py
      ├── commands.py      (CLI命令定义)
      ├── processor.py     (核心业务逻辑)
      └── models.py        (数据模型定义)
```

### 2.2 复用现有模块
- **SFTP模块**: 复用`src/sftp/`现有的SFTP上传功能
- **配置管理**: 扩展`src/config/settings.py`增加微信相关配置
- **数据模型**: 扩展`src/database/models.py`增加微信数据表

### 2.3 技术栈
- **PDF生成**: Playwright + Chromium浏览器
- **数据库**: MySQL双数据库架构（wewe_rss源数据库 + test目标数据库）
- **文件传输**: SFTP协议
- **命令行**: 集成到现有CLI系统

## 3. 数据流设计

### 3.1 完整数据流程
```
用户执行命令
    ↓
同步微信公众号账号信息（可选）
    ↓
从wewe_rss数据库获取文章列表
    ↓
检查test数据库去重（基于article_id）
    ↓
逐个处理文章：
  - 生成真实浏览器请求头
  - 启动Playwright访问文章页面
  - 等待图片加载完成
  - 转换为PDF
  - 延迟5秒（反限流）
  ↓
按YYMM格式组织文件路径
    ↓
上传PDF到SFTP服务器
    ↓
更新处理状态到test数据库
    ↓
输出处理统计报告
```

### 3.2 时间窗口重试机制
- 失败的文章不会被标记为完成（pdf_path为NULL）
- 下次运行时会被重新发现和处理
- 直到超过N天时限后自动放弃

## 4. 核心组件设计

### 4.1 WeChatAccountSync（账号同步器）
**职责**: 从wewe_rss数据库同步微信公众号账号信息到test数据库

**核心方法**:
```python
def sync_accounts(self) -> int:
    """同步账号信息，返回同步数量"""
```

**实现逻辑**:
1. 连接wewe_rss数据库查询所有账号信息
2. 连接test数据库的wx_account表
3. 对比account_id，执行UPSERT操作

### 4.2 WeChatArticleProcessor（文章处理器）
**职责**: 处理微信公众号文章，生成PDF并上传

**核心方法**:
```python
def process_articles(self, days: int = 3) -> Dict[str, int]:
    """处理指定天数内的文章，返回处理统计"""
    
def _process_single_article(self, article: Dict) -> bool:
    """处理单个文章，返回是否成功"""
```

**实现逻辑**:
1. 从wewe_rss数据库查询指定天数内的文章
2. 在test数据库中检查是否已处理（基于article_id）
3. 对未处理的文章：
   - 使用Playwright访问文章URL
   - 等待页面图片加载完成
   - 生成PDF到临时文件
   - 延迟5秒
   - 上传PDF到SFTP服务器
   - 更新数据库记录

### 4.3 PDFGenerator（PDF生成器）
**职责**: 使用Playwright生成PDF文件

**核心方法**:
```python
def generate_pdf(self, url: str, output_path: str) -> bool:
    """生成PDF文件，返回是否成功"""
```

**实现逻辑**:
1. 配置Chromium浏览器参数（headless模式）
2. 设置真实浏览器的请求头
3. 访问文章URL
4. 等待页面加载和图片渲染
5. 生成PDF到指定路径

## 5. 配置设计

### 5.1 环境变量配置
在`.env`文件中新增以下配置：

```bash
# 微信文章处理功能开关
WXCHAT_ENABLED=true

# wewe_rss数据库配置（源数据库）
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=123456
WXCHAT_WEWE_DB_NAME=wewe_rss

# 微信文章基础URL
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/

# PDF生成配置
WXCHAT_PDF_TIMEOUT=60          # 页面加载超时时间（秒）
WXCHAT_IMAGE_WAIT_TIME=20       # 图片加载等待时间（秒）

# 反限流配置
WXCHAT_DOWNLOAD_DELAY=5         # 每篇文章处理后延迟时间（秒）

# 历史查询配置
WXCHAT_MAX_DAYS=30              # 最大查询天数
```

### 5.2 配置验证
在`Settings`类中增加微信相关配置的加载和验证：
- 验证数据库连接参数
- 验证数值参数的合理性
- 提供合理的默认值

## 6. 错误处理和反限流设计

### 6.1 错误处理策略
**分层错误处理**:

1. **数据库连接错误**: 立即终止，显示清晰错误信息
2. **PDF生成错误**: 记录错误，跳过当前文章，继续处理下一篇
3. **SFTP上传错误**: 记录错误，保留临时文件，支持手动重试
4. **超时错误**: 增加重试机制，最多3次尝试

**错误记录**:
- 所有错误都记录到数据库的error_message字段
- 错误同时输出到日志文件
- 提供详细的错误上下文信息

### 6.2 反限流措施
**多重反限流策略**:

1. **真实浏览器请求头**:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
```

2. **延迟策略**: 每篇文章下载完成后暂停5秒
3. **超时控制**: 页面加载超时设置为60秒
4. **失败重试**: 暂时的网络错误自动重试，最多3次

### 6.3 优雅降级
- 部分文章失败不影响整体处理
- 提供详细的处理报告
- 失败的文章可以在下次运行时重试

## 7. 数据库表结构设计

### 7.1 微信公众号账号表 (wx_account)
```sql
CREATE TABLE IF NOT EXISTS wx_account (
    account_id VARCHAR(100) PRIMARY KEY COMMENT '账号ID',
    account_name VARCHAR(255) NOT NULL COMMENT '账号名称',
    app_id VARCHAR(100) COMMENT '所属应用ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_app_id (app_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号账号表';
```

### 7.2 微信公众号文章表 (wx_article)
```sql
CREATE TABLE IF NOT EXISTS wx_article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id VARCHAR(100) NOT NULL UNIQUE COMMENT '文章ID',
    account_id VARCHAR(100) NOT NULL COMMENT '账号ID',
    title VARCHAR(500) COMMENT '文章标题',
    publish_date DATETIME COMMENT '发布时间',
    pdf_url VARCHAR(500) COMMENT 'PDF的SFTP路径',
    processed_at DATETIME COMMENT '处理完成时间',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    INDEX idx_account_id (account_id),
    INDEX idx_publish_date (publish_date),
    INDEX idx_processed_at (processed_at),
    INDEX idx_pdf_url (pdf_url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微信公众号文章表';
```

### 7.3 字段说明
- **article_id**: 唯一标识文章，用于去重
- **pdf_url**: 字段为NULL表示未处理，有值表示已处理完成
- **retry_count**: 记录重试次数，超过阈值后放弃
- **error_message**: 记录最新的错误信息

## 8. 文件结构设计

### 8.1 新增文件结构
```
src/wxchat/
├── __init__.py          # 模块初始化
├── commands.py          # CLI命令定义
├── processor.py         # 核心业务逻辑
└── models.py            # 数据模型定义
```

### 8.2 文件职责划分
- **__init__.py**: 导出主要函数和类
- **commands.py**: 定义CLI命令和参数处理
- **processor.py**: 实现所有业务逻辑
- **models.py**: 定义数据模型和表结构

### 8.3 代码组织原则
- 每个文件职责单一，功能明确
- 避免循环依赖
- 提供清晰的接口定义
- 支持单元测试

## 9. 测试策略

### 9.1 单元测试
**测试覆盖**:
- 账号同步逻辑测试
- 文章去重逻辑测试
- PDF生成功能测试
- SFTP上传功能测试
- 错误处理测试

**测试工具**: pytest

### 9.2 集成测试
**测试场景**:
- 完整的处理流程测试
- 数据库连接测试
- SFTP连接测试
- 反限流措施验证

### 9.3 手动测试
**测试用例**:
1. 测试账号同步功能
2. 测试不同天数的文章处理
3. 测试错误重试机制
4. 测试反限流措施
5. 测试SFTP文件上传

### 9.4 性能测试
**测试指标**:
- 单篇文章处理时间
- 批量文章处理吞吐量
- 内存使用情况
- PDF生成稳定性

## 10. 部署和使用说明

### 10.1 环境准备
**依赖安装**:
```bash
# 新增Playwright依赖
pip install playwright
playwright install chromium

# 确保现有依赖完整
pip install -r requirements.txt
```

**数据库准备**:
```bash
# 确认wewe_rss数据库可访问
# 确认test数据库已创建

# 创建必要的表
mysql -u root -p test < database/wxchat_tables.sql
```

**SFTP准备**:
```bash
# 确保SFTP服务器可访问
# 确保目标目录权限正确
```

### 10.2 配置文件设置
**`.env`文件配置**:
```bash
# 微信文章处理配置（新增）
WXCHAT_ENABLED=true
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PORT=3306
WXCHAT_WEWE_DB_USER=root
WXCHAT_WEWE_DB_PASSWORD=123456
WXCHAT_WEWE_DB_NAME=wewe_rss
WXCHAT_BASE_URL=https://mp.weixin.qq.com/s/
WXCHAT_PDF_TIMEOUT=60
WXCHAT_IMAGE_WAIT_TIME=20
WXCHAT_DOWNLOAD_DELAY=5
WXCHAT_MAX_DAYS=30
```

### 10.3 使用方式
**基本使用**:
```bash
# 处理最近3天的文章（默认）
python main.py wxchat

# 处理最近7天的文章
python main.py wxchat --days 7

# 处理最近1天的文章
python main.py wxchat --days 1

# 仅同步账号信息
python main.py wxchat --sync-accounts
```

**定时任务**:
```bash
# 添加到crontab，每天凌晨2点执行
0 2 * * * cd /path/to/baidu-download && python main.py wxchat --days 1
```

### 10.4 监控和日志
**日志查看**:
```bash
# 查看处理日志
tail -f logs/transfer.log

# 查找处理结果
grep "处理完成" logs/transfer.log
```

**数据库监控**:
```sql
-- 查看处理统计
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed,
    COUNT(CASE WHEN pdf_url IS NULL THEN 1 END) as pending
FROM wx_article;

-- 查看最近处理记录  
SELECT * FROM wx_article 
ORDER BY processed_at DESC 
LIMIT 10;
```

### 10.5 故障排查
**常见问题**:
- PDF生成失败：检查Playwright安装和网络连接
- SFTP上传失败：检查SFTP连接配置和权限
- 数据库连接失败：检查数据库配置和网络
- 文章处理失败：检查文章URL是否有效

## 11. 实现优先级

### 11.1 第一阶段（核心功能）
1. 基础数据模型和表结构创建
2. 账号同步功能实现
3. 文章获取和去重逻辑
4. PDF生成功能
5. SFTP上传集成

### 11.2 第二阶段（增强功能）
1. 错误处理和重试机制
2. 反限流措施
3. CLI命令集成
4. 日志和监控

### 11.3 第三阶段（优化功能）
1. 性能优化
2. 测试完善
3. 文档完善
4. 部署自动化

## 12. 风险和挑战

### 12.1 技术风险
- **微信公众号限制**: 可能面临访问频率限制
- **PDF生成稳定性**: 页面结构变化可能影响PDF生成
- **SFTP连接稳定性**: 网络问题可能导致上传失败

### 12.2 缓解措施
- 实施多重反限流策略
- 提供稳定的重试机制
- 支持手动干预和恢复
- 完善的错误日志记录

### 12.3 监控指标
- 文章处理成功率
- PDF生成失败率
- SFTP上传失败率
- 平均处理时间

## 13. 未来扩展

### 13.1 可能的增强功能
- 支持批量并发处理
- 增加处理进度通知
- 提供Web管理界面
- 支持多种文件格式转换
- 增加文章内容分析功能

### 13.2 集成扩展
- 与现有消息处理系统集成
- 支持多种RSS源
- 提供API接口

---

**设计文档完成，等待用户审核后进入实现计划阶段。**