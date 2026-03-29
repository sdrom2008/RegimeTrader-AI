import ccxt
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

def run_simulation():
    exchange = ccxt.binance()
    sim_file = "sim_account.json"
    log_file = "realtime_profits.log"
    
    # Initialize simulation account if not exists
    if not os.path.exists(sim_file):
        account = {
            "balance": 10000.0, 
            "position": 0, # 1: Long BTC/Short XRP, -1: Short BTC/Long XRP
            "entry_btc": 0.0,
            "entry_xrp": 0.0,
            "equity": 10000.0,
            "start_time": str(datetime.now())
        }
        with open(sim_file, "w") as f: json.dump(account, f)
    else:
        with open(sim_file, "r") as f: account = json.load(f)

    try:
        # 1. Fetch data for Z-Score (last 24h of 1h data)
        print("Fetching market context...")
        ohlcv_btc = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
        ohlcv_xrp = exchange.fetch_ohlcv('XRP/USDT', '1h', limit=100)
        
        df_btc = pd.DataFrame(ohlcv_btc, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df_xrp = pd.DataFrame(ohlcv_xrp, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # Calculate Ratio
        ratios = df_btc['c'] / df_xrp['c']
        curr_ratio = ratios.iloc[-1]
        mean = ratios.mean()
        std = ratios.std()
        zscore = (curr_ratio - mean) / std
        
        curr_btc = df_btc['c'].iloc[-1]
        curr_xrp = df_xrp['c'].iloc[-1]
        
        fee_rate = 0.0004 # 0.04%
        signal = "HOLD"

        # 2. Trading Logic
        if account['position'] == 0:
            if zscore < -2.0:
                # BTC cheap, Buy BTC / Sell XRP
                account['position'] = 1
                account['entry_btc'] = curr_btc
                account['entry_xrp'] = curr_xrp
                signal = "OPEN_LONG_BTC_SHORT_XRP"
            elif zscore > 2.0:
                # XRP cheap, Sell BTC / Buy XRP
                account['position'] = -1
                account['entry_btc'] = curr_btc
                account['entry_xrp'] = curr_xrp
                signal = "OPEN_SHORT_BTC_LONG_XRP"
        
        elif account['position'] == 1: # Long BTC / Short XRP
            if zscore >= 0: # Reverted to mean
                pnl_btc = (curr_btc / account['entry_btc']) - 1
                pnl_xrp = 1 - (curr_xrp / account['entry_xrp'])
                total_pnl = (pnl_btc + pnl_xrp) / 2
                account['balance'] *= (1 + total_pnl - (fee_rate * 4))
                account['position'] = 0
                signal = f"CLOSE_POSITION_PROFIT_{total_pnl*100:.2f}%"
        
        elif account['position'] == -1: # Short BTC / Long XRP
            if zscore <= 0: # Reverted to mean
                pnl_btc = 1 - (curr_btc / account['entry_btc'])
                pnl_xrp = (curr_xrp / account['entry_xrp']) - 1
                total_pnl = (pnl_btc + pnl_xrp) / 2
                account['balance'] *= (1 + total_pnl - (fee_rate * 4))
                account['position'] = 0
                signal = f"CLOSE_POSITION_PROFIT_{total_pnl*100:.2f}%"

        # Calculate Equity
        if account['position'] == 0:
            account['equity'] = account['balance']
        else:
            p_btc = (curr_btc/account['entry_btc'] - 1) if account['position'] == 1 else (1 - curr_btc/account['entry_btc'])
            p_xrp = (1 - curr_xrp/account['entry_xrp']) if account['position'] == 1 else (curr_xrp/account['entry_xrp'] - 1)
            account['equity'] = account['balance'] * (1 + (p_btc + p_xrp)/2)

        # Save state
        with open(sim_file, "w") as f: json.dump(account, f)
        
        # Log
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now()}] Z:{zscore:.2f} Ratio:{curr_ratio:.2f} Equity:{account['equity']:.2f} Signal:{signal}\n")
            
        print(f"Update Complete. Z-Score: {zscore:.2f}, Signal: {signal}")

    except Exception as e:
        with open(log_file, "a") as f: f.write(f"Error: {str(e)}\n")

if __name__ == "__main__":
    run_simulation()
