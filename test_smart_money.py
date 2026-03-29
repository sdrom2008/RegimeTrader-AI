import urllib.request
import json

def get_binance_ls_ratio(symbol="BTCUSDT", period="1d", limit=1):
    url_accounts = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    url_positions = f"https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={symbol}&period={period}&limit={limit}"
    url_global = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"

    result = {}
    try:
        def fetch_json(url):
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))

        acc_resp = fetch_json(url_accounts)
        pos_resp = fetch_json(url_positions)
        global_resp = fetch_json(url_global)
        
        if acc_resp and isinstance(acc_resp, list):
            latest_acc = acc_resp[-1]
            result['top_account_ls_ratio'] = float(latest_acc['longShortRatio'])
            
        if pos_resp and isinstance(pos_resp, list):
            latest_pos = pos_resp[-1]
            result['top_position_ls_ratio'] = float(latest_pos['longShortRatio'])
            
        if global_resp and isinstance(global_resp, list):
            latest_global = global_resp[-1]
            result['global_ls_ratio'] = float(latest_global['longShortRatio'])

        return result
    except Exception as e:
        print(f"Error fetching smart money data: {e}")
        return None

if __name__ == "__main__":
    print(get_binance_ls_ratio())
