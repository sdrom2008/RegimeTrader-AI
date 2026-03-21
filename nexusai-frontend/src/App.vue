<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="header">
      <div class="logo">NexusAI</div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="horizontal"
        :style="{ lineHeight: '64px' }"
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
    </a-layout-header>
    <a-layout-content class="content">
      <router-view />
    </a-layout-content>
    <a-layout-footer class="footer">
      NexusAI Tech ©2026
    </a-layout-footer>
  </a-layout>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const selectedKeys = ref(['marketing'])

watch(() => route.path, (path) => {
  if (path.startsWith('/marketing')) selectedKeys.value = ['marketing']
  else if (path.startsWith('/chat')) selectedKeys.value = ['chat']
  else if (path.startsWith('/product')) selectedKeys.value = ['product']
  else if (path.startsWith('/competitor')) selectedKeys.value = ['competitor']
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  background: #001529;
}
.logo {
  color: white;
  font-size: 20px;
  font-weight: bold;
  margin-right: 40px;
}
.content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
}
.footer {
  text-align: center;
  color: #666;
}
</style>
