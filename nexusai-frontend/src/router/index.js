import { createRouter, createWebHistory } from 'vue-router'
import Marketing from '@/views/MarketingCopy.vue'
import Chat from '@/views/Chat.vue'
import Product from '@/views/ProductOptimization.vue'
import Competitor from '@/views/CompetitorAnalysis.vue'

const routes = [
  { path: '/', redirect: '/marketing' },
  { path: '/marketing', component: Marketing },
  { path: '/chat', component: Chat },
  { path: '/product', component: Product },
  { path: '/competitor', component: Competitor }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
