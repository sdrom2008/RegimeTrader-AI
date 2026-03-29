import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r"""    <!-- 其他 -->
    <view class="other-list">"""

    replacement = """    <!-- 团队管理 -->
    <view class="other-list" style="margin-bottom: 24rpx;">
      <view class="list-item" @tap="toTeam">
        <text>团队管理</text>
        <text class="arrow">></text>
      </view>
    </view>

    <!-- 其他 -->
    <view class="other-list">"""
        
    content = re.sub(pattern, replacement, content)
    
    # Add method
    method_pattern = r"""    toAccount\(\) \{"""
    
    method_replacement = """    toTeam() {
      uni.navigateTo({ url: '/pages/merchant/team' });
    },

    toAccount() {"""
    
    content = re.sub(method_pattern, method_replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('/home/sdrom2008/.openclaw/workspace/my-project/frontend/src/pages/profile/index.vue')
