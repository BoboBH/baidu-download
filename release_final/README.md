# 百度网盘PDF文件自动传输系统 - 微信功能版 v1.2.5

## 重要更新

### ✅ 命令行参数改进
- **新增**: 支持 `--wechat` 和 `--wxchat` 两种参数格式
- **优化**: 使用命令行参数时不再需要配置 `WXCHAT_ENABLED` 开关

### ✅ SFTP目录配置修复
- **新增**: `WXCHAT_SFTP_REMOTE_PATH` 配置参数，默认值 `/wxchat`

### ✅ 问题已解决
已修复微信文章PDF上传到SFTP服务器时缺少专门的目录配置问题。

### 🔧 新增配置参数
**配置名称**: `WXCHAT_SFTP_REMOTE_PATH`  
**默认值**: `/wxchat`  
**用途**: 指定微信文章PDF文件的SFTP上传根目录

### 📁 目录组织方式
系统会自动按**YYMM格式**组织微信PDF文件：
```
/wxchat/                      ← WXCHAT_SFTP_REMOTE_PATH
├── 2407/                    ← 2024年7月
│   ├── article_001.pdf
│   └── ...
└── 2408/                    ← 2024年8月
    └── ...
```

## 快速开始

### 1. 配置文件设置
复制`.env.example`为`.env`并配置：

```bash
# 微信功能配置（使用命令行参数时不再需要WXCHAT_ENABLED开关）
# WXCHAT_ENABLED=false

# 如需启用微信功能，只需配置以下参数：
WXCHAT_WEWE_DB_HOST=localhost
WXCHAT_WEWE_DB_PASSWORD=your_password
WXCHAT_WEWE_DB_NAME=wewe_rss
WXCHAT_SFTP_REMOTE_PATH=/wxchat  # 新增配置
```

**重要**: 现在使用 `--wechat` 或 `--wxchat` 命令行参数时，**不需要**设置 `WXCHAT_ENABLED=true`

### 2. 数据库初始化
```bash
mysql -u root -p test < wxchat_tables.sql
```

### 3. 运行程序
```bash
# 百度网盘功能（原有）
baidu-download.exe --auto

# 微信文章功能（新增）- 支持两种参数格式
baidu-download.exe --wechat
baidu-download.exe --wxchat
baidu-download.exe --wechat --wechat-days 7
baidu-download.exe --wxchat --wxchat-days 7
```

**注意**: 使用 `--wechat` 或 `--wxchat` 参数时，无需设置 `WXCHAT_ENABLED` 开关

## 📦 包含文件

- **baidu-download.exe** - 主程序 (18MB)
- **BaiduPCS-Go.exe** - 百度网盘工具 (13MB)  
- **.env.example** - 配置文件模板
- **wxchat_tables.sql** - 微信数据库脚本

## 🎯 核心功能

1. **飞书/钉钉消息处理** - 自动接收并处理分享链接
2. **SFTP自动上传** - 文件自动上传到SFTP服务器
3. **微信文章PDF处理** - 从wewe_rss获取文章，生成PDF并上传
4. **智能去重** - 避免重复处理相同内容
5. **统计监控** - 详细的处理日志和统计信息

## ⚙️ 配置说明

### 必需配置
- `SFTP_HOST` - SFTP服务器地址
- `SFTP_USERNAME` - SFTP用户名  
- `SFTP_PASSWORD` - SFTP密码
- `SFTP_REMOTE_PATH` - SFTP远程路径
- `DB_HOST` - 数据库主机
- `DB_USER` - 数据库用户名
- `DB_PASSWORD` - 数据库密码
- `DB_NAME` - 数据库名称

### 微信功能配置（可选）
- `WXCHAT_ENABLED=true`
- `WXCHAT_WEWE_DB_HOST` - wewe_rss数据库地址
- `WXCHAT_WEWE_DB_USER` - wewe_rss数据库用户
- `WXCHAT_WEWE_DB_PASSWORD` - wewe_rss数据库密码
- `WXCHAT_WEWE_DB_NAME` - wewe_rss数据库名称
- `WXCHAT_SFTP_REMOTE_PATH=/wxchat` - **新增：微信PDF上传目录**

