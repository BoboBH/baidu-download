# 生产部署检查清单 - v1.0.9

## 🎯 发布前检查

### ✅ 版本信息确认
- [x] 版本号更新至 v1.0.9
- [x] 构建日期: 2026-07-16
- [x] 发布包大小: 19.8 MB
- [x] SHA256校验和生成完成

### ✅ 包文件完整性
- [x] baidu-download-v1.0.9-exe.zip (主发布包)
- [x] baidu-download-v1.0.9-exe-checksum.txt (校验文件)
- [x] v1.0.9_RELEASE_SUMMARY.md (发布说明)

### ✅ 功能验证
- [x] 16个单元测试全部通过
- [x] 集成测试验证完整
- [x] --no-sftp 模式测试通过
- [x] SFTP 模式切换逻辑验证
- [x] 错误处理机制测试

### ✅ 文档完整性
- [x] README.txt - 用户使用说明
- [x] INSTALL.txt - 安装部署指南
- [x] VERSION - 版本信息文件
- [x] .env - 配置文件模板
- [x] init_db_auto.bat/sh - 数据库初始化脚本

## 🚀 生产部署步骤

### 1. 备份当前环境
```bash
# 备份现有可执行文件
cp baidu-download.exe baidu-download.exe.backup.$(date +%Y%m%d)

# 备份配置文件
cp .env .env.backup.$(date +%Y%m%d)

# 备份数据库（可选）
mysqldump -u root -p baidu_download > backup_$(date +%Y%m%d).sql
```

### 2. 下载和验证
```bash
# 下载发布包
wget baidu-download-v1.0.9-exe.zip

# 验证校验和
sha256sum -c baidu-download-v1.0.9-exe-checksum.txt

# 解压文件
unzip baidu-download-v1.0.9-exe.zip
```

### 3. 配置更新
```bash
# 检查配置文件差异
diff .env.backup.20260716 .env

# 更新配置（如需要）
nano .env
```

### 4. 数据库更新（如需要）
```bash
# 运行数据库初始化脚本
./init_db_auto.bat    # Windows
./init_db_auto.sh     # Linux

# 检查数据库表结构
mysql -u root -p baidu_download -e "SHOW TABLES;"
```

### 5. 功能测试
```bash
# 测试程序帮助
baidu-download.exe --help

# 测试配置验证
baidu-download.exe --link "test" --code "test" --folder "test" --dry-run

# 测试SFTP连接（如启用）
baidu-download.exe --link "test" --code "test" --folder "test_connection"
```

### 6. 监控和验证
```bash
# 查看日志文件
tail -f logs/transfer.log

# 检查进程状态
ps aux | grep baidu-download

# 监控资源使用
top -p $(pgrep baidu-download)
```

## 🔍 部署后验证

### 功能验证清单
- [ ] 程序能正常启动
- [ ] 配置文件正确加载
- [ ] 数据库连接成功
- [ ] SFTP连接正常（如启用）
- [ ] 百度网盘下载功能正常
- [ ] 文件上传功能正常
- [ ] 日志记录正常
- [ ] 临时文件清理正常

### 回滚计划
```bash
# 如遇问题，立即回滚
cp baidu-download.exe.backup.20260716 baidu-download.exe
cp .env.backup.20260716 .env

# 重启服务
# 根据部署方式执行相应重启命令
```

## 📞 应急联系

### 常见问题处理
1. **程序启动失败**
   - 检查系统兼容性
   - 验证文件权限
   - 查看日志文件

2. **数据库连接失败**
   - 验证数据库服务状态
   - 检查配置文件连接信息
   - 测试网络连接

3. **SFTP上传失败**
   - 验证SFTP服务器配置
   - 检查网络连接和防火墙
   - 确认目录权限

### 支持资源
- **日志文件**: logs/transfer.log
- **版本信息**: VERSION 文件
- **配置示例**: .env 文件
- **文档**: README.txt, INSTALL.txt

## ✅ 部署完成确认

- [ ] 所有功能测试通过
- [ ] 监控系统正常
- [ ] 备份完成
- [ ] 文档更新
- [ ] 用户通知完成

---

**部署人员**: _____________  
**部署日期**: _____________  
**验证状态**: ✅ 通过 / ❌ 需回滚  
**备注**: ___________________
