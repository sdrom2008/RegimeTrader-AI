import backtrader as bt
import pandas as pd
import os

# Define a basic strategy
class BasicStrategy(bt.Strategy):
    params = (
        ('maperiod', 15),
    )

    def __init__(self):
        # Keep track of the closing price in the parameters
        self.dataclose = self.datas[0].close

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        # If not in the market and not yet passed the moving average
        if not self.position:
            if self.dataclose[0] > self.sma[0]:
                # Buy signal
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()

        else:
            # Already in the market
            if self.dataclose[0] < self.sma[0]:
                # Sell signal
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

def run_backtest(csv_path, strategy_class, strategy_params=None):
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(strategy_class, **(strategy_params or {}))

    # Create a Data Feed
    data_feed = bt.feeds.GenericCSVData(
        dataname=csv_path,
        fromdate=pd.Timestamp('2023-01-01', tz='UTC'), # Example date, adjust as needed
        todate=pd.Timestamp('2024-01-01', tz='UTC'),   # Example date, adjust as needed
        dtformat='%Y-%m-%dT%H:%M:%S.%fZ', # Adjust format if necessary, Binance might not have milliseconds for 1h data
        datetime=0, # Assuming Open time is the first column (index 0)
        open=1,     # Open price is the second column (index 1)
        high=2,     # High price is the third column (index 2)
        low=3,      # Low price is the fourth column (index 3)
        close=4,    # Close price is the fifth column (index 4)
        volume=5,   # Volume is the sixth column (index 5)
        openinterest=-1 # No open interest in kline data
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data_feed)

    # Set our portfolio cash
    cerebro.broker.setcash(100000.0)

    # Add a FixedSize Sizer (buy/sell fixed size)
    cerebro.addsizer(bt.sizers.FixedSize, stake=10) # Example stake size

    # Set commission
    cerebro.broker.setcommission(commission=0.001) # Example commission

    # Run the backtest
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

if __name__ == '__main__':
    print("--- Backtrader Basic Backtest ---")

    # Ensure the data directory and CSV files exist
    if not os.path.exists("data/csv"):
        print("Error: CSV data directory not found. Please run the data processing script first.")
        exit(1)

    # Backtest BTC/USDT data
    btc_csv_path = "data/csv/BTCUSDT_1h.csv"
    if os.path.exists(btc_csv_path):
        print(f"\nRunning backtest for {btc_csv_path}...")
        run_backtest(btc_csv_path, BasicStrategy, strategy_params={'maperiod': 20})
    else:
        print(f"Error: BTC CSV file not found at {btc_csv_path}")

    # Backtest ETH/USDT data (optional, can be added if needed)
    # eth_csv_path = "data/csv/ETHUSDT_1h.csv"
    # if os.path.exists(eth_csv_path):
    #     print(f"\nRunning backtest for {eth_csv_path}...")
    #     run_backtest(eth_csv_path, BasicStrategy, strategy_params={'maperiod': 20})
    # else:
    #     print(f"Error: ETH CSV file not found at {eth_csv_path}")

    print("\nBacktest completed.")
