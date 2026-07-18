# 智能数据库初始化脚本使用说明

## 🎯 功能说明

新的初始化脚本会**自动读取`.env`文件中的`DB_NAME`配置**来创建数据库，确保配置文件与实际数据库完全同步。

## 🚀 使用方法

### Windows系统

```bash
# 在项目根目录或release/dist目录中运行
init_db_auto.bat
```

### Linux/Mac系统

```bash
# 在项目根目录或release/dist目录中运行
chmod +x init_db_auto.sh
./init_db_auto.sh
```

## 📋 脚本功能

### 1. 自动查找.env文件
脚本会按优先级查找.env文件：
1. 当前目录: `.env`
2. Release目录: `release/dist/.env`
3. 父目录Release: `../release/dist/.env`

### 2. 读取DB_NAME配置
从找到的.env文件中读取：
```bash
DB_NAME=test  # 或者你在.env中配置的任何数据库名
```

### 3. 用户确认
显示将要创建的数据库名称，请求用户确认：
```
确认创建数据库 'test'? (Y/N):
```

### 4. 创建数据库和表
- 创建指定名称的数据库
- 创建`file_transfer_log`表
- 创建`execution_summary`表

### 5. 验证创建
显示创建的表列表，确认初始化成功。

## 🔧 配置示例

### 示例1: 使用测试数据库

**.env配置**:
```bash
DB_NAME=test
```

**运行脚本**:
```bash
init_db_auto.bat
```

**结果**: 创建名为`test`的数据库

### 示例2: 使用项目专用数据库

**.env配置**:
```bash
DB_NAME=project_files_2026
```

**运行脚本**:
```bash
init_db_auto.bat
```

**结果**: 创建名为`project_files_2026`的数据库

## ✅ 优势

### 1. 配置同步
- ✅ 数据库名称与.env配置完全一致
- ✅ 无需手动修改配置
- ✅ 避免配置错误

### 2. 灵活性
- ✅ 支持任意数据库名称
- ✅ 不同项目使用不同数据库
- ✅ 开发/测试/生产环境分离

### 3. 安全性
- ✅ 创建前用户确认
- ✅ 避免误操作
- ✅ 配置验证

## 📋 完整流程

### 第一次部署

1. **配置.env文件**:
   ```bash
   # 编辑 release\dist\.env
   DB_NAME=my_custom_db
   ```

2. **运行初始化脚本**:
   ```bash
   cd release\dist
   ..\..\init_db_auto.bat
   ```

3. **确认创建**:
   ```
   确认创建数据库 'my_custom_db'? (Y/N): Y
   ```

4. **验证完成**:
   ```
   数据库初始化完成!
   现在可以运行程序了
   ```

## 🎯 与旧脚本对比

### 旧脚本 (init_db.bat)
```bash
# 需要手动指定数据库名
init_db.bat my_database

# 还需要手动修改.env文件
# DB_NAME=my_database  # 手动修改
```

### 新脚本 (init_db_auto.bat)
```bash
# 自动读取.env配置
init_db_auto.bat

# .env中: DB_NAME=my_database
# 自动同步，无需手动修改
```

## 🔍 故障排除

### 问题1: 找不到.env文件
```
错误: 找不到.env文件
```
**解决**: 确保在正确的目录中运行脚本

### 问题2: 未找到DB_NAME配置
```
错误: .env文件中未找到DB_NAME配置
```
**解决**: 在.env文件中添加 `DB_NAME=your_database_name`

### 问题3: MySQL连接失败
```
错误: 创建数据库失败
```
**解决**: 检查MySQL服务状态和root密码

## 🎉 总结

**核心改进**: 
- ✅ 自动读取.env配置
- ✅ 配置自动同步
- ✅ 避免手动错误

**使用体验**:
- ✅ 一步完成初始化
- ✅ 配置与实际一致
- ✅ 支持灵活命名

**现在数据库初始化更加智能和自动化了！** 🎯