## 🔍 配置验证

### 检查微信配置是否生效
```bash
# 运行微信功能
baidu-download.exe --wxchat --wxchat-days 1

# 查看日志确认SFTP上传路径
tail -f logs/transfer.log | grep "PDF上传成功"
# 应该看到: PDF上传成功: /wxchat/2407/article_xxx.pdf
```

## 📋 系统要求

- **操作系统**: Windows 10/11
- **数据库**: MySQL 5.7+
- **SFTP服务器**: 可访问的SFTP服务
- **微信功能依赖**: wewe_rss系统（可选）
- **微信功能额外依赖**: 
  ```bash
  pip install playwright
  playwright install chromium
  ```

## 🚀 使用示例

### 飞书消息处理
```bash
baidu-download.exe --auto                    # 自动处理模式
baidu-download.exe --receive-messages         # 接收消息
baidu-download.exe --process-pending          # 处理待处理消息
```

### 微信文章处理
```bash
# 使用 --wechat 参数（推荐）
baidu-download.exe --wechat                              # 处理最近3天文章
baidu-download.exe --wechat --wechat-days 7             # 处理最近7天文章
baidu-download.exe --wechat --wechat-sync-accounts      # 同步账号

# 或使用 --wxchat 参数（兼容旧版本）
baidu-download.exe --wxchat                              # 处理最近3天文章
baidu-download.exe --wxchat --wxchat-days 7              # 处理最近7天文章
baidu-download.exe --wxchat --wxchat-sync-accounts       # 同步账号
```

### 手动模式
```bash
baidu-download.exe --link "分享链接" --code "提取码" --folder "目录名"
```

## 📊 监控和管理

### 日志文件
- 位置: `logs/transfer.log`
- 自动创建，按日期滚动
- 包含详细的处理信息和错误记录

### 数据库监控
```sql
-- 查看微信文章处理统计
SELECT COUNT(*) as total, 
       COUNT(CASE WHEN pdf_url IS NOT NULL THEN 1 END) as processed
FROM wx_article;

-- 查看最近的处理记录
SELECT * FROM wx_article 
ORDER BY processed_at DESC 
LIMIT 10;
```

## 🔧 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查`.env`文件中的数据库配置
   - 确保数据库服务正在运行

2. **SFTP上传失败**
   - 检查SFTP服务器连接
   - 确保目标目录存在且有写权限
   - 对于微信功能，确保`WXCHAT_SFTP_REMOTE_PATH`配置正确

3. **微信PDF生成失败**
   - 确保已安装Playwright: `pip install playwright`
   - 安装浏览器: `playwright install chromium`
   - 检查wewe_rss数据库连接

## 📝 版本信息

- **版本**: v1.2.5
- **发布日期**: 2026-07-28
- **更新内容**: 
  - ✅ **参数别名**: 支持 `--wechat` 和 `--wxchat` 两种参数格式
  - ✅ **简化配置**: 使用命令行参数时不再需要 `WXCHAT_ENABLED` 开关
  - ✅ 新增微信公众号文章PDF处理功能
  - ✅ 新增SFTP目录配置修复
  - ✅ 完整测试覆盖（53个测试）
  - ✅ 完整用户文档

## ⚠️ 重要说明

1. **首次使用**: 请先配置`.env`文件
2. **数据库准备**: 确保数据库和SFTP服务可访问
3. **微信功能**: 需要额外配置wewe_rss数据库
4. **SFTP目录**: 确保微信PDF上传目录存在且有写权限
5. **定期维护**: 建议定期检查日志文件和系统状态
6. **新特性**: 使用 `--wechat` 参数时无需设置 `WXCHAT_ENABLED` 开关

---

**部署就绪**: ✅ 系统已完成打包并准备部署使用  
**修复状态**: ✅ SFTP目录配置问题已完全解决  
**用户体验**: ✅ 支持灵活的命令行参数，无需配置开关  
**文档状态**: ✅ 包含完整的配置说明和使用指南