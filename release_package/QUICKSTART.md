# 快速入门指南

**5分钟上手百度网盘PDF文件自动传输系统**

---

## ⚡ 快速开始

### 步骤1：配置环境（2分钟）

**1.1 重命名配置文件**
```cmd
rename .env.example .env
```

**1.2 编辑 .env 文件，填写必需配置**
```bash
# 最小配置示例
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download

BAIDUPCS_GO_PATH=./BaiduPCS-Go.exe
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_user
SFTP_PASSWORD=your_password
SFTP_REMOTE_PATH=/remote/path
```

### 步骤2：初始化数据库（1分钟）

**2.1 创建数据库**
```sql
CREATE DATABASE baidu_download;
```

**2.2 导入表结构**
- 从源代码的 `middle/db_init.sql` 导入

### 步骤3：运行程序（2分钟）

**3.1 钉钉服务（推荐）**
```cmd
baidu-download.exe --dingtalk-service
```

**3.2 在钉钉群中发送测试消息**
```
@机器人 260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
```

**3.3 查看处理结果**
- 程序会自动下载并上传文件
- 日志会显示处理进度

---

## 🎯 三种运行模式

### 模式1：钉钉实时接收（推荐）

**适用场景：** 钉钉群实时接收消息

**启动方式：**
```cmd
baidu-download.exe --dingtalk-service
```

**消息格式：**
```
@机器人 260723：https://pan.baidu.com/s/xxx
```

**优点：**
- ✅ 实时接收，无需轮询
- ✅ 自动处理，全自动
- ✅ 消息去重，避免重复

### 模式2：飞书自动处理

**适用场景：** 飞书群自动处理

**启动方式：**
```cmd
baidu-download.exe --auto
```

**优点：**
- ✅ 一站式处理
- ✅ 自动获取和下载
- ✅ 发送处理通知

### 模式3：手动处理

**适用场景：** 单次处理分享链接

**启动方式：**
```cmd
baidu-download.exe --link "链接" --code "提取码" --folder "目录名"
```

**示例：**
```cmd
baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
```

**优点：**
- ✅ 精确控制
- ✅ 适合单次使用
- ✅ 立即执行

---

## 📱 消息格式示例

### 钉钉群消息

**正确格式：**
```
@机器人 260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
```

**格式说明：**
- 提取码：6位数字（YYDDMM格式）
- 分隔符：中文冒号`：`或英文冒号`:`
- 必须@机器人

**错误示例：**
```
❌ 260723 https://pan.baidu.com/s/xxx （缺少@）
❌ 26723：https://pan.baidu.com/s/xxx （提取码错误）
❌ @机器人 https://pan.baidu.com/s/xxx （缺少提取码）
```

---

## 🔧 配置检查清单

### 必需配置

- [ ] **数据库配置**
  - [ ] DB_HOST - 数据库地址
  - [ ] DB_PORT - 端口号
  - [ ] DB_USER - 用户名
  - [ ] DB_PASSWORD - 密码
  - [ ] DB_NAME - 数据库名

- [ ] **百度网盘配置**
  - [ ] BAIDUPCS_GO_PATH - 工具路径
  - [ ] baidu-cookies.txt - cookies文件

- [ ] **SFTP配置**
  - [ ] SFTP_HOST - 服务器地址
  - [ ] SFTP_PORT - 端口号
  - [ ] SFTP_USERNAME - 用户名
  - [ ] SFTP_PASSWORD - 密码
  - [ ] SFTP_REMOTE_PATH - 远程路径

### 可选配置

- [ ] **钉钉配置**
  - [ ] DINGTALK_APP_KEY
  - [ ] DINGTALK_APP_SECRET

- [ ] **飞书配置**
  - [ ] FEISHU_APP_ID
  - [ ] FEISHU_APP_SECRET
  - [ ] FEISHU_CHAT_ID

---

## ⚡ 常见问题快速解答

### Q1: 程序启动失败？

**A:** 检查 .env 文件配置，确保所有必需项都已填写。

### Q2: 数据库连接失败？

**A:** 
1. 确认数据库服务运行正常
2. 验证数据库用户名和密码
3. 检查数据库是否已创建

### Q3: 钉钉消息未接收？

**A:**
1. 确保消息格式正确：`@机器人 提取码：链接`
2. 验证机器人已在群中
3. 检查钉钉应用配置

### Q4: 文件上传失败？

**A:**
1. 检查SFTP连接配置
2. 验证远程路径权限
3. 确认网络连接正常

### Q5: 如何查看详细日志？

**A:** 使用 `--verbose` 参数：
```cmd
baidu-download.exe --dingtalk-service --verbose
```

---

## 📊 监控运行状态

### 查看日志

```cmd
type logs\transfer.log
```

### 数据库查询

```sql
-- 查看最近处理的消息
SELECT * FROM message_process_log 
ORDER BY created_at DESC 
LIMIT 10;

-- 统计处理数量
SELECT source, process_status, COUNT(*) 
FROM message_process_log 
GROUP BY source, process_status;
```

---

## 🎉 开始使用

1. **配置环境** → 重命名并编辑 .env 文件
2. **初始化数据库** → 创建数据库和表
3. **选择模式** → 钉钉/飞书/手动
4. **发送消息** → 在群中发送测试链接
5. **查看结果** → 检查日志和数据库

**就这么简单！5分钟开始使用。** 🚀

---

*百度网盘PDF文件自动传输系统 v1.2.3*  
*快速入门指南 - 2026-07-25*
