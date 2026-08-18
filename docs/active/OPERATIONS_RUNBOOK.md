# 运维手册 - 百度网盘PDF文件自动传输系统

**版本:** 1.0  
**适用系统版本:** v1.4.4+  
**维护团队:** 运维组  
**最后更新:** 2026-08-19

---

## 📋 运维手册概述

本运维手册为百度网盘PDF文件自动传输系统的操作指南，包含系统监控、故障排查、性能优化和应急响应的标准操作程序（SOP）。

### 目标读者
- 系统运维工程师
- 平台支持工程师  
- 值班技术人员
- 系统管理员

### 使用场景
- 日常系统监控和巡检
- 故障诊断和问题处理
- 性能优化和容量规划
- 应急响应和事故处理

---

## 🚨 1. 应急响应程序

### 1.1 高优先级告警处理

#### 告警级别定义
| 级别 | 响应时间 | 影响范围 | 示例 |
|------|----------|----------|------|
| P0 | 立即（5分钟内） | 系统完全不可用 | 主服务进程崩溃，数据库连接失败 |
| P1 | 15分钟内 | 核心功能不可用 | 文件传输失败率>50%，SFTP连接失败 |
| P2 | 1小时内 | 部分功能受影响 | 单个消息源异常，重试率升高 |
| P3 | 4小时内 | 性能下降 | 处理延迟增加，资源使用率偏高 |

#### P0告警响应程序
```bash
# 1. 立即检查服务状态
tasklist | findstr baidu-download
# 或
ps aux | grep baidu-download

# 2. 检查数据库连接
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT 1"

# 3. 查看最新错误日志
tail -n 100 logs/transfer.log | grep ERROR

# 4. 快速诊断
python scripts/diagnose_recent_failures.py
```

**决策树:**
- 如果进程不存在 → 执行服务重启程序
- 如果数据库连接失败 → 执行数据库故障恢复程序
- 如果发现明显错误 → 按错误类型执行对应处理程序

### 1.2 服务重启程序

#### 正常重启流程
```bash
# 1. 停止当前进程（优雅关闭）
# Windows:
taskkill /PID <process_id> /T

# Linux:
kill -TERM <process_id>

# 2. 验证进程已停止
tasklist | findstr baidu-download  # Windows
ps aux | grep baidu-download      # Linux

# 3. 启动服务
# EXE版本:
baidu-download.exe --auto --verbose

# Python版本:
python main.py --auto --verbose

# 4. 验证服务启动成功
# 检查日志显示正常启动
tail -n 20 logs/transfer.log
```

#### 强制重启流程（仅紧急情况）
```bash
# 强制终止进程
taskkill /F /PID <process_id> /T   # Windows
kill -9 <process_id>                # Linux

# 立即重启
baidu-download.exe --auto --verbose
```

---

## 📊 2. 监控和指标

### 2.1 核心监控指标

#### 系统健康指标
```sql
-- 检查系统整体健康状况
SELECT 
    COUNT(*) as total_messages,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN process_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN process_status = 'processing' THEN 1 ELSE 0 END) as processing_count,
    SUM(CASE WHEN process_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
    ROUND(SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);
```

#### 消息重试监控
```sql
-- 重试统计和分布
SELECT 
    retry_count,
    COUNT(*) as message_count,
    SUM(CASE WHEN process_status = 'failed' THEN 1 ELSE 0 END) as still_failing,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as recovered,
    MIN(created_at) as first_occurrence,
    MAX(updated_at) as last_update
FROM message_process_log 
WHERE retry_count > 0 
GROUP BY retry_count
ORDER BY retry_count DESC;
```

#### 性能指标监控
```sql
-- 处理性能统计
SELECT 
    AVG(processing_time_ms) as avg_processing_time,
    MAX(processing_time_ms) as max_processing_time,
    MIN(processing_time_ms) as min_processing_time,
    STDDEV(processing_time_ms) as stddev_processing_time
FROM message_process_log 
WHERE processing_time_ms IS NOT NULL 
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);
```

