# 分享链接转存功能问题修复

## 🔍 问题诊断

您提到的 **"sharelink -> personalfolder 看起来不成功"** 问题确实存在！

## 🐛 根本原因

代码中使用了错误的百度网盘命令：

```python
# ❌ 错误的命令 (之前的代码)
result = self._run_command([
    'share',      # 错误：share 命令用于分享文件，不是转存
    'save',
    share_link,
    code,
    '-p', f'/{folder_name}'
])
```

## ✅ 修复方案

已修正为正确的 `transfer` 命令：

```python
# ✅ 正确的命令 (修复后的代码)
# 1. 切换到根目录
self._run_command(['cd', '/'])

# 2. 使用 transfer 命令转存分享链接
clean_link = share_link.split('?pwd=')[0]
if code and code.strip():
    command = ['transfer', clean_link, code]
else:
    command = ['transfer', clean_link]

result = self._run_command(command)

# 3. 自动检测转存后的目录名并重命名到指定目录
new_items = self._find_new_items(before_result['stdout'], after_result['stdout'])
if folder_name and new_items[0] != folder_name:
    self._run_command(['mv', f'/{new_items[0]}', f'/{folder_name}'])
```

## 🎯 修复内容

### 1. **命令修正**
- 从 `share save` 改为正确的 `transfer` 命令
- `transfer` 命令才是百度网盘中转存分享链接的正确命令

### 2. **逻辑优化**
- 先获取转存前的目录列表
- 执行转存操作
- 比较转存前后的差异，自动检测转存后的目录名
- 如果需要，自动重命名到指定的目录名

### 3. **兼容性改进**
- 支持有提取码和无提取码的分享链接
- 自动处理链接中的 `?pwd=` 参数
- 支持目录和单文件转存

## 🚀 测试方法

```python
from src.processor.file_processor import FileProcessor

processor = FileProcessor()

# 测试转存功能
share_link = "https://pan.baidu.com/s/xxxxx"
code = "提取码"
folder_name = "target_folder"

result = processor.process_files(share_link, code, folder_name)
print(f"处理结果: {result}")
```

## 📋 BaiduPCS-Go 命令参考

正确的转存命令格式：

```bash
# 有提取码
BaiduPCS-Go transfer https://pan.baidu.com/s/1VYzSl7465sdrQXe8GT5RdQ 704e

# 无提取码
BaiduPCS-Go transfer https://pan.baidu.com/s/1VYzSl7465sdrQXe8GT5RdQ

# 带密码参数的链接
BaiduPCS-Go transfer https://pan.baidu.com/s/1VYzSl7465sdrQXe8GT5RdQ?pwd=704e
```

## ⚠️ 注意事项

1. **transfer 命令限制**: 只能转存到当前目录，不能直接指定目标路径
2. **目录命名**: 转存后的目录名由分享链接决定，可能不是您指定的名称
3. **重命名处理**: 代码会自动处理目录名不一致的情况

## 🔧 文件修改位置

- **文件**: `src/downloader/baidu_client.py`
- **方法**: `save_share_link`
- **新增方法**: `_find_new_items` (用于检测转存后的目录名)

---

**修复完成！现在分享链接转存功能应该可以正常工作了。** 🎉

您可以重新测试 sharelink -> personalfolder 的功能了。
