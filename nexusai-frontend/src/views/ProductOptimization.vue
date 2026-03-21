<template>
  <div>
    <h2>商品优化</h2>
    <a-form :model="form" layout="vertical" @finish="onSubmit">
      <a-form-item label="商品标题" name="title" :rules="[{ required: true, message: '请输入商品标题' }]">
        <a-input v-model:value="form.title" placeholder="例如：新款无线蓝牙耳机" />
      </a-form-item>
      <a-form-item label="商品描述" name="description" :rules="[{ required: true, message: '请输入商品描述' }]">
        <a-textarea v-model:value="form.description" :rows="5" placeholder="详细描述商品特性、规格、适用场景" />
      </a-form-item>
      <a-form-item label="关键词（可选，每行一个）" name="keywords">
        <a-textarea v-model:value="form.keywords" :rows="3" placeholder="例如：降噪&#10;长续航&#10;运动耳机" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" html-type="submit" :loading="loading">开始优化</a-button>
      </a-form-item>
    </a-form>

    <a-divider />

    <div v-if="result" class="result">
      <a-descriptions bordered title="优化建议">
        <a-descriptions-item label="优化标题">
          {{ result.optimizedTitle || '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="优化描述">
          <div style="white-space: pre-wrap;">{{ result.optimizedDescription || '-' }}</div>
        </a-descriptions-item>
        <a-descriptions-item label="营销方案">
          <div style="white-space: pre-wrap;">{{ result.marketingPlan || '-' }}</div>
        </a-descriptions-item>
        <a-descriptions-item label="图片生成提示词">
          <div style="white-space: pre-wrap;">{{ result.imagePrompt || '-' }}</div>
        </a-descriptions-item>
      </a-descriptions>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'

const form = reactive({
  title: '',
  description: '',
  keywords: ''
})

const loading = ref(false)
const result = ref(null)

const onSubmit = async () => {
  loading.value = true
  try {
    const keywords = form.keywords.split('\n').filter(k => k.trim())
    const data = await request.post('/api/agent/optimizeproduct', {
      title: form.title,
      description: form.description,
      keywords: keywords
    })
    result.value = data
    message.success('优化完成')
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}
</script>
