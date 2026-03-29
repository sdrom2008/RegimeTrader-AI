#!/bin/bash
# OpenClaw 极速交付脚本 (国内加速版)
# 专为 199 元代装服务设计

echo "=== OpenClaw Professional Deployment Started ==="

# 1. 自动切换国内镜像源 (针对 Ubuntu)
echo "Optimizing package sources..."
sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sudo apt-get update -y

# 2. 安装 Node.js 20+
echo "Installing Node.js Environment..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. 安装 Python 依赖
echo "Configuring Python 3.12..."
sudo apt-get install -y python3-pip python3-venv

# 4. 全局安装 OpenClaw
echo "Deploying OpenClaw Core..."
sudo npm install -g openclaw --registry=https://registry.npmmirror.com

# 5. 初始化配置 (安全加固)
echo "Initializing Gateway..."
openclaw configure --non-interactive

echo "=== DEPLOYMENT SUCCESSFUL ==="
echo "Access local Dashboard at http://localhost:60000"
