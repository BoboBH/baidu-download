# SFTP开关功能使用指南

## 🎯 功能概述

v1.0.3版本新增了SFTP上传开关功能，允许用户控制是否将文件上传到SFTP服务器。

## 🔧 参数说明

### 1. `--no-sftp`
- **类型**: 布尔标志
- **默认值**: False
- **说明**: 明确禁用SFTP上传

### 2. `--with-sftp`
- **类型**: 布尔标志
- **默认值**: False  
- **说明**: 明确启用SFTP上传

### 3. 默认行为
- **SFTP上传默认禁用**
- 只有明确指定`--with-sftp`时才会启用SFTP上传
- `--no-sftp`优先级高于`--with-sftp`

## 📋 使用示例

### 示例1: 默认模式（不上传SFTP）
```bash
python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test"
```
**效果**: 只下载文件到本地，不上传到SFTP服务器

### 示例2: 明确禁用SFTP
```bash
python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test" --no-sftp
```
**效果**: 明确禁用SFTP上传（与默认行为相同）

### 示例3: 启用SFTP上传
```bash
python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test" --with-sftp
```
**效果**: 下载文件并上传到SFTP服务器

### 示例4: 同时指定两个参数（优先级）
```bash
python main.py --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test" --with-sftp --no-sftp
```
**效果**: `--no-sftp`优先级更高，SFTP上传被禁用

## 🔄 行为对比

### 启用SFTP上传时
1. 下载文件到本地临时目录
2. 连接SFTP服务器
3. 上传文件到SFTP服务器
4. 验证上传成功
5. 删除本地临时文件
6. 记录完整日志到数据库

### 禁用SFTP上传时（默认）
1. 下载文件到本地临时目录
2. **跳过SFTP连接和上传**
3. 直接标记为成功
4. 删除本地临时文件
5. 记录日志到数据库（状态为success）

## 📊 日志输出对比

### 启用SFTP上传时的日志
```
[INFO] FileProcessor initialized (SFTP: enabled)
[INFO] SFTP connection established
[INFO] Processing file: example.pdf
[INFO] Downloading example.pdf to temp_a.pdf (attempt 1/3)
[INFO] Downloaded: example.pdf -> temp_a.pdf
[INFO] Uploading example.pdf to SFTP...
[INFO] File uploaded successfully: temp_a.pdf -> /sftp01/upload/test/example.pdf
[INFO] Successfully processed: example.pdf
```

### 禁用SFTP上传时的日志（默认）
```
[INFO] FileProcessor initialized (SFTP: disabled)
[INFO] SFTP upload disabled, skipping connection
[INFO] Processing file: example.pdf
[INFO] Downloading example.pdf to temp_a.pdf (attempt 1/3)
[INFO] Downloaded: example.pdf -> temp_a.pdf
[INFO] SFTP upload disabled, marking example.pdf as success
[INFO] Successfully processed (no SFTP upload): example.pdf
```

## ⚙️ 配置要求

### 禁用SFTP上传时（默认）
- ✅ 不需要SFTP服务器配置
- ✅ 不需要.env中的SFTP相关配置
- ✅ 只需要百度网盘配置
- ✅ 需要MySQL数据库配置（用于记录日志）

### 启用SFTP上传时
- ✅ 需要完整的SFTP服务器配置
- ✅ 需要百度网盘配置
- ✅ 需要MySQL数据库配置

## 🎯 使用场景

### 场景1: 仅下载测试
```bash
# 测试下载功能，不需要上传到SFTP
python main.py --link "测试链接" --code "提取码" --folder "test"
```

### 场景2: 生产环境部署
```bash
# 生产环境需要上传到SFTP服务器
python main.py --link "生产链接" --code "提取码" --folder "production" --with-sftp
```

### 场景3: 开发调试
```bash
# 开发时快速测试，跳过SFTP上传
python main.py --link "测试链接" --code "提取码" --folder "dev" --verbose
```

## 🔍 数据库记录

无论是否启用SFTP上传，系统都会在数据库中记录文件处理日志：

### 禁用SFTP上传时的记录
```sql
-- 文件状态仍然为success
INSERT INTO file_transfer_log (
    file_name, transfer_status, download_time, upload_time
) VALUES (
    'example.pdf', 'success', '2026-07-13 10:00:00', '2026-07-13 10:00:01'
);
```

**注意**: 禁用SFTP时，upload_time为download_time稍后的时间戳，表示"处理完成"时间，而非实际上传时间。

## 🚀 性能优势

### 禁用SFTP上传时的优势
- ⚡ **更快的处理速度**: 跳过SFTP连接和上传步骤
- 💾 **节省网络带宽**: 不消耗上传带宽
- 🔒 **减少依赖**: 不需要SFTP服务器可用
- 🛠️ **简化配置**: 减少配置复杂度

### 性能对比示例
**63个PDF文件，每个约5MB**:

| 模式 | 下载时间 | 上传时间 | 总时间 | 网络流量 |
|------|----------|----------|--------|----------|
| 禁用SFTP | 5分钟 | 0秒 | **5分钟** | 315MB下载 |
| 启用SFTP | 5分钟 | 8分钟 | **13分钟** | 315MB下载+315MB上传 |

## 🔧 故障排除

### 问题1: 启用了--with-sftp但连接失败
```
[WARNING] SFTP connection failed, upload will be skipped
[INFO] FileProcessor initialized (SFTP: disabled)
```
**解决方法**: 
1. 检查.env中的SFTP配置
2. 验证SFTP服务器可访问性
3. 系统会自动降级为禁用模式

### 问题2: 不确定当前是否启用了SFTP
**解决方法**: 查看日志中的初始化信息
```
[INFO] FileProcessor initialized (SFTP: enabled)  # 已启用
[INFO] FileProcessor initialized (SFTP: disabled) # 已禁用
```

### 问题3: 数据库记录状态不对
**说明**: 禁用SFTP时，文件状态仍然为`success`，这是正常行为。系统认为文件已"成功处理"（下载+标记成功）。

## 📝 版本兼容性

- **v1.0.3+**: 支持SFTP开关功能
- **v1.0.2及更早**: 总是启用SFTP上传（需要配置）

## 🎉 总结

**默认行为变更**:
- v1.0.3及以后版本默认**禁用**SFTP上传
- 需要**明确指定**`--with-sftp`才能启用SFTP上传
- 这一变更是为了简化使用和降低配置复杂度

**推荐做法**:
1. 测试/开发: 使用默认模式（禁用SFTP）
2. 生产环境: 使用`--with-sftp`启用完整功能
3. 仅下载需求: 使用默认模式即可

---

**文档版本**: v1.0.3  
**更新时间**: 2026-07-13  
**功能状态**: ✅ 已实现并测试