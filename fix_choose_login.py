import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r"""    <!-- 协议 -->
    <view class="protocol">"""

    replacement = """    <!-- 客服入口 -->
    <view class="agent-entry">
      <text class="link" @tap="goToAgentLogin">{{ currentLang === 'zh-CN' ? '员工/客服登录' : 'Agent Login' }}</text>
    </view>

    <!-- 协议 -->
    <view class="protocol">"""
        
    content = re.sub(pattern, replacement, content)
    
    # Also need to add the method
    method_pattern = r"""    loginPhone\(\) \{"""
    
    method_replacement = """    goToAgentLogin() {
      uni.navigateTo({ url: '/pages/login/agent-login' });
    },

    loginPhone() {"""
    
    content = re.sub(method_pattern, method_replacement, content)
    
    # Also add styles
    style_pattern = r"""\.protocol \{"""
    
    style_replacement = """.agent-entry {
  margin-top: 60rpx;
  font-size: 28rpx;
  color: #64748b;
  text-decoration: underline;
  cursor: pointer;
}

.protocol {"""

    content = re.sub(style_pattern, style_replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('/home/sdrom2008/.openclaw/workspace/my-project/frontend/src/pages/login/choose-login.vue')
