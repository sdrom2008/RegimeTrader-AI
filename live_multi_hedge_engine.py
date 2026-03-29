import ccxt
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

def run_multi_simulation():
    exchange = ccxt.binance()
    sim_file = "sim_multi_account.json"
    log_dir = "logs"
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f"{current_date}_multi_hedge.log")
    
    # Pairs to monitor based on Golden Pair scan
    targets = ['XRP/USDT', 'BNB/USDT', 'LINK/USDT']
    base = 'BTC/USDT'
    
    # Initialize simulation account if not exists
    if not os.path.exists(sim_file):
        # We split the $10,000 across 3 pairs (approx 3300 each)
        account = {
            "total_equity": 10000.0,
            "cash": 10000.0,
            "positions": {t: {"status": 0, "entry_base": 0.0, "entry_target": 0.0, "allocated": 0.0} for t in targets},
            "start_time": str(datetime.now())
        }
        with open(sim_file, "w") as f: json.dump(account, f)
    else:
        with open(sim_file, "r") as f: account = json.load(f)

    try:
        print("Fetching market context for multi-pair sniper...")
        # Get base asset data
        ohlcv_base = exchange.fetch_ohlcv(base, '1h', limit=100)
        df_base = pd.DataFrame(ohlcv_base, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        curr_base = df_base['c'].iloc[-1]
        
        fee_rate = 0.0004
        logs = []

        for target in targets:
            ohlcv_t = exchange.fetch_ohlcv(target, '1h', limit=100)
            df_t = pd.DataFrame(ohlcv_t, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            curr_target = df_t['c'].iloc[-1]
            
            # Calculate Ratio and Z-Score
            ratios = df_base['c'] / df_t['c']
            curr_ratio = ratios.iloc[-1]
            mean = ratios.mean()
            std = ratios.std()
            zscore = (curr_ratio - mean) / std
            
            pos = account['positions'][target]
            signal = "HOLD"
            
            # 2. Trading Logic (Threshold strictly at 2.0 to maintain win rate)
            if pos['status'] == 0:
                if zscore < -2.0:
                    # Base cheap, Target expensive
                    alloc = account['cash'] / 3 if account['cash'] > 100 else account['cash']
                    if alloc > 10: # Minimum trade size
                        pos['status'] = 1
                        pos['entry_base'] = curr_base
                        pos['entry_target'] = curr_target
                        pos['allocated'] = alloc
                        account['cash'] -= alloc
                        signal = f"OPEN_LONG_{base.split('/')[0]}_SHORT_{target.split('/')[0]}"
                elif zscore > 2.0:
                    # Base expensive, Target cheap
                    alloc = account['cash'] / 3 if account['cash'] > 100 else account['cash']
                    if alloc > 10:
                        pos['status'] = -1
                        pos['entry_base'] = curr_base
                        pos['entry_target'] = curr_target
                        pos['allocated'] = alloc
                        account['cash'] -= alloc
                        signal = f"OPEN_SHORT_{base.split('/')[0]}_LONG_{target.split('/')[0]}"
            
            elif pos['status'] == 1:
                if zscore >= 0: # Revert to mean
                    pnl_base = (curr_base / pos['entry_base']) - 1
                    pnl_target = 1 - (curr_target / pos['entry_target'])
                    profit_pct = (pnl_base + pnl_target) / 2
                    returned_cash = pos['allocated'] * (1 + profit_pct - (fee_rate * 4))
                    account['cash'] += returned_cash
                    pos['status'] = 0
                    signal = f"CLOSE_PROFIT_{profit_pct*100:.2f}%"
            
            elif pos['status'] == -1:
                if zscore <= 0: # Revert to mean
                    pnl_base = 1 - (curr_base / pos['entry_base'])
                    pnl_target = (curr_target / pos['entry_target']) - 1
                    profit_pct = (pnl_base + pnl_target) / 2
                    returned_cash = pos['allocated'] * (1 + profit_pct - (fee_rate * 4))
                    account['cash'] += returned_cash
                    pos['status'] = 0
                    signal = f"CLOSE_PROFIT_{profit_pct*100:.2f}%"
                    
            # Calculate running equity for this pair (for logging/debug)
            if pos['status'] == 0:
                current_val = 0
            else:
                p_b = (curr_base/pos['entry_base'] - 1) if pos['status'] == 1 else (1 - curr_base/pos['entry_base'])
                p_t = (1 - curr_target/pos['entry_target']) if pos['status'] == 1 else (curr_target/pos['entry_target'] - 1)
                current_val = pos['allocated'] * (1 + (p_b + p_t)/2)
                
            logs.append(f"[{target.split('/')[0]}] Z:{zscore:+.2f} Sig:{signal}")
            
        # Update total equity correctly (cash + sum of current position values)
        def position_value(p, base_price, target_price):
            if p['status'] == 0:
                return 0
            alloc = p['allocated']
            eb = p['entry_base']
            et = p['entry_target']
            if p['status'] == 1:  # LONG base, SHORT target
                pnl_base = (base_price / eb) - 1
                pnl_target = 1 - (target_price / et)
            else:  # SHORT base, LONG target (status = -1)
                pnl_base = 1 - (base_price / eb)
                pnl_target = (target_price / et) - 1
            profit_pct = (pnl_base + pnl_target) / 2
            return alloc * (1 + profit_pct)

        total_pos_value = sum(position_value(account['positions'][t], curr_base, curr_target) for t in targets)
        account['total_equity'] = account['cash'] + total_pos_value
            
        # Save state
        with open(sim_file, "w") as f: json.dump(account, f)
        
        # Log all
        log_str = f"[{datetime.now().strftime('%H:%M:%S')}] Eq:${account['total_equity']:.2f} | " + " | ".join(logs)
        with open(log_file, "a") as f: f.write(log_str + "\\n")
        print(log_str)

    except Exception as e:
        with open(log_file, "a") as f: f.write(f"Error: {str(e)}\\n")

if __name__ == "__main__":
    run_multi_simulation()
