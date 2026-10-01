from typing import Dict, List
from datetime import datetime
import statistics

class MarketResearcher:
    def __init__(self):
        self.market_snapshots = {}
        self.trend_analysis = {}

    def analyze_market_conditions(self, market_data: List[Dict]) -> Dict:
        if len(market_data) < 2:
            return {"status": "insufficient_data"}

        closes = [d.get("close", 0) for d in market_data]
        volumes = [d.get("volume", 0) for d in market_data]
        highs = [d.get("high", 0) for d in market_data]
        lows = [d.get("low", 0) for d in market_data]

        volatility = self._calculate_volatility(closes)
        trend = self._detect_trend(closes)
        liquidity = sum(volumes) / len(volumes) if volumes else 0
        atr = self._calculate_atr(highs, lows, closes)

        conditions = {
            "timestamp": datetime.utcnow().isoformat(),
            "volatility": round(volatility, 4),
            "trend": trend,
            "liquidity": round(liquidity, 2),
            "atr": round(atr, 2),
            "volume_trend": self._analyze_volume_trend(volumes),
            "price_level": "overbought" if closes[-1] > max(closes[:-1]) else "oversold" if closes[-1] < min(closes[:-1]) else "normal",
        }

        return conditions

    def _calculate_volatility(self, prices: List[float]) -> float:
        if len(prices) < 2:
            return 0.0

        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices)) if prices[i-1] != 0]

        if not returns:
            return 0.0

        return statistics.stdev(returns) if len(returns) > 1 else 0.0

    def _detect_trend(self, prices: List[float]) -> str:
        if len(prices) < 3:
            return "insufficient_data"

        recent = prices[-5:]
        rising = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])

        if rising >= 4:
            return "strong_uptrend"
        elif rising >= 3:
            return "uptrend"
        elif rising <= 1:
            return "strong_downtrend"
        elif rising <= 2:
            return "downtrend"
        else:
            return "neutral"

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        if len(closes) < 2:
            return 0.0

        trs = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)

        return sum(trs) / len(trs) if trs else 0.0

    def _analyze_volume_trend(self, volumes: List[float]) -> str:
        if len(volumes) < 2:
            return "insufficient_data"

        recent_avg = sum(volumes[-5:]) / 5
        prev_avg = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else recent_avg

        if prev_avg == 0:
            return "neutral"

        volume_change = (recent_avg - prev_avg) / prev_avg

        if volume_change > 0.2:
            return "increasing"
        elif volume_change < -0.2:
            return "decreasing"
        else:
            return "stable"

    def identify_opportunities(self, agent_name: str, market_conditions: Dict, recent_trades: List[Dict]) -> List[Dict]:
        opportunities = []

        volatility = market_conditions.get("volatility", 0)
        trend = market_conditions.get("trend", "neutral")

        if agent_name == "OPTIONS" and volatility > 0.03:
            opportunities.append({
                "type": "high_volatility_play",
                "confidence": min(1.0, volatility / 0.1),
                "action": "Increase position size for volatility strategies"
            })

        if agent_name == "STOCKS" and "uptrend" in trend:
            opportunities.append({
                "type": "trend_following",
                "confidence": 0.8,
                "action": "Stack buy signals during trend"
            })

        if agent_name == "XAUUSD" and market_conditions.get("volume_trend") == "increasing":
            opportunities.append({
                "type": "breakout_play",
                "confidence": 0.7,
                "action": "Monitor for breakout levels"
            })

        return opportunities
