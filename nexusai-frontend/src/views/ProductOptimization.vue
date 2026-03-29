<template>
  <div class="product-optimization-page">
    <div class="header-section">
      <h2>🚀 商品智能优化</h2>
      <p class="subtitle">AI一键优化商品信息，提升搜索排名与转化率</p>
    </div>

    <a-card title="📋 原始商品信息" :bordered="false" class="form-card">
      <a-form :model="form" layout="vertical" @finish="onSubmit">
        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="商品标题" name="title" :rules="[{ required: true, message: '请输入商品标题' }]">
              <a-input
                v-model:value="form.title"
                placeholder="例如：新款无线蓝牙耳机 降噪运动耳机 适用iPhone安卓通用"
                size="large"
                show-count
                :maxlength="200"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="商品详细描述" name="description" :rules="[{ required: true, message: '请输入商品描述' }]">
              <a-textarea
                v-model:value="form.description"
                :rows="6"
                placeholder="详细描述商品特性、规格参数、材质、适用场景、使用方法等，越详细优化效果越好"
                size="large"
                show-count
                :maxlength="2000"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item label="关键词/标签（可选，每行一个）" name="keywords">
              <a-textarea
                v-model:value="form.keywords"
                :rows="4"
                placeholder="例如：&#10;降噪耳机&#10;运动耳机&#10;长续航&#10;蓝牙5.3&#10;适用跑步"
                size="large"
              />
              <div class="form-hint">提供关键词有助于优化搜索匹配和SEO</div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="24">
            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="loading" size="large" :icon="h(ToolOutlined)">
                ✨ 开始智能优化
              </a-button>
              <a-button style="margin-left: 12px" @click="resetForm" :disabled="loading">重置</a-button>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-divider v-if="result" />

    <div v-if="loading" class="loading-section">
      <a-spin size="large" />
      <p>AI正在分析商品并生成优化方案...</p>
      <p class="hint">通常需要10-30秒，请耐心等待</p>
    </div>

    <div v-else-if="result" class="results-section">
      <div class="results-header">
        <h3>✅ 优化完成</h3>
        <a-space>
          <a-button type="primary" size="small" @click="applyAll">一键复制</a-button>
          <a-button size="small" @click="result = null">关闭</a-button>
        </a-space>
      </div>

      <a-descriptions title="📊 优化建议" :bordered="true" :column="{ xxl: 1, xl: 1, lg: 1, md: 1, sm: 1, xs: 1 }">
        <a-descriptions-item label="优化标题">
          <div class="text-block">{{ result.optimizedTitle || '-' }}</div>
        </a-descriptions-item>

        <a-descriptions-item label="优化描述">
          <div class="text-block pre-wrap">{{ result.optimizedDescription || '-' }}</div>
        </a-descriptions-item>

        <a-descriptions-item label="营销方案">
          <div class="text-block pre-wrap">{{ result.marketingPlan || '-' }}</div>
        </a-descriptions-item>

        <a-descriptions-item label="图片生成提示词">
          <div class="text-block pre-wrap highlight">{{ result.imagePrompt || '-' }}</div>
        </a-descriptions-item>
      </a-descriptions>

      <a-card title="💡 优化要点" size="small" class="tips-card" :bordered="false">
        <a-list :data="[
          { text: '标题已加入高搜索量关键词，提升曝光', icon: '🔍' },
          { text: '描述结构优化，突出卖点与用户痛点', icon: '📝' },
          { text: '营销方案针对不同渠道定制', icon: '📢' },
          { text: '图片Prompt支持AI生成高质量主图', icon: '🎨' }
        ]">
          <template #renderItem="{ item }">
            <a-list-item>
              <span>{{ item.icon }}</span>
              <span style="margin-left: 8px">{{ item.text }}</span>
            </a-list-item>
          </template>
        </a-list>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, h } from 'vue'
import { message } from 'ant-design-vue'
import { ToolOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'

const form = reactive({
  title: '',
  description: '',
  keywords: ''
})

const loading = ref(false)
const result = ref(null)

const resetForm = () => {
  form.title = ''
  form.description = ''
  form.keywords = ''
  result.value = null
}

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
    message.success('商品优化完成！')
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

const applyAll = () => {
  if (!result.value) return
  const text = `优化标题：\n${result.value.optimizedTitle || ''}\n\n` +
               `优化描述：\n${result.value.optimizedDescription || ''}\n\n` +
               `营销方案：\n${result.value.marketingPlan || ''}\n\n` +
               `图片提示词：\n${result.value.imagePrompt || ''}`
  navigator.clipboard.writeText(text).then(() => {
    message.success('所有优化结果已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败，请手动复制')
  })
}
</script>

<style scoped>
.product-optimization-page {
  max-width: 1000px;
  margin: 0 auto;
}

.header-section {
  text-align: center;
  margin-bottom: 24px;
}

.header-section h2 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #722ed1;
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

.loading-section .hint {
  font-size: 13px;
  color: #bbb;
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
  color: #52c41a;
}

.tips-card {
  margin-top: 16px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.text-block {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 6px;
  max-height: 300px;
  overflow-y: auto;
  border-left: 3px solid #722ed1;
}

.text-block.pre-wrap {
  white-space: pre-wrap;
  line-height: 1.6;
}

.text-block.highlight {
  background: #fff7e6;
  border-left-color: #fa8c16;
}
</style>
