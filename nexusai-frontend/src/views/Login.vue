<template>
  <div class="login-page">
    <div class="login-container">
      <div class="logo-section">
        <div class="logo-icon">🚀</div>
        <h1 class="logo-text">NexusAI Tech</h1>
        <p class="subtitle">AI 智能营销与客服平台</p>
      </div>

      <a-card class="login-card" :bordered="false">
        <a-tabs v-model:activeKey="loginMode" class="login-tabs">
          <a-tab-pane key="seller" tab="📱 卖家登录" />
          <a-tab-pane key="agent" tab="👤 客服登录" />
        </a-tabs>

        <!-- 卖家手机登录 -->
        <a-form
          v-if="loginMode === 'seller'"
          :model="sellerForm"
          layout="vertical"
          @finish="handleSellerLogin"
        >
          <a-form-item label="手机号" name="phone" :rules="[{ required: true, message: '请输入手机号' }]">
            <a-input
              v-model:value="sellerForm.phone"
              placeholder="请输入手机号"
              size="large"
              :maxlength="11"
            />
          </a-form-item>

          <a-form-item label="验证码" name="code" :rules="[{ required: true, message: '请输入验证码' }]">
            <a-space style="width: 100%">
              <a-input
                v-model:value="sellerForm.code"
                placeholder="请输入验证码"
                size="large"
                style="flex: 1"
                :maxlength="6"
              />
              <a-button
                type="primary"
                :loading="sendingCode"
                :disabled="countdown > 0"
                @click="sendVerificationCode"
                size="large"
              >
                {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
              </a-button>
            </a-space>
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              :loading="sellerLoading"
              size="large"
              block
            >
              登录
            </a-button>
          </a-form-item>
        </a-form>

        <!-- 客服邮箱登录 -->
        <a-form
          v-else
          :model="agentForm"
          layout="vertical"
          @finish="handleAgentLogin"
        >
          <a-form-item label="邮箱" name="email" :rules="[{ required: true, message: '请输入邮箱' }]">
            <a-input
              v-model:value="agentForm.email"
              placeholder="请输入客服邮箱"
              size="large"
            />
          </a-form-item>

          <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
            <a-input-password
              v-model:value="agentForm.password"
              placeholder="请输入密码"
              size="large"
            />
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              :loading="agentLoading"
              size="large"
              block
            >
              登录
            </a-button>
          </a-form-item>
        </a-form>

        <div class="login-footer">
          <p v-if="loginMode === 'seller'">
            还没有账号？<a-button type="link" @click="handleRegister">立即注册</a-button>
          </p>
          <p v-else>
            忘记密码？<a-button type="link" disabled>联系管理员重置</a-button>
          </p>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loginMode = ref('seller') // 'seller' or 'agent'

const sellerForm = reactive({
  phone: '',
  code: ''
})

const agentForm = reactive({
  email: '',
  password: ''
})

const sellerLoading = ref(false)
const agentLoading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)

// 发送验证码
const sendVerificationCode = async () => {
  if (!sellerForm.phone || sellerForm.phone.length !== 11) {
    message.error('请输入正确的手机号')
    return
  }

  sendingCode.value = true
  try {
    // TODO: 调用 /api/auth/send-code
    // await authStore.sendCode(sellerForm.phone)
    message.success('验证码已发送（测试模式，验证码：123456）')
    startCountdown()
  } catch (e) {
    message.error('发送失败，请重试')
  } finally {
    sendingCode.value = false
  }
}

const startCountdown = () => {
  countdown.value = 60
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}

// 卖家登录
const handleSellerLogin = async () => {
  sellerLoading.value = true
  try {
    // TODO: 调用 /api/auth/phone-login
    // const data = await authStore.loginByPhone(sellerForm.phone, sellerForm.code)
    // 模拟返回
    const mockData = {
      token: 'mock-seller-token',
      sellerId: '123e4567-e89b-12d3-a456-426614174000',
      nickname: '测试商家',
      freeQuota: 100,
      subscriptionLevel: 'Basic'
    }
    authStore.setAuth(mockData.token, mockData.sellerId, 'Seller', mockData)
    message.success('登录成功！')
    router.push('/dashboard')
  } catch (e) {
    message.error('登录失败：' + (e.message || '验证码错误'))
  } finally {
    sellerLoading.value = false
  }
}

// 客服登录
const handleAgentLogin = async () => {
  agentLoading.value = true
  try {
    // TODO: 调用 /api/auth/agent-login
    // const data = await authStore.loginAgent(agentForm.email, agentForm.password)
    const mockData = {
      token: 'mock-agent-token',
      agentId: '123e4567-e89b-12d3-a456-426614174001',
      name: '客服小王',
      role: 'Agent'
    }
    authStore.setAuth(mockData.token, mockData.agentId, mockData.role, mockData)
    message.success('登录成功！')
    // 根据角色跳转
    if (mockData.role === 'Supervisor') {
      router.push('/support/supervisor')
    } else {
      router.push('/support/workbench')
    }
  } catch (e) {
    message.error('登录失败：账号或密码错误')
  } finally {
    agentLoading.value = false
  }
}

const handleRegister = () => {
  message.info('注册功能暂未开放，请联系管理员开通')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  width: 100%;
  max-width: 420px;
  padding: 20px;
}

.logo-section {
  text-align: center;
  margin-bottom: 24px;
  color: white;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.logo-text {
  font-size: 28px;
  font-weight: bold;
  margin: 0;
}

.subtitle {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 8px;
}

.login-card {
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

:deep(.ant-card-body) {
  padding: 32px;
}

.login-tabs {
  margin-bottom: 24px;
}

:deep(.ant-tabs-nav) {
  justify-content: center;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  color: #666;
}

:deep(.ant-btn-link) {
  padding: 0;
  font-size: 14px;
}
</style>
