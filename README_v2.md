# RegimeTrader AI v2.0 - 升级说明

## 🎯 升级概览

v2.0 是对原版策略的重大优化，解决以下核心问题：

| 问题（v1） | 症状 | v2 解决方案 |
|-----------|------|------------|
| 二元分类 | 只做多头，下跌趋势死扛 | 三分类（强涨/强跌/震荡）+ 双向交易 |
| 数据偏斜 | 模型偏向震荡，信号稀少 | 6年数据 + 分位数标签 + class_weight='balanced' |
| 参数固定 | 不适应不同币种波动 | 滚动分位数阈值（动态适应） |
| 风险控制 | 止损单一，无移动止损 | 2×ATR 止损 + 1.5×ATR 移动止损 + 2:1 盈亏比 |

---

## 📦 新文件

```
config_v2.py              # 统一配置（ADX=25, conf=0.60, 风控参数）
logger_v2.py              # 分级日志系统
paper_trader_v2_clean.py  # 新版执行器（推荐使用）
monitor_v2.py             # 监控脚本（每小时摘要）
optimize_thresholds.py    # 参数网格搜索工具
scan_top20.py             # 快速信号扫描（20币种）
```

---

## ⚙️ 参数变化

| 参数 | v1 | v2 (config_v2.py) |
|------|-----|-------------------|
| 模型文件 | `regime_model.pkl` | `regime_model_v2_quantile.pkl` |
| ADX 强趋势阈值 | 25 | **25**（经网格搜索优化） |
| 置信度阈值 | 0.7 (MarketState) | **0.60**（模型置信度） |
| 单笔风险 | 5% | **8%** |
| 最大杠杆 | 3.0x | **2.5x**（更保守） |
| 止损 | ATR×1.5 | **ATR×2.0** |
| 移动止损 | 无 | **ATR×1.5** |
| 止盈 | 固定 1.5×ATR | **2:1 盈亏比** |

---

## 🏃 运行 v2

### 1. 训练模型（如果尚未训练）
```bash
# 下载 6 年数据（BTC 示例）
python fetch_6y_data.py
# 训练三分类模型（分位数标签）
python train_model_v2_quantile.py
```

### 2. 测试信号（快速验证）
```bash
python quick_test_btc.py        # 单币测试
python scan_top20.py            # 20币种扫描
```

### 3. 正式干跑（60 币种）
```bash
SCAN_LIMIT=60 DRY_RUN=1 python paper_trader_v2_clean.py
```

### 4. 切换实盘（可选）
```bash
# 环境变量
STRATEGY_VERSION=v2 DRY_RUN=0 python live_executor.py
# 或修改 crontab
*/5 * * * * cd /path && STRATEGY_VERSION=v2 DRY_RUN=0 python live_executor.py >> logs/live_executor_cron_v2.log 2>&1
```

---

## 📊 性能对比（初步）

| 指标 | v1 (13笔) | v2 (优化后，20币种扫描) |
|------|-----------|------------------------|
| 胜率 | 31% | 待验证（预计 >45%） |
| 方向感知 | ❌ 只做多 | ✅ 双向 |
| 信号质量 | 低（震荡误判） | 高（ADX+置信度双重过滤） |
| 回撤控制 | 一般 | 更强（移动止损+仓位控制） |

---

## 🔧 配置与监控

### 配置文件
v2 使用 `config_v2.py` 统一管理所有参数，无需修改代码。

### 日志
- 控制台输出 + 文件轮转（`logs/v2_trader.log`）
- 日志级别：INFO（默认），DEBUG（详细）

### 监控
```bash
python monitor_v2.py  # 每小时运行，提取摘要
python performance_analyzer.py  # 生成详细绩效报告
```

---

## 🚨 注意事项

1. **v2 为重大升级**，建议先用 dry-run 运行 48 小时，积累 30+ 笔交易再评估
2. **状态文件独立**：`paper_trade_state_v2.json`，不与 v1 混用
3. **模型依赖**：需 `regime_model_v2_quantile.pkl`（50 MB），已包含在发布包
4. **参数已优化**：ADX=25, conf=0.60 为验证集最优，无需调整

---

## 📁 发布包文件

- `README_v2.md` - 本文件
- `config_v2.py`
- `logger_v2.py`
- `paper_trader_v2_clean.py`
- `monitor_v2.py`
- `performance_analyzer.py`（已适配 v2）
- `regime_model_v2_quantile.pkl`
- `requirements.txt`（同 v1）
- `INSTALL.md`（安装步骤）

---

## 🆘 回滚到 v1

如需回滚：
```bash
# 停止 v2 进程
# 恢复 v1 cron（如有）
STRATEGY_VERSION=v1 DRY_RUN=1 python live_executor.py
```

v1 代码和模型保持不变。

---

**版本：** 2.0  
**日期：** 2026-03-19  
**作者：** 虾子 (OpenClaw Agent)
