# NexusAI Tech - 部署与演示指南

## 📦 项目结构

- **后端 API**: `my-project/Synerixis.Api/` (ASP.NET Core, 端口 7092)
- **前端**: `my-project/frontend/` (uni-app Vue3)
- **模拟测试端点**: `POST /api/webhook/shopee/test`

---

## 🚀 快速启动（演示环境）

### 1. 启动后端服务

```bash
cd /home/sdrom2008/.openclaw/workspace
./start-api.sh
```

等待输出：
```
Now listening on: http://localhost:7092
Application started. Press Ctrl+C to shut down.
```

### 2. 测试模拟 Shopee 消息

打开另一个终端，执行：

```bash
curl -X POST http://localhost:7092/api/webhook/shopee/test \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "test_user_001",
    "customerName": "测试买家",
    "message": "你好，我想咨询一下这个商品还有货吗？"
  }'
```

预期响应：
```json
{
  "code": 0,
  "message": "success",
  "reply": "这是一个模拟的 AI 自动回复。实际部署后将连接阿里云通义千问。"
}
```

### 3. 查看数据库记录

SQLite 数据库位置：
```
my-project/Synerixis.Api/bin/Release/net10.0/dev.db
```

可使用 `sqlite3` 查看：
```bash
sqlite3 my-project/Synerixis.Api/bin/Release/net10.0/dev.db
SELECT * FROM chat_sessions;
SELECT * FROM chat_messages;
```

---

## 🌐 前端部署（预览版）

### 构建前端

```bash
cd /home/sdrom2008/.openclaw/workspace/my-project/frontend
npm install  # 如果还没安装依赖
npm run build:h5  # 构建 H5 版本
```

构建产物位于：`frontend/dist/build/h5/`

### 配置后端地址

编辑 `frontend/dist/build/h5/assets/js/app.js`（或使用 HBuilderX 配置）：
- 将 API BASE_URL 设为 `http://your-server-ip:7092`

### 本地预览

使用 HBuilderX 导入 `frontend/` 项目，运行到浏览器或手机模拟器。

---

## 🔧 生产部署（Windows Server 2022）

1. **发布后端**：
   ```bash
   cd my-project/Synerixis.Api
   dotnet publish -c Release -o C:\Deploy\NexusAI
   ```
   配置 `appsettings.json` 中的 MySQL 连接和 JWT 密钥。

2. **配置反向代理**（IIS + ASP.NET Core Module）或使用 `nginx`。

3. **配置域名与 HTTPS**（Shopee Webhook 需要公网可访问的 HTTPS URL）。

4. **部署前端**：
   - 将 `frontend/dist/build/h5/` 上传到 Web 服务器目录
   - 配置 Nginx/Apache 提供静态文件

5. ** Shopee 开放平台配置**：
   - 创建应用（类型：Seller In-house System）
   - 设置 Webhook URL: `https://your-domain.com/api/webhook/shopee`
   - 订阅消息：`webchat_push` (买家聊天)
   - 填入 `AppKey`, `AppSecret`, `AccessToken`, `ShopID` 到 `appsettings.json`

---

## 📝 待办（真实接入 Shopee）

- [ ] 实现 `ShopeePlatformClient` 的签名验证（HMAC-SHA256）
- [ ] 解析真实 Webhook JSON 结构（参考 Shopee 开放平台文档）
- [ ] 实现 `SendReplyAsync` 调用 Shopee 聊天 API
- [ ] 配置 `appsettings.json` 中的真实 Credentials
- [ ] 公网部署并备案域名

---

## ✅ 演示要点

**现在**你就可以：
1. 启动后端 (`./start-api.sh`)
2. 用 `curl` 测试模拟消息
3. 查看数据库中的会话和消息记录
4. 在前端工作台查看会话列表（需登录）

这就是一个完整的、可演示的原型！等到 Shopee 审核通过后，填入真实密钥即可上线。
