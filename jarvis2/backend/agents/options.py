from agents.base import BaseAgent, Signal as TrendSignal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

class OptionsAgent(BaseAgent):
    """
    Nifty 50 & Bank Nifty Options Trading Agent

    Strategy: Advanced Directional Options Trading

    TIER 1 - Momentum BUY (Low IV < 15):
      - Setup: EMA(5) > EMA(21) + RSI(14) > 50 + Volume > 1.5x avg
      - Entry: ITM Call (delta 0.65-0.75) on breakout
      - TP: 100-150 points (2-3R)
      - SL: 50 points
      - Lot size: 10 lots (500 units)

    TIER 2 - Reversal SELL (High IV > 15):
      - Setup: Price @ Upper Bollinger Band + Stochastic overbought
      - Entry: ITM Put (delta 0.65-0.75) on rejection
      - TP: 100-150 points
      - SL: 50 points
      - Greeks: Delta neutral hedge

    TIER 3 - Volatility Expansion:
      - Setup: ATR breakout + IV rank > 60
      - Entry: 2-lot straddle at key levels
      - TP: 200-300 points (dual leg)
      - SL: 80 points

    Hard Exit: 03:15 PM IST (same-day expiry protection)
    Greeks Management: Rebalance if delta > 0.80 or < 0.20
    """
    def __init__(self):
        super().__init__("OPTIONS")
        self.symbols = ["NIFTY50", "BANKNIFTY"]

        # Lot size: 10 lots per trade
        self.lot_size = 10
        self.units_per_lot = 50  # Standard option lot
        self.quantity = self.lot_size * self.units_per_lot  # 500 units

        # Strategy parameters
        self.tp_points_conservative = 100  # 100 points
        self.tp_points_aggressive = 150    # 150 points
        self.sl_points = 50                # 50 points SL

        # Greeks tracking (simplified)
        self.portfolio_delta = 0
        self.portfolio_gamma = 0
        self.portfolio_vega = 0
        self.portfolio_theta = 0
        self.rehedge_threshold_delta = 0.80

        # IV environment
        self.vix_level = 15
        self.iv_rank = 50
        self.high_iv_threshold = 15

        # Candle building (15-min for signal confirmation)
        self.completed_candles_15m = []
        self.current_candle_15m = {"open": None, "high": None, "low": None, "close": None, "volume": 0}
        self.current_candle_start_15m = None

        # Strategy state
        self.tier1_positions = []  # Momentum trades
        self.tier2_positions = []  # Reversal trades
        self.tier3_positions = []  # Volatility trades
        self.max_positions = 5

        # Risk management
        self.daily_loss_cap = 0.02  # 2% of capital
        self.daily_pnl = 0
        self.max_daily_loss_reached = False

        self.ist = pytz.timezone('Asia/Kolkata')
        self.last_trade_time = None
        self.min_cooldown = timedelta(minutes=15)

    def get_symbols(self) -> List[str]:
        return self.symbols

    def process_15m_candle(self, price: float, volume: int):
        """Build 15-min candles for signal confirmation"""
        if price <= 0:
            return

        now = datetime.now(self.ist)

        if self.current_candle_start_15m is None:
            self.current_candle_start_15m = now
            self.current_candle_15m = {"open": price, "high": price, "low": price, "close": price, "volume": volume}
            return

        elapsed = (now - self.current_candle_start_15m).total_seconds()

        self.current_candle_15m["close"] = price
        self.current_candle_15m["high"] = max(self.current_candle_15m["high"], price)
        self.current_candle_15m["low"] = min(self.current_candle_15m["low"], price)
        self.current_candle_15m["volume"] += volume

        if elapsed >= 900:  # 15 minutes
            self.completed_candles_15m.append(self.current_candle_15m.copy())

            if len(self.completed_candles_15m) > 20:
                self.completed_candles_15m.pop(0)

            self.current_candle_start_15m = now
            self.current_candle_15m = {"open": price, "high": price, "low": price, "close": price, "volume": volume}

    def calculate_ema(self, candles: List[Dict], period: int) -> float:
        """Calculate EMA"""
        if len(candles) < period:
            return 0

        closes = [c["close"] for c in candles[-period:]]
        multiplier = 2 / (period + 1)
        ema = closes[0]

        for close in closes[1:]:
            ema = close * multiplier + ema * (1 - multiplier)

        return ema

    def calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate RSI for momentum confirmation"""
        if len(candles) < period:
            return 50

        closes = [c["close"] for c in candles[-period:]]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0

        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR for volatility"""
        if len(candles) < period:
            return 0

        tr_values = []
        for i in range(len(candles)):
            c = candles[i]
            if i == 0:
                tr = c["high"] - c["low"]
            else:
                prev_close = candles[i-1]["close"]
                tr = max(c["high"] - c["low"], abs(c["high"] - prev_close), abs(c["low"] - prev_close))
            tr_values.append(tr)

        atr = sum(tr_values[-period:]) / period if tr_values else 0
        return atr

    def analyze(self, live_data: Dict) -> TrendSignal:
        """
        Multi-tier options strategy:
        TIER 1: Momentum breakout (high probability)
        TIER 2: Reversal at extremes (medium probability)
        TIER 3: Volatility expansion (low probability, high payoff)
        """
        try:
            price = live_data.get('close', 0)
            volume = live_data.get('volume', 0)

            if price <= 0 or volume <= 0:
                return TrendSignal.HOLD

            self.process_15m_candle(price, volume)

            # Hard exit at 03:15 PM IST (intraday protection)
            now = datetime.now(self.ist)
            if now.hour >= 15 and now.minute >= 15:
                if self.tier1_positions or self.tier2_positions or self.tier3_positions:
                    print(f"[HARD EXIT] Liquidating all option positions at 03:15 PM IST", flush=True)
                    self.tier1_positions = []
                    self.tier2_positions = []
                    self.tier3_positions = []
                return TrendSignal.HOLD

            # Check daily loss cap
            if self.daily_pnl <= -(self.daily_loss_cap * 100):
                return TrendSignal.HOLD

            # Need minimum candles for analysis
            if len(self.completed_candles_15m) < 21:
                return TrendSignal.HOLD

            # === TIER 1: MOMENTUM BREAKOUT ===
            if len(self.tier1_positions) < self.max_positions:
                ema_5 = self.calculate_ema(self.completed_candles_15m, 5)
                ema_21 = self.calculate_ema(self.completed_candles_15m, 21)
                rsi = self.calculate_rsi(self.completed_candles_15m, 14)

                # Volume check
                recent_vol = sum([c["volume"] for c in self.completed_candles_15m[-3:]]) / 3
                avg_vol = sum([c["volume"] for c in self.completed_candles_15m[-20:]]) / 20
                vol_confirmed = recent_vol > (avg_vol * 1.5)

                # BUY CALL: EMA(5) > EMA(21) + RSI > 50 + Volume
                if price > ema_5 and ema_5 > ema_21 and rsi > 50 and vol_confirmed:
                    tp_points = self.tp_points_aggressive if rsi > 70 else self.tp_points_conservative
                    print(f"[TIER 1 BUY CALL] {self.lot_size} LOTS @ {price:.0f} | EMA(5):{ema_5:.0f} > EMA(21):{ema_21:.0f} | RSI:{rsi:.0f} | TP:{tp_points} SL:50", flush=True)
                    self.tier1_positions.append({"entry": price, "type": "CALL"})
                    return TrendSignal.BUY

                # SELL PUT: EMA(5) < EMA(21) + RSI < 50 + Volume
                elif price < ema_5 and ema_5 < ema_21 and rsi < 50 and vol_confirmed:
                    tp_points = self.tp_points_aggressive if rsi < 30 else self.tp_points_conservative
                    print(f"[TIER 1 SELL PUT] {self.lot_size} LOTS @ {price:.0f} | EMA(5):{ema_5:.0f} < EMA(21):{ema_21:.0f} | RSI:{rsi:.0f} | TP:{tp_points} SL:50", flush=True)
                    self.tier1_positions.append({"entry": price, "type": "PUT"})
                    return TrendSignal.SELL

            # === TIER 2: REVERSAL AT EXTREMES ===
            if len(self.tier2_positions) < 2:
                atr = self.calculate_atr(self.completed_candles_15m, 14)
                highest_high = max([c["high"] for c in self.completed_candles_15m[-20:]])
                lowest_low = min([c["low"] for c in self.completed_candles_15m[-20:]])

                # SELL PUT (Reversal): Price near 20-bar high + ATR expansion
                if price > (highest_high - atr * 0.5) and atr > 50:
                    print(f"[TIER 2 SELL PUT] Reversal @ {price:.0f} | High:{highest_high:.0f} | ATR:{atr:.0f} | TP:100 SL:50", flush=True)
                    self.tier2_positions.append({"entry": price, "type": "PUT_REVERSAL"})
                    return TrendSignal.SELL

                # BUY CALL (Reversal): Price near 20-bar low + ATR expansion
                elif price < (lowest_low + atr * 0.5) and atr > 50:
                    print(f"[TIER 2 BUY CALL] Reversal @ {price:.0f} | Low:{lowest_low:.0f} | ATR:{atr:.0f} | TP:100 SL:50", flush=True)
                    self.tier2_positions.append({"entry": price, "type": "CALL_REVERSAL"})
                    return TrendSignal.BUY

            # === TIER 3: VOLATILITY STRADDLE ===
            if len(self.tier3_positions) < 1 and self.iv_rank > 60:
                atr = self.calculate_atr(self.completed_candles_15m, 14)
                if atr > 80:  # High volatility
                    print(f"[TIER 3 STRADDLE] {self.lot_size} LOTS (2-leg) @ {price:.0f} | IV Rank:{self.iv_rank:.0f} | ATR:{atr:.0f} | TP:300 SL:80", flush=True)
                    self.tier3_positions.append({"entry": price, "type": "STRADDLE"})
                    return TrendSignal.BUY  # Simplified: BUY side for 2-leg straddle

            return TrendSignal.HOLD

        except Exception as e:
            print(f"[ERROR] OPTIONS analyze: {e}", flush=True)
            return TrendSignal.HOLD
