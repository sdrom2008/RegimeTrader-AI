<template>
  <div class="chat-page">
    <div class="header-section">
      <h2>💬 AI 智能客服</h2>
      <p class="subtitle">自动回复客户咨询，意图识别准确率高达98%</p>
    </div>

    <a-card title="会话控制" :bordered="false" class="control-card">
      <a-space align="center">
        <span>客户ID：</span>
        <a-input
          v-model:value="customerId"
          placeholder="请输入客户ID"
          style="width: 200px"
          size="small"
        />
        <a-button type="primary" size="small" @click="startNewChat">🆕 新建会话</a-button>
        <a-button size="small" @click="clearChat">🗑️ 清空对话</a-button>
        <a-tag color="blue" v-if="connected">已连接</a-tag>
        <a-tag color="default" v-else>未连接</a-tag>
      </a-space>
    </a-card>

    <div class="chat-container">
      <div class="messages" ref="msgContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">💭</div>
          <p>开始输入消息，与AI客服对话吧！</p>
          <p class="hint">支持：商品咨询、下单、物流查询、售后问题</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="avatar">
            <template v-if="msg.role === 'user'">👤</template>
            <template v-else>🤖</template>
          </div>
          <div class="content-wrapper">
            <div class="bubble">{{ msg.content }}</div>
            <div v-if="msg.intent" class="intent-tag">
              意图: {{ msg.intent }}
              <a-rate :value="msg.confidence" disabled allow-half :count="5" style="font-size: 10px; margin-left: 4px;" />
            </div>
            <div class="time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="avatar">🤖</div>
          <div class="content-wrapper">
            <div class="bubble thinking">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-input
          v-model:value="inputMessage"
          placeholder="输入消息... (Enter 发送)"
          @keyup.enter="sendMessage"
          :disabled="loading"
          size="large"
        >
          <template #prefix>
            <span v-if="customerId" class="customer-badge">{{ customerId }}</span>
          </template>
        </a-input>
        <a-button
          type="primary"
          @click="sendMessage"
          :loading="loading"
          size="large"
          :icon="h(SendOutlined)"
          style="margin-left: 12px;"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, h } from 'vue'
import { message } from 'ant-design-vue'
import { SendOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'

const customerId = ref('user_001')
const inputMessage = ref('')
const messages = ref([])
const loading = ref(false)
const msgContainer = ref(null)
const connected = ref(false)

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = () => {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

watch(messages, scrollToBottom, { deep: true })

const startNewChat = () => {
  if (customerId.value.trim()) {
    messages.value = []
    message.success(`已为客户 ${customerId.value} 创建新会话`)
    connected.value = true
  } else {
    message.warning('请输入客户ID')
  }
}

const clearChat = () => {
  messages.value = []
  message.info('对话已清空')
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) {
    message.warning('请输入消息内容')
    return
  }
  if (!customerId.value.trim()) {
    message.warning('请先输入客户ID')
    return
  }

  const userMsg = {
    role: 'user',
    content: inputMessage.value,
    timestamp: Date.now()
  }
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
      confidence: data.confidence,
      timestamp: Date.now()
    })
  } catch (e) {
    // 错误已在拦截器处理
    messages.value.push({
      role: 'assistant',
      content: '抱歉，系统暂时无法响应，请稍后再试。',
      timestamp: Date.now()
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-page {
  max-width: 1000px;
  margin: 0 auto;
  height: calc(100vh - 180px);
  display: flex;
  flex-direction: column;
}

.header-section {
  text-align: center;
  margin-bottom: 16px;
}

.header-section h2 {
  font-size: 26px;
  margin-bottom: 6px;
  color: #1890ff;
}

.subtitle {
  color: #666;
  font-size: 13px;
}

.control-card {
  border-radius: 8px;
  margin-bottom: 16px;
}

.customer-badge {
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.chat-container {
  flex: 1;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state .hint {
  font-size: 13px;
  color: #bbb;
  margin-top: 8px;
}

.message {
  display: flex;
  max-width: 85%;
  animation: message-in 0.3s ease;
}

@keyframes message-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.message.user .avatar {
  margin-left: 8px;
  background: #1890ff;
}

.message.assistant .avatar {
  margin-right: 8px;
  background: #52c41a;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
}

.bubble {
  padding: 10px 14px;
  border-radius: 16px;
  max-width: 100%;
  word-break: break-word;
  line-height: 1.5;
}

.message.user .bubble {
  background: linear-gradient(135deg, #1890ff, #096dd9);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .bubble {
  background: white;
  border: 1px solid #d9d9d9;
  border-bottom-left-radius: 4px;
}

.intent-tag {
  font-size: 11px;
  color: #52c41a;
  margin-top: 4px;
  padding: 2px 6px;
  background: #f6ffed;
  border-radius: 4px;
  align-self: flex-start;
}

.time {
  font-size: 10px;
  color: #bfbfbf;
  margin-top: 2px;
}

.message.user .time {
  text-align: right;
}

.thinking {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}

.thinking span {
  width: 8px;
  height: 8px;
  background: #1890ff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.thinking span:nth-child(1) { animation-delay: -0.32s; }
.thinking span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
  padding: 16px;
  background: white;
  border-top: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
}
</style>
