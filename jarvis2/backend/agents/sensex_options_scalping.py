from agents.base import BaseAgent, Signal as TrendSignal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz


def _timestamp_in_ist(value, ist):
    """Normalize event timestamps so historical replay does not use wall time."""
    if value is None:
        return datetime.now(ist)
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid market-data timestamp") from exc
    if not isinstance(value, datetime):
        raise ValueError("Invalid market-data timestamp")
    if value.tzinfo is None:
        return ist.localize(value)
    return value.astimezone(ist)


class SensexOptionsScalpingAgent(BaseAgent):
    """
    SENSEX Options Scalping - Breakout Momentum Strategy

    UPTREND ENTRY:
      1. Green candle closes
      2. Next candle opens green
      3. Next candle HIGH > Previous candle HIGH = BUY signal
      4. TP: 10-15 points (dynamic)
      5. SL: First green candle LOW

    DOWNTREND ENTRY:
      1. Red candle closes
      2. Next candle opens red
      3. Next candle LOW < Previous candle LOW = SELL signal
      4. TP: 10-15 points (dynamic)
      5. SL: First red candle HIGH
    """
    def __init__(self):
        super().__init__("SENSEX_OPTIONS_SCALPING")
        self.symbols = ["SENSEX"]

        # Lot sizing: 50 lots × 20 units/lot = 1000 units per trade
        self.lot_size = 50
        self.units_per_lot = 20
        self.quantity = self.lot_size * self.units_per_lot

        # Scalping parameters
        self.take_profit_pips_min = 10   # Min TP
        self.take_profit_pips_max = 15   # Max TP (dynamic based on volatility)
        self.stop_loss_pips = 25         # Fixed SL from entry

        # Candle building (1-minute for scalping)
        self.completed_candles = []
        self.current_candle_start = None
        self.current_candle_last_timestamp = None
        self.current_candle = {"open": None, "high": None, "low": None, "close": None, "volume": 0}

        # Strategy tracking
        self.ist = pytz.timezone('Asia/Kolkata')
        self.last_closed_candle = None  # Store last completed candle for breakout comparison

        # Premium data is supplied only by the live Dhan option-chain feed.
        self.last_signal_target_points = self.take_profit_pips_min

        # Trade limiting (max 2-3 per day)
        self.max_trades_per_day = 3
        self.trades_today = []
        self.last_trade_time = None
        self.min_time_between_trades = timedelta(minutes=10)
        self.cooldown_after_loss = timedelta(minutes=15)

    def get_symbols(self) -> List[str]:
        return self.symbols

    def get_history_status(self, symbol: str = "SENSEX") -> Dict:
        completed = len(self.completed_candles)
        ready = completed >= 2
        return {
            "status": "READY" if ready else "WARMING_UP",
            "completed_bars": completed,
            "required_bars": 2,
            "reason": (
                "Two authentic one-minute candles are available"
                if ready
                else f"Collecting authentic one-minute SENSEX candles ({completed}/2)"
            ),
        }

    def calculate_dynamic_tp(self, entry_price: float, recent_candles: List[Dict]) -> int:
        """Calculate TP based on recent volatility (10-15 points range)"""
        if len(recent_candles) < 2:
            return self.take_profit_pips_min

        # Calculate ATR (simple version: average range of last 2 candles)
        ranges = [c["high"] - c["low"] for c in recent_candles[-2:]]
        avg_range = sum(ranges) / len(ranges) if ranges else 10

        # Dynamic TP: 10-15 points based on volatility
        if avg_range > 15:  # High volatility
            return self.take_profit_pips_max  # 15 points
        else:
            return self.take_profit_pips_min  # 10 points

    def process_tick(self, price: float, volume: float = 0, timestamp=None):
        """Build 1-minute candles"""
        if price <= 0:
            return

        now = _timestamp_in_ist(timestamp, self.ist)
        candle_start = now.replace(second=0, microsecond=0)

        if self.current_candle_start is None:
            self.current_candle_start = candle_start
            self.current_candle_last_timestamp = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": volume}
            return

        if now < self.current_candle_last_timestamp:
            return

        if candle_start != self.current_candle_start:
            if candle_start.date() == self.current_candle_start.date():
                elapsed = (candle_start - self.current_candle_start).total_seconds()
            else:
                elapsed = None

            # Close the old bar before incorporating the first tick of the next
            # minute. Skip gaps; only observed consecutive minutes are stored.
            if elapsed == 60:
                self.completed_candles.append(self.current_candle.copy())
                self.last_closed_candle = self.current_candle.copy()

                if len(self.completed_candles) > 20:
                    self.completed_candles.pop(0)

            self.current_candle_start = candle_start
            self.current_candle_last_timestamp = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": volume}
            return

        self.current_candle["close"] = price
        self.current_candle["high"] = max(self.current_candle["high"], price)
        self.current_candle["low"] = min(self.current_candle["low"], price)
        self.current_candle["volume"] = self.current_candle.get("volume", 0) + volume
        self.current_candle_last_timestamp = now

    def can_trade_now(self, now=None) -> bool:
        """Check if we can place a trade (respects daily limit and cooldown)"""
        now = _timestamp_in_ist(now, self.ist)

        # Reset trades counter at start of new day
        if self.trades_today and self.trades_today[0]['date'].date() != now.date():
            self.trades_today = []

        # Check daily limit
        if len(self.trades_today) >= self.max_trades_per_day:
            return False

        # Check cooldown from last trade
        if self.last_trade_time:
            if now - self.last_trade_time < self.min_time_between_trades:
                return False

            # Extra cooldown after losing trade
            last_trade = self.trades_today[-1] if self.trades_today else None
            if last_trade and last_trade.get('pnl', 0) < 0:
                if now - self.last_trade_time < self.cooldown_after_loss:
                    return False

        return True

    def log_trade(self, signal: str, price: float, timestamp=None):
        """Log trade for daily limit tracking"""
        now = _timestamp_in_ist(timestamp, self.ist)
        self.trades_today.append({
            'date': now,
            'signal': signal,
            'entry_price': price,
            'pnl': 0
        })
        self.last_trade_time = now

    def analyze(self, live_data: Dict) -> TrendSignal:
        """
        Breakout Momentum Strategy:
        - Detect completed candle direction
        - Check if next candle breaks previous candle's extremum
        - Enter on confirmed breakout
        """
        try:
            price = live_data.get('close', 0)
            if price <= 0:
                return TrendSignal.HOLD

            event_time = _timestamp_in_ist(live_data.get("timestamp"), self.ist)
            self.process_tick(price, live_data.get("volume", 0), event_time)

            # Need at least 2 completed candles (previous + current forming)
            if len(self.completed_candles) < 2:
                return TrendSignal.HOLD

            # Check if we can trade now
            if not self.can_trade_now(event_time):
                return TrendSignal.HOLD

            # Get last 2 candles
            prev_candle = self.completed_candles[-2]
            curr_candle = self.completed_candles[-1]

            prev_is_green = prev_candle["close"] > prev_candle["open"]
            curr_is_green = curr_candle["close"] > curr_candle["open"]

            # UPTREND: Previous green + Current green + Current breaks previous high
            if prev_is_green and curr_is_green:
                if curr_candle["high"] > prev_candle["high"]:
                    tp_points = self.calculate_dynamic_tp(price, self.completed_candles[-3:])
                    self.last_signal_target_points = tp_points
                    print(f"[BREAKOUT] UPTREND BUY @ {price:.0f} | TP: {tp_points} pts | SL: {prev_candle['low']:.0f} | Trades: {len(self.trades_today)}/{self.max_trades_per_day}", flush=True)
                    return TrendSignal.BUY

            # DOWNTREND: Previous red + Current red + Current breaks previous low
            prev_is_red = prev_candle["close"] < prev_candle["open"]
            curr_is_red = curr_candle["close"] < curr_candle["open"]

            if prev_is_red and curr_is_red:
                if curr_candle["low"] < prev_candle["low"]:
                    tp_points = self.calculate_dynamic_tp(price, self.completed_candles[-3:])
                    self.last_signal_target_points = tp_points
                    print(f"[BREAKOUT] DOWNTREND SELL @ {price:.0f} | TP: {tp_points} pts | SL: {prev_candle['high']:.0f} | Trades: {len(self.trades_today)}/{self.max_trades_per_day}", flush=True)
                    return TrendSignal.SELL

            return TrendSignal.HOLD

        except Exception as e:
            print(f"[ERROR] SENSEX_OPTIONS_SCALPING analyze: {e}", flush=True)
            return TrendSignal.HOLD
