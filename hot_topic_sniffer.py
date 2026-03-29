import requests
import json
import time
from datetime import datetime

def sniff_trends():
    # 简单的热点嗅探原型：抓取知乎热榜前5
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    
    print(f"[{datetime.now()}] Sniffing hot topics...")
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        hot_topics = []
        for item in data['data'][:5]:
            hot_topics.append(item['target']['title'])
            
        with open("daily_trends.log", "a") as f:
            f.write(f"[{datetime.now()}] HOT: {', '.join(hot_topics)}\n")
        print("Trends updated.")
    except Exception as e:
        print(f"Sniffing error: {str(e)}")

if __name__ == "__main__":
    sniff_trends()
