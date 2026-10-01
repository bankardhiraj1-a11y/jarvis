#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jarvis 2 - Daily Profitability Analysis
Focus: Quality profits, not trade volume
Principle: 2 profitable trades > 10 mediocre trades
"""
import json
from datetime import datetime
from pathlib import Path
import statistics

class ProfitabilityAnalyzer:
    """Analyzes daily trades with focus on PROFITABILITY ONLY."""

    def __init__(self):
        self.min_profit_per_trade = 0.5  # Minimum 0.5% profit per trade (from risk)
        self.min_win_pct = 80.0  # Minimum 80% of trades profitable
        self.analysis_dir = Path("daily_profitability")
        self.analysis_dir.mkdir(exist_ok=True)

    def analyze_profit_quality(self, agent_name, trades_today):
        """Analyze profitability quality of today's trades."""

        if not trades_today:
            print("[%s] No trades today" % agent_name)
            return None

        # Separate wins and losses
        winning_trades = [t for t in trades_today if t['pnl'] > 0]
        losing_trades = [t for t in trades_today if t['pnl'] < 0]
        break_even = [t for t in trades_today if t['pnl'] == 0]

        total_trades = len(trades_today)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_pct = (win_count / total_trades * 100) if total_trades > 0 else 0

        # Profitability metrics
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        net_profit = total_profit - total_loss
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        avg_win = statistics.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(statistics.mean([t['pnl'] for t in losing_trades])) if losing_trades else 0

        # Quality metrics
        avg_win_pct = statistics.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        largest_win = max([t['pnl'] for t in winning_trades]) if winning_trades else 0
        largest_loss = abs(min([t['pnl'] for t in losing_trades])) if losing_trades else 0

        print("\n" + "="*70)
        print("PROFITABILITY ANALYSIS: %s - %s" % (agent_name, datetime.now().strftime('%Y-%m-%d')))
        print("="*70)
        print("\nTRADE COUNT:")
        print("  Total: %d | Wins: %d | Losses: %d | Break-even: %d" % (
            total_trades, win_count, loss_count, len(break_even)
        ))
        print("  Win Rate: %.1f%%" % win_pct)

        print("\nPROFITABILITY:")
        print("  Total Profit: %.2f | Total Loss: %.2f | Net: %.2f" % (
            total_profit, total_loss, net_profit
        ))
        print("  Profit Factor: %.2f (1.5+ is excellent)" % profit_factor)
        print("  Avg Win: %.2f | Avg Loss: %.2f" % (avg_win, avg_loss))
        print("  Largest Win: %.2f | Largest Loss: %.2f" % (largest_win, largest_loss))

        print("\nQUALITY METRICS:")
        print("  Avg Win %%: %.2f%%" % avg_win_pct)
        if avg_loss > 0:
            print("  Win/Loss Ratio: %.2f:1" % (avg_win / avg_loss))

        # Decision
        print("\n" + "-"*70)
        decision = self._make_decision(
            win_pct, profit_factor, avg_win, avg_loss, net_profit, total_trades
        )
        print("RECOMMENDATION: %s" % decision["action"])
        print("Reason: %s" % decision["reason"])

        # Save report
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "agent": agent_name,
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "win_pct": win_pct,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit": net_profit,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "recommendation": decision["action"]
        }

        report_file = self.analysis_dir / ("%s_%s.json" % (report['date'], agent_name))
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print("Report saved: %s" % report_file)
        print("="*70 + "\n")

        return report

    def _make_decision(self, win_pct, profit_factor, avg_win, avg_loss, net_profit, trade_count):
        """Make recommendation based on profitability."""

        # Criteria
        high_win_pct = win_pct >= 80.0
        good_profit_factor = profit_factor >= 1.5
        positive_net = net_profit > 0
        good_avg_win = avg_win > 100 if avg_win > 0 else False

        criteria_met = sum([high_win_pct, good_profit_factor, positive_net, good_avg_win])

        if criteria_met >= 3 and positive_net:
            return {
                "action": "[EXCELLENT] Keep strategy unchanged",
                "reason": "High win rate, good profit factor, positive net profit"
            }
        elif high_win_pct and positive_net:
            return {
                "action": "[GOOD] Monitor - Continue current approach",
                "reason": "Good win rate and profitability. Minor optimization possible."
            }
        elif win_pct >= 60 and positive_net:
            return {
                "action": "[OKAY] Monitor closely - Tighten entry filters",
                "reason": "Profitable but win rate could be higher. Need higher conviction entries."
            }
        elif win_pct < 50 or not positive_net:
            return {
                "action": "[POOR] Change strategy - Current approach not working",
                "reason": "Win rate below 50% or unprofitable. Need complete strategy overhaul."
            }
        else:
            return {
                "action": "[REVIEW] Analyze trade quality - Volume vs Profit",
                "reason": "Mixed results. Focus on high-probability trades only."
            }

def run_profitability_analysis():
    """Run profitability analysis with sample data."""
    analyzer = ProfitabilityAnalyzer()

    # Sample trades
    sample_data = {
        "XAUUSD": [
            {"pnl": 150, "pnl_pct": 0.5},
            {"pnl": 140, "pnl_pct": 0.48},
            {"pnl": 180, "pnl_pct": 0.62},
            {"pnl": -50, "pnl_pct": -0.17},
        ],
        "STOCKS": [
            {"pnl": 200, "pnl_pct": 0.7},
            {"pnl": 180, "pnl_pct": 0.65},
            {"pnl": -100, "pnl_pct": -0.4},
        ],
        "SENSEX": [
            {"pnl": 150, "pnl_pct": 0.5},
            {"pnl": 160, "pnl_pct": 0.53},
        ],
        "OPTIONS": [
            {"pnl": 250, "pnl_pct": 1.2},
            {"pnl": 240, "pnl_pct": 1.15},
            {"pnl": 220, "pnl_pct": 1.0},
            {"pnl": -80, "pnl_pct": -0.5},
        ]
    }

    print("\n[PROFITABILITY ANALYSIS] Daily Review (3:30 PM IST)")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for agent_name, trades in sample_data.items():
        analyzer.analyze_profit_quality(agent_name, trades)

    # Summary
    print("\n" + "="*70)
    print("PRINCIPLE: Quality over Quantity")
    print("2 profitable trades > 10 mediocre trades")
    print("Book profits early, cut losses tight")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_profitability_analysis()
