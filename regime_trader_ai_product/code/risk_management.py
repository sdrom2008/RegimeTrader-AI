# risk_management.py

import pandas as pd
import numpy as np

class RiskManager:
    def __init__(self, atr_period=14, stop_loss_atr_multiplier=1.5, take_profit_atr_multiplier=2.0, min_stop_loss_pct=0.01, min_take_profit_pct=0.01):
        self.atr_period = atr_period
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier # Stop loss distance based on ATR multiples
        self.take_profit_atr_multiplier = take_profit_atr_multiplier # Take profit target based on ATR multiples
        self.min_stop_loss_pct = min_stop_loss_pct # Minimum stop loss as percentage of entry price
        self.min_take_profit_pct = min_take_profit_pct # Minimum take profit as percentage of entry price

    def calculate_atr(self, high, low, close, period):
        if len(close) < period:
            return np.nan
        
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Use EMA for smoothing TR to get ATR
        atr = true_range.ewm(span=period, adjust=False).mean()
        return atr

    def set_stop_loss_price(self, entry_price, direction, atr_value):
        if pd.isna(atr_value) or pd.isna(entry_price):
            return None

        # Calculate stop loss based on ATR multiplier
        stop_loss_distance = atr_value * self.stop_loss_atr_multiplier
        
        if direction == 'long':
            stop_loss = entry_price - stop_loss_distance
            # Apply minimum stop loss percentage if calculated stop is too close
            min_stop_loss_based_on_pct = entry_price * (1 - self.min_stop_loss_pct)
            stop_loss = max(stop_loss, min_stop_loss_based_on_pct)
        elif direction == 'short':
            stop_loss = entry_price + stop_loss_distance
            # Apply minimum stop loss percentage
            min_stop_loss_based_on_pct = entry_price * (1 + self.min_stop_loss_pct)
            stop_loss = min(stop_loss, min_stop_loss_based_on_pct)
        else:
            stop_loss = None
            
        return stop_loss

    def set_take_profit_price(self, entry_price, direction, atr_value):
        if pd.isna(atr_value) or pd.isna(entry_price):
            return None

        # Calculate take profit based on ATR multiplier or fixed percentage
        take_profit_distance = atr_value * self.take_profit_atr_multiplier
        
        if direction == 'long':
            take_profit = entry_price + take_profit_distance
            # Apply minimum take profit percentage
            min_take_profit_based_on_pct = entry_price * (1 + self.min_take_profit_pct)
            take_profit = max(take_profit, min_take_profit_based_on_pct)
        elif direction == 'short':
            take_profit = entry_price - take_profit_distance
            # Apply minimum take profit percentage
            min_take_profit_based_on_pct = entry_price * (1 - self.min_take_profit_pct)
            take_profit = min(take_profit, min_take_profit_based_on_pct)
        else:
            take_profit = None
            
        return take_profit

# Example usage snippet (for context within ai_trader.py):
# from risk_management import RiskManager
# 
# # Inside trader class or function:
# risk_manager = RiskManager(atr_period=14, stop_loss_atr_multiplier=1.5, take_profit_atr_multiplier=2.0)
# latest_data = data_handler.get_latest_data() # Assume this returns a DataFrame row
# atr_value = risk_manager.calculate_atr(latest_data['High'], latest_data['Low'], latest_data['Close'], risk_manager.atr_period)
# entry_price = ... # Get actual entry price
# direction = 'long' # or 'short'
# stop_loss = risk_manager.set_stop_loss_price(entry_price, direction, atr_value)
# take_profit = risk_manager.set_take_profit_price(entry_price, direction, atr_value)
# print(f"Stop Loss: {stop_loss}, Take Profit: {take_profit}")
