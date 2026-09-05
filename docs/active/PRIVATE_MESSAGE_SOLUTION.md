# 钉钉私信功能问题和解决方案

## 问题诊断

根据钉钉开放平台文档搜索结果，私信失败的主要原因：

### 1. 用户ID格式错误
**当前格式**: `$:LWCP_v1:$TobB/UgOeoc+Mp6oIwzzUQ==`
**正确格式**: 简单字符串，如 "1001"、"manager4220"

### 2. 权限配置缺失
需要以下权限：
- 企业员工电话号码和邮箱信息
- 联系人管理权限
- 消息发送权限

### 3. access_token问题
可能使用了错误的token类型或传递方式

## 解决步骤

### 1. 获取正确的userId
从钉钉通讯录API获取标准userId：
```python
# 使用钉钉通讯录API获取正确的userId
```

### 2. 配置应用权限
在钉钉开发者后台：
1. 进入应用管理 → 权限管理
2. 申请消息发送相关权限
3. 添加目标用户到授权范围

### 3. 验证access_token
确认使用企业内部应用的access_token，不是个人应用的token

## 相关文档
- [钉钉API调用指南](https://open.dingtalk.com/document/development/server-api-calling-guide)
- [获取用户详情](https://open.dingtalk.com/document/app/queries-user-details)
- [权限管理](https://open.dingtalk.com/document/development/obtain-user-token)

## 当前状态
- ✅ webhook通知正常工作
- ❌ 私信功能需要正确的userId和权限配置
- 📝 需要用户在钉钉开放平台配置权限