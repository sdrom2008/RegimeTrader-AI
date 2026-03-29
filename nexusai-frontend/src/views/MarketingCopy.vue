<template>
  <div class="marketing-copy-page">
    <div class="header-section">
      <h2>🎯 营销文案生成</h2>
      <p class="subtitle">基于AI自动生成多套产品营销文案，提升转化率</p>
    </div>

    <a-card title="📝 填写产品信息" class="form-card" :bordered="false">
      <a-form :model="form" layout="vertical" @finish="onSubmit">
        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="产品名称" name="productName" :rules="[{ required: true, message: '请输入产品名称' }]">
              <a-input v-model:value="form.productName" placeholder="例如：智能蓝牙耳机 Pro Max" size="large" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="产品描述" name="productDescription" :rules="[{ required: true, message: '请输入产品描述' }]">
              <a-textarea
                v-model:value="form.productDescription"
                :rows="4"
                placeholder="详细描述产品特点、功能、适用场景、目标用户等"
                size="large"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="核心卖点（可选，每行一个）" name="sellingPoints">
              <a-textarea
                v-model:value="form.sellingPoints"
                :rows="3"
                placeholder="例如：&#10;主动降噪，静享音乐&#10;30小时超长续航&#10;人体工学设计，舒适佩戴一整天"
                size="large"
              />
              <div class="form-hint">建议提供3-5个核心卖点，生成效果更佳</div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="loading" size="large" :icon="h(ThunderboltOutlined)">
                开始生成文案
              </a-button>
              <a-button style="margin-left: 12px" @click="resetForm">重置</a-button>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-divider v-if="results.length || loading" />

    <div v-if="loading" class="loading-section">
      <a-spin size="large" />
      <p>AI正在为你创作文案，请稍候...</p>
    </div>

    <div v-else-if="results.length" class="results-section">
      <div class="results-header">
        <h3>✨ 生成结果（共 {{ results.length }} 条文案）</h3>
        <a-space>
          <a-button type="primary" size="small" @click="copyAll">复制全部</a-button>
          <a-button size="small" @click="results = []">清空</a-button>
        </a-space>
      </div>

      <a-list :data-source="results" bordered class="results-list">
        <template #renderItem="{ item, index }">
          <a-list-item class="result-item">
            <a-list-item-meta>
              <template #title>
                <a-space>
                  <span class="result-tag">方案 {{ index + 1 }}</span>
                  <a-rate :value="4" disabled allow-half style="font-size: 12px" />
                </a-space>
              </template>
              <template #description>
                <div class="copy-text">{{ item }}</div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button type="link" size="small" @click="copyText(item)">📋 复制</a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { message } from 'ant-design-vue'
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'

const form = reactive({
  productName: '',
  productDescription: '',
  sellingPoints: ''
})

const loading = ref(false)
const results = ref([])

const resetForm = () => {
  form.productName = ''
  form.productDescription = ''
  form.sellingPoints = ''
  results.value = []
}

const onSubmit = async () => {
  loading.value = true
  try {
    const points = form.sellingPoints.split('\n').filter(p => p.trim())
    const data = await request.post('/api/marketing/generate-copy', {
      productName: form.productName,
      productDescription: form.productDescription,
      sellingPoints: points
    })
    results.value = data.copy || []
    if (results.value.length === 0) {
      message.warning('未生成文案，请检查输入或联系管理员')
    } else {
      message.success(`生成成功，共 ${results.value.length} 条文案`)
    }
  } catch (e) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

const copyText = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败，请手动复制')
  })
}

const copyAll = () => {
  const allText = results.value.map((item, idx) => `方案${idx + 1}：\n${item}`).join('\n\n')
  navigator.clipboard.writeText(allText).then(() => {
    message.success('已复制全部文案到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}
</script>

<style scoped>
.marketing-copy-page {
  max-width: 900px;
  margin: 0 auto;
}

.header-section {
  text-align: center;
  margin-bottom: 24px;
}

.header-section h2 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #1890ff;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.form-card {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.form-hint {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}

.loading-section {
  text-align: center;
  padding: 60px 0;
  color: #666;
}

.loading-section p {
  margin-top: 16px;
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
  font-size: 18px;
  color: #333;
}

.results-list {
  border-radius: 8px;
}

.result-item {
  padding: 16px !important;
}

.result-tag {
  background: #e6f7ff;
  color: #1890ff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.copy-text {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #333;
  background: #f9f9f9;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #1890ff;
}
</style>
