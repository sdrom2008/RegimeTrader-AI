import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os

def label_data(df, look_forward_candles=24, atr_multiplier=3):
    """
    Labels the data based on future price movement.
    If future price movement > (ATR * multiplier), it's a trend. Otherwise, a range.
    
    Args:
        df (pd.DataFrame): DataFrame with features, must include 'High', 'Low', 'ATRr_14'.
        look_forward_candles (int): How many candles to look into the future.
        atr_multiplier (float): The multiplier for ATR to define a significant move.
        
    Returns:
        pd.DataFrame: DataFrame with a new 'regime' column.
    """
    print(f"[*] Labeling data... Looking forward {look_forward_candles} candles, ATR multiplier: {atr_multiplier}")
    
    # Calculate future price range
    future_high = df['High'].shift(-look_forward_candles).rolling(window=look_forward_candles).max()
    future_low = df['Low'].shift(-look_forward_candles).rolling(window=look_forward_candles).min()
    future_price_range = future_high - future_low
    
    # Define the threshold for a trend
    trend_threshold = df['ATRr_14'] * atr_multiplier
    
    # Create the label: 1 for Trend, 0 for Range
    # A trend is identified if the future price range exceeds our threshold
    df['regime'] = np.where(future_price_range > trend_threshold, 1, 0)
    
    # Drop the last 'look_forward_candles' rows as they have no future to evaluate
    df.dropna(subset=['regime'], inplace=True)
    
    print("[+] Labeling complete.")
    print(df['regime'].value_counts(normalize=True))
    
    return df

def train_model(features_file='data/BTC_USDT_1h_2y_features.csv'):
    """
    Trains a RandomForestClassifier to predict the market regime.
    """
    if not os.path.exists(features_file):
        print(f"[!] Features file not found: {features_file}")
        return

    # 1. Load data and label it
    df = pd.read_csv(features_file, index_col='timestamp', parse_dates=True)
    df_labeled = label_data(df)
    
    # 2. Define features (X) and target (y)
    # We exclude price data and other potential data leaks from the features
    features = [col for col in df_labeled.columns if 'ADX' in col or 'DMP' in col or 'DMN' in col or 'BB' in col or 'ATR' in col or 'RSI' in col or 'EMA' in col or 'DIST' in col]
    X = df_labeled[features]
    y = df_labeled['regime']
    
    print(f"[*] Using {len(features)} features for training.")

    # 3. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"[*] Data split: {len(X_train)} training samples, {len(X_test)} testing samples.")

    # 4. Train the model
    print("[*] Training the RandomForestClassifier model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1, class_weight='balanced')
    model.fit(X_train, y_train)
    print("[+] Model training complete.")

    # 5. Evaluate the model
    print("[*] Evaluating model performance...")
    y_pred = model.predict(X_test)
    
    print("\n--- Model Evaluation Report ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(classification_report(y_test, y_pred, target_names=['Range (0)', 'Trend (1)']))
    print("---------------------------------")

    # 6. Save the model
    model_filename = 'regime_model.pkl'
    print(f"[*] Saving trained model to {model_filename}...")
    with open(model_filename, 'wb') as f:
        pickle.dump(model, f)
    print(f"[+] Model saved successfully!")

if __name__ == '__main__':
    train_model()
