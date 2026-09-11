"""
v2 策略配置文件（优化后）
"""

import os

# ========================
# 市场与扫描参数
# ========================
SCAN_LIMIT = 60                # 每次扫描前N个流动性币种（总池）
# Lock to train-set symbols (multi_full model). Empty list = scan top SCAN_LIMIT.
TRADING_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
MIN_VOLUME_RANK = 20           # 最小交易量排名（可加）
LOOK_FORWARD_CANDLES = 24      # 预测未来N根K线（24h）
QUANTILE_THRESHOLD = 0.6       # 分位数阈值（强趋势定义）

# ========================
# 技术指标参数（优化后）
# ========================
# 2026-09-10: raised after disastrous offline backtest (WR~35%, PF~0.53, ~-100%).
# Old defaults: ADX_STRONG_THRESHOLD=20, CONFIDENCE_THRESHOLD=0.55
ADX_STRONG_THRESHOLD = 35      # edge切片：强趋势才开枪
ADX_WEAK_THRESHOLD = 20        # ADX 震荡阈值
MIN_DI_DIFF = 15.0             # |+DI - -DI| 最小差（强方向）
# CONFIDENCE_THRESHOLD = 0.75  # 模型置信度阈值（was 0.70；日更再抬）
CONFIDENCE_THRESHOLD = 0.85    # edge切片候选：少开高打

# ========================
# 信号观察模式（不新开仓，只记 journal 评估准确率）
# ========================
SIGNAL_OBSERVE_MODE = False  # 收集真实纸交易样本；勿长期空转观察
SIGNAL_JOURNAL_FILE = 'logs/signal_journal.jsonl'

# ========================
# 周期对齐（1h 模型 + 5min 扫描）
# ========================
# 模型/特征按 1h 训练；SCAN_INTERVAL=300 只负责盯仓。
# True：开仓/信号只用「已收盘」的 1h K，每根收盘棒最多评估一次，避免未收盘棒 conf 乱晃。
ENTRY_ON_CLOSED_1H_ONLY = True


# ========================
# 风控参数
# ========================
# 2026-09-10 v3: tighter risk after v2 still ~-98% equity. Old: LEVERAGE=2.5,
# RISK_PER_TRADE_PCT=0.05, STOP_LOSS_ATR_MULT=2.0, TAKE_PROFIT_RR=2.0
LEVERAGE = 2.0                 # 纸交易杠杆封顶 2
RISK_PER_TRADE_PCT = 0.02      # 单枪 2%：打中要有体感，打错可活
STOP_LOSS_ATR_MULT = 1.5       # 止损：1.5×ATR（was 2.0，收紧无效波动）
TAKE_PROFIT_RR = 2.5           # 止盈：2.5倍风险（was 2.0，补偿~37%胜率）
TRAILING_STOP_ATR = 1.5        # 移动止损：1.5×ATR
TRAIL_ACTIVATE_R = 99.0        # 近似关闭 trail（切片显示关 trail 更赚）；靠 TP/SL/MAX_HOLD
MAX_MARGIN_PCT_OF_EQUITY = 0.40  # 单仓保证金上限（占权益），避免一笔吃光现金
MAX_CONCURRENT_POSITIONS = 2   # 同时最多 2 枪，避免手续费稀释
MAX_HOLD_HOURS = 24            # 最长持仓（小时），超时市价平（对齐预测窗口）

# ========================
# 交易冷却（减少翻炒）
# ========================
# Per-symbol bars/hours to wait after a close before re-entry (1h timeframe).
MIN_BARS_BETWEEN_TRADES = 6    # 平仓后至少间隔 6 根 1h K 线
COOLDOWN_HOURS = 6             # 等价小时数，供 paper_trader 用时间戳判断

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
# Primary trained multi-symbol model. If missing, resolve_model_file() falls back
# to regime_model_v2_quantile.pkl (BTC-only quantile). Importing this module
# never requires the pkl to exist.
MODEL_FILE = 'regime_model_v2_multi_full.pkl'
MODEL_FILE_FALLBACK = 'regime_model_v2_quantile.pkl'
STATE_FILE = 'paper_trade_state_v2.json'  # v2 独立状态文件
LOG_FILE = 'logs/v2_trader.log'

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def resolve_model_file(preferred=None):
    """Return path to a usable model file.

    Prefers MODEL_FILE (multi_full), then MODEL_FILE_FALLBACK (quantile).
    Does not raise if neither exists — callers should handle FileNotFoundError
    when opening the returned path.
    """
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.extend([MODEL_FILE, MODEL_FILE_FALLBACK])
    seen = set()
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        path = name if os.path.isabs(name) else os.path.join(_REPO_ROOT, name)
        if os.path.exists(path):
            return path
    # Default to preferred/multi path for clearer error messages on open()
    return os.path.join(_REPO_ROOT, preferred or MODEL_FILE)

# ========================
# 执行器参数
# ========================
# STRATEGY_V4: SCAN_INTERVAL=300 confirmed (5 min cadence for observe/live paper)
SCAN_INTERVAL = 300  # 扫描间隔（秒），默认5分钟

# ========================
# 成交滑点（paper + backtest，仅不利方向）
# ========================
SLIPPAGE_BPS = 2.0          # STRATEGY_V4: 每笔成交不利滑点（bps），开平仓均计
SLIPPAGE_ATR_FRAC = 0.0     # 可选：>0 时再加 atr*frac 不利滑点；0=关闭

# ========================
# STRATEGY_V4 observe-ready 包（文档见 STRATEGY_V4.md）
# ========================
# Universe: TRADING_SYMBOLS = BTC/ETH/BNB/SOL/XRP（训练集五币）
# Timeframe: 1h K；Scan: SCAN_INTERVAL=300s（5 min）
# SIGNAL_OBSERVE_MODE=True（仅 journal；翻 False 即开纸仓）
# Gates: CONFIDENCE_THRESHOLD=0.80, ADX_STRONG_THRESHOLD=25, DI 方向过滤保留
# Risk: RISK_PER_TRADE_PCT=0.02, LEVERAGE=2.0, SL=1.5 ATR, TP RR=2.5,
#       TRAILING_STOP_ATR=1.5, TRAIL_ACTIVATE_R=1.0, MAX_MARGIN_PCT=0.40,
#       MAX_CONCURRENT_POSITIONS=2, COOLDOWN=6h/bars, MAX_HOLD_HOURS=24
# Costs: SLIPPAGE_BPS=2.0 (+ optional ATR frac), fee_rate=0.0004 on slipped notional
