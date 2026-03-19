# v2 策略测试计划

## ✅ 已完成
- 三分类模型训练完成（regime_model_v2.pkl）
- BTC 单币信号验证成功（输出 SELL 信号）
- 虚拟环境依赖安装完成

## 📋 待执行测试

### 测试1: 规则版快速验证（无需模型）
```bash
cd regime_trader_ai_product
. .venv/bin/activate
DRY_RUN=1 python paper_trader_v2_quick.py 2>&1 | tee v2_quick_test.log
```
目标：验证方向逻辑是否能同时产生 BUY 和 SELL 信号

### 测试2: 模型版完整扫描（20个币）
```bash
cd regime_trader_ai_product
. .venv/bin/activate
SCAN_LIMIT=20 DRY_RUN=1 python paper_trader_v2.py 2>&1 | tee v2_scan20.log
```
目标：观察模型在实际扫描中是否产生双向信号，统计开仓数量

### 测试3: 对比 v1 vs v2
暂时停止 v1 cron（避免干扰），专注测试 v2

## 📊 评估指标（测试阶段）
- 开仓信号数量（期望：多头+空头混合）
- 方向准确性（肉眼检查：做空时是否真的在下跌趋势）
- 仓位计算合理性（单仓是否 ≤8%）
- 是否出现异常错误

## ⚠️ 已知问题
1. v1 仍在运行，占用资金且持仓为多头 → 建议暂停 v1 cron
2. v2 quick 版和 paper_trader_v2.py 的 feature 计算依赖 strategy_v2，但 strategy_v2 顶部直接 import sklearn → 导致非训练环境无法加载
   - 解决方案：将常量/函数拆分到独立文件（如 `strategy_v2_constants.py`）

## 🎯 下一步（测试完成后）
- 如果 v2 表现优于 v1（方向正确、胜率提升）→ 切换 cron 到 v2
- 如果模型误判率高 → 考虑：
  - 增加训练数据（ETH、BNB 等多币种）
  - 调整标签阈值（ATR multiplier 从 2.0 → 2.5）
  - 特征工程优化（添加 VWAP、布林带宽度变化率等）
