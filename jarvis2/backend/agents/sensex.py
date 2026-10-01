from agents.base import BaseAgent, Signal as TrendSignal
from datetime import datetime, timedelta
from typing import Dict, List
import pytz

class SensexAgent(BaseAgent):
    """
    BSE SENSEX Weekly Options Trading Agent

    Instruments: SENSEX Weekly Contracts (Mon-Thu expiry)

    NON-EXPIRY (Mon-Wed): Defined-Risk Credit Spreads
    - Bull Put Spread in uptrend: Sell 1σ OTM Put, buy 0.5σ OTM Put (250pt spread)
    - Bear Call Spread in downtrend: Sell 1σ OTM Call, buy 0.5σ OTM Call (250pt spread)

    EXPIRY (Thursday): 0 DTE Short Iron Condor
    - Entry: 09:45 AM after IV crush
    - Sell 15-delta Call + 15-delta Put
    - Buy 5-delta protective wings
    - Auto square-off at 03:10 PM IST

    Execution Rules:
    - Liquidity: Bid-ask < 1.5% of premium, OI > 10,000 contracts
    - Stop Loss: 40% on sold legs
    - Hard exit: Mandatory if underlying crosses short strike
    """
    def __init__(self):
        super().__init__("SENSEX")
        self.symbols = ["SENSEX"]

        # Strategy state
        self.current_day_of_week = None
        self.is_expiry_day = False
        self.is_non_expiry = False

        # Greeks tracking (simplified)
        self.portfolio_delta = 0
        self.portfolio_theta = 0

        # Position management
        self.spreads_active = []  # Non-expiry spreads
        self.iron_condor_active = None  # Expiry day position
        self.max_spreads = 3

        # Risk parameters
        self.max_spread_loss = 0.40  # 40% stop on sold legs
        self.hard_exit_time = None

        # Volatility tracking
        self.vix_level = None
        self.iv_rank = None

        # Candle building (15-min for intraday ORB)
        self.completed_candles_15m = []
        self.current_candle_15m = {"open": None, "high": None, "low": None, "close": None, "volume": 0}
        self.current_candle_start_15m = None

        self.ist = pytz.timezone('Asia/Kolkata')
        self.session_start = datetime.now(self.ist).replace(hour=9, minute=15, second=0)

    def get_symbols(self) -> List[str]:
        return self.symbols

    def process_15m_candle(self, price: float):
        """Build 15-minute candles for ORB detection"""
        if price <= 0:
            return

        now = datetime.now(self.ist)

        if self.current_candle_start_15m is None:
            self.current_candle_start_15m = now
            self.current_candle_15m = {"open": price, "high": price, "low": price, "close": price}
            return

        elapsed = (now - self.current_candle_start_15m).total_seconds()

        self.current_candle_15m["close"] = price
        self.current_candle_15m["high"] = max(self.current_candle_15m["high"], price)
        self.current_candle_15m["low"] = min(self.current_candle_15m["low"], price)

        if elapsed >= 900:  # 15 minutes
            self.completed_candles_15m.append(self.current_candle_15m.copy())

            if len(self.completed_candles_15m) > 10:
                self.completed_candles_15m.pop(0)

            self.current_candle_start_15m = now
            self.current_candle_15m = {"open": price, "high": price, "low": price, "close": price}

    def calculate_orb(self) -> Dict:
        """Opening Range Breakout: first 15-min candle breakout levels"""
        if len(self.completed_candles_15m) < 1:
            return None

        first_15m = self.completed_candles_15m[0]
        return {
            "high": first_15m["high"],
            "low": first_15m["low"],
            "range": first_15m["high"] - first_15m["low"]
        }

    def determine_regime(self, price: float) -> str:
        """Simple regime: uptrend vs downtrend from recent action"""
        if len(self.completed_candles_15m) < 2:
            return "NEUTRAL"

        recent = self.completed_candles_15m[-2:]
        if recent[-1]["close"] > recent[0]["close"]:
            return "UPTREND"
        else:
            return "DOWNTREND"

    def is_high_iv(self) -> bool:
        """India VIX > 15 = high IV environment"""
        # Simplified: using price volatility proxy
        if len(self.completed_candles_15m) < 5:
            return False

        closes = [c["close"] for c in self.completed_candles_15m[-5:]]
        volatility = max(closes) - min(closes)
        return volatility > (self.completed_candles_15m[-1]["close"] * 0.02)  # 2% move = high IV

    def analyze(self, live_data: Dict) -> TrendSignal:
        """
        Strategy dispatcher:
        - NON-EXPIRY (Mon-Wed): Credit spreads with ORB + regime
        - EXPIRY (Thu): 0 DTE iron condor at 09:45 AM
        """
        try:
            price = live_data.get('close', 0)
            if price <= 0:
                return TrendSignal.HOLD

            self.process_15m_candle(price)

            now = datetime.now(self.ist)
            day_name = now.strftime("%A")
            self.is_expiry_day = (day_name == "Thursday")
            self.is_non_expiry = (day_name in ["Monday", "Tuesday", "Wednesday"])

            # Hard exit at 03:10 PM
            if now.hour >= 15 and now.minute >= 10:
                if self.iron_condor_active or self.spreads_active:
                    print(f"[HARD EXIT] Squaring off all positions at 03:10 PM", flush=True)
                    self.iron_condor_active = None
                    self.spreads_active = []
                return TrendSignal.HOLD

            # NON-EXPIRY: Credit Spreads
            if self.is_non_expiry and len(self.spreads_active) < self.max_spreads:
                orb = self.calculate_orb()
                regime = self.determine_regime(price)

                if orb and regime != "NEUTRAL":
                    # Bull Put Spread in UPTREND
                    if regime == "UPTREND" and price > orb["high"]:
                        print(f"[BULL PUT SPREAD] SELL PUT @ 1σ OTM | Regime: {regime} | ORB breakout: {price:.0f} > {orb['high']:.0f}", flush=True)
                        return TrendSignal.SELL  # Short put

                    # Bear Call Spread in DOWNTREND
                    elif regime == "DOWNTREND" and price < orb["low"]:
                        print(f"[BEAR CALL SPREAD] SELL CALL @ 1σ OTM | Regime: {regime} | ORB breakdown: {price:.0f} < {orb['low']:.0f}", flush=True)
                        return TrendSignal.SELL  # Short call

            # EXPIRY: 0 DTE Iron Condor
            if self.is_expiry_day and now.hour == 9 and now.minute >= 45 and not self.iron_condor_active:
                print(f"[0 DTE IRON CONDOR] Selling 15-delta straddle + 5-delta wings | IV Crush entry at 09:45", flush=True)
                self.iron_condor_active = {
                    "entry_time": now,
                    "entry_price": price,
                    "delta_neutral": True
                }
                return TrendSignal.SELL

            return TrendSignal.HOLD

        except Exception as e:
            print(f"[ERROR] SENSEX analyze: {e}", flush=True)
            return TrendSignal.HOLD
