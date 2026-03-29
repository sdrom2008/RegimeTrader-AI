<template>
  <div class="competitor-analysis-page">
    <div class="header-section">
      <h2>🔍 竞品智能分析</h2>
      <p class="subtitle">批量分析竞品链接，自动生成竞争力评估与优化建议</p>
    </div>

    <a-card title="📥 输入竞品链接" :bordered="false" class="form-card">
      <a-form :model="form" layout="vertical" @finish="onSubmit">
        <a-form-item label="竞品商品链接（每行一个，支持多链接批量分析）" name="urls" :rules="[{ required: true, message: '请输入至少一个链接' }]">
          <a-textarea
            v-model:value="form.urls"
            :rows="6"
            placeholder="https://example.com/product1&#10;https://example.com/product2&#10;https://example.com/product3"
            size="large"
          />
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="loading" size="large" :icon="h(SearchOutlined)">
              🚀 开始分析
            </a-button>
            <a-button size="large" @click="clearForm">清空</a-button>
            <a-tag color="orange" v-if="loading">分析中...（每个链接约5-10秒）</a-tag>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>

    <a-divider v-if="result || loading" />

    <div v-if="loading" class="loading-section">
      <a-steps :current="0" size="small">
        <a-step title="连接平台" description="获取商品数据" />
        <a-step title="分析要素" description="价格、主图、标题、详情" />
        <a-step title="生成报告" description="竞争力评估" />
      </a-steps>
      <a-spin size="large" style="margin-top: 24px;" />
      <p>正在深度分析竞品，预计 {{ estimatedTime }} 秒...</p>
    </div>

    <div v-else-if="result" class="results-section">
      <div class="results-header">
        <h3>📈 分析报告</h3>
        <a-space>
          <a-button type="primary" size="small" @click="exportReport">导出报告</a-button>
          <a-button size="small" @click="result = null">关闭</a-button>
        </a-space>
      </div>

      <a-card title="📋 分析摘要" class="summary-card" :bordered="false">
        <div style="white-space: pre-wrap;">{{ result.summary }}</div>
      </a-card>

      <a-card title="📊 竞品对比表" class="table-card" :bordered="false" style="margin-top: 16px;">
        <a-table
          v-if="result.details && result.details.length"
          :columns="columns"
          :data-source="result.details"
          :pagination="{ pageSize: 10, showSizeChanger: true, showTotal: total => `共 ${total} 个竞品` }"
          bordered
          size="middle"
          :scroll="{ x: 1000 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'score'">
              <div class="score-cell">
                <a-rate :value="record.score / 20" disabled allow-half style="font-size: 14px;" />
                <span class="score-value">{{ record.score }}</span>
              </div>
            </template>
            <template v-else-if="column.key === 'url'">
              <a :href="record.url" target="_blank" class="url-link">{{ formatUrl(record.url) }}</a>
            </template>
            <template v-else>
              {{ record[column.key] || '-' }}
            </template>
          </template>
        </a-table>
      </a-card>

      <a-card title="💡 优化建议" class="suggestions-card" :bordered="false" style="margin-top: 16px;">
        <a-list :data="generateSuggestions()">
          <template #renderItem="{ item }">
            <a-list-item>
              <template #prefix>
                <span class="suggestion-icon">{{ item.icon }}</span>
              </template>
              <div class="suggestion-content">
                <div class="suggestion-title">{{ item.title }}</div>
                <div class="suggestion-desc">{{ item.description }}</div>
              </div>
            </a-list-item>
          </template>
        </a-list>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'

const form = reactive({
  urls: ''
})

const loading = ref(false)
const result = ref(null)

const estimatedTime = computed(() => {
  const count = form.urls.split('\n').filter(u => u.trim()).length
  return count * 8
})

const columns = [
  { title: '竞品链接', key: 'url', width: 250, fixed: 'left' },
  { title: '竞争力评分', key: 'score', width: 180 },
  { title: '价格区间', key: 'priceRange', width: 120 },
  { title: '主图风格', key: 'imageStyle', width: 120 },
  { title: '核心优势', key: 'strengths' },
  { title: '改进点', key: 'weaknesses', width: 200, fixed: 'right' }
]

const formatUrl = (url) => {
  try {
    const urlObj = new URL(url)
    return `${urlObj.hostname}...${urlObj.pathname.slice(-20)}`
  } catch {
    return url.slice(0, 50) + (url.length > 50 ? '...' : '')
  }
}

const clearForm = () => {
  form.urls = ''
  result.value = null
}

const onSubmit = async () => {
  loading.value = true
  try {
    const urls = form.urls.split('\n').filter(u => u.trim())
    const data = await request.post('/api/competitor/analyze', { urls })
    result.value = data
    message.success(`分析完成，共分析 ${urls.length} 个竞品`)
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

const generateSuggestions = () => {
  if (!result.value || !result.value.details) return []

  const suggestions = []
  const avgScore = result.value.details.reduce((sum, d) => sum + (d.score || 0), 0) / result.value.details.length

  if (avgScore < 60) {
    suggestions.push({
      icon: '⚠️',
      title: '竞争力较弱',
      description: `您的商品综合评分仅 ${avgScore.toFixed(1)} 分，建议从标题优化、主图设计、价格策略等方面重点改进。`
    })
  } else if (avgScore >= 80) {
    suggestions.push({
      icon: '🎉',
      title: '表现优秀',
      description: `您的商品竞争力达 ${avgScore.toFixed(1)} 分，请保持优势并持续监控竞品动态。`
    })
  }

  const weakPoints = result.value.details.flatMap(d => d.weaknesses || [])
  if (weakPoints.length > 0) {
    const topWeakness = weakPoints[0]
    suggestions.push({
      icon: '🔧',
      title: '首要改进点',
      description: `多数竞品短板：${topWeakness}，建议优先优化。`
    })
  }

  suggestions.push({
    icon: '📊',
    title: '持续监控',
    description: '建议每周进行一次竞品分析，及时调整策略。'
  })

  return suggestions
}

const exportReport = () => {
  if (!result.value) return

  const text = `【NexusAI 竞品分析报告】\n生成时间：${new Date().toLocaleString()}\n\n分析摘要：\n${result.value.summary}\n\n竞品详情：\n` +
    result.value.details.map(d => `链接：${d.url}\n评分：${d.score}\n价格：${d.priceRange}\n主图风格：${d.imageStyle}\n优势：${d.strengths}\n短板：${d.weaknesses}\n`).join('\n---\n')

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `竞品分析报告_${new Date().toISOString().slice(0,10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
  message.success('报告已导出')
}
</script>

<style scoped>
.competitor-analysis-page {
  max-width: 1200px;
  margin: 0 auto;
}

.header-section {
  text-align: center;
  margin-bottom: 24px;
}

.header-section h2 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #fa8c16;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.form-card {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.loading-section {
  text-align: center;
  padding: 40px 0;
}

.loading-section p {
  margin-top: 24px;
  color: #666;
}

.results-section {
  margin-top: 24px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.results-header h3 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.summary-card {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 16px;
}

.table-card {
  border-radius: 8px;
}

.score-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-value {
  font-weight: bold;
  color: #fa8c16;
}

.url-link {
  color: #1890ff;
  text-decoration: none;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

.url-link:hover {
  text-decoration: underline;
}

.suggestions-card {
  border-radius: 8px;
  background: #fafafa;
}

.suggestion-icon {
  font-size: 20px;
  margin-right: 8px;
}

.suggestion-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.suggestion-desc {
  color: #666;
  font-size: 13px;
}
</style>
