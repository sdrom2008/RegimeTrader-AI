"""
新闻抓取器（RSS + Nitter）
"""

import feedparser
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib

from config_news_sentiment import NEWS_RSS_FEEDS, NITTER_BASE, TWITTER_ACCOUNTS

def fetch_rss_feed(url, max_items=10):
    """抓取单个 RSS 源，返回 [{title, link, published, summary}]"""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            # 生成唯一 ID（链接哈希）
            link = entry.get('link', '')
            content = entry.get('summary', entry.get('description', ''))
            published = entry.get('published', entry.get('updated', ''))
            
            item = {
                'title': entry.get('title', ''),
                'link': link,
                'published': published,
                'summary': content[:200] if content else '',
                'source': url,
                'news_id': hashlib.md5(link.encode()).hexdigest()[:12]
            }
            items.append(item)
        return items
    except Exception as e:
        print(f"[!] RSS fetch error {url}: {e}")
        return []

def fetch_nitter_tweets(account, max_items=10):
    """从 nitter 获取最新推文（无需登录）"""
    url = f"{NITTER_BASE}/{account}/rss"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, 'xml')
        items = []
        entries = soup.find_all('entry')[:max_items]
        for entry in entries:
            title = entry.title.text if entry.title else ''
            link = entry.link['href'] if entry.link else ''
            published = entry.published.text if entry.published else ''
            summary = entry.summary.text if entry.summary else ''
            
            item = {
                'title': title,
                'link': urljoin(NITTER_BASE, link),
                'published': published,
                'summary': summary[:200],
                'source': f"nitter/{account}",
                'news_id': hashlib.md5(link.encode()).hexdigest()[:12]
            }
            items.append(item)
        return items
    except Exception as e:
        print(f"[!] Nitter fetch error {account}: {e}")
        return []

def fetch_all_news(max_per_source=5):
    """从所有源抓取新闻，去重后返回列表（按时间倒序）"""
    all_items = []
    
    # RSS 源
    for rss_url in NEWS_RSS_FEEDS:
        items = fetch_rss_feed(rss_url, max_items=max_per_source)
        all_items.extend(items)
    
    # Twitter 账号（通过 nitter）
    for account in TWITTER_ACCOUNTS:
        tweets = fetch_nitter_tweets(account, max_items=max_per_source)
        all_items.extend(tweets)
        time.sleep(0.5)  # 避免请求过快
    
    # 按发布时间排序（最新在前）
    def parse_time(item):
        try:
            # 尝试解析 RSS 时间格式
            t = datetime.strptime(item['published'][:19], '%Y-%m-%dT%H:%M:%S')
            return t
        except:
            return datetime.min
    
    all_items.sort(key=parse_time, reverse=True)
    
    # 去重（基于 news_id）
    unique_items = []
    seen = set()
    for item in all_items:
        if item['news_id'] not in seen:
            seen.add(item['news_id'])
            unique_items.append(item)
    
    return unique_items

if __name__ == '__main__':
    # 测试
    news = fetch_all_news()
    print(f"Fetched {len(news)} unique news items")
    for n in news[:5]:
        print(f"\n[{n['source']}] {n['title']}")
        print(f"  published: {n['published']}")
        print(f"  summary: {n['summary'][:80]}...")
