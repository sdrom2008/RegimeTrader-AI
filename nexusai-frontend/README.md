# NexusAI Frontend

基于 Vue 3 + Ant Design Vue + Vite 的 AI 营销 SaaS 平台前端

## 🚀 快速开始

### 环境要求
- Node.js 16+
- npm 或 yarn

### 安装依赖
```bash
cd nexusai-frontend
npm install
```

### 开发环境
```bash
npm run dev
```
访问: http://localhost:5173

### 生产构建
```bash
npm run build
```
构建输出: `dist/` 目录

## ⚙️ 配置

### API 地址配置
前端默认代理到后端 `http://192.168.1.254:7092/api`

如需修改，编辑以下文件：
- `src/utils/request.js` - axios 实例的 baseURL
- `vite.config.js` - 开发服务器代理配置

### 环境变量（可选）
在项目根目录创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://192.168.1.254:7092/api
```
然后在 `request.js` 中使用 `import.meta.env.VITE_API_BASE_URL`

## 📱 功能模块

1. **营销文案生成** (`/marketing`)
   - 输入产品信息自动生成多条营销文案
   - 支持自定义卖点
   - 一键复制全部结果

2. **AI 智能客服** (`/chat`)
   - 基于意图识别的自动回复
   - 实时对话展示
   - 支持多客户端会话管理

3. **商品优化** (`/product`)
   - AI 优化标题、描述
   - 生成营销方案
   - 提供图片生成提示词（支持 Midjourney/DALL-E）

4. **竞品分析** (`/competitor`)
   - 批量分析竞品链接
   - 自动生成竞争力评分
   - 导出完整分析报告

## 🛠️ 技术栈

- **框架**: Vue 3.4+
- **构建**: Vite 5.0+
- **UI 组件**: Ant Design Vue 4.x
- **HTTP 客户端**: Axios
- **路由**: Vue Router 4
- **状态管理**: Pinia (已安装，待用)

## 📂 项目结构

```
nexusai-frontend/
├── src/
│   ├── views/           # 页面组件
│   │   ├── MarketingCopy.vue
│   │   ├── Chat.vue
│   │   ├── ProductOptimization.vue
│   │   └── CompetitorAnalysis.vue
│   ├── utils/
│   │   └── request.js   # axios 封装
│   ├── router/
│   │   └── index.js     # 路由配置
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

## 🔧 开发说明

### 后端联调
1. 确保后端 API 已启动并监听 7092 端口
2. 启动前端开发服务器
3. 如果遇到 CORS 错误，检查后端是否正确配置了 CORS 或使用 Vite 代理

### 调试
- 使用浏览器开发者工具
- 日志查看: `console.log`
- 网络请求: Network 面板

## 📦 部署

### 静态部署
构建后可直接部署到任何静态服务器（Nginx、CDN 等）：
```bash
npm run build
# 将 dist/ 目录上传到服务器
```

### Docker (示例)
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## 📝 待办事项

- [ ] 添加 API 请求重试机制
- [ ] 实现 WebSocket 实时对话（客服模块）
- [ ] 添加国际化支持（中英文）
- [ ] 完善错误处理和用户提示
- [ ] 添加表单验证增强
- [ ] 单元测试覆盖
- [ ] 性能监控集成

## 🤝 贡献

欢迎提出 Issue 和 Pull Request！

## 📄 License

MIT
