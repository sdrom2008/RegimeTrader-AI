import pandas as pd
import pandas_ta as ta
import os

def generate_features(input_file='data/BTC_USDT_1h_2y.csv'):
    """
    Reads historical data and enriches it with technical indicators (features).
    """
    if not os.path.exists(input_file):
        print(f"[!] Input file not found: {input_file}")
        return None

    print(f"[*] Reading data from {input_file}...")
    df = pd.read_csv(input_file, index_col='timestamp', parse_dates=True)

    print("[*] Calculating technical indicators (features)...")
    
    # Calculate a set of indicators using pandas_ta
    # These will be our features for the ML model
    df.ta.adx(length=14, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)

    # Print column names for debugging, in case of naming changes in the library
    print("[*] Generated columns:", df.columns.tolist())

    # --- Create custom features that might be useful for regime detection ---
    
    # 1. Bollinger Band Width (normalized)
    # A narrow band width suggests a consolidating/ranging market
    # Note: Column names are case-sensitive and library-dependent. Using correct names found via debugging.
    df['BB_WIDTH'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0']
    
    # 2. RSI Standard Deviation
    # A low standard deviation in RSI suggests it's oscillating in a tight range
    df['RSI_STD_20'] = df['RSI_14'].rolling(window=20).std()
    
    # 3. Price distance from a long-term moving average (normalized)
    # Large distance suggests a strong trend
    df['PRICE_EMA200_DIST'] = (df['Close'] - df['EMA_200']) / df['EMA_200']
    
    print("[*] Cleaning up data (dropping NaN values)...")
    # Drop rows with NaN values resulting from indicator calculations
    df.dropna(inplace=True)
    
    # Define output filename
    output_file = input_file.replace('.csv', '_features.csv')
    
    print(f"[+] Saving features to {output_file}...")
    df.to_csv(output_file)
    
    print(f"[*] Feature generation complete. Final dataset has {len(df)} rows.")
    return output_file

if __name__ == '__main__':
    # Ensure the pandas_ta library is installed
    try:
        import pandas_ta
    except ImportError:
        print("[!] pandas_ta is not installed. Please install it using: pip install pandas_ta")
        exit()
        
    generate_features()
