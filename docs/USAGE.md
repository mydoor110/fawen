# 公文文件号管理系统 - 使用说明

## 🌐 访问地址

### API 文档界面（推荐使用）

这两个地址提供了完整的API文档和交互式测试界面：

1. **Swagger UI** (推荐，界面更友好)
   - 访问地址: http://192.168.1.99:8000/docs
   - 功能: 完整的API文档 + 在线测试接口

2. **ReDoc** (文档更详细)
   - 访问地址: http://192.168.1.99:8000/redoc
   - 功能: 美观的API文档

### 基础服务地址

- 根路径: http://192.168.1.99:8000/
- 健康检查: http://192.168.1.99:8000/health

## 📝 如何使用 Swagger UI

### 1. 打开浏览器
访问: http://192.168.1.99:8000/docs

### 2. 登录系统
1. 展开 `/api/auth/login` 接口
2. 点击 "Try it out"
3. 在 Request body 中输入:
   ```
   username: admin
   password: admin123
   ```
4. 点击 "Execute"
5. 复制返回的 `access_token`

### 3. 使用其他API
1. 点击右上角的 "Authorize" 按钮
2. 输入: `Bearer 你的access_token`
3. 点击 "Authorize"
4. 现在可以测试所有需要认证的接口了

## 🔧 命令行使用（curl）

### 登录获取Token
```bash
curl -X POST http://192.168.1.99:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### 使用Token访问API
```bash
TOKEN="你的access_token"

# 查看用户信息
curl -X GET http://192.168.1.99:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 查看所有用户
curl -X GET http://192.168.1.99:8000/api/admin/users \
  -H "Authorization: Bearer $TOKEN"
```

## 👥 默认账号

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin | admin123 | 系统管理员 | 所有权限 |

## 📋 可用功能

### 用户管理
- 查看用户列表
- 查看用户详情
- 更新用户信息
- 删除用户
- 分配角色

### 文档管理
- 创建文档
- 查看文档列表
- 上传Word文档
- 提交校对
- 提交审批

### 校对流程
- 查看校对任务
- 完成校对（通过/不通过）

### 审批流程
- 查看审批任务
- 审批通过
- 审批驳回

### 编号管理
- 查看编号池
- 查看编号记录
- 分配文件号

### 系统管理
- 查看角色列表
- 分配审批角色

## ⚠️ 注意事项

1. **仅后端API**: 目前只有后端服务，没有网页管理界面
2. **推荐使用Swagger UI**: 通过浏览器访问 /docs 进行操作
3. **Token有效期**: 24小时，过期后需要重新登录
4. **修改密码**: 建议立即修改默认管理员密码

## 🚀 后续开发计划

- [ ] 开发前端管理界面
- [ ] 添加文件上传界面
- [ ] 添加流程可视化
- [ ] 添加消息通知功能

## 📞 获取帮助

如果遇到问题，请：
1. 检查服务是否正常运行: http://192.168.1.99:8000/health
2. 查看API文档: http://192.168.1.99:8000/docs
3. 查看服务器日志

---

**快速开始**: 打开浏览器访问 http://192.168.1.99:8000/docs
