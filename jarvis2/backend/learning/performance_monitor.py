from typing import Dict, List
from datetime import datetime, timedelta

class PerformanceMonitor:
    def __init__(self, target_win_rate: float = 0.90):
        self.target_win_rate = target_win_rate
        self.performance_history = {}
        self.alerts = []

    def track_agent_performance(self, agent_name: str, trades: List[Dict]) -> Dict:
        if not trades:
            return {"status": "no_trades"}

        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]

        win_rate = (len(wins) / len(trades)) if trades else 0
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 0

        performance = {
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "total_trades": len(trades),
            "win_rate": round(win_rate * 100, 2),
            "win_count": len(wins),
            "loss_count": len(losses),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
            "status": self._determine_status(win_rate),
            "actions": self._generate_actions(win_rate, agent_name)
        }

        if agent_name not in self.performance_history:
            self.performance_history[agent_name] = []

        self.performance_history[agent_name].append(performance)

        return performance

    def _determine_status(self, win_rate: float) -> str:
        if win_rate >= self.target_win_rate:
            return "EXCELLENT"
        elif win_rate >= 0.80:
            return "STRONG"
        elif win_rate >= 0.60:
            return "GOOD"
        elif win_rate >= 0.50:
            return "FAIR"
        else:
            return "POOR"

    def _generate_actions(self, win_rate: float, agent_name: str) -> List[str]:
        actions = []

        if win_rate >= self.target_win_rate:
            actions.append("✓ Target achieved - maintain current parameters")
            actions.append("→ Monitor for consistency")
        elif win_rate >= 0.85:
            actions.append("↑ Close to target - fine-tune entry signals")
            actions.append("→ Reduce position size to protect capital")
        elif win_rate >= 0.70:
            actions.append("→ Moderate performance - optimize stop loss")
            actions.append("→ Review losing trade patterns")
        elif win_rate >= 0.55:
            actions.append("↓ Below expectations - adjust parameters significantly")
            actions.append("→ Increase stop loss distance")
        else:
            actions.append("⚠ Critical - pause trading and redesign strategy")
            actions.append("→ Backtest new parameters thoroughly")

        return actions

    def get_segment_summary(self, segment: str, days: int = 7) -> Dict:
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        total_trades = 0
        total_wins = 0
        total_pnl = 0

        for agent_name, history in self.performance_history.items():
            for perf in history:
                ts = datetime.fromisoformat(perf["timestamp"])
                if ts > cutoff_time:
                    total_trades += perf["total_trades"]
                    total_wins += perf["win_count"]
                    total_pnl += perf["total_pnl"]

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        return {
            "segment": segment,
            "period_days": days,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "target_win_rate": round(self.target_win_rate * 100, 2),
            "total_pnl": round(total_pnl, 2),
            "status": "✓ TARGET MET" if win_rate >= (self.target_win_rate * 100) else "⚠ BELOW TARGET",
            "gap": round((self.target_win_rate * 100) - win_rate, 2)
        }

    def get_improvement_plan(self, agent_name: str) -> List[Dict]:
        if agent_name not in self.performance_history or not self.performance_history[agent_name]:
            return [{"step": 1, "action": "Insufficient data for improvement plan"}]

        recent = self.performance_history[agent_name][-10:] if len(self.performance_history[agent_name]) >= 10 else self.performance_history[agent_name]

        avg_win_rate = sum(p["win_rate"] for p in recent) / len(recent) / 100

        plan = []
        if avg_win_rate < 0.50:
            plan = [
                {"step": 1, "priority": "CRITICAL", "action": "Review entry signal logic - too many false signals"},
                {"step": 2, "priority": "HIGH", "action": "Increase stop loss to reduce whipsaws"},
                {"step": 3, "priority": "HIGH", "action": "Add trend confirmation filter"},
                {"step": 4, "priority": "MEDIUM", "action": "Backtest over 3-month period with new params"},
            ]
        elif avg_win_rate < 0.70:
            plan = [
                {"step": 1, "priority": "HIGH", "action": "Tighten entry thresholds"},
                {"step": 2, "priority": "HIGH", "action": "Add volatility filter for position sizing"},
                {"step": 3, "priority": "MEDIUM", "action": "Optimize take profit levels"},
                {"step": 4, "priority": "MEDIUM", "action": "Validate with recent market data"},
            ]
        else:
            plan = [
                {"step": 1, "priority": "LOW", "action": "Fine-tune parameters for consistency"},
                {"step": 2, "priority": "LOW", "action": "Monitor for regime changes"},
                {"step": 3, "priority": "MEDIUM", "action": "Document successful patterns"},
            ]

        return plan
