# ai_trader.py

import pandas as pd
import numpy as np

# Import necessary modules
from market_state_logic import MarketStateAnalyzer
from risk_management import RiskManager
from position_sizing import PositionSizer
from sentiment_handler import MacroSentimentHandler
# from data_handler import load_ohlcv_data # Placeholder for data loading

class RegimeTraderAI:
    def __init__(self, data_path='data/binance_data.csv', config_path='config/ai_config.json'):
        # Load configuration
        # self.config = self.load_config(config_path)
        
        # Initialize components
        self.market_analyzer = MarketStateAnalyzer(
            ema_short_period=12, ema_long_period=26, adx_period=14, atr_period=14
        )
        self.risk_manager = RiskManager(
            atr_period=14, stop_loss_atr_multiplier=1.5, take_profit_atr_multiplier=2.0, 
            min_stop_loss_pct=0.01, min_take_profit_pct=0.01
        )
        self.position_sizer = PositionSizer(
            base_position_pct=0.05, min_dynamic_pct=0.03, max_dynamic_pct=0.08, max_total_risk_pct=0.20, atr_period=14
        )
        self.sentiment_handler = MacroSentimentHandler()
        self.sentiment_handler.load_data() # Load F&G history
        
        self.account_capital = 100000 # Example initial capital
        self.data_path = data_path
        self.data = None
        self.current_position = None # Track current open positions
        self.last_trade_signal = "HOLD"

    def load_config(self, config_path):
        # Placeholder for loading configuration from a JSON file
        try:
            import json
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at {config_path}. Using default settings.")
            return {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {config_path}. Using default settings.")
            return {}

    def load_market_data(self):
        # Load historical or real-time market data
        # For now, assume data is loaded into self.data as a pandas DataFrame
        # with OHLCV columns and necessary indicator columns.
        # Example placeholder: simulate data loading
        print(f"Loading market data from {self.data_path}...")
        try:
            # In a real scenario, this would load from CSV or a live feed.
            # For demonstration, we'll create dummy data if file not found.
            try:
                self.data = pd.read_csv(self.data_path)
            except FileNotFoundError:
                print(f"Data file not found: {self.data_path}. Creating dummy data.")
                # Dummy data for demonstration if file doesn't exist
                dummy_data_dict = {
                    'Date': pd.to_datetime(pd.date_range(start='2023-01-01', periods=200, freq='D')),
                    'Open': np.random.rand(200) * 100 + 100,
                    'High': np.random.rand(200) * 100 + 100 + 5,
                    'Low': np.random.rand(200) * 100 + 100 - 5,
                    'Close': np.random.rand(200) * 100 + 100,
                    'Volume': np.random.rand(200) * 10000
                }
                self.data = pd.DataFrame(dummy_data_dict)
                # Save dummy data to a file if it was created, for future runs
                self.data.to_csv(self.data_path, index=False)

            # Ensure necessary indicators are calculated if not in the loaded data
            # This is a simplified approach; ideally, indicators are calculated once and stored.
            self.market_analyzer.analyze(self.data)

            self.data['EMA_200'] = self.data['Close'].ewm(span=200, adjust=False).mean()
            
            # Calculate RSI and Volume SMA for advanced filtering
            delta = self.data['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            self.data['RSI'] = 100 - (100 / (1 + rs))
            self.data['Volume_SMA'] = self.data['Volume'].rolling(window=20).mean()
        
        except Exception as e:
            import traceback; traceback.print_exc(); print(f"Error loading or processing market data: {e}")
            self.data = None

    def generate_trading_signal(self, current_data, verbose=True):
        if current_data is None or current_data.empty:
            if verbose: print("No market data available. Cannot generate signal.")
            return None, None, None, None, None

        # Get the latest available data row
        latest_data_row = current_data.iloc[-1]
        
        # 1. Analyze Market State
        market_state, confidence_score = self.market_analyzer.analyze(current_data)
        if verbose: print(f"Market State Analysis: {market_state}, Confidence: {confidence_score:.2f}")

        # 2. Get Risk Parameters (using latest available ATR)
        atr_value = latest_data_row['ATR']
        entry_price = latest_data_row['Close'] # Using latest close as a proxy for entry price

        # 3. Determine Stop Loss and Take Profit Prices
        # Placeholder for actual entry direction (e.g., based on previous signal or predefined)
        # For demonstration, assume we are evaluating for a 'long' position.
        direction = 'long' # Defaulting to long for calculation example
        
        stop_loss_price = self.risk_manager.set_stop_loss_price(entry_price, direction, atr_value)
        take_profit_price = self.risk_manager.set_take_profit_price(entry_price, direction, atr_value)
        
        if verbose: print(f"Entry Price: {entry_price}, Stop Loss: {stop_loss_price}, Take Profit: {take_profit_price}")

        # 4. Determine Position Size
        # This is a critical step. We need to decide when to enter a trade.
        # Filter: Only buy if price is above 200 EMA (Long-term trend alignment)
        ema_200 = latest_data_row.get('EMA_200', 0)
        is_above_200ema = entry_price > ema_200 if ema_200 > 0 else True
        
        # Tech Filters: Volume & RSI
        rsi = latest_data_row.get('RSI', 50)
        vol = latest_data_row.get('Volume', 0)
        vol_sma = latest_data_row.get('Volume_SMA', 0)
        macd_hist = latest_data_row.get('MACD_hist', 0)
        
        has_volume_support = vol > (vol_sma * 0.8) if vol_sma > 0 else True
        is_overbought = rsi > 85
        is_oversold = rsi < 30
        
        # Simple MACD momentum filter
        has_macd_momentum = macd_hist > 0
        
        # 5. Get Sentiment Data
        fng_score, fng_label = self.sentiment_handler.get_sentiment_for_date(latest_data_row['Date'])
        if verbose: print(f"Sentiment Index: {fng_score} ({fng_label})")

        # Basic F&G Filters: Don't buy if Extreme Greed (too risky, local top)
        # Avoid shorting in Extreme Fear (local bottom)
        
        # Simple entry condition: Strong uptrend with high confidence AND macro trend alignment
        if market_state in ["Uptrend", "Volatile Uptrend"] and confidence_score > 0.7:
            if not is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Uptrend, but below 200 EMA (Macro Downtrend).")
                return "HOLD", 0, None, None
                
            if not has_volume_support:
                if verbose: print(f"Signal Filtered: Uptrend breakout lacks volume support (Vol: {vol:.0f} vs SMA: {vol_sma:.0f}).")
                return "HOLD", 0, None, None
                
            if is_overbought:
                if verbose: print(f"Signal Filtered: Uptrend but market is overbought (RSI={rsi:.1f}). Waiting for pullback.")
                return "HOLD", 0, None, None
            
            # F&G Filter: Refuse to Buy if everyone is extremely greedy
            if fng_score >= 90: # Only block if it's INSANELY greedy (e.g., > 90)
                if verbose: print(f"Signal Filtered: Market is in Uptrend but sentiment is overheated (F&G={fng_score}). Waiting for cool-off.")
                return "HOLD", 0, None, None
                
            position_size_pct = self.position_sizer.determine_position_size(
                self.account_capital, entry_price, stop_loss_price, confidence_score, atr_value
            )
            
            # Translate percentage to actual trade details (e.g., number of units)
            # This part requires knowing the available capital and order execution mechanism.
            # For now, we return the percentage.
            if verbose: print(f"Signal: BUY. Position Size: {position_size_pct:.2%}")
            return "BUY", position_size_pct, stop_loss_price, take_profit_price
        elif market_state in ["Downtrend", "Volatile Downtrend"] and confidence_score > 0.7:
            if is_above_200ema:
                if verbose: print("Signal Filtered: Market is in short-term Downtrend, but above 200 EMA (Macro Uptrend).")
                return "HOLD", 0, None, None
                
            if fng_score < 20:
                if verbose: print(f"Signal Filtered: Downtrend but Extreme Fear (F&G={fng_score}). High risk of short squeeze.")
                return "HOLD", 0, None, None
            
            position_size_pct = self.position_sizer.determine_position_size(
                self.account_capital, entry_price, stop_loss_price, confidence_score, atr_value
            )
            # For short selling, position sizing logic might need adjustment or negative units.
            # For simplicity, we'll just use the same percentage for now.
            if verbose: print(f"Signal: SELL. Position Size: {position_size_pct:.2%}")
            return "SELL", position_size_pct, stop_loss_price, take_profit_price
            

                
        else:
            if verbose: print("Signal: HOLD. Market conditions not suitable for new trades.")
            return "HOLD", 0, None, None

    def run_backtesting(self):
        # This would be the main loop for backtesting the strategy
        print("Starting backtesting...")
        self.load_market_data()
        
        if self.data is None or len(self.data) < self.market_analyzer.adx_period + self.market_analyzer.ema_long_period: # Ensure enough data for indicators
            print("Not enough data to perform analysis.")
            return

        fee_rate = 0.001      # 0.1% Binance spot fee
        slippage_rate = 0.0005 # 0.05% slippage
        self.trade_history = []
        
        print(f"Initial Capital: ${self.account_capital:.2f}")
        print("-" * 50)

        # Process data day by day or candle by candle
        for i in range(len(self.data)):
            current_data_chunk = self.data.iloc[:i+1] # Provide data up to the current point
            latest_row = current_data_chunk.iloc[-1]
            date = latest_row['Date']
            current_close = latest_row['Close']
            current_high = latest_row['High']
            current_low = latest_row['Low']
            
            # 1. Manage existing positions (Exit logic)
            if self.current_position is not None:
                pos = self.current_position
                exit_price = None
                exit_reason = ""
                
                # Check for Stop Loss or Take Profit hit during this period
                if pos['type'] == 'BUY':
                    # Trailing Stop Logic
                    if current_high > pos.get('highest_seen', pos['entry_price']):
                        pos['highest_seen'] = current_high
                        # If price moved up by 1 ATR, move SL to breakeven + fee cover
                        breakeven_price = pos['entry_price'] * (1 + fee_rate * 2)
                        if current_high > pos['entry_price'] + latest_row['ATR']:
                            if pos['sl'] < breakeven_price:
                                pos['sl'] = breakeven_price
                        
                        # Trail by 1.5 ATR from highest peak
                        trail_sl = pos['highest_seen'] - (latest_row['ATR'] * 1.5)
                        if trail_sl > pos['sl']:
                            pos['sl'] = trail_sl

                    if current_low <= pos['sl']:
                        exit_price = pos['sl'] * (1 - slippage_rate)
                        exit_reason = "Hit SL (Trailing)" if 'highest_seen' in pos else "Hit SL"
                    elif current_high >= pos['tp']:
                        exit_price = pos['tp'] # Assuming limit order, no slippage on TP
                        exit_reason = "Hit TP"
                elif pos['type'] == 'SELL':
                    # Trailing Stop Logic (Short)
                    if current_low < pos.get('lowest_seen', pos['entry_price']):
                        pos['lowest_seen'] = current_low
                        breakeven_price = pos['entry_price'] * (1 - fee_rate * 2)
                        if current_low < pos['entry_price'] - latest_row['ATR']:
                            if pos['sl'] > breakeven_price:
                                pos['sl'] = breakeven_price
                                
                        trail_sl = pos['lowest_seen'] + (latest_row['ATR'] * 1.5)
                        if trail_sl < pos['sl']:
                            pos['sl'] = trail_sl

                    if current_high >= pos['sl']:
                        exit_price = pos['sl'] * (1 + slippage_rate)
                        exit_reason = "Hit SL (Trailing)" if 'lowest_seen' in pos else "Hit SL"
                    elif current_low <= pos['tp']:
                        exit_price = pos['tp']
                        exit_reason = "Hit TP"
                        
                if exit_price is not None:
                    exit_value = exit_price * pos['units']
                    exit_fee = exit_value * fee_rate
                    
                    if pos['type'] == 'BUY':
                        gross_pnl = (exit_price - pos['entry_price']) * pos['units']
                    else:
                        gross_pnl = (pos['entry_price'] - exit_price) * pos['units']
                        
                    net_pnl = gross_pnl - pos['entry_fee'] - exit_fee
                    
                    # Return invested capital back to account, plus/minus net PnL
                    self.account_capital += (pos['invested_capital'] + net_pnl)
                    
                    self.trade_history.append({
                        'entry_date': pos['date'],
                        'exit_date': date,
                        'type': pos['type'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'net_pnl': net_pnl,
                        'capital_after': self.account_capital
                    })
                    print(f"[{date}] EXIT {pos['type']} @ {exit_price:.2f} ({exit_reason}) | Net PnL: ${net_pnl:.2f} | Capital: ${self.account_capital:.2f}")
                    self.current_position = None
                    continue # Skip entry logic on the same bar we exit, keep it simple

            # Analyze market state for the latest point
            market_state, confidence_score = self.market_analyzer.analyze(current_data_chunk)
            
            if market_state == "Insufficient Data":
                continue

            # 2. Check for New Entries
            if self.current_position is None:
                # Generate trading signal silently
                signal, position_size_pct, sl_price, tp_price = self.generate_trading_signal(current_data_chunk, verbose=True)

                if signal in ["BUY", "SELL"] and position_size_pct > 0:
                    target_investment = self.account_capital * position_size_pct
                    
                    if signal == "BUY":
                        entry_price = current_close * (1 + slippage_rate)
                    else:
                        entry_price = current_close * (1 - slippage_rate)
                        
                    units = target_investment / entry_price
                    entry_fee = target_investment * fee_rate
                    
                    # Deduct invested amount and fee from available capital
                    self.account_capital -= (target_investment + entry_fee)
                    
                    self.current_position = {
                        'date': date,
                        'type': signal,
                        'entry_price': entry_price,
                        'units': units,
                        'invested_capital': target_investment,
                        'entry_fee': entry_fee,
                        'sl': sl_price,
                        'tp': tp_price
                    }
                    print(f"[{date}] ENTRY {signal} @ {entry_price:.2f} | Risk Size: {position_size_pct:.1%} | SL: {sl_price:.2f} | TP: {tp_price:.2f}")

        # Final Report
        print("-" * 50)
        print("Backtesting Finished.")
        print(f"Final Capital (Liquid): ${self.account_capital:.2f}")
        
        if self.current_position is not None:
            pos = self.current_position
            current_close = self.data.iloc[-1]['Close']
            if pos['type'] == 'BUY':
                unrealized_pnl = (current_close - pos['entry_price']) * pos['units']
            else:
                unrealized_pnl = (pos['entry_price'] - current_close) * pos['units']
            print(f"Open Position: {pos['type']} (Unrealized PnL: ${unrealized_pnl:.2f})")
            print(f"Total Equity: ${self.account_capital + pos['invested_capital'] + unrealized_pnl:.2f}")
        else:
            print(f"Total Equity: ${self.account_capital:.2f}")
        
        trades_df = pd.DataFrame(self.trade_history)
        if not trades_df.empty:
            win_rate = len(trades_df[trades_df['net_pnl'] > 0]) / len(trades_df)
            total_net_pnl = trades_df['net_pnl'].sum()
            print(f"Total Trades: {len(trades_df)}")
            print(f"Win Rate: {win_rate:.2%}")
            print(f"Total Net PnL (Closed Trades): ${total_net_pnl:.2f}")
        else:
            print("No trades executed.")


# --- Main execution block for running the trader ---
# This is for demonstration and testing purposes.
# In a real application, this would be part of a larger framework.
if __name__ == "__main__":
    trader = RegimeTraderAI()
    # This will run a simple backtest using dummy data if no file is found
    trader.run_backtesting()
