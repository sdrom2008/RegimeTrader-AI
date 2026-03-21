<template>
  <div>
    <h2>营销文案生成</h2>
    <a-form :model="form" layout="vertical" @finish="onSubmit">
      <a-form-item label="产品名称" name="productName" :rules="[{ required: true, message: '请输入产品名称' }]">
        <a-input v-model:value="form.productName" placeholder="例如：智能蓝牙耳机" />
      </a-form-item>
      <a-form-item label="产品描述" name="productDescription" :rules="[{ required: true, message: '请输入产品描述' }]">
        <a-textarea v-model:value="form.productDescription" :rows="4" placeholder="简要描述产品特点、适用场景等" />
      </a-form-item>
      <a-form-item label="卖点（可选，每行一个）" name="sellingPoints">
        <a-textarea v-model:value="form.sellingPoints" :rows="3" placeholder="例如：降噪&#10;长续航&#10;舒适佩戴" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" html-type="submit" :loading="loading">
          生成文案
        </a-button>
      </a-form-item>
    </a-form>

    <a-divider />

    <div v-if="results.length">
      <h3>生成结果</h3>
      <a-list :data-source="results" bordered>
        <template #renderItem="{ item, index }">
          <a-list-item>
            <a-list-item-meta :description="item">
              <template #title>
                <span>方案 {{ index + 1 }}</span>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button type="link" size="small" @click="copyText(item)">复制</a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'

const form = reactive({
  productName: '',
  productDescription: '',
  sellingPoints: ''
})

const loading = ref(false)
const results = ref([])

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
    message.success(`生成成功，共 ${results.value.length} 条文案`)
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
    message.error('复制失败')
  })
}
</script>
