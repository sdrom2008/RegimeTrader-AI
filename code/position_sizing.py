# position_sizing.py

import pandas as pd
import numpy as np

class PositionSizer:
    def __init__(self, base_position_pct=0.05, min_dynamic_pct=0.03, max_dynamic_pct=0.08, max_total_risk_pct=0.20, atr_period=14):
        self.base_position_pct = base_position_pct  # Base position size as a percentage of capital, e.g., 5%
        self.min_dynamic_pct = min_dynamic_pct    # Minimum dynamic position size percentage
        self.max_dynamic_pct = max_dynamic_pct    # Maximum dynamic position size percentage
        self.max_total_risk_pct = max_total_risk_pct # Maximum total risk exposure as a percentage of capital
        self.atr_period = atr_period

    def calculate_atr(self, high, low, close, period):
        # Ensure data series are of sufficient length for calculation
        if len(close) < period:
            return np.nan
        
        # Calculate True Range (TR)
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Use EMA for smoothing TR to get ATR. EMA is common for ATR calculation.
        atr = true_range.ewm(span=period, adjust=False).mean()
        return atr

    def determine_position_size(self, account_capital, entry_price, stop_loss_price, confidence_score, market_volatility):
        # Determine position size based on risk per trade and confidence/volatility
        
        # 1. Calculate risk per trade in terms of price points
        if stop_loss_price is None or entry_price is None:
            return 0 # Cannot calculate risk without valid prices
            
        risk_per_trade_points = abs(entry_price - stop_loss_price)
        if risk_per_trade_points == 0:
            return 0 # Avoid division by zero if stop loss is at entry price
        
        # 2. Determine capital to risk for this trade, influenced by confidence
        # Higher confidence allows for potentially higher risk capital, up to max_total_risk_pct.
        # Assuming confidence_score is normalized between 0 and 1.
        
        # Scale base risk capital by confidence score. Higher confidence means we can risk more.
        # This is a simplification; actual methods can be more complex.
        capital_to_risk = (self.base_position_pct * account_capital) * confidence_score 
        
        # Ensure this trade's risk doesn't exceed the overall max risk percentage of the account
        capital_to_risk = min(capital_to_risk, self.max_total_risk_pct * account_capital)

        # 3. Calculate number of units based on capital to risk and risk per trade points
        # Units = Capital to Risk / Risk Per Trade Points
        num_units = capital_to_risk / risk_per_trade_points
        
        # 4. Apply volatility adjustment to position size (simplified)
        # High volatility generally implies smaller position sizes to manage risk.
        # Lower volatility might allow for larger positions (within dynamic caps).
        # This is a crucial part that needs careful tuning and testing.
        # Example: Reduce position if market_volatility (ATR) is high.
        if market_volatility > 0:
            # Inverse relationship: higher volatility -> lower position size multiplier
            # We need to normalize market_volatility relative to some baseline or average.
            # For demonstration, let's assume market_volatility is a relevant value.
            # A simple heuristic: if ATR is high, reduce position size.
            # We can use a factor based on ATR relative to price or a benchmark.
            # Example: if ATR is > X% of price, reduce position by Y%.
            # For now, let's use a direct inverse relationship, capped to avoid extreme values.
            volatility_factor = max(0.5, 1.0 / (market_volatility + 1)) # Capped at 0.5 for very high volatility
            num_units *= volatility_factor

        # 5. Apply min/max caps to the calculated position size (as a percentage of capital, for reporting)
        # First, convert num_units back to a percentage of capital.
        if entry_price > 0:
            calculated_position_pct = (num_units * entry_price) / account_capital
        else:
            calculated_position_pct = 0
        
        # Apply the dynamic percentage caps
        final_position_pct = max(self.min_dynamic_pct, min(self.max_dynamic_pct, calculated_position_pct))
        
        # Final check to ensure we don't exceed total risk (though previous steps should manage this)
        final_position_pct = min(final_position_pct, self.max_total_risk_pct)

        return final_position_pct # Returning as percentage of capital for simplicity

# --- Example usage (would be called from ai_trader.py) ---
# This section is for standalone testing and demonstration.
# It will not be executed when this module is imported into ai_trader.py.
# if __name__ == "__main__":
#     # Dummy data and values for demonstration
#     account_capital = 100000
#     entry_price = 100
#     stop_loss_price = 98 # Risk per trade in points = 2
#     confidence_score = 0.8 # High confidence
#     market_volatility = 2.5 # Example ATR value
#
#     sizer = PositionSizer(base_position_pct=0.05, min_dynamic_pct=0.03, max_dynamic_pct=0.08, max_total_risk_pct=0.20, atr_period=14)
#     position_size_pct = sizer.determine_position_size(account_capital, entry_price, stop_loss_price, confidence_score, market_volatility)
#     print(f"Recommended Position Size Percentage: {position_size_pct:.2%}")

