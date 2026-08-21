# v1.5.0 快速部署指南

## 🚀 5分钟快速部署

### 前置条件检查
- ✅ 现有v1.4.x系统正常运行
- ✅ 数据库访问权限
- ✅ 文件系统备份空间

### 第一步：备份现有系统 (2分钟)
```bash
# 1. 备份配置文件
cp .env .env.backup.v1.4.31

# 2. 备份数据库
mysqldump -u root -p baidu_download > backup_v1.4.31_$(date +%Y%m%d_%H%M%S).sql

# 3. 验证备份文件
ls -lh .env.backup.v1.4.31
ls -lh backup_v1.4.31_*.sql
```

### 第二步：部署新版本 (2分钟)
```bash
# 1. 停止现有服务
taskkill /F /IM baidu-download.exe

# 2. 解压新版本
unzip baidu-download-v1.5.0.zip
cd release/dist-new

# 3. 验证配置兼容性
./baidu-download.exe --verify-config
```

### 第三步：数据库迁移 (1分钟)
```bash
# 执行数据库迁移
mysql -u root -p baidu_download < database/migrations/004_add_message_type_support.sql

# 验证迁移成功
mysql -u root -p baidu_download -e "SHOW COLUMNS FROM message_process_log LIKE 'message_type';"
```

### 第四步：启动新版本 (30秒)
```bash
# 启动服务
./baidu-download.exe --auto

# 查看启动日志
tail -f logs/transfer.log
```

### 第五步：功能验证 (30秒)
```bash
# 测试百度网盘功能（现有功能）
# 在飞书中发送百度网盘链接，验证处理正常

# 测试PDF链接功能（新功能）
# 在飞书中发送PDF链接，如：
# "请处理这份PDF: https://example.com/test.pdf"

# 检查处理状态
mysql -u root -p baidu_download -e "SELECT message_type, process_status FROM message_process_log ORDER BY created_at DESC LIMIT 5;"
```

## ⚠️ 回滚方案

如果遇到问题，可以快速回滚到v1.4.31：

```bash
# 1. 停止新版本
taskkill /F /IM baidu-download.exe

# 2. 恢复旧版本
cd release/previous-version
./baidu-download.exe --auto

# 3. 恢复配置（如需要）
cp .env.backup.v1.4.31 .env

# 4. 恢复数据库（如需要）
mysql -u root -p baidu_download < backup_v1.4.31_*.sql
```

## 🔍 部署验证检查清单

- [ ] 备份文件创建成功
- [ ] 数据库迁移无错误
- [ ] 新版本启动正常
- [ ] 日志无错误信息
- [ ] 百度网盘功能正常
- [ ] PDF链接处理测试通过
- [ ] 数据库记录正确

## 📊 部署后监控

### 第一小时监控
```bash
# 每15分钟检查一次系统状态
watch -n 900 'mysql -u root -p baidu_download -e "SELECT message_type, process_status, COUNT(*) FROM message_process_log WHERE created_at >= NOW() - INTERVAL 1 HOUR GROUP BY message_type, process_status;"'
```

### 关键指标检查
```sql
-- 消息处理成功率
SELECT message_type,
       SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
FROM message_process_log
WHERE created_at >= NOW() - INTERVAL 1 HOUR
GROUP BY message_type;

-- 错误统计
SELECT message_type, process_status, COUNT(*) as count
FROM message_process_log
WHERE created_at >= NOW() - INTERVAL 1 HOUR
  AND process_status IN ('failed', 'critical_error')
GROUP BY message_type, process_status;
```

## 🆘 常见问题排查

### 问题1：数据库迁移失败
**症状**: 迁移脚本执行错误
**解决**: 检查数据库权限，确认表结构兼容

```bash
# 检查表结构
mysql -u root -p baidu_download -e "DESC message_process_log;"

# 检查迁移历史
mysql -u root -p baidu_download -e "SELECT * FROM schema_migrations ORDER BY version;"
```

### 问题2：新功能不工作
**症状**: PDF链接或钉钉文件无法处理
**解决**: 检查环境变量和网络连接

```bash
# 验证配置
./baidu-download.exe --show-config

# 测试网络连接
curl -I https://example.com/test.pdf
```

### 问题3：性能下降
**症状**: 系统响应变慢
**解决**: 检查索引和数据库性能

```sql
-- 检查索引使用情况
EXPLAIN SELECT * FROM message_process_log WHERE message_type = 'pdf_link';

-- 检查慢查询
SHOW PROCESSLIST;
```

## 📞 技术支持

如果遇到无法解决的问题：

1. **收集诊断信息**:
   ```bash
   ./baidu-download.exe --diagnose > diagnosis_$(date +%Y%m%d_%H%M%S).txt
   ```

2. **查看详细日志**:
   ```bash
   tail -n 1000 logs/transfer.log > recent_logs_$(date +%Y%m%d_%H%M%S).txt
   ```

3. **联系技术支持**: support@baidu-download.com

---

**预计部署时间**: 5-8分钟  
**难度等级**: ⭐ 简单  
**风险等级**: ⭐⭐ 低风险（完全向后兼容）  

**最后更新**: 2026-08-20