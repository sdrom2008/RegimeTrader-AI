<template>
  <div>
    <h2>客服对话</h2>
    <a-form layout="inline" style="margin-bottom: 16px;">
      <a-form-item label="客户ID">
        <a-input v-model:value="customerId" placeholder="例如：user_001" />
      </a-form-item>
    </a-form>

    <div class="chat-container">
      <div class="messages" ref="msgContainer">
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="bubble">{{ msg.content }}</div>
          <div v-if="msg.intent" class="intent">意图: {{ msg.intent }} ({{ (msg.confidence*100).toFixed(1) }}%)</div>
        </div>
        <div v-if="loading" class="message assistant">
          <div class="bubble thinking">...</div>
        </div>
      </div>

      <a-input-group compact style="margin-top: 12px;">
        <a-input
          v-model:value="inputMessage"
          placeholder="输入消息..."
          @keyup.enter="sendMessage"
          style="width: calc(100% - 80px)"
        />
        <a-button type="primary" @click="sendMessage" :loading="loading">发送</a-button>
      </a-input-group>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'

const customerId = ref('user_001')
const inputMessage = ref('')
const messages = ref([])
const loading = ref(false)
const msgContainer = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

watch(messages, scrollToBottom, { deep: true })

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  const userMsg = { role: 'user', content: inputMessage.value }
  messages.value.push(userMsg)
  const query = inputMessage.value
  inputMessage.value = ''
  loading.value = true

  try {
    const data = await request.post('/api/chat/send', {
      customerId: customerId.value,
      message: query
    })
    messages.value.push({
      role: 'assistant',
      content: data.reply,
      intent: data.intent,
      confidence: data.confidence
    })
  } catch (e) {
    // 错误处理
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-container {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}
.messages {
  height: 400px;
  overflow-y: auto;
}
.message {
  margin-bottom: 12px;
  max-width: 70%;
}
.message.user {
  margin-left: auto;
}
.message.assistant {
  margin-right: auto;
}
.bubble {
  padding: 8px 12px;
  border-radius: 12px;
  display: inline-block;
  word-break: break-word;
}
.message.user .bubble {
  background: #1890ff;
  color: white;
  border-bottom-right-radius: 2px;
}
.message.assistant .bubble {
  background: #fff;
  border: 1px solid #d9d9d9;
  border-bottom-left-radius: 2px;
}
.intent {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
}
.thinking::after {
  content: '...';
  animation: ellipsis 1.5s infinite;
}
@keyframes ellipsis {
  0% { content: ''; }
  25% { content: '.'; }
  50% { content: '..'; }
  75% { content: '...'; }
  100% { content: ''; }
}
</style>
