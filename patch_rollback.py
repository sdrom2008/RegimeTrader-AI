import re

with open('regime_trader_ai_product/code/ai_trader.py', 'r') as f:
    content = f.read()

# Remove the buggy 20d breakout and mean reversion cross logic, restore simple RSI + Vol
old_tech_filters = """        # Tech Filters: Volume, RSI Cross, & 20-Day Breakout
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

new_tech_filters = """        # Tech Filters: Volume & RSI
        rsi = latest_data_row.get('RSI', 50)
        vol = latest_data_row.get('Volume', 0)
        vol_sma = latest_data_row.get('Volume_SMA', 0)
        has_volume_support = vol > (vol_sma * 0.8) if vol_sma > 0 else True
        is_overbought = rsi > 85
        is_oversold = rsi < 30"""

content = content.replace(old_tech_filters, new_tech_filters)

# Restore uptrend logic
old_uptrend_logic = """        # Simple entry condition: Strong uptrend with high confidence AND macro trend alignment
        if market_state in ["Uptrend", "Volatile Uptrend"] and confidence_score > 0.7:
            if not is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Uptrend, but below 200 EMA (Macro Downtrend).")
                return "HOLD", 0, None, None
                
            if not is_20d_high_breakout:
                if verbose: print("Signal Filtered: Uptrend but not a 20-day high breakout. Waiting for momentum.")
                return "HOLD", 0, None, None"""

new_uptrend_logic = """        # Simple entry condition: Strong uptrend with high confidence AND macro trend alignment
        if market_state in ["Uptrend", "Volatile Uptrend"] and confidence_score > 0.7:
            if not is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Uptrend, but below 200 EMA (Macro Downtrend).")
                return "HOLD", 0, None, None"""

content = content.replace(old_uptrend_logic, new_uptrend_logic)

# Restore Mean Reversion buy
old_mean_reversion_buy = """            # Mean Reversion Engine
            if is_rsi_cross_up_30 and is_above_200ema: # Right-side buy the dip in a macro bull market"""

new_mean_reversion_buy = """            # Mean Reversion Engine
            if is_oversold and is_above_200ema: # Buy the dip in a macro bull market"""

content = content.replace(old_mean_reversion_buy, new_mean_reversion_buy)

# Restore Mean Reversion sell
old_mean_reversion_sell = """            elif is_rsi_cross_down_85 and not is_above_200ema: # Right-side sell the rip in a macro bear market"""

new_mean_reversion_sell = """            elif is_overbought and not is_above_200ema: # Sell the rip in a macro bear market"""

content = content.replace(old_mean_reversion_sell, new_mean_reversion_sell)

# Turn OFF Mean Reversion block by commenting out the return logic, effectively falling back to 20.83% win-rate version.
# Actually, the 20.83% win rate version did NOT have mean reversion at all.
# Let's just remove the entire `elif market_state in ["Ranging", "Choppy"]:` block.
old_ranging_block = """        elif market_state in ["Ranging", "Choppy"]:
            # Mean Reversion Engine
            if is_oversold and is_above_200ema: # Buy the dip in a macro bull market
                mr_sl = entry_price - (atr_value * 1.0) # Tighter stop for range trading
                mr_tp = entry_price + (atr_value * 1.5) # Quick target (e.g. mean)
                position_size_pct = self.position_sizer.determine_position_size(
                    self.account_capital, entry_price, mr_sl, confidence_score, atr_value
                )
                if verbose: print(f"Mean Reversion Signal: BUY (RSI={rsi:.1f}). Position Size: {position_size_pct:.2%}")
                return "BUY", position_size_pct, mr_sl, mr_tp
                
            elif is_overbought and not is_above_200ema: # Sell the rip in a macro bear market
                mr_sl = entry_price + (atr_value * 1.0)
                mr_tp = entry_price - (atr_value * 1.5)
                position_size_pct = self.position_sizer.determine_position_size(
                    self.account_capital, entry_price, mr_sl, confidence_score, atr_value
                )
                if verbose: print(f"Mean Reversion Signal: SELL (RSI={rsi:.1f}). Position Size: {position_size_pct:.2%}")
                return "SELL", position_size_pct, mr_sl, mr_tp
            else:
                if verbose: print(f"Signal: HOLD. Ranging market, waiting for RSI extremes (RSI={rsi:.1f}).")
                return "HOLD", 0, None, None"""

content = content.replace(old_ranging_block, "")

with open('regime_trader_ai_product/code/ai_trader.py', 'w') as f:
    f.write(content)

print("Rollback applied successfully.")
