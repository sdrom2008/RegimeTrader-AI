import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Add Admin Backend task to the Strategy section
    pattern = r"""- \*\*战略思考: SaaS 产品演进 \(OpenClaw 时代\)\*\*
    - \*\*方向\*\*: 升级为 \*\*\"AI 主控 Agent \+ 子Agent 协作 \+ 工具自动执行\"\*\* 模式
    - \*\*行动项\*\*:"""

    replacement = """- **战略思考: SaaS 产品演进 (跨境电商转型)**
    - **新方向**: 国内平台API封闭，全面转型**跨境电商（首发 Shopee，后续 Lazada/TikTok）**
    - **新增基建**: **管理后台 (Admin Panel)** - 用于管理商户、订阅、账单及系统级配置（尚未构建）。
    - **行动项**:"""
        
    content = re.sub(pattern, replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('/home/sdrom2008/.openclaw/workspace/HEARTBEAT.md')
