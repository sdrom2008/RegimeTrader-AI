# NexusAI Tech - 部署指南

## 前置条件

- **.NET 10 SDK**（或 .NET 8+）
- **Node.js 18+**
- **MySQL 8.0+**
- **Git**（可选）

---

## 1. 数据库准备

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE IF NOT EXISTS synerixis_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选）
CREATE USER 'nexusai'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL ON synerixis_dev.* TO 'nexusai'@'localhost';
FLUSH PRIVILEGES;
```

---

## 2. 后端配置

编辑 `my-project/Synerixis.Api/appsettings.Development.json`：

```json
{
  "Logging": { "LogLevel": { "Default": "Information", "Microsoft.AspNetCore": "Warning" } },
  "AllowedHosts": "*",
  "Jwt": {
    "Key": "YOUR_RANDOM_32_CHARS_OR_MORE_STRING",
    "Issuer": "Synerixis-Dev",
    "Audience": "Synerixis-Clients-Dev"
  },
  "MySqlConnection": "server=localhost;port=3306;database=synerixis_dev;user=root;password=yourpassword;",
  "Tongyi": {
    "Qianwen": {
      "ApiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }
}
```

> **注意**：`Jwt.Key` 至少 32 字符；`MySqlConnection` 密码与数据库设置一致；`Tongyi.ApiKey` 从阿里云 DashScope 控制台获取。

---

## 3. 数据库迁移

在 `my-project/` 目录执行：

```bash
dotnet tool install --global dotnet-ef   # 如果未安装
dotnet ef database update
```

或在 Synerixis.Api 项目内：
```bash
cd my-project/Synerixis.Api
dotnet ef database update
```

这将自动创建所有表（基于 `AppDbContext`）。

---

## 4. 启动后端

```bash
cd my-project/Synerixis.Api
dotnet run
```

默认监听：
- HTTP: http://localhost:5145
- HTTPS: https://localhost:7145

测试健康：
```bash
curl http://localhost:5145/health
```

Swagger（如果已启用）：
http://localhost:5145/swagger

---

## 5. 前端部署

```bash
cd nexusai-frontend
npm install
npm run build
```

构建产物在 `dist/` 目录。

### 5.1 开发模式（代理到后端）
```bash
npm run dev
```
访问 http://localhost:5173

---

## 6. Nginx 反向代理（生产建议）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://localhost:5145;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection keep-alive;
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /path/to/nexusai-frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 7. API 端点清单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/marketing/generate-copy` | 生成营销文案 |
| POST | `/api/chat/send` | 客服对话 |
| POST | `/api/agent/optimizeproduct` | 商品优化 |
| POST | `/api/competitor/analyze` | 竞品分析 |

---

## 8. 常见问题

### MySQL 连接失败
- 检查防火墙/权限
- 确保 `MySqlConnection` 正确
- 使用 `mysql -u root -p -h localhost` 测试连接

### 模型调用失败
- 确认 `Tongyi.ApiKey` 有效
- 检查网络（DashScope API 可访问）

### CORS 错误
- 确保后端 `app.UseCors("AllowAll")` 已启用（ Program.cs ）
- 或在前端请求添加 `mode: 'cors'`

---

## 9. 后续优化

- 启用 HTTPS
- 配置日志文件
- 数据库备份策略
- 监控与告警

---

祝上线顺利！🚀
