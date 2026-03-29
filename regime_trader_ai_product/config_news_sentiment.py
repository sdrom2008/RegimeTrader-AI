"""
新闻与情绪监控配置
"""

# 监控频率（分钟）
CHECK_INTERVAL_MINUTES = 10

# 新闻源（RSS 免费）
NEWS_RSS_FEEDS = [
    "https://feeds.feedburner.com/CoinDesk",
    "https://theblock.co/feed/",
    "https://cointelegraph.com/rss",
    "https://cryptoslate.com/feed/",
]

# X 平台监控账号（通过 nitter RSS）
# 格式：nitter 实例 + 账号名
NITTER_BASE = "https://nitter.net"
TWITTER_ACCOUNTS = [
    "cz_binance",
    "coinbase",
    "coinmarketcap",
    "CryptoSlate",
    "CoinDesk",
]

# 负面关键词（中英文）
NEGATIVE_KEYWORDS = {
    'en': [
        'hack', 'scam', 'fraud', 'ban', 'banned', 'regulation', 'regulatory',
        'crash', 'collapse', 'bankruptcy', 'liquidation', 'exploit',
        'downtrend', 'bearish', 'dead cat bounce',
        'security breach', 'cyber attack', 'theft', 'rug pull',
        'SEC charges', 'lawsuit', 'investigation',
        'delisting', 'halt', 'suspend',
    ],
    'zh': [
        '黑客', '诈骗', '跑路', '禁止', '监管', '合规',
        '崩盘', '暴跌', '腰斩', '归零',
        '调查', '起诉', '罚款',
        '提现', '暂停', '危机',
    ]
}

# 严重词（立即高风险）
CRITICAL_KEYWORDS = {
    'en': ['exchange collapse', 'exchange hack', 'stablecoin depeg', 'bankruptcy filing', 'liquidity crisis'],
    'zh': ['交易所暴雷', '交易所跑路', '稳定币脱锚', '流动性危机']
}

# 风险阈值（0-1 分数）
WARNING_THRESHOLD = 0.3   # 超过此值触发 WARNING
CRITICAL_THRESHOLD = 0.6  # 超过此值触发 CRITICAL（暂停开仓）

# 缓存的新闻 ID 去重（内存）
SEEN_NEWS_IDS = set()

# 输出设置
SEND_WHATSAPP_ALERT = True  # 是否发送 WhatsApp 警报
WHATSAPP_TARGET = "+8613908412393"
