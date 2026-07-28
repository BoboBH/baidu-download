# 钉钉消息接收服务部署指南

## 📋 部署概述

钉钉消息接收服务是一个常驻进程，实时监听钉钉群消息并自动处理百度网盘链接。

## 🚀 快速部署

### 1. 环境准备

**必需软件：**
- Python 3.8+
- MySQL 5.7+

**Python 依赖安装：**
```bash
pip install dingtalk-stream
```

### 2. 配置文件

在项目根目录创建 `.env` 文件：

```bash
# 钉钉应用配置
DINGTALK_APP_KEY=dingcu3gdk9wnifpzm16
DINGTALK_APP_SECRET=yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=baidu_download

# 百度网盘配置
BAIDUPCS_GO_PATH=/path/to/BaiduPCS-Go
SFTP_HOST=your_sftp_host
SFTP_PORT=22
SFTP_USERNAME=your_sftp_user
SFTP_PASSWORD=your_sftp_password
SFTP_REMOTE_PATH=/remote/path
```

### 3. 启动服务

**开发环境启动：**
```bash
python main.py --dingtalk-service
```

**详细日志模式：**
```bash
python main.py --dingtalk-service --verbose
```

**Windows .exe 部署：**
```bash
# 假设编译后的程序名为 baidu_transfer.exe
baidu_transfer.exe --dingtalk-service
```

### 4. 验证运行

服务启动后，在钉钉群中 @机器人 发送测试消息：

```
260723：https://pan.baidu.com/s/1URIJc3aUvO8VHJulEW3DWg
```

如果配置正确，应该看到：
- 控制台输出消息处理日志
- 数据库中存储解析结果

## 🔧 进阶配置

### 作为 Windows 服务运行

**使用 NSSM（推荐）：**

1. 下载 NSSM：https://nssm.cc/download

2. 安装服务：
```cmd
nssm install BaiduTransfer "C:\path\to\baidu_transfer.exe" --dingtalk-service
nssm set BaiduTransfer AppDirectory "C:\path\to\app"
nssm set BaiduTransfer DisplayName "百度网盘文件传输服务"
nssm set BaiduTransfer Description "钉钉消息接收和文件传输服务"
nssm set BaiduTransfer Start SERVICE_AUTO_START
```

3. 启动服务：
```cmd
nssm start BaiduTransfer
```

### 使用任务计划程序（Windows）

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：启动时
4. 操作：启动程序
   - 程序：`C:\path\to\baidu_transfer.exe`
   - 参数：`--dingtalk-service`
   - 起始于：`C:\path\to\app`

### Docker 部署

**Dockerfile：**
```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py", "--dingtalk-service"]
```

**docker-compose.yml：**
```yaml
version: '3'
services:
  baidu_transfer:
    build: .
    container_name: baidu_transfer_service
    restart: always
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./temp:/app/temp
```

## 📊 监控和维护

### 日志查看

**日志文件位置：**
```
logs/transfer.log  # 主日志文件
```

**实时查看日志：**
```bash
tail -f logs/transfer.log
```

### 数据库检查

**查看最近的消息记录：**
```sql
SELECT * FROM message_process_log 
WHERE source = 'dingtalk' 
ORDER BY created_at DESC 
LIMIT 10;
```

**统计钉钉消息数量：**
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN process_status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as success
FROM message_process_log 
WHERE source = 'dingtalk';
```

### 服务状态检查

**检查服务运行状态：**
```bash
# Windows 任务计划程序
# 在服务列表中找到 "百度网盘文件传输服务"

# 或使用命令行
sc query BaiduTransfer
```

## 🛠️ 故障排除

### 常见问题

**1. 服务启动失败**
- 检查 `.env` 文件配置是否正确
- 确认数据库服务运行正常
- 查看日志文件获取详细错误信息

**2. 消息未接收**
- 确认机器人已在钉钉群中
- 验证消息格式是否正确：`260723：https://pan.baidu.com/s/xxx`
- 检查钉钉应用权限配置

**3. 数据库连接失败**
- 验证数据库配置参数
- 确认数据库用户权限
- 检查网络连接

### 日志调试

启用详细日志：
```bash
baidu_transfer.exe --dingtalk-service --verbose
```

## 🔒 安全建议

1. **配置文件安全**
   - 不要将 `.env` 文件包含在版本控制中
   - 设置合适的文件权限
   - 定期轮换密钥

2. **网络安全**
   - 使用强密码
   - 限制数据库访问权限
   - 配置防火墙规则

3. **运行安全**
   - 使用专用服务账户运行
   - 限制文件系统访问权限
   - 定期更新依赖包

## 📈 性能优化

### 数据库优化

**添加索引（如果不存在）：**
```sql
CREATE INDEX idx_source_created ON message_process_log(source, created_at);
CREATE INDEX idx_status_source ON message_process_log(process_status, source);
```

### 日志管理

**定期清理旧日志：**
```bash
# 删除 30 天前的日志
find logs/ -name "*.log" -mtime +30 -delete
```

## 📞 技术支持

- **日志文件**: `logs/transfer.log`
- **配置文件**: `.env`
- **主程序**: `main.py`
- **钉钉客户端**: `src/feishu/dingtalk_group_client.py`

---

**部署检查清单：**
- [ ] 环境依赖安装完成
- [ ] `.env` 配置文件创建
- [ ] 数据库连接测试通过
- [ ] 钉钉应用配置正确
- [ ] 钉钉机器人添加到群中
- [ ] 服务启动测试成功
- [ ] 消息接收测试通过
- [ ] 数据库存储验证成功

**部署完成！** 🎉
