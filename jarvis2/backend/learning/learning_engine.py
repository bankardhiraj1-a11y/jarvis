from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class LearningEngine:
    def __init__(self):
        self.daily_review = {}
        self.strategy_history = {}
        self.performance_trends = {}
        self.confidence_scores = {}

    def analyze_daily_performance(self, agent_name: str, trades: List[Dict]) -> Dict:
        if not trades:
            return {"message": "No trades to analyze"}

        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]

        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(abs(t["pnl"]) for t in losses) / len(losses) if losses else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

        insights = {
            "agent": agent_name,
            "date": datetime.utcnow().isoformat(),
            "total_trades": len(trades),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_pnl": sum(t.get("pnl", 0) for t in trades),
            "recommendations": []
        }

        if win_rate < 50:
            insights["recommendations"].append("Win rate below 50% - review entry signals")
        if profit_factor < 1:
            insights["recommendations"].append("Profit factor < 1 - adjust risk management")
        if win_rate > 70:
            insights["recommendations"].append("Strong performance - increase position size")

        self.daily_review[agent_name] = insights
        return insights

    def suggest_strategy_adjustments(self, agent_name: str, market_conditions: Dict) -> List[str]:
        suggestions = []

        volatility = market_conditions.get("volatility", 0)
        trend = market_conditions.get("trend", "neutral")
        liquidity = market_conditions.get("liquidity", 0)

        if volatility > 0.5 and agent_name != "OPTIONS":
            suggestions.append("High volatility detected - increase stop loss distance")

        if trend == "strong_uptrend" and agent_name == "STOCKS":
            suggestions.append("Strong uptrend - favor buy signals, reduce sell entries")

        if liquidity < 1000000 and agent_name in ["SENSEX", "XAUUSD"]:
            suggestions.append("Low liquidity - reduce position size to minimize slippage")

        if volatility < 0.1:
            suggestions.append("Low volatility - tighten profit targets")

        return suggestions

    def calculate_confidence(self, agent_name: str, recent_performance: List[Dict]) -> float:
        if not recent_performance:
            return 0.5

        recent_trades = recent_performance[-20:]
        if not recent_trades:
            return 0.5

        win_rate = len([t for t in recent_trades if t.get("pnl", 0) > 0]) / len(recent_trades)
        consistency = self._measure_consistency(recent_trades)

        confidence = (win_rate * 0.6) + (consistency * 0.4)
        return round(max(0.0, min(1.0, confidence)), 2)

    def _measure_consistency(self, trades: List[Dict]) -> float:
        if len(trades) < 2:
            return 0.5

        pnls = [t.get("pnl", 0) for t in trades]
        mean_pnl = sum(pnls) / len(pnls)
        variance = sum((x - mean_pnl) ** 2 for x in pnls) / len(pnls)
        std_dev = variance ** 0.5

        if mean_pnl == 0:
            return 0.0

        consistency = 1 / (1 + (std_dev / abs(mean_pnl)))
        return max(0.0, min(1.0, consistency))
