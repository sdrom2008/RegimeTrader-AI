"""
情绪与风险分析器
"""

import re
from datetime import datetime

from config_news_sentiment import NEGATIVE_KEYWORDS, CRITICAL_KEYWORDS, SEEN_NEWS_IDS

class SentimentAnalyzer:
    def __init__(self):
        self.negative_keywords = set(NEGATIVE_KEYWORDS['en'] + NEGATIVE_KEYWORDS['zh'])
        self.critical_keywords = set(CRITICAL_KEYWORDS['en'] + CRITICAL_KEYWORDS['zh'])
    
    def analyze_text(self, text, title_weight=2.0):
        """
        分析单条新闻的负面情绪分数
        - 标题中出现关键词权重更高
        - 返回: (score, is_critical)
          score: 0-1 之间，越高越负面
          is_critical: 是否包含严重词
        """
        if not text:
            return 0.0, False
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        neg_count = sum(1 for w in words if w in self.negative_keywords)
        crit_count = sum(1 for w in words if w in self.critical_keywords)
        
        # 简单评分算法
        base_score = min(1.0, (neg_count * 0.3) + (crit_count * 0.7))
        
        # 包含严重词直接标记
        is_critical = crit_count > 0
        
        return base_score, is_critical
    
    def analyze_news_list(self, news_items, time_window_hours=1):
        """
        分析一批新闻，返回整体风险评分（0-1）
        - 只考虑最近 time_window_hours 的新闻
        - 严重事件权重更高
        """
        now = datetime.utcnow()
        relevant = []
        for item in news_items:
            try:
                pub_str = item.get('published', '')
                if not pub_str:
                    continue
                # 简化时间解析
                pub_time = datetime.strptime(pub_str[:19], '%Y-%m-%dT%H:%M:%S')
                if (now - pub_time).total_seconds() <= time_window_hours * 3600:
                    relevant.append(item)
            except:
                continue
        
        if not relevant:
            return 0.0, False, []
        
        scores = []
        critical_flags = []
        details = []
        
        for item in relevant:
            text = f"{item['title']} {item.get('summary', '')}"
            score, is_critical = self.analyze_text(text)
            scores.append(score)
            critical_flags.append(is_critical)
            details.append({
                'title': item['title'],
                'source': item['source'],
                'score': score,
                'critical': is_critical,
                'link': item['link']
            })
        
        # 整体评分：最高分 + 平均分加权
        max_score = max(scores) if scores else 0.0
        avg_score = sum(scores) / len(scores) if scores else 0.0
        overall = (max_score * 0.6) + (avg_score * 0.4)
        
        has_critical = any(critical_flags)
        
        return overall, has_critical, details

if __name__ == '__main__':
    # 测试
    from news_fetcher import fetch_all_news
    
    print("Fetching news...")
    news = fetch_all_news(max_per_source=3)
    print(f"Total: {len(news)}\n")
    
    analyzer = SentimentAnalyzer()
    overall, critical, details = analyzer.analyze_news_list(news)
    
    print(f"Risk Score: {overall:.2%} | Critical: {critical}")
    print("\nHigh-scoring items:")
    for d in details:
        if d['score'] > 0.2:
            print(f"- [{d['source']}] {d['title'][:60]}... (score={d['score']:.2f}, critical={d['critical']})")
