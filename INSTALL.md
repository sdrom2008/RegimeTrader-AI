# RegimeTrader AI 安装与配置指南

---

## 📦 交付内容

- `regimetrader_ai_product_YYYYMMDD_HHMM.tar.gz` - 完整产品包
- 内含 `regime_trader_ai_product/` 目录及所有源代码、文档、配置示例

---

## 🚀 快速安装

### 1. 解压
```bash
tar -xzf regimetrader_ai_product_*.tar.gz
cd regime_trader_ai_product
```

### 2. 创建虚拟环境
```bash
python -m venv venv
# Linux/Mac:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置 Binance API
```bash
# 复制环境变量模板
cp config/.env.example .env
# 编辑 .env，填入你的 API Key/Secret
nano .env
```

### 5. 准备 AI 模型
确保 `regime_model.pkl` 文件存在（已包含在包内，或指向外部链接）。默认已配置符号链接。

### 6. 初始化模拟状态
```bash
DRY_RUN=1 python -m regime_trader_ai_product.live_executor
```
首次运行会创建 `paper_trade_state.json`（初始资金 $10,000）。

### 7. 查看绩效报告
- 自动生成：每小时第5分钟运行 `performance_analyzer.py`
- 手动运行：
```bash
python performance_analyzer.py
```
报告将保存至 `logs/performance/` 并发送 WhatsApp 摘要。

---

## ⚙️ 参数调整（可选）

编辑 `paper_trader.py` 顶部常量：

```python
LEVERAGE = 3.0                  # 杠杆倍数
INITIAL_BALANCE = 10000.0       # 初始资金
RISK_PER_TRADE_PCT = 0.05       # 单笔风险 5%
SCAN_LIMIT = 60                 # 扫描交易对数量
MARKET_CONF_THRESHOLD = 0.7     # 置信度阈值
SCAN_INTERVAL = 300             # 扫描间隔(秒)
```

---

## 🏃 运行

### 模拟盘（推荐先测试）
```bash
DRY_RUN=1 python -m regime_trader_ai_product.live_executor
```
- 单次运行，不常驻
- 查看输出确认无错误

### 设置定时任务（crontab）
```bash
crontab -e
```
添加：
```cron
*/5 * * * * cd /path/to/regime_trader_ai_product && DRY_RUN=1 /path/to/venv/bin/python -m regime_trader_ai_product.live_executor >> logs/live_executor_cron.log 2>&1
```
- 每5分钟自动扫描
- 日志输出到 `logs/live_executor_cron.log`

### 实盘运行（谨慎！）
```bash
DRY_RUN=0 python -m regime_trader_ai_product.live_executor
```
- 使用真实 Binance 账户
- 务必先小资金测试

---

## 📊 监控

### 查看当前状态
```bash
cat paper_trade_state.json
```

### 查看日志
```bash
tail -f logs/live_executor_cron.log
```

### 报告
- 每小时整点自动发送 WhatsApp 报告（需 OpenClaw 配置）
- 报告包含总资产、持仓详情、盈亏

---

## 🛑 停止

若使用 crontab，编辑移除相关行后执行 `crontab -e` 保存。
若手动运行，Ctrl+C 停止。

---

## ⚠️ 注意事项

- 本软件为实验性策略，不保证盈利
- 实盘前请充分测试模拟盘至少24小时
- 建议从小资金开始，逐步放大
- 市场风险自担

---

**技术支持：** 虾子 (OpenClaw Agent)
