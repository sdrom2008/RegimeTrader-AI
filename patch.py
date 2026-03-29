import re

with open('regime_trader_ai_product/code/ai_trader.py', 'r') as f:
    content = f.read()

# 1. Update RiskManager ATR multipliers
content = re.sub(
    r'stop_loss_atr_multiplier=1\.5, take_profit_atr_multiplier=2\.0',
    r'stop_loss_atr_multiplier=3.0, take_profit_atr_multiplier=6.0',
    content
)

# 2. Update trailing stop ATR multipliers from 1.5 to 3.0
content = re.sub(r'latest_row\[\'ATR\'\] \* 1\.5', r'latest_row[\'ATR\'] * 3.0', content)

# 3. Add 20-day high and RSI cross logic
old_tech_filters = """        # Tech Filters: Volume & RSI
        rsi = latest_data_row.get('RSI', 50)
        vol = latest_data_row.get('Volume', 0)
        vol_sma = latest_data_row.get('Volume_SMA', 0)
        has_volume_support = vol > (vol_sma * 0.8) if vol_sma > 0 else True
        is_overbought = rsi > 85
        is_oversold = rsi < 30"""

new_tech_filters = """        # Tech Filters: Volume, RSI Cross, & 20-Day Breakout
        rsi = latest_data_row.get('RSI', 50)
        prev_rsi = current_data.iloc[-2].get('RSI', 50) if len(current_data) > 1 else 50
        vol = latest_data_row.get('Volume', 0)
        vol_sma = latest_data_row.get('Volume_SMA', 0)
        
        has_volume_support = vol > (vol_sma * 0.8) if vol_sma > 0 else True
        is_overbought = rsi > 85
        
        # Mean Reversion right-side entry (Crossing thresholds)
        is_rsi_cross_up_30 = prev_rsi <= 30 and rsi > 30
        is_rsi_cross_down_85 = prev_rsi >= 85 and rsi < 85
        
        # Donchian Breakout (20-day high)
        if len(current_data) >= 20:
            recent_20_high = current_data['High'].iloc[-20:-1].max()
            is_20d_high_breakout = entry_price > recent_20_high
        else:
            is_20d_high_breakout = True"""

content = content.replace(old_tech_filters, new_tech_filters)

# 4. Update the Uptrend logic to include 20-day breakout
old_uptrend_logic = """        # Simple entry condition: Strong uptrend with high confidence AND macro trend alignment
        if market_state in ["Uptrend", "Volatile Uptrend"] and confidence_score > 0.7:
            if not is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Uptrend, but below 200 EMA (Macro Downtrend).")
                return "HOLD", 0, None, None"""

new_uptrend_logic = """        # Simple entry condition: Strong uptrend with high confidence AND macro trend alignment
        if market_state in ["Uptrend", "Volatile Uptrend"] and confidence_score > 0.7:
            if not is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Uptrend, but below 200 EMA (Macro Downtrend).")
                return "HOLD", 0, None, None
                
            if not is_20d_high_breakout:
                if verbose: print("Signal Filtered: Uptrend but not a 20-day high breakout. Waiting for momentum.")
                return "HOLD", 0, None, None"""

content = content.replace(old_uptrend_logic, new_uptrend_logic)

# 5. Update the Ranging Mean Reversion logic to use crosses
old_mean_reversion_buy = """            # Mean Reversion Engine
            if is_oversold and is_above_200ema: # Buy the dip in a macro bull market"""

new_mean_reversion_buy = """            # Mean Reversion Engine
            if is_rsi_cross_up_30 and is_above_200ema: # Right-side buy the dip in a macro bull market"""

content = content.replace(old_mean_reversion_buy, new_mean_reversion_buy)

old_mean_reversion_sell = """            elif is_overbought and not is_above_200ema: # Sell the rip in a macro bear market"""

new_mean_reversion_sell = """            elif is_rsi_cross_down_85 and not is_above_200ema: # Right-side sell the rip in a macro bear market"""

content = content.replace(old_mean_reversion_sell, new_mean_reversion_sell)

with open('regime_trader_ai_product/code/ai_trader.py', 'w') as f:
    f.write(content)

print("Patch applied successfully.")