### 2.2 告警阈值配置

#### 推荐告警规则
| 指标 | 警告阈值 | 严重阈值 | 检查频率 |
|------|----------|----------|----------|
| 服务可用性 | < 95% | < 90% | 每分钟 |
| 消息成功率 | < 90% | < 80% | 每5分钟 |
| 处理延迟 | > 30秒 | > 60秒 | 每5分钟 |
| 重试消息占比 | > 20% | > 30% | 每10分钟 |
| 数据库连接失败 | > 5次/小时 | > 10次/小时 | 每小时 |

#### 自定义监控脚本
```bash
#!/bin/bash
# 快速健康检查脚本

echo "=== 系统健康检查 ==="
echo "检查时间: $(date)"

# 1. 检查服务进程
if pgrep -f "baidu-download" > /dev/null; then
    echo "✓ 服务进程运行正常"
else
    echo "✗ 服务进程未运行 - 需要立即处理"
    exit 1
fi

# 2. 检查数据库连接
if mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT 1" &> /dev/null; then
    echo "✓ 数据库连接正常"
else
    echo "✗ 数据库连接失败 - 需要立即处理"
    exit 1
fi

# 3. 检查最近失败率
FAILED_RATE=$(mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -N -e "
SELECT ROUND(SUM(CASE WHEN process_status = 'failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);")

echo "最近1小时失败率: ${FAILED_RATE}%"

if (( $(echo "$FAILED_RATE > 20" | bc -l) )); then
    echo "⚠ 失败率超过20% - 需要关注"
elif (( $(echo "$FAILED_RATE > 40" | bc -l) )); then
    echo "✗ 失败率超过40% - 需要立即处理"
    exit 1
fi

echo "=== 系统状态正常 ==="
```

### 2.3 监控仪表板配置

#### 日常监控项目清单
```bash
# 每日巡检脚本
echo "=== 每日系统巡检 ==="
echo "执行时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 1. 消息处理统计（过去24小时）
echo "1. 消息处理统计（24小时）"
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    DATE_FORMAT(created_at, '%Y-%m-%d %H:00') as hour,
    COUNT(*) as total_messages,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN process_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    ROUND(AVG(processing_time_ms)/1000, 2) as avg_processing_seconds
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:00')
ORDER BY hour DESC;"

# 2. 重试限制统计
echo "2. 消息重试统计"
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    '总消息数' as metric, COUNT(*) as value FROM message_process_log
UNION ALL
SELECT '有重试记录', COUNT(*) FROM message_process_log WHERE retry_count > 0
UNION ALL
SELECT '达到重试上限', COUNT(*) FROM message_process_log WHERE retry_count >= 10
UNION ALL
SELECT '当前失败状态', COUNT(*) FROM message_process_log WHERE process_status = 'failed';"

# 3. 错误分布分析
echo "3. 主要错误类型（过去24小时）"
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    SUBSTRING_INDEX(error_message, ':', 1) as error_type,
    COUNT(*) as occurrence_count
FROM message_process_log 
WHERE error_message IS NOT NULL 
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY error_type
ORDER BY occurrence_count DESC
LIMIT 10;"

echo "=== 巡检完成 ==="
```

---

## 🔧 3. 故障诊断和排查

### 3.1 常见问题诊断程序

#### 问题: 消息处理失败率突然升高
```bash
# 1. 检查失败消息的时间分布
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') as time_period,
    COUNT(*) as failed_count,
    process_status,
    SUBSTRING_INDEX(error_message, '\n', 1) as error_preview
FROM message_process_log 
WHERE process_status IN ('failed', 'critical_error')
AND created_at >= DATE_SUB(NOW(), INTERVAL 6 HOUR)
GROUP BY time_period, process_status, error_preview
ORDER BY time_period DESC;"

# 2. 分析错误类型分布
python scripts/analyze_failures.py

# 3. 检查重试统计
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT retry_count, COUNT(*) as count, process_status
FROM message_process_log 
WHERE retry_count > 0
GROUP BY retry_count, process_status
ORDER BY retry_count DESC;"
```

