#!/bin/bash

# NexusAI Tech - 快速启动脚本（演示版）
# 用途：启动后端 API 服务，供前端和测试使用

cd /home/sdrom2008/.openclaw/workspace/my-project/Synerixis.Api

echo "🔧 清理并重建项目..."
dotnet clean Synerixis.Api.csproj --configuration Release
dotnet build Synerixis.Api.csproj --configuration Release

if [ $? -ne 0 ]; then
    echo "❌ 构建失败，请检查错误"
    exit 1
fi

echo "✅ 构建成功！"
echo "🚀 启动 API 服务（端口 7092）..."
echo "📝 日志将输出到控制台"
echo "🌐 API 地址: http://localhost:7092"
echo "🛑 按 Ctrl+C 停止服务"
echo "----------------------------------------"

# 启动服务（使用 Release 配置，SQLite 开发数据库）
dotnet run --configuration Release
