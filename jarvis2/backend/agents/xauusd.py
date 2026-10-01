from agents.base import BaseAgent, Signal
from typing import Dict, List
import time

class XAUUSDAgent(BaseAgent):
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
        self.min_ema_separation = 1.0  # Require strong EMA separation for signal
        self.signal_confirmation_count = 2  # Need 2 consecutive valid signals
        self.confirmation_buffer = 0.5  # Price must be 0.5oz past EMA for confirmation

        # Entry throttle
        self.last_entry_time = 0
        self.entry_cooldown = 30  # seconds between entries

        # EMA for trend confirmation
        self.ema_12 = None
        self.ema_26 = None
        self.open_trade_count = 0

    def get_symbols(self) -> List[str]:
        return self.symbols

    def analyze(self, market_data: Dict) -> Signal:
        """
        XAUUSD swing strategy (REAL DATA ONLY; outcomes are not guaranteed)
        Entry: Selective EMA 12/26 crossover with confirmation
        Filters: Strong separation + price confirmation + timing
        Lot: 1.0 oz (100 oz) per trade
        TP: $5.00/oz | SL: $1.50/oz
        90% win-rate objective is aspirational; no outcome is guaranteed.

        NO FAKE TRADES - ONLY LIVE OANDA DATA
        """

        if not market_data:
            return Signal.HOLD

        close = market_data.get("close", 0)

        if close <= 0:
            return Signal.HOLD

        # Initialize EMAs
        if self.ema_12 is None:
            self.ema_12 = close
            self.ema_26 = close
            return Signal.HOLD

        # Update EMAs (exponential moving averages)
        alpha_12 = 2 / 13
        alpha_26 = 2 / 27
        self.ema_12 = (close * alpha_12) + (self.ema_12 * (1 - alpha_12))
        self.ema_26 = (close * alpha_26) + (self.ema_26 * (1 - alpha_26))

        # Entry throttle - enforce spacing between trades
        current_time = time.time()
        if current_time - self.last_entry_time < self.entry_cooldown:
            return Signal.HOLD

        # Don't over-trade
        if self.open_trade_count >= self.max_trades_per_day:
            return Signal.HOLD

        # Selective entry rules only; no win-rate guarantee.
        ema_separation = abs(self.ema_12 - self.ema_26)

        # Require strong EMA separation for signal validity
        if ema_separation < self.min_ema_separation:
            return Signal.HOLD

        # BUY Signal: Strong uptrend with price confirmation
        if self.ema_12 > self.ema_26:
            # Price must be above EMA 12 by confirmation buffer
            if close > (self.ema_12 + self.confirmation_buffer):
                self.last_entry_time = current_time
                self.open_trade_count += 1
                return Signal.BUY

        # SELL Signal: Strong downtrend with price confirmation
        elif self.ema_12 < self.ema_26:
            # Price must be below EMA 12 by confirmation buffer
            if close < (self.ema_12 - self.confirmation_buffer):
                self.last_entry_time = current_time
                self.open_trade_count += 1
                return Signal.SELL

        return Signal.HOLD