#### 问题: 服务响应缓慢
```bash
# 1. 检查处理时间统计
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    AVG(processing_time_ms) as avg_time,
    MAX(processing_time_ms) as max_time,
    COUNT(*) as total_processed
FROM message_process_log 
WHERE processing_time_ms > 5000  -- 超过5秒的处理
AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);"

# 2. 检查数据库性能
SHOW PROCESSLIST;

# 3. 检查SFTP连接状态
python scripts/diagnose_sftp.py
```

#### 问题: 重试消息不减少
```bash
# 1. 检查重试限制配置
grep MESSAGE_MAX_RETRIES .env

# 2. 检查接近重试上限的消息
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    message_hash,
    LEFT(original_message, 50) as message_preview,
    retry_count,
    process_status,
    error_message,
    created_at,
    updated_at
FROM message_process_log 
WHERE retry_count >= 8
ORDER BY retry_count DESC, updated_at DESC;"

# 3. 验证重试计数逻辑
grep -A 10 "def update_message_status" src/database/repository.py
```

### 3.2 诊断命令参考

#### 系统状态快速检查
```bash
# 一键系统健康检查
python scripts/check_db.py

# 最近失败分析
python scripts/diagnose_recent_failures.py

# 文件时间戳分析
python scripts/analyze_file_timestamps.py
```

#### 日志分析命令
```bash
# 查看最近错误
tail -n 1000 logs/transfer.log | grep ERROR | tail -n 20

# 统计错误频率
grep ERROR logs/transfer.log | awk '{print $1}' | sort | uniq -c | sort -rn

# 查看重试相关日志
grep "retry" logs/transfer.log | tail -n 20

# 查看性能相关日志
grep "processing.*ms" logs/transfer.log | tail -n 20
```

---

## 📈 4. 性能优化

### 4.1 数据库性能优化

#### 索引维护
```sql
-- 检查索引使用情况
SHOW INDEX FROM message_process_log;

-- 分析表性能
ANALYZE TABLE message_process_log;

-- 优化表
OPTIMIZE TABLE message_process_log;
```

#### 查询性能监控
```sql
-- 查找慢查询
SELECT * FROM mysql.slow_log 
WHERE start_time > DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY query_time DESC
LIMIT 10;
```

### 4.2 应用性能调优

#### 配置优化建议
```ini
# 性能优化配置建议
MAX_RETRIES=3                  # 减少不必要的重试
CONCURRENT_UPLOADS=1           # 控制并发避免资源争用
MESSAGE_MAX_RETRIES=10         # 平衡重试和性能

# 日志级别配置（生产环境）
LOG_LEVEL=WARNING             # 减少日志输出量
```

#### 资源使用监控
```bash
# CPU和内存使用监控
top -p $(pgrep -f baidu-download)

# 磁盘使用监控
df -h

# 日志文件大小监控
ls -lh logs/transfer.log
du -sh logs/
```

---

## 🔄 5. 维护操作程序

### 5.1 日常维护任务

#### 每日任务
```bash
#!/bin/bash
# daily_maintenance.sh - 每日维护任务

echo "开始每日维护任务: $(date)"

# 1. 检查系统健康状态
python scripts/check_db.py

# 2. 分析失败情况
python scripts/diagnose_recent_failures.py

# 3. 清理旧日志（保留7天）
find logs/ -name "*.log" -mtime +7 -delete

# 4. 数据库备份
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD baidu_download > backup/baidu_download_$(date +%Y%m%d).sql

# 5. 检查磁盘空间
df -h | grep -E "(Filesystem|/$|/var)"

echo "每日维护任务完成: $(date)"
```

