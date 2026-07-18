# 数据库配置灵活性改进说明

## 🎯 问题发现

用户发现 `file_transfer_log` 表的数据库名称是硬编码的 `baidu_download`，不够灵活。

## ✅ 解决方案

### 方案1: 动态数据库名（推荐）

使用新的初始化脚本支持自定义数据库名称：

**Windows**:
```bash
# 使用默认数据库名 (baidu_download)
init_db.bat

# 使用自定义数据库名
init_db.bat my_project_db
```

**Linux/Mac**:
```bash
# 使用默认数据库名 (baidu_download)
chmod +x init_db.sh
./init_db.sh

# 使用自定义数据库名
./init_db.sh my_project_db
```

### 方案2: 手动修改

如果你想手动控制数据库创建过程：

1. **手动创建数据库**:
```sql
CREATE DATABASE IF NOT EXISTS my_project_db
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;
```

2. **修改 middle/db_init.sql**:
```sql
-- 将第5行改为：
USE my_project_db;
```

3. **修改 .env 文件**:
```
DB_NAME=my_project_db
```

4. **执行初始化**:
```bash
mysql -u root -p < middle/db_init.sql
```

## 🔧 当前配置

### 代码配置 (✅ 灵活)
```python
# src/config/settings.py
self.db_name = self._get_required_env('DB_NAME')
```
**状态**: 代码已经支持环境变量配置 ✅

### 初始化脚本 (❌ 硬编码)
```sql
-- middle/db_init.sql
CREATE DATABASE IF NOT EXISTS baidu_download  -- 硬编码 ❌
```
**状态**: 需要使用新的init_db脚本 ✅

### 环境配置 (✅ 灵活)
```bash
# .env
DB_NAME=baidu_download  # 可以修改 ✅
```
**状态**: 可以通过修改.env文件配置 ✅

## 📋 使用示例

### 示例1: 为不同项目使用不同数据库

**项目A**:
```bash
# 1. 创建数据库
init_db.bat project_a

# 2. 更新 .env
DB_NAME=project_a

# 3. 运行程序
baidu-download.exe --link="..." --folder="project_a"
```

**项目B**:
```bash
# 1. 创建数据库
init_db.bat project_b

# 2. 更新 .env  
DB_NAME=project_b

# 3. 运行程序
baidu-download.exe --link="..." --folder="project_b"
```

### 示例2: 开发/测试/生产环境分离

**开发环境**:
```bash
init_db.bat baidu_download_dev
# DB_NAME=baidu_download_dev
```

**测试环境**:
```bash
init_db.bat baidu_download_test
# DB_NAME=baidu_download_test
```

**生产环境**:
```bash
init_db.bat baidu_download_prod
# DB_NAME=baidu_download_prod
```

## 🚀 快速开始

### 新项目部署

1. **初始化自定义数据库**:
   ```bash
   init_db.bat my_custom_db
   ```

2. **更新配置文件**:
   ```
   # release\dist\.env
   DB_NAME=my_custom_db
   ```

3. **运行程序**:
   ```bash
   baidu-download.exe --link="..." --folder="my_folder"
   ```

### 从现有配置迁移

如果你已经在使用 `baidu_download` 数据库：

**选项1: 继续使用 (推荐)**
- 无需修改，保持现状
- 所有项目数据在一个数据库中
- 通过 `folder_name` 字段区分不同项目

**选项2: 迁移到新数据库**
- 导出现有数据
- 创建新数据库
- 导入数据
- 更新配置

## 📋 配置最佳实践

### 推荐做法

1. **小型项目**: 使用默认 `baidu_download` 数据库
2. **多项目环境**: 使用独立数据库，便于管理
3. **团队环境**: 每个开发/测试/生产使用独立数据库

### 数据库命名建议

```
baidu_download           # 默认数据库
baidu_download_dev      # 开发环境
baidu_download_test     # 测试环境  
baidu_download_prod     # 生产环境
project_name_files      # 项目特定数据库
```

## 🎉 改进总结

**问题**: 数据库名称硬编码
**解决**: 提供灵活的初始化脚本
**效果**: 支持自定义数据库名称

**现在你可以为每个项目使用独立的数据库了！** 🎯