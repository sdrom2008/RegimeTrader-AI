# OpenClaw 全平台极速交付手册 (2026.3 修正版)

## 一、 Windows 11/10 (终极稳定版方案)

**第一步：环境降级 (解决 v24 不兼容问题)**
1. 在“添加或删除程序”中卸载现有的 Node.js。
2. 下载并安装稳定版：[华为云 Node v20 高速下载](https://mirrors.huaweicloud.com/nodejs/v20.11.1/node-v20.11.1-x64.msi)
3. 安装完毕后，**重启**终端窗口。

**第二步：解锁权限与纯净安装**
打开 **PowerShell (管理员)**，粘贴以下命令：
```powershell
# 解锁脚本权限
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force;
# 切换阿里镜像
npm config set registry https://registry.npmmirror.com;
# 只装核心(跳过报错插件)
npm install -g openclaw --no-optional --omit=optional;
# 验证
openclaw status
```

---

## 二、 Linux (Ubuntu / Debian)

**第一步：基础环境**
```bash
sudo apt update && sudo apt install -y curl
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**第二步：极速安装**
```bash
sudo npm install -g openclaw --registry=https://registry.npmmirror.com --no-optional
```

---

## 三、 macOS (Mac mini / MacBook)

**第一步：安装 Node.js**
前往下载：[Node.js v20 PKG](https://npmmirror.com/mirrors/node/v20.11.1/node-v20.11.1.pkg)

**第二步：安装核心**
```zsh
sudo npm install -g openclaw --registry=https://registry.npmmirror.com --no-optional
```