#### 每周任务
```bash
#!/bin/bash
# weekly_maintenance.sh - 每周维护任务

echo "开始每周维护任务: $(date)"

# 1. 数据库性能优化
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "OPTIMIZE TABLE baidu_download.message_process_log;"

# 2. 分析一周性能数据
python scripts/analyze_final_results.py

# 3. 检查重试统计
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -D baidu_download -e "
SELECT 
    '本周消息总数' as metric, COUNT(*) as value FROM message_process_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
UNION ALL
SELECT '成功率', ROUND(SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) FROM message_process_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
UNION ALL
SELECT '平均重试次数', ROUND(AVG(retry_count), 2) FROM message_process_log WHERE retry_count > 0;"

echo "每周维护任务完成: $(date)"
```

### 5.2 数据维护程序

#### 清理过期数据
```sql
-- 清理30天前的成功记录（可选）
DELETE FROM message_process_log 
WHERE process_status = 'success' 
AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
LIMIT 1000;

-- 清理超过重试上限的失败记录（谨慎操作）
-- 建议先归档再删除
CREATE TABLE message_process_log_archive_2026_08 AS
SELECT * FROM message_process_log 
WHERE retry_count >= 10 
AND process_status IN ('failed', 'critical_error')
AND updated_at < DATE_SUB(NOW(), INTERVAL 60 DAY);

-- 删除已归档的数据
DELETE FROM message_process_log 
WHERE retry_count >= 10 
AND process_status IN ('failed', 'critical_error')
AND updated_at < DATE_SUB(NOW(), INTERVAL 60 DAY);
```

### 5.3 升级和维护窗口

#### 推荐维护时间
- **日常维护**: 每天凌晨2:00-4:00（低峰期）
- **升级部署**: 周日凌晨1:00-6:00
- **数据库维护**: 每周日凌晨2:00-4:00

#### 升级前检查清单
```bash
# 升级前准备检查表
echo "=== 升级前检查 ==="

# 1. 数据库备份完成
echo "✓ 数据库备份: backup/baidu_download_pre_upgrade_$(date +%Y%m%d_%H%M%S).sql"

# 2. 当前版本记录
echo "✓ 当前版本: $(cat VERSION)"

# 3. 配置文件备份
echo "✓ 配置备份: cp .env .env.backup_$(date +%Y%m%d)"

# 4. 依赖项检查
echo "✓ 依赖检查: pip check"

# 5. 磁盘空间检查
echo "✓ 磁盘空间: df -h"

# 6. 运行状态检查
echo "✓ 服务状态: tasklist | findstr baidu-download"

echo "=== 升级前检查完成 ==="
```

---

## 🚀 6. 部署和回滚程序

### 6.1 标准部署程序

#### 部署前检查
```bash
# 1. 验证环境配置
python -c "from src.config.settings import Settings; Settings().validate()"

# 2. 检查数据库连接
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT DATABASE();"

# 3. 验证SFTP连接
python scripts/diagnose_sftp.py

# 4. 检查依赖版本
pip list | grep -E "(paramiko|pymysql|cryptography)"
```

#### 部署步骤
```bash
# 1. 停止当前服务
taskkill /PID $(tasklist | findstr baidu-download | awk '{print $2}') /T

# 2. 备份当前版本
mkdir backup
copy baidu-download.exe backup/baidu-download_$(date +%Y%m%d).exe
cp -r src backup/src_$(date +%Y%m%d)

# 3. 部署新版本
copy new_release/baidu-download.exe .
xcopy /E /I new_release\src src\

# 4. 更新配置（如需要）
copy new_release/.env.example .env.new
# 手动合并配置...

# 5. 启动新版本
baidu-download.exe --auto --verbose

# 6. 验证部署
tail -n 50 logs/transfer.log
python scripts/check_db.py
```

### 6.2 回滚程序

#### 快速回滚
```bash
# 1. 停止当前版本
taskkill /PID $(tasklist | findstr baidu-download | awk '{print $2}') /T

# 2. 恢复之前版本
copy backup/baidu-download_YYYYMMDD.exe baidu-download.exe
cp -r backup/src_YYYYMMDD src

# 3. 恢复配置
cp backup/.env_YYYYMMDD .env

# 4. 重启服务
baidu-download.exe --auto --verbose

# 5. 验证回滚成功
tail -n 30 logs/transfer.log
```

