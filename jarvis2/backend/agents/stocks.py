from agents.base import BaseAgent, Signal as TrendSignal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

class StocksAgent(BaseAgent):
    """
    NSE Equity Swing & Momentum Trading Agent

    Universe: Nifty 500 (liquid only: 20-day ADV > 500k shares, price > ₹50)
    Strategy: VCP breakout on daily chart with volume confirmation

    Regime Filter: Daily 200 EMA > 50 EMA (uptrend only)
    Setup: 20-period EMA pullback or VCP contraction
    Trigger: Break 20-day high with volume > 2x 20-day volume SMA

    TP: Scale 50% at 2R, trail 50% on 20 EMA
    SL: Low of breakout bar or 1.5x ATR(14), max 3% loss per trade
    """
    def __init__(self):
        super().__init__("STOCKS")
        self.symbols = ["RELIANCE", "TCS", "INFY", "WIPRO", "ICICIBANK", "HDFCBANK", "BAJAJFINSV"]

        # Risk & exposure
        self.max_positions = 5
        self.max_risk_per_trade = 0.01  # 1% of equity
        self.max_loss_per_trade = 0.03  # 3% absolute
        self.base_quantity = 50  # 50 shares per trade (increased from 1)

        # Regime filter
        self.ema_200_threshold = None
        self.ema_50_threshold = None

        # Candle building (daily for swing)
        self.completed_candles = []
        self.current_candle = {"open": None, "high": None, "low": None, "close": None, "volume": 0}
        self.current_candle_start = None

        # Volume filter
        self.volume_sma_20 = []
        self.volume_threshold_multiplier = 2.0

        # ATR calculation
        self.atr_14 = None

        # Trade tracking
        self.ist = pytz.timezone('Asia/Kolkata')
        self.open_positions = []
        self.trades_today = []
        self.max_trades_per_day = 3
        self.last_trade_time = None
        self.min_cooldown = timedelta(hours=2)

    def get_symbols(self) -> List[str]:
        return self.symbols

    def calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR for stop loss sizing"""
        if len(candles) < period:
            return 0

        tr_values = []
        for i in range(len(candles)):
            c = candles[i]
            if i == 0:
                tr = c["high"] - c["low"]
            else:
                prev_close = candles[i-1]["close"]
                tr = max(
                    c["high"] - c["low"],
                    abs(c["high"] - prev_close),
                    abs(c["low"] - prev_close)
                )
            tr_values.append(tr)

        atr = sum(tr_values[-period:]) / period if tr_values else 0
        return atr

    def process_daily_tick(self, price: float, volume: int):
        """Build daily candles from tick data"""
        if price <= 0:
            return

        now = datetime.now(self.ist)

        if self.current_candle_start is None:
            self.current_candle_start = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": volume}
            return

        # Check if day changed (daily candle completion)
        elapsed_days = (now - self.current_candle_start).days

        self.current_candle["close"] = price
        self.current_candle["high"] = max(self.current_candle["high"], price)
        self.current_candle["low"] = min(self.current_candle["low"], price)
        self.current_candle["volume"] += volume

        if elapsed_days >= 1:  # Day completed
            self.completed_candles.append(self.current_candle.copy())
            self.volume_sma_20.append(self.current_candle["volume"])

            if len(self.volume_sma_20) > 20:
                self.volume_sma_20.pop(0)

            if len(self.completed_candles) > 50:  # Keep 50 days history
                self.completed_candles.pop(0)

            # Reset for new day
            self.current_candle_start = now
            self.current_candle = {"open": price, "high": price, "low": price, "close": price, "volume": volume}

    def calculate_ema(self, candles: List[Dict], period: int) -> float:
        """Calculate EMA for regime filter"""
        if len(candles) < period:
            return 0

        closes = [c["close"] for c in candles[-period:]]
        multiplier = 2 / (period + 1)
        ema = closes[0]

        for close in closes[1:]:
            ema = close * multiplier + ema * (1 - multiplier)

        return ema

    def can_trade_now(self) -> bool:
        """Check position limits and cooldown"""
        if len(self.open_positions) >= self.max_positions:
            return False

        now = datetime.now(self.ist)

        # Reset daily trades counter at start of day
        if self.trades_today and self.trades_today[0]['date'].date() != now.date():
            self.trades_today = []

        if len(self.trades_today) >= self.max_trades_per_day:
            return False

        if self.last_trade_time and (now - self.last_trade_time) < self.min_cooldown:
            return False

        return True

    def analyze(self, live_data: Dict) -> TrendSignal:
        """
        VCP Breakout Strategy:
        1. Regime: 200 EMA > 50 EMA (uptrend)
        2. Setup: VCP or 20 EMA pullback
        3. Trigger: Break 20-day high + volume > 2x SMA
        """
        try:
            price = live_data.get('close', 0)
            volume = live_data.get('volume', 0)

            if price <= 0 or volume <= 0:
                return TrendSignal.HOLD

            self.process_daily_tick(price, volume)

            # Need at least 21 days for EMA + 20-day high
            if len(self.completed_candles) < 21:
                return TrendSignal.HOLD

            # Regime filter
            ema_200 = self.calculate_ema(self.completed_candles, 200)
            ema_50 = self.calculate_ema(self.completed_candles, 50)

            if ema_200 <= ema_50:  # Not in uptrend
                return TrendSignal.HOLD

            # Can we trade?
            if not self.can_trade_now():
                return TrendSignal.HOLD

            # Get last candle and 20-day high
            last_candle = self.completed_candles[-1]
            high_20d = max([c["high"] for c in self.completed_candles[-20:]])

            # Volume filter
            vol_sma_20 = sum(self.volume_sma_20) / len(self.volume_sma_20) if self.volume_sma_20 else 0
            volume_confirmed = volume > (vol_sma_20 * self.volume_threshold_multiplier)

            # Breakout signal
            if price > high_20d and volume_confirmed:
                # Calculate stops and targets
                atr_14 = self.calculate_atr(self.completed_candles, 14)
                sl_atr = price - (1.5 * atr_14)
                sl_bar = last_candle["low"]
                sl_price = max(sl_atr, sl_bar)  # Tighter stop

                # Enforce 3% max loss
                risk_amount = price - sl_price
                if (risk_amount / price) > self.max_loss_per_trade:
                    sl_price = price * (1 - self.max_loss_per_trade)

                tp_price = price + (2 * (price - sl_price))  # 2R target

                self.last_trade_time = datetime.now(self.ist)
                self.trades_today.append({'date': self.last_trade_time, 'entry': price})

                print(f"[VCP BREAKOUT] BUY {self.base_quantity} shares @ {price:.2f} | TP: {tp_price:.2f} | SL: {sl_price:.2f} | Vol: {volume:.0f} > {vol_sma_20:.0f}", flush=True)
                return TrendSignal.BUY

            return TrendSignal.HOLD

        except Exception as e:
            print(f"[ERROR] STOCKS analyze: {e}", flush=True)
            return TrendSignal.HOLD
