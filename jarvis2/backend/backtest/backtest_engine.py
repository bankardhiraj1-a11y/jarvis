from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass

@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    consecutive_wins: int
    consecutive_losses: int

class BacktestEngine:
    def __init__(self):
        self.results_cache = {}

    def run_backtest(self, agent, historical_data: List[Dict], parameters: Dict = None) -> BacktestResult:
        """Run comprehensive backtest for an agent on historical data"""

        if not historical_data or len(historical_data) < 2:
            return BacktestResult(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_pnl=0, max_drawdown=0, profit_factor=0,
                sharpe_ratio=0, avg_win=0, avg_loss=0,
                consecutive_wins=0, consecutive_losses=0
            )

        trades = []
        cash = 100000  # Starting capital
        position = None
        entry_price = 0

        # Simulate trading
        for i in range(1, len(historical_data)):
            candle = historical_data[i]
            prev_candle = historical_data[i-1]

            # Analyze using agent's logic
            signal = agent.analyze(candle)

            # Entry logic
            if signal.value == "BUY" and not position:
                entry_price = candle.get("close", 0)
                position = {
                    "entry": entry_price,
                    "qty": 1,
                    "type": "BUY",
                    "entry_idx": i,
                }

            # Exit logic
            elif signal.value == "SELL" and position and position["type"] == "BUY":
                exit_price = candle.get("close", 0)
                pnl = (exit_price - entry_price) * position["qty"]

                trades.append({
                    "entry_idx": position["entry_idx"],
                    "exit_idx": i,
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "type": "BUY",
                })

                position = None

        # Calculate metrics
        if not trades:
            return BacktestResult(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_pnl=0, max_drawdown=0, profit_factor=0,
                sharpe_ratio=0, avg_win=0, avg_loss=0,
                consecutive_wins=0, consecutive_losses=0
            )

        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] < 0]

        total_pnl = sum(t["pnl"] for t in trades)
        win_rate = len(winning_trades) / len(trades) if trades else 0

        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t["pnl"] for t in losing_trades) / len(losing_trades)) if losing_trades else 0

        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

        # Drawdown calculation
        equity_curve = [100000]
        for trade in trades:
            equity_curve.append(equity_curve[-1] + trade["pnl"])

        running_max = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > running_max:
                running_max = eq
            dd = (running_max - eq) / running_max if running_max > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplified)
        returns = [trades[i]["pnl"] / 100000 for i in range(len(trades))]
        avg_return = sum(returns) / len(returns) if returns else 0
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns) if returns else 1
        sharpe = (avg_return / (variance ** 0.5 * 0.01)) if variance > 0 else 0

        # Consecutive wins/losses
        consec_w = consec_l = 0
        max_consec_w = max_consec_l = 0

        for trade in trades:
            if trade["pnl"] > 0:
                consec_w += 1
                consec_l = 0
                max_consec_w = max(max_consec_w, consec_w)
            else:
                consec_l += 1
                consec_w = 0
                max_consec_l = max(max_consec_l, consec_l)

        return BacktestResult(
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=round(win_rate * 100, 2),
            total_pnl=round(total_pnl, 2),
            max_drawdown=round(max_dd * 100, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            consecutive_wins=max_consec_w,
            consecutive_losses=max_consec_l,
        )

    def optimize_parameters(self, agent, historical_data: List[Dict],
                           param_ranges: Dict[str, Tuple[float, float]]) -> Dict:
        """Grid search to find optimal parameters"""

        best_params = {}
        best_result = None
        best_win_rate = 0

        # Simple grid search (in production, use more sophisticated optimization)
        for param_name, (min_val, max_val) in param_ranges.items():
            step = (max_val - min_val) / 5

            for value in [min_val + step * i for i in range(6)]:
                # Test this parameter value
                # (In production, would set agent parameters and run backtest)
                result = self.run_backtest(agent, historical_data, {param_name: value})

                if result.win_rate > best_win_rate:
                    best_win_rate = result.win_rate
                    best_params[param_name] = value
                    best_result = result

        return {
            "optimized_parameters": best_params,
            "best_result": {
                "win_rate": best_result.win_rate if best_result else 0,
                "total_pnl": best_result.total_pnl if best_result else 0,
                "profit_factor": best_result.profit_factor if best_result else 0,
            }
        }

    def monte_carlo_analysis(self, trades: List[Dict], iterations: int = 1000) -> Dict:
        """Monte Carlo simulation to test strategy robustness"""

        if not trades:
            return {"status": "no_trades"}

        import random

        results = {
            "worst_case": {"pnl": 0, "probability": 0},
            "best_case": {"pnl": 0, "probability": 0},
            "median_pnl": 0,
            "confidence_interval": {"lower": 0, "upper": 0},
        }

        simulated_pnls = []

        for _ in range(iterations):
            # Shuffle trades and calculate cumulative PnL
            shuffled = random.sample(trades, len(trades))
            total_pnl = sum(t["pnl"] for t in shuffled)
            simulated_pnls.append(total_pnl)

        simulated_pnls.sort()

        results["worst_case"]["pnl"] = simulated_pnls[0]
        results["best_case"]["pnl"] = simulated_pnls[-1]
        results["median_pnl"] = simulated_pnls[len(simulated_pnls) // 2]

        # 95% confidence interval
        lower_idx = int(len(simulated_pnls) * 0.025)
        upper_idx = int(len(simulated_pnls) * 0.975)
        results["confidence_interval"]["lower"] = simulated_pnls[lower_idx]
        results["confidence_interval"]["upper"] = simulated_pnls[upper_idx]

        return results

    def walk_forward_analysis(self, agent, historical_data: List[Dict],
                            window_size: int = 50, step: int = 10) -> List[Dict]:
        """Walk-forward testing to validate strategy robustness"""

        results = []

        for i in range(0, len(historical_data) - window_size, step):
            in_sample = historical_data[i:i + window_size]
            out_sample_start = i + window_size
            out_sample_end = min(out_sample_start + (window_size // 2), len(historical_data))
            out_sample = historical_data[out_sample_start:out_sample_end]

            if not out_sample:
                continue

            # Test on out-of-sample data
            result = self.run_backtest(agent, out_sample)

            results.append({
                "period": f"{i}-{i + window_size}",
                "out_sample_period": f"{out_sample_start}-{out_sample_end}",
                "win_rate": result.win_rate,
                "total_pnl": result.total_pnl,
                "profit_factor": result.profit_factor,
            })

        return results
