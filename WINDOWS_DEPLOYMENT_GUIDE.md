# Windows Server 2022 部署完整指南

**目标**: 将 NexusAI Tech (ASP.NET Core 10.0 + MySQL 8.4.8) 部署到 Windows Server 2022 + IIS

---

## 📋 前提条件

- [x] Windows Server 2022 已安装
- [x] IIS 已安装（含 ASP.NET Core 模块）
- [x] MySQL 8.4.8 已安装并运行
- [ ] .NET 10.0 Runtime 待安装

---

## 第 1 步：安装 .NET 10.0 Runtime

### 方法 A：手动下载安装（推荐）
1. 访问 https://dotnet.microsoft.com/download/dotnet/10.0
2. 下载 **.NET 10.0 Runtime (x64)** 安装包
   - 文件名示例：`dotnet-runtime-10.0.0-win-x64.exe`
3. 在服务器上运行安装程序，默认选项即可
4. 验证安装：
   ```powershell
   dotnet --version
   # 输出应类似：10.0.0
   ```

### 方法 B：PowerShell 自动安装（使用我提供的脚本）
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install-dotnet-windows.ps1
```

---

## 第 2 步：准备数据库（MySQL）

### 2.1 创建数据库和用户
登录 MySQL：
```powershell
mysql -u root -p
```

执行 SQL（见 `mysql-schema.sql`）：
```sql
CREATE DATABASE nexusai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'nexusai'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON nexusai.* TO 'nexusai'@'localhost';
FLUSH PRIVILEGES;
```

### 2.2 运行 EF Core 迁移（生成表结构）

在后端发布目录执行：
```powershell
cd C:\Deploy\NexusAI\publish
dotnet Synerixis.Api.dll --migrations
# 注意：如果已用 EnsureCreated 开发环境，此处可能不需要迁移
```

或者直接使用 `mysql-schema.sql` 手动创建所有表。

---

## 第 3 步：发布后端应用

### 3.1 在开发机发布
```bash
cd my-project/Synerixis.Api
dotnet publish -c Release -o C:\Deploy\NexusAI\publish
```

### 3.2 拷贝到服务器
将整个 `publish` 文件夹上传到服务器的 `C:\Deploy\NexusAI\publish`

### 3.3 配置 appsettings.json
编辑 `C:\Deploy\NexusAI\publish\appsettings.json`：

```json
{
  "Database": {
    "ConnectionString": "server=localhost;port=3306;database=nexusai;user=nexusai;password=你的密码;"
  },
  "Jwt": {
    "Key": "一个至少32字符的随机字符串，例如：a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "Issuer": "NexusAI",
    "Audience": "NexusAI"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "Shopee": {
    "AppKey": "",
    "AppSecret": "",
    "AccessToken": "",
    "ShopId": ""
  }
}
```

---

## 第 4 步：配置 IIS 站点

### 4.1 打开 IIS Manager
`Win + R` → `inetmgr`

### 4.2 添加应用程序池
- 名称：`NexusAI-AppPool`
- .NET CLR 版本：`No Managed Code`
- 托管管道：`Integrated`
- 启动Mode: `AlwaysRunning`

### 4.3 添加网站
- 网站名称：`NexusAI`
- 物理路径：`C:\Deploy\NexusAI\publish`
- 绑定：类型 `http`，IP `All Unassigned`，端口 `80`（或 `7092`）
- 主机名：留空（或填你的域名）
- 应用程序池：选择 `NexusAI-AppPool`

### 4.4 配置处理程序映射
确保已安装 **ASP.NET Core 10.0** 模块（通常安装 .NET Runtime 后自动注册）
- 路径：`*`
- 模块：`AspNetCoreModuleV2`
- 可执行文件：`%home%\dotnet\` 或 `C:\Program Files\dotnet\`

### 4.5 设置文件夹权限
```powershell
icacls "C:\Deploy\NexusAI" /grant "IIS_IUSRS:(OI)(CI)RX"
icacls "C:\Deploy\NexusAI\publish" /grant "IIS_IUSRS:(OI)(CI)RX"
```

如果需要写入日志，给 `Modify` 权限。

---

## 第 5 步：测试 API

### 5.1 本地测试（在服务器上）
```powershell
cd C:\Deploy\NexusAI\publish
dotnet Synerixis.Api.dll
```
访问 http://localhost:7092/api/auth/test（如果有测试端点）看是否返回 200。

### 5.2 停止测试（Ctrl+C），让 IIS 托管

### 5.3 重启 IIS
```powershell
iisreset
```

### 5.4 浏览器访问
http://你的服务器IP:7092/swagger（如果启用了 Swagger）
或 http://你的服务器IP:7092/api/auth/login

---

## 第 6 步：配置 HTTPS（生产必须）

### 6.1 获取 SSL 证书
- 自签名（测试）：`New-SelfSignedCertificate`
- 正式：从 Let's Encrypt 或证书提供商获取 `.pfx` 文件

### 6.2 导入证书到 IIS
1. IIS Manager → 服务器节点 → 服务器证书 → 导入
2. 选择 `.pfx` 文件，设置密码

### 6.3 绑定 HTTPS
- 网站 → 绑定 → 添加
- 类型：`https`，端口：`443`
- SSL 证书：选择刚导入的证书

### 6.4 强制 HTTPS（可选）
在 `Program.cs` 添加：
```csharp
app.UseHttpsRedirection();
```

---

## 第 7 步：配置防火墙

```powershell
# 开放 80 和 443
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 第 8 步：配置 Shopee Webhook（当你有密钥后）

编辑 `appsettings.json` 填入真实值：
```json
"Shopee": {
  "AppKey": "your_app_key",
  "AppSecret": "your_app_secret",
  "AccessToken": "your_access_token",
  "ShopId": "your_shop_id"
}
```

Shopee 控制台设置：
- Webhook URL: `https://your-domain.com/api/webhook/shopee`
- 订阅事件：`webchat_push`
- 测试：调用 `/api/webhook/shopee/test` 验证

---

## 🔄 常见问题

**Q: 502.5 错误？**
A: 检查 .NET Runtime 是否安装，应用程序池是否为 `No Managed Code`，权限是否正确。

**Q: 数据库连接失败？**
A: 确保 MySQL 服务运行，防火墙开放 3306，连接字符串正确。

**Q: 日志在哪里看？**
A: IIS 站点日志在 `C:\inetpub\logs\LogFiles`，应用日志可在 `Program.cs` 配置写入文件。

**Q: 如何更新？**
A: 停止网站 → 替换 `publish` 目录文件 → 重启网站。

---

## 📞 支持

如遇到问题，检查：
- Event Viewer (Windows 日志)
- IIS 错误页面详细信息
- MySQL 连接测试：`mysql -u nexusai -p -h localhost`

祝部署顺利！🚀
