<template>
  <div>
    <h2>竞品分析</h2>
    <a-form :model="form" layout="vertical" @finish="onSubmit">
      <a-form-item label="竞品链接（每行一个）" name="urls" :rules="[{ required: true, message: '请输入至少一个链接' }]">
        <a-textarea v-model:value="form.urls" :rows="5" placeholder="https://example.com/product1&#10;https://example.com/product2" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" html-type="submit" :loading="loading">分析</a-button>
      </a-form-item>
    </a-form>

    <a-divider />

    <div v-if="result" class="result">
      <a-card title="分析摘要" :bordered="false" style="margin-bottom: 16px;">
        <p style="white-space: pre-wrap;">{{ result.summary }}</p>
      </a-card>

      <a-table
        v-if="result.details && result.details.length"
        :columns="columns"
        :data-source="result.details"
        :pagination="{ pageSize: 5 }"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'score'">
            <a-rate :value="record.score / 20" disabled allow-half style="font-size: 14px;" />
            <span style="margin-left: 8px;">{{ record.score }}</span>
          </template>
          <template v-else>
            {{ record[column.key] }}
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'

const form = reactive({
  urls: ''
})

const loading = ref(false)
const result = ref(null)

const columns = [
  { title: '链接', key: 'url', width: 300 },
  { title: '竞争力评分', key: 'score', width: 150 },
  { title: '价格区间', key: 'priceRange' },
  { title: '主图风格', key: 'imageStyle' },
  { title: '核心优势', key: 'strengths' },
  { title: '改进点', key: 'weaknesses' }
]

const onSubmit = async () => {
  loading.value = true
  try {
    const urls = form.urls.split('\n').filter(u => u.trim())
    const data = await request.post('/api/competitor/analyze', { urls })
    result.value = data
    message.success('分析完成')
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}
</script>
