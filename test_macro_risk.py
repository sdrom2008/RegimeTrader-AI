"""测试宏风险监控模块"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接在当前目录导入（非包结构）
from news_fetcher import fetch_all_news
from sentiment_analyzer import SentimentAnalyzer
from risk_controller import RiskController

print("=== 宏观风险监控测试 ===\n")

# 1. 抓取新闻
print("1. 抓取新闻源...")
news = fetch_all_news(max_per_source=2)
print(f"   共获取 {len(news)} 条新闻\n")

# 2. 情绪分析
analyzer = SentimentAnalyzer()
risk_score, has_critical, details = analyzer.analyze_news_list(news)
print(f"2. 风险评分: {risk_score:.1%}")
print(f"   严重事件: {has_critical}\n")

# 3. 风险决策
controller = RiskController()
assessment = controller.assess_risk(risk_score, has_critical, details)
print("3. 风险评估:", assessment['level'], assessment['action'])
print("   原因:", assessment.get('reason', 'N/A'))

# 4. 警报消息
alert = controller.format_alert(assessment)
print("\n4. WhatsApp 警报预览:")
print(alert)

print("\n=== 测试完成 ===")
