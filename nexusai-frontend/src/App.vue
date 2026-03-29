<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="header">
      <div class="logo-container">
        <div class="logo-icon">🚀</div>
        <div class="logo-text">
          <div class="logo-main">NexusAI</div>
          <div class="logo-sub">Tech</div>
        </div>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="horizontal"
        :style="{ lineHeight: '64px', flex: 1, minWidth: 0 }"
      >
        <a-menu-item key="marketing">
          <router-link to="/marketing">营销文案</router-link>
        </a-menu-item>
        <a-menu-item key="chat">
          <router-link to="/chat">客服对话</router-link>
        </a-menu-item>
        <a-menu-item key="product">
          <router-link to="/product">商品优化</router-link>
        </a-menu-item>
        <a-menu-item key="competitor">
          <router-link to="/competitor">竞品分析</router-link>
        </a-menu-item>
      </a-menu>
      <div class="header-actions">
        <a-badge :count="systemStatus" :offset="[10, 0]">
          <a-button type="text" class="status-btn" @click="checkStatus">
            <template #icon><CheckCircleOutlined /></template>
          </a-button>
        </a-badge>
      </div>
    </a-layout-header>

    <a-layout-content class="content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </a-layout-content>

    <a-layout-footer class="footer">
      <div class="footer-content">
        <span>NexusAI Tech ©2026 | 智能营销 SaaS 平台</span>
        <span class="version">v1.0.0</span>
      </div>
    </a-layout-footer>

    <!-- 全局加载遮罩 -->
    <a-spin v-if="globalLoading" size="large" class="global-spin" />
  </a-layout>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { CheckCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const route = useRoute()
const selectedKeys = ref(['marketing'])
const globalLoading = ref(false)
const systemStatus = ref(0)

watch(() => route.path, (path) => {
  if (path.startsWith('/marketing')) selectedKeys.value = ['marketing']
  else if (path.startsWith('/chat')) selectedKeys.value = ['chat']
  else if (path.startsWith('/product')) selectedKeys.value = ['product']
  else if (path.startsWith('/competitor')) selectedKeys.value = ['competitor']
})

const checkStatus = async () => {
  globalLoading.value = true
  try {
    // 检查后端健康状态
    const response = await fetch('http://192.168.1.254:7092/api/weatherforecast', {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    })
    if (response.ok) {
      systemStatus.value = 1
      message.success('后端服务运行正常')
    } else {
      systemStatus.value = 2
      message.error('后端服务异常')
    }
  } catch (e) {
    systemStatus.value = 2
    message.error('无法连接到后端服务')
  } finally {
    globalLoading.value = false
  }
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #001529 0%, #003a70 100%) !important;
  padding: 0 24px;
  position: relative;
  z-index: 10;
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 40px;
  user-select: none;
}

.logo-icon {
  font-size: 28px;
  margin-right: 12px;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-main {
  color: white;
  font-size: 20px;
  font-weight: bold;
  letter-spacing: 1px;
}

.logo-sub {
  color: #1890ff;
  font-size: 12px;
  font-weight: 600;
}

.header-actions {
  margin-left: auto;
}

.status-btn {
  color: rgba(255, 255, 255, 0.85);
  font-size: 18px;
}

.content {
  margin: 24px;
  padding: 0;
  background: transparent;
  border-radius: 8px;
  min-height: calc(100vh - 140px);
}

.footer {
  background: #f0f2f5;
  padding: 16px 24px;
  border-top: 1px solid #e8e8e8;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  color: #666;
  font-size: 13px;
}

.version {
  color: #999;
  font-size: 12px;
}

.global-spin {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
