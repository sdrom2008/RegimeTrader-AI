from PIL import Image, ImageDraw, ImageFont
import os

def create_promo_image(filename, title, content, color=(0, 255, 65)):
    # Create a dark background image
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 40)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 20)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    
    # Draw Title
    draw.text((50, 50), title, font=font_title, fill=color)
    
    # Draw Content
    y_offset = 150
    for line in content.split('\n'):
        draw.text((50, y_offset), line, font=font_body, fill=color)
        y_offset += 30
        
    # Draw a "Border" to make it look like a terminal
    draw.rectangle([10, 10, width-10, height-10], outline=color, width=2)
    
    img.save(filename)
    print(f"Image saved to {filename}")

# Image 1: Tech/Status
tech_content = """
$ openclaw status
[SYSTEM]: Gateway running on port 60000
[AGENTS]: 1 Active (Master Mode)
[NODES]: 1 Linked
[STRATEGY]: BTC-XRP Hedge (Live)
[STATUS]: Environment Optimized for Latency

>>> DEPLOYMENT SUCCESSFUL
"""

# Image 2: Service Pitch
service_content = """
OPENCLAW 远程专业部署服务
--------------------------------
1. 环境自动搭建 (Node.js/Python)
2. Gateway 安全加固
3. 国内镜像网络优化
4. API 密钥双重加密
5. 1对1 调试指导

>>> 15分钟极速交付
"""

os.makedirs('promo_assets', exist_ok=True)
create_promo_image('promo_assets/tech_status.png', "SYSTEM READY", tech_content)
create_promo_image('promo_assets/service_pitch.png', "PRO SERVICE", service_content, color=(255, 204, 0))
