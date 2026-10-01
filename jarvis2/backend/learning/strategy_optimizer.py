from typing import Dict, List, Tuple
from datetime import datetime

class StrategyOptimizer:
    def __init__(self):
        self.parameter_ranges = {
            "STOCKS": {
                "entry_threshold": (0.5, 2.5),
                "exit_threshold": (1.0, 5.0),
                "stop_loss": (1.0, 3.0),
                "take_profit": (2.0, 6.0),
            },
            "SENSEX": {
                "entry_threshold": (0.3, 2.0),
                "exit_threshold": (0.5, 3.5),
                "stop_loss": (0.8, 2.5),
                "take_profit": (1.5, 5.0),
            },
            "OPTIONS": {
                "entry_threshold": (0.8, 3.0),
                "exit_threshold": (1.0, 4.0),
                "stop_loss": (1.5, 4.0),
                "take_profit": (3.0, 8.0),
            },
            "CANDLE": {
                "body_ratio": (0.5, 0.9),
                "range_threshold": (1.0, 3.0),
            },
            "XAUUSD": {
                "ema_short": (10, 20),
                "ema_long": (20, 50),
                "threshold": (0.1, 0.5),
            },
        }

        self.current_params = {agent: {} for agent in self.parameter_ranges.keys()}
        self.optimization_history = {agent: [] for agent in self.parameter_ranges.keys()}

    def optimize_for_conditions(self, agent_name: str, market_conditions: Dict, recent_performance: List[Dict]) -> Dict:
        if not recent_performance:
            return self._get_default_params(agent_name)

        win_rate = len([t for t in recent_performance if t.get("pnl", 0) > 0]) / len(recent_performance)
        avg_pnl = sum(t.get("pnl", 0) for t in recent_performance) / len(recent_performance)

        optimized_params = self._adjust_parameters(agent_name, win_rate, avg_pnl, market_conditions)

        self.current_params[agent_name] = optimized_params
        self.optimization_history[agent_name].append({
            "timestamp": datetime.utcnow().isoformat(),
            "params": optimized_params,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
        })

        return optimized_params

    def _adjust_parameters(self, agent_name: str, win_rate: float, avg_pnl: float, market_conditions: Dict) -> Dict:
        volatility = market_conditions.get("volatility", 0)
        trend = market_conditions.get("trend", "neutral")

        params = {}

        if agent_name in self.parameter_ranges:
            for param_name, (min_val, max_val) in self.parameter_ranges[agent_name].items():
                if win_rate > 0.7:
                    params[param_name] = max_val * 0.8
                elif win_rate < 0.5:
                    params[param_name] = min_val * 1.2
                else:
                    params[param_name] = (min_val + max_val) / 2

                if volatility > 0.5:
                    params[param_name] *= 1.1
                elif volatility < 0.2:
                    params[param_name] *= 0.9

        return params

    def _get_default_params(self, agent_name: str) -> Dict:
        ranges = self.parameter_ranges.get(agent_name, {})
        return {param: (min_val + max_val) / 2 for param, (min_val, max_val) in ranges.items()}

    def backtest_parameters(self, agent_name: str, params: Dict, historical_data: List[Dict]) -> float:
        if not historical_data or not params:
            return 0.5

        total_pnl = 0
        trades = 0

        for i, candle in enumerate(historical_data):
            close = candle.get("close", 0)
            open_price = candle.get("open", 0)

            if open_price == 0:
                continue

            change_percent = abs((close - open_price) / open_price * 100)
            threshold = params.get("entry_threshold", 1.0)

            if change_percent > threshold:
                trades += 1
                total_pnl += candle.get("pnl", 0) if "pnl" in candle else 0

        if trades == 0:
            return 0.5

        return min(1.0, abs(total_pnl) / (trades * 100))
