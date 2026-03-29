#!/usr/bin/env python3

import backtrader as bt

class RegimeTradingStrategy(bt.Strategy):
    params = (
        ('ema_short_period', 10),
        ('ema_long_period', 20),
        ('ema_very_long_period', 50),
        ('ema_super_long_period', 100),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('adx_period', 14),
        ('atr_period', 14),
        # Risk management parameters
        ('stop_loss_pct', 0.02),  # 2% stop loss
        ('take_profit_pct', 0.05), # 5% take profit
        ('initial_cash', 100000.0),
        ('position_size', 0.95), # Use 95% of available cash for each trade
    )

    def __init__(self):
        # Technical Indicators
        self.ema_short = bt.indicators.EMA(period=self.p.ema_short_period)
        self.ema_long = bt.indicators.EMA(period=self.p.ema_long_period)
        self.ema_very_long = bt.indicators.EMA(period=self.p.ema_very_long)
        self.ema_super_long = bt.indicators.EMA(period=self.p.ema_super_long)
        self.macd = bt.indicators.MACD( 
            fastperiod=self.p.macd_fast,
            slowperiod=self.p.macd_slow,
            signalperiod=self.p.macd_signal
        )
        self.adx = bt.indicators.ADX(period=self.p.adx_period)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)

        # Market state identification (placeholder)
        self.market_state = ""

        # AI decision placeholder
        self.ai_decision = None

        # Order tracking
        self.order = None
        self.stop_price = None
        self.take_profit_price = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # Set stop loss and take profit prices
                self.stop_price = order.executed.price * (1 - self.p.stop_loss_pct)
                self.take_profit_price = order.executed.price * (1 + self.p.take_profit_pct)

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            
            self.bar_executed = len(self) # Track the bar number when the order was executed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            # Reset stop/take profit prices if order is not completed
            self.stop_price = None
            self.take_profit_price = None

        # Write down: reset the order
        self.order = None

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def next(self):
        self.log(f'Close: {self.data.close[0]:.2f}')

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Get current market state (placeholder - needs implementation)
        self.identify_market_state()

        # Get AI decision (placeholder - needs implementation)
        self.get_ai_decision()

        # --- Trading Logic ---
        if not self.position:  # If not in a position
            # Entry conditions (example using EMAs and ADX)
            if (
                self.ema_short[0] > self.ema_long[0] 
                and self.ema_long[0] > self.ema_very_long[0] 
                and self.ema_very_long[0] > self.ema_super_long[0] 
                and self.adx[0] > 25 # Example ADX threshold for strong trend
            ):
                # Buy signal
                self.log('BUY CREATE')
                # Calculate order size based on position size and available cash
                cash = self.broker.get_cash()
                size = cash * self.p.position_size / self.data.close[0]
                self.order = self.buy(size=size)
        else:
            # Exit conditions
            if (
                self.data.close[0] < self.stop_price or 
                self.data.close[0] > self.take_profit_price
            ):
                # Sell signal (stop loss or take profit hit)
                self.log('SELL CREATE')
                self.order = self.sell()

    def identify_market_state(self):
        ''' Placeholder for market state identification logic '''
        # Example: Determine if market is trending, ranging, etc.
        # This would use indicators like ADX, Bollinger Bands, etc.
        adx_val = self.adx[0]
        if adx_val > 30: # Example threshold for strong trend
            self.market_state = "trending"
        elif adx_val < 20: # Example threshold for ranging market
            self.market_state = "ranging"
        else:
            self.market_state = "transitional"
        self.log(f"Market State: {self.market_state} (ADX: {adx_val:.2f})")

    def get_ai_decision(self):
        ''' Placeholder for AI decision logic '''
        # This function would interface with an AI model to get a trading decision.
        # For now, it's a dummy implementation.
        self.ai_decision = "HOLD" # Default to HOLD
        # Example: if self.market_state == "trending" and some_ai_condition:
        #    self.ai_decision = "BUY"
        # elif self.market_state == "ranging" and some_other_ai_condition:
        #    self.ai_decision = "SELL"
        self.log(f"AI Decision: {self.ai_decision}")

    def stop(self):
        self.log(f'(simulation end) Ending Value {self.broker.getvalue():.2f}')

if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(RegimeTradingStrategy)

    # Create a Data Feed
    # In a real scenario, you would load data from your data_manager.py script
    # For this example, we'll use dummy data.
    data_path = 'dummy_data.csv' # Replace with your actual data path
    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        fromdate=datetime(2023, 1, 1),
        todate=datetime(2023, 12, 31),
        nullvalue=0.0,
        dtformat=('%Y-%m-%d %H:%M:%S'),
        datetime=0, open=1, high=2, low=3, close=4, volume=5, openinterest=-1
    )

    # Add the data feed
    cerebro.adddata(data)

    # Broker settings
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001) # 0.1% commission

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.Drawdown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run the backtest
    results = cerebro.runtext(withstats=True, stdstats=False)

    print('\n--- Backtest Results ---')
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Print analyzers results
    strat = results[0] # Get the first strategy instance
    print('Sharpe Ratio:', strat.analyzers.sharpe_ratio.get_analysis()['sharperatio'])
    print('Max Drawdown:', strat.analyzers.drawdown.get_analysis()['max']['drawdown'])
    print('Total Trades:', strat.analyzers.trade_analyzer.get_analysis()['total']['total'])
    print('Profit Trades:', strat.analyzers.trade_analyzer.get_analysis()['total']['won']['total'])
    print('Loss Trades:', strat.analyzers.trade_analyzer.get_analysis()['total']['lost']['total'])

    # Plot the results (optional)
    # cerebro.plottext()
