# 百度网盘PDF文件自动传输系统 v1.0.0

## 🚀 快速开始指南

### 📦 安装包内容

```
baidu-download-v1.0.0.zip
├── main.py                      # 主程序
├── requirements.txt             # Python依赖
├── .env.example                 # 配置模板
├── README.md                    # 详细说明
├── CHANGELOG.md                 # 版本更新
├── DEPLOYMENT.md                # 部署指南
├── src/                         # 源代码
├── middle/                      # 数据库脚本
└── 工具脚本/                    # 诊断工具
```

### ⚡ 5分钟快速部署

#### 1. 解压安装包
```bash
# 解压到任意目录，例如 D:\baidu-download\
unzip baidu-download-v1.0.0.zip
```

#### 2. 安装依赖
```bash
cd baidu-download-v1.0.0
pip install -r requirements.txt
```

#### 3. 配置系统
```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件，填写：
# - BaiduPCS-Go路径
# - SFTP服务器信息
# - MySQL数据库信息
# - 百度网盘Cookie
```

#### 4. 初始化数据库
```bash
# 登录MySQL并执行脚本
mysql -u root -p < middle/db_init.sql
```

#### 5. 运行程序
```bash
python main.py --link "分享链接" --code "提取码" --folder "目录名"
```

### 📋 详细说明

- **README.md** - 完整使用说明和API文档
- **DEPLOYMENT.md** - 详细部署指南和故障排查
- **CHANGELOG.md** - 版本更新和新功能说明

### 🔧 常见问题

#### Q: BaiduPCS-Go是什么？
A: 百度网盘命令行工具，需要单独下载：[GitHub下载](https://github.com/qjfoidnh/BaiduPCS-Go)

#### Q: 如何获取百度网盘Cookie？
A: 参考DEPLOYMENT.md中的详细步骤，使用浏览器开发者工具获取

#### Q: SFTP连接失败怎么办？
A: 使用附带的诊断工具：
```bash
python diagnose_sftp.py          # 诊断连接问题
python interactive_sftp_test.py # 测试凭证
```

### 🎯 使用示例

```bash
# 基本使用
python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "docs"

# 详细日志
python main.py -l "链接" -c "码" -f "目录" --verbose

# 仅测试配置
python main.py -l "链接" -c "码" -f "目录" --dry-run
```

### 📞 技术支持

- 查看日志文件：`logs/transfer.log`
- 参考部署指南：`DEPLOYMENT.md`
- 检查配置文件：`.env`

---

**版本**: v1.0.0 | **发布时间**: 2026-07-11 | **包大小**: 0.03 MB