# 钉钉API权限申请指南

## 🔑 需要申请的权限

**权限名称：** `qyapi_chat_read` （聊天记录读取权限）

**权限描述：** 允许应用读取群聊消息历史记录

## 📋 申请步骤

### 1. 访问钉钉开放平台权限申请页面

直接访问以下链接（你的应用已预填充）：

```
https://open-dev.dingtalk.com/appscope/apply?content=dingcu3gdk9wnifpzm16%23qyapi_chat_read
```

或者手动访问：`https://open-dev.dingtalk.com/appscope/apply`

### 2. 登录并选择应用

使用管理员账号登录钉钉开放平台
- 选择应用：`dingcu3gdk9wnifpzm16`
- 申请权限：`qyapi_chat_read`

### 3. 提交申请理由

申请理由示例：

> 需要读取群聊消息以自动处理百度网盘分享链接，实现文件自动化传输功能。

### 4. 等待审批

- 通常需要1-2个工作日
- 审批通过后会收到通知

## ✅ 申请批准后的验证

一旦权限申请批准，运行以下测试验证：

```bash
python test_dingtalk_api.py
```

预期结果：
- ✅ 能够成功获取群消息列表
- ✅ 返回消息内容和元数据

## 🔧 技术实现状态

**已完成：**
- ✅ API端点确认：`https://oapi.dingtalk.com/chat/get`
- ✅ 认证机制：access_token获取正常
- ✅ 代码实现：`DingtalkMessageClient.get_messages()` 方法已实现
- ✅ 错误处理：权限不足、API限流等场景已处理
- ✅ 数据库迁移：`source` 字段添加成功

**待完成（需要权限）：**
- ⏸️ 真实API测试验证
- ⏸️ 完整流程测试

## 📞 如需帮助

如果在申请过程中遇到问题：
1. 检查应用是否有足够的权限范围
2. 确认账号是否有管理员权限
3. 联系钉钉技术支持

---

**状态：** 等待权限申请批准  
**下一步：** 权限批准后进行端到端测试