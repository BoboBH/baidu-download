# 百度网盘PDF文件自动传输系统 v1.4.3

## 📦 **版本信息**
- **版本号**: 1.4.3
- **发布日期**: 2026-08-03
- **包名称**: baidu-download-v1.4.3.zip
- **包大小**: 234MB

## 🎯 **核心功能**
- ✅ 百度网盘文件自动下载和传输
- ✅ 消息解析：目录名称从消息提取，提取码从配置取
- ✅ SFTP文件上传
- ✅ 飞书/钉钉消息自动处理
- ✅ 微信公众号文章PDF生成

## 🔧 **配置说明**

### 关键配置项
```env
# 统一提取码（用于访问所有百度网盘链接）
MESSAGE_DEFAULT_EXTRACTION_CODE=0409
```

## 🚀 **使用说明**

### 解压和配置
```bash
# 解压
unzip baidu-download-v1.4.3.zip

# 进入目录
cd release/dist-new

# 运行程序
./baidu-download.exe --auto
```

## 📊 **版本管理**
- 版本命名：baidu-download-vX.Y.Z.zip
- 无功能描述，保持简洁
- 递增规则：1.4.3 → 1.4.4 → 1.4.5

## 📄 **详细文档**
完整的使用说明和技术文档请参考项目内的README文件。

---
**制作**: baidu-download team  
**构建**: PyInstaller 6.21.0 + Python 3.8.10