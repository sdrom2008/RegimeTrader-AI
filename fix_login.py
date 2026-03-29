import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # replace the LAST </view> before </template>
    footer_html = """
    <!-- 页脚备案信息 -->
    <view class="footer">
      <text class="icp">蜀ICP备2026123456号-1</text>
      <text class="copyright">© 2024-2026 Synerixis All Rights Reserved</text>
    </view>
  </view>
</template>"""

    css = """
.footer {
  position: absolute;
  bottom: 40rpx;
  width: 100%;
  left: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0.5;
}

.footer .icp, .footer .copyright {
  font-size: 20rpx;
  color: #64748b;
  margin-top: 8rpx;
}
</style>"""

    # Fix template
    content = re.sub(r'  </view>\n</template>', footer_html, content)
    
    # Fix CSS
    content = re.sub(r'</style>', css, content)
    
    with open(filename, 'w') as f:
        f.write(content)

fix('frontend/src/pages/login/login.vue')
fix('frontend/src/pages/login/wechat-login.vue')
