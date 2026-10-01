"""Frozen pre-optimization XAUUSD strategy for reproducible baseline tests.

Do not tune this reference class. In particular, preserve its original
process-lifetime three-signal counter so historical baseline results remain
comparable; the optimized candidate has an explicitly daily counter instead.
"""

from agents.base import BaseAgent, Signal
from typing import Dict, List
import time


class XAUUSDBaselineAgent(BaseAgent):
    def __init__(self):
        super().__init__("XAUUSD")
        self.symbols = ["XAUUSD"]

        # XAUUSD swing-strategy parameters; the target win rate is aspirational.
        self.lot_size = 1.00  # 100 oz per trade (1 lot)
        self.target_pips = 5.00  # $5 take profit per oz
        self.stop_loss_pips = 1.50  # $1.50 stop loss per oz; outcomes are not guaranteed
        self.max_trades_per_day = 3
        self.risk_per_trade = 150.00  # $150 max risk per trade (tighter SL)

        # Selective-entry filters; they do not guarantee a win rate.
        self.min_ema_separation = 1.0
        self.signal_confirmation_count = 2
        self.confirmation_buffer = 0.5

        # Kept verbatim: the original implementation throttled with wall time
        # and did not reset this counter on a UTC date boundary.
        self.last_entry_time = 0
        self.entry_cooldown = 30
        self.ema_12 = None
        self.ema_26 = None
        self.open_trade_count = 0

    def get_symbols(self) -> List[str]:
        return self.symbols

    def analyze(self, market_data: Dict) -> Signal:
        """The original baseline analyze method, retained unchanged."""
        if not market_data:
            return Signal.HOLD

        close = market_data.get("close", 0)
        if close <= 0:
            return Signal.HOLD

        if self.ema_12 is None:
            self.ema_12 = close
            self.ema_26 = close
            return Signal.HOLD

        alpha_12 = 2 / 13
        alpha_26 = 2 / 27
        self.ema_12 = (close * alpha_12) + (self.ema_12 * (1 - alpha_12))
        self.ema_26 = (close * alpha_26) + (self.ema_26 * (1 - alpha_26))

        current_time = time.time()
        if current_time - self.last_entry_time < self.entry_cooldown:
            return Signal.HOLD

        if self.open_trade_count >= self.max_trades_per_day:
            return Signal.HOLD

        ema_separation = abs(self.ema_12 - self.ema_26)
        if ema_separation < self.min_ema_separation:
            return Signal.HOLD

        if self.ema_12 > self.ema_26:
            if close > (self.ema_12 + self.confirmation_buffer):
                self.last_entry_time = current_time
                self.open_trade_count += 1
                return Signal.BUY

        elif self.ema_12 < self.ema_26:
            if close < (self.ema_12 - self.confirmation_buffer):
                self.last_entry_time = current_time
                self.open_trade_count += 1
                return Signal.SELL

        return Signal.HOLD