import time
from typing import Dict

class AgenticWallet:
    def __init__(self, daily_limit_sol: float = 0.5):
        self.daily_limit = daily_limit_sol
        self.spent_today = 0.0
        self.last_reset = time.time()
        self.whitelist = ["Jupiter", "Drift", "Birdeye"]

    def _reset_if_needed(self):
        # Simplistic 24h reset
        if time.time() - self.last_reset > 86400:
            self.spent_today = 0.0
            self.last_reset = time.time()

    def check_and_sign(self, tx_amount_sol: float, protocol: str) -> bool:
        self._reset_if_needed()
        
        # Security Policy 1: Whitelist Check
        if protocol not in self.whitelist:
            print(f"[SECURITY ALERT] Unrecognized Protocol: {protocol}. Transaction Blocked.")
            return False
            
        # Security Policy 2: Daily Quota Check
        if self.spent_today + tx_amount_sol > self.daily_limit:
            print(f"[SECURITY ALERT] Daily Limit Exceeded (Limit: {self.daily_limit} SOL). Transaction Blocked.")
            return False
            
        # If all checks pass
        self.spent_today += tx_amount_sol
        print(f"[WALLET] Transaction Approved: {tx_amount_sol} SOL to {protocol}. (Today's Spend: {self.spent_today:.4f} SOL)")
        return True

if __name__ == "__main__":
    wallet = AgenticWallet(daily_limit_sol=1.0)
    
    # Test 1: Normal Trade
    wallet.check_and_sign(0.2, "Jupiter")
    
    # Test 2: Unknown Protocol
    wallet.check_and_sign(0.1, "Raydium")
    
    # Test 3: Exceeding Limit
    wallet.check_and_sign(0.9, "Drift")
