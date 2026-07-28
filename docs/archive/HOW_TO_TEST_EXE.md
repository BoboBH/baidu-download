# 🚀 .exe文件测试指南

## 📍 .exe文件位置

**主程序文件**: `release/dist/baidu-download.exe` (11MB)

这是完整的Windows可执行文件，包含了所有Python依赖，无需目标服务器安装Python环境。

---

## 🧪 快速测试

### 1. 配置测试 (推荐)
```bash
cd release/dist
./baidu-download.exe --link "测试链接" --code "测试码" --folder "test" --dry-run
```

这个命令会：
- ✅ 验证配置文件是否正确
- ✅ 检查BaiduPCS-Go工具路径
- ✅ 验证SFTP和数据库配置
- ❌ 不执行实际的下载上传操作

### 2. 完整功能测试
```bash
cd release/dist
./baidu-download.exe --link "https://pan.baidu.com/s/xxx" --code "1234" --folder "test_files"
```

---

## 📋 测试前检查

### 1. 配置文件
确保项目根目录有`.env`文件：
```bash
# 检查配置文件
test -f ../.env && echo "配置文件存在" || echo "需要创建.env文件"
```

### 2. BaiduPCS-Go工具
确保BaiduPCS-Go工具路径正确：
```bash
# 检查工具路径
test -f "D:/tools/BaiduPCS-Go-v4.0.1-windows-x64/BaiduPCS-Go.exe" && echo "工具存在" || echo "需要下载BaiduPCS-Go"
```

### 3. 数据库连接
确保MySQL数据库正在运行：
```bash
# 测试数据库连接
mysql -u root -p -e "SHOW DATABASES;"
```

---

## 🔧 常见问题解决

### 问题1: 找不到配置文件
```bash
# 解决方案：将.env文件复制到exe所在目录
copy ..\\.env .env
cd release/dist
./baidu-download.exe --dry-run
```

### 问题2: BaiduPCS-Go路径错误
```bash
# 检查.env中的BAIDUPCS_GO_PATH配置
# 确保路径格式：D:/tools/... (使用正斜杠)
```

### 问题3: 缺少依赖文件
```bash
# 确保以下文件存在：
# - .env 配置文件
# - baidu-cookies.txt 百度网盘Cookie
# - BaiduPCS-Go.exe 工具
```

---

## 📊 测试场景

### 场景1: 配置验证测试
```bash
cd release/dist
./baidu-download.exe --link "https://pan.baidu.com/s/test" --code "0000" --folder "config-test" --dry-run
```
**预期结果**: 显示配置验证通过，不执行实际操作

### 场景2: 下载功能测试
```bash
cd release/dist
./baidu-download.exe --link "有效分享链接" --code "提取码" --folder "download-test" --verbose
```
**预期结果**: 显示详细的下载过程日志

### 场景3: 完整流程测试
```bash
cd release/dist
./baidu-download.exe --link "有效分享链接" --code "提取码" --folder "full-test"
```
**预期结果**: 完整的下载→上传→清理流程

---

## 🎯 推荐测试步骤

### 1. 基础配置测试
```bash
cd release/dist
./baidu-download.exe --help
```
查看帮助信息，确认exe文件可以正常运行。

### 2. 配置文件测试
```bash
./baidu-download.exe --link "test" --code "test" --folder "test" --dry-run
```
验证所有配置项是否正确。

### 3. 实际功能测试
```bash
./baidu-download.exe --link "你的分享链接" --code "提取码" --folder "test-$(date +%Y%m%d)" --verbose
```
测试完整的文件传输功能。

---

## 💡 测试技巧

### 使用详细日志
```bash
./baidu-download.exe --link "链接" --code "码" --folder "目录" --verbose
```
`--verbose` 参数会显示详细的日志信息，便于调试。

### 使用测试目录
```bash
# 使用包含日期的目录名，避免冲突
./baidu-download.exe --link "链接" --code "码" --folder "test-$(date +%Y%m%d-%H%M%S)"
```

### 检查临时文件
```bash
# 查看临时目录
ls -la ../temp/

# 查看日志文件
cat ../logs/transfer.log
```

---

## 📝 测试成功标志

### ✅ 配置测试成功
```
配置验证通过
分享链接: xxx
提取码: xxx
目录名: xxx
Dry-run模式：配置验证完成，不执行实际操作
```

### ✅ 下载测试成功
```
[INFO] 登录成功
[INFO] 分享链接转存成功
[INFO] 找到 X 个PDF文件
[INFO] 文件下载成功
```

### ✅ 完整测试成功
```
处理完成！
总文件数: X
成功: X
失败: 0
跳过: 0
```

---

## 🚨 常见错误处理

### 错误1: Configuration file not found
**原因**: 找不到.env文件
**解决**: 复制.env文件到exe所在目录

### 错误2: BaiduPCS-Go not found
**原因**: BaiduPCS-Go工具路径不正确
**解决**: 下载并配置正确的工具路径

### 错误3: Database connection failed
**原因**: MySQL数据库连接失败
**解决**: 检查数据库服务状态和配置

---

**测试前建议先使用 --dry-run 参数验证配置！** 🎯