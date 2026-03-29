import pandas as pd
import json
import urllib.request
import os
import datetime

class MacroSentimentHandler:
    def __init__(self, data_path='data/fng_data.csv'):
        self.data_path = data_path
        self.fng_data = None
        
    def fetch_historical_fng(self):
        """Fetches historical Fear & Greed Index from alternative.me"""
        print("Fetching historical Crypto Fear & Greed Index...")
        url = "https://api.alternative.me/fng/?limit=0" # limit=0 gets all historical data
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))['data']
                    df = pd.DataFrame(data)
                    # Convert timestamp to datetime
                    df['timestamp'] = df['timestamp'].astype(int)
                    df['Date'] = pd.to_datetime(df['timestamp'], unit='s').dt.normalize()
                    df['fng_value'] = df['value'].astype(int)
                    df['fng_classification'] = df['value_classification']
                    
                    # Select relevant columns and sort by date ascending
                    df = df[['Date', 'fng_value', 'fng_classification']].sort_values('Date').reset_index(drop=True)
                    
                    # Save to CSV
                    os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
                    df.to_csv(self.data_path, index=False)
                    self.fng_data = df
                    print(f"Successfully saved {len(df)} days of Fear & Greed data to {self.data_path}")
                else:
                    print(f"Failed to fetch data. Status code: {response.status}")
        except Exception as e:
            print(f"Error fetching sentiment data: {e}")

    def load_data(self):
        """Loads F&G data from CSV"""
        if os.path.exists(self.data_path):
            self.fng_data = pd.read_csv(self.data_path)
            self.fng_data['Date'] = pd.to_datetime(self.fng_data['Date'])
            return True
        return False

    def get_sentiment_for_date(self, target_date):
        """Returns the F&G value and classification for a specific date."""
        if self.fng_data is None:
            if not self.load_data():
                return 50, "Neutral" # Default if no data
                
        # Find the row for the target date
        # Note: target_date should be a pandas Timestamp normalized to midnight
        row = self.fng_data[self.fng_data['Date'] == pd.to_datetime(target_date).normalize()]
        if not row.empty:
            return row.iloc[0]['fng_value'], row.iloc[0]['fng_classification']
        else:
            # If exact date not found, return a neutral default or fill forward (simplified here)
            return 50, "Neutral"

if __name__ == "__main__":
    handler = MacroSentimentHandler()
    handler.fetch_historical_fng()
