"""
v2 策略配置文件（优化后）
"""

# ========================
# 市场与扫描参数
# ========================
SCAN_LIMIT = 60                # 每次扫描前N个流动性币种（总池）
TRADING_SYMBOLS = []           # 空列表 = 扫描全部币种（放开白名单）
MIN_VOLUME_RANK = 20           # 最小交易量排名（可加）
LOOK_FORWARD_CANDLES = 24      # 预测未来N根K线（24h）
QUANTILE_THRESHOLD = 0.6       # 分位数阈值（强趋势定义）

# ========================
# 技术指标参数（优化后）
# ========================
ADX_STRONG_THRESHOLD = 20      # ADX 强趋势阈值（从23降到20，捕捉更多信号）
ADX_WEAK_THRESHOLD = 20        # ADX 震荡阈值
CONFIDENCE_THRESHOLD = 0.55    # 模型置信度阈值（从0.60降到0.55）

# ========================
# 风控参数
# ========================
LEVERAGE = 2.5                 # 最大杠杆
RISK_PER_TRADE_PCT = 0.05      # 单仓风险（总资金5%，测试多持仓）
STOP_LOSS_ATR_MULT = 2.0       # 止损：2×ATR
TAKE_PROFIT_RR = 2.0           # 止盈：2倍风险（2:1盈亏比）
TRAILING_STOP_ATR = 1.5        # 移动止损：1.5×ATR

# ========================
# 过滤条件
# ========================
ENABLE_FUNDING_FILTER = True   # 资金费率过滤
FUNDING_RATE_THRESHOLD = 0.0005  # 0.05%
MIN_PRICE = 0.001              # 最小价格（过滤垃圾币）
MIN_MARKET_CAP = 100_000_000   # 最小市值（USDT，可选）

# ========================
# 文件路径
# ========================
MODEL_FILE = 'regime_model_v2_multi_full.pkl'
STATE_FILE = 'paper_trade_state_v2.json'  # v2 独立状态文件
LOG_FILE = 'logs/v2_trader.log'

# ========================
# 执行器参数
# ========================
SCAN_INTERVAL = 300  # 扫描间隔（秒），默认5分钟