#### 数据库回滚（谨慎使用）
```sql
-- 保存当前状态
CREATE TABLE message_process_log_before_rollback AS SELECT * FROM message_process_log;

-- 回滚数据变更（根据实际变更调整）
-- 例如：删除新添加的字段
ALTER TABLE message_process_log DROP COLUMN retry_count;

-- 验证回滚
DESCRIBE message_process_log;
```

---

## 📞 7. 联系和支持

### 7.1 升级路径和联系方式

#### 问题升级路径
1. **一级** (值班工程师): 30分钟内响应
2. **二级** (高级工程师): 2小时内响应  
3. **三级** (架构师/开发团队): 24小时内响应

#### 紧急联系方式
- **系统负责人**: [负责人名称] - [联系方式]
- **数据库管理员**: [DBA联系方式]
- **平台支持**: [支持团队联系方式]

### 7.2 变更管理程序

#### 变更请求模板
```markdown
## 变更请求

**变更类型**: [功能增强/缺陷修复/配置调整/紧急修复]
**优先级**: [高/中/低]
**预计影响**: [影响范围和用户]
**变更窗口**: [日期时间]
**执行人员**: [负责人]
**批准人员**: [批准人]

### 变更描述
[详细描述变更内容]

### 风险评估
- 技术风险: [风险评估]
- 业务风险: [业务影响评估]
- 回滚方案: [回滚步骤]

### 测试验证
- [ ] 功能测试完成
- [ ] 性能测试完成  
- [ ] 回归测试完成
- [ ] 回滚测试完成
```

---

## 📋 附录

### A. 快速参考命令

```bash
# 服务控制
baidu-download.exe --auto --verbose    # 启动服务
taskkill /PID <pid> /T                # 停止服务
tasklist | findstr baidu-download     # 查看进程

# 日志查看
tail -n 100 logs/transfer.log        # 最新日志
grep "ERROR" logs/transfer.log        # 错误日志

# 数据库操作
mysql -h $DB_HOST -u $DB_USER -p      # 连接数据库
mysqldump [options] database > backup.sql  # 数据库备份

# 健康检查
python scripts/check_db.py            # 数据库检查
python scripts/diagnose_recent_failures.py  # 失败分析
```

### B. 常用SQL查询

```sql
-- 系统健康概览
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) as success,
    ROUND(AVG(processing_time_ms)/1000, 2) as avg_seconds
FROM message_process_log 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 重试统计
SELECT 
    retry_count,
    COUNT(*) as count,
    process_status
FROM message_process_log 
WHERE retry_count > 0
GROUP BY retry_count, process_status
ORDER BY retry_count DESC;

-- 错误分布
SELECT 
    SUBSTRING_INDEX(error_message, ':', 2) as error_type,
    COUNT(*) as count
FROM message_process_log 
WHERE error_message IS NOT NULL
AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY error_type
ORDER BY count DESC;
```

### C. 配置参数参考

```ini
# 核心配置
MESSAGE_MAX_RETRIES=10              # 消息重试上限
MAX_RETRIES=3                       # 文件传输重试次数
CONCURRENT_UPLOADS=1                # 并发上传数

# 资源限制
TEMP_DIR=./temp                     # 临时文件目录
LOG_LEVEL=INFO                      # 日志级别
LOG_FILE=./logs/transfer.log        # 日志文件路径
```

---

**文档版本:** 1.0  
**最后更新:** 2026-08-19  
**下次审核:** 2026-09-19  
**维护人员:** 运维团队

---

## 🔖 变更历史

| 日期 | 版本 | 变更内容 | 修改人 |
|------|------|----------|--------|
| 2026-08-19 | 1.0 | 初始版本，包含完整运维程序 | 运维团队 |