from agents.base import BaseAgent, Signal as TrendSignal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

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
        self.current_candle = {"open": None, "high": None, "low": None, "close": None, "volume": 0}

        # Strategy tracking
        self.ist = pytz.timezone('Asia/Kolkata')
        self.last_closed_candle = None  # Store last completed candle for breakout comparison

        # Option strike tracking
        self.current_atm_strike = None
        self.last_option_price = None
        self.last_option_premium = None  # Track actual option premium
        self.option_strike_interval = 100  # SENSEX options are in 100-point intervals
        self.implied_volatility = 0.20  # Default IV 20% for SENSEX options

        # Trade limiting (max 2-3 per day)
        self.max_trades_per_day = 3
        self.trades_today = []
        self.last_trade_time = None
        self.min_time_between_trades = timedelta(minutes=10)
        self.cooldown_after_loss = timedelta(minutes=15)

    def get_symbols(self) -> List[str]:
        return self.symbols

    def calculate_atm_strike(self, price: float) -> str:
        """Calculate ATM strike (nearest 100-point strike)"""
        strike = (round(price / self.option_strike_interval) * self.option_strike_interval)
        return f"{int(strike)}"

    def calculate_option_premium(self, strike: float, current_price: float, is_put: bool = True) -> float:
        """
        Simplified option premium calculation using Greeks approximation
        Returns estimated premium for 1-week OTM put/call
        """
        # Delta approximation
        moneyness = abs(current_price - strike) / current_price

        if is_put:
            # OTM Put premium
            if current_price < strike:  # ITM Put
                delta = 0.70
            else:  # OTM Put
                delta = min(0.50 - moneyness * 0.5, 0.50)
        else:
            # OTM Call premium
            if current_price > strike:  # ITM Call
                delta = 0.70
            else:  # OTM Call
                delta = min(0.50 - moneyness * 0.5, 0.50)

        # Base premium calculation (simplified)
        # For 1-week options: premium ≈ (distance to strike / 100) × 5 + base
        time_decay = 0.98  # 1-week decay factor
        base_premium = max(current_price * 0.0015, 25)  # Minimum ₹25 premium
        distance_premium = abs(current_price - strike) * 0.001

        premium = (base_premium + distance_premium) * time_decay * self.implied_volatility * 10
        return max(premium, 25)  # Minimum ₹25 per unit

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

    def process_tick(self, price: float):
        """Build 1-minute candles"""
        if price <= 0:
            return

        # Track current ATM strike and option premium
        self.current_atm_strike = self.calculate_atm_strike(price)
        self.last_option_price = price
        # Calculate realistic option premium for the ATM strike
        strike_price = float(self.current_atm_strike)
        self.last_option_premium = self.calculate_option_premium(strike_price, price, is_put=True)

        now = datetime.now(self.ist)

        if self.current_candle_start is None:
            self.current_candle_start = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": 1}
            return

        elapsed = (now - self.current_candle_start).total_seconds()

        self.current_candle["close"] = price
        self.current_candle["high"] = max(self.current_candle["high"], price)
        self.current_candle["low"] = min(self.current_candle["low"], price)
        self.current_candle["volume"] = self.current_candle.get("volume", 0) + 1

        # Complete candle after 60 seconds (1 minute)
        if elapsed >= 60:
            self.completed_candles.append(self.current_candle.copy())
            self.last_closed_candle = self.current_candle.copy()

            if len(self.completed_candles) > 20:
                self.completed_candles.pop(0)

            self.current_candle_start = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": 1}

    def can_trade_now(self) -> bool:
        """Check if we can place a trade (respects daily limit and cooldown)"""
        now = datetime.now(self.ist)

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

    def log_trade(self, signal: str, price: float):
        """Log trade for daily limit tracking"""
        now = datetime.now(self.ist)
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

            self.process_tick(price)

            # Need at least 2 completed candles (previous + current forming)
            if len(self.completed_candles) < 2:
                return TrendSignal.HOLD

            # Check if we can trade now
            if not self.can_trade_now():
                return TrendSignal.HOLD

            # Get last 2 candles
            prev_candle = self.completed_candles[-2]
            curr_candle = self.completed_candles[-1]

            prev_is_green = prev_candle["close"] > prev_candle["open"]
            curr_is_green = curr_candle["close"] > curr_candle["open"]

            # UPTREND: Previous green + Current green + Current breaks previous high
            if prev_is_green and curr_is_green:
                if curr_candle["high"] > prev_candle["high"]:
                    self.log_trade('BUY', price)
                    tp_points = self.calculate_dynamic_tp(price, self.completed_candles[-3:])
                    print(f"[BREAKOUT] UPTREND BUY @ {price:.0f} | TP: {tp_points} pts | SL: {prev_candle['low']:.0f} | Trades: {len(self.trades_today)}/{self.max_trades_per_day}", flush=True)
                    return TrendSignal.BUY

            # DOWNTREND: Previous red + Current red + Current breaks previous low
            prev_is_red = prev_candle["close"] < prev_candle["open"]
            curr_is_red = curr_candle["close"] < curr_candle["open"]

            if prev_is_red and curr_is_red:
                if curr_candle["low"] < prev_candle["low"]:
                    self.log_trade('SELL', price)
                    tp_points = self.calculate_dynamic_tp(price, self.completed_candles[-3:])
                    print(f"[BREAKOUT] DOWNTREND SELL @ {price:.0f} | TP: {tp_points} pts | SL: {prev_candle['high']:.0f} | Trades: {len(self.trades_today)}/{self.max_trades_per_day}", flush=True)
                    return TrendSignal.SELL

            return TrendSignal.HOLD

        except Exception as e:
            print(f"[ERROR] SENSEX_OPTIONS_SCALPING analyze: {e}", flush=True)
            return TrendSignal.HOLD
