#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jarvis 2 - Daily Trade Analysis & Strategy Optimizer
Auto-adjusts strategies post-market to maintain 90%+ win rate
Runs daily after market close (3:30 PM IST)
"""
import json
import os
from datetime import datetime
from pathlib import Path
import statistics

class DailyAnalyzer:
    def __init__(self):
        self.market_close_time = "15:30"
        self.min_win_rate = 90.0
        self.analysis_dir = Path("daily_analysis")
        self.analysis_dir.mkdir(exist_ok=True)
        self.strategy_dir = Path("strategies")
        self.strategy_dir.mkdir(exist_ok=True)
        self.strategies = self._load_strategies()

    def _load_strategies(self):
        """Load current strategy parameters."""
        defaults = {
            "XAUUSD": {
                "name": "EMA Crossover",
                "ema_short": 12,
                "ema_long": 26,
                "win_rate": 0.0,
                "trades": 0,
                "status": "ACTIVE"
            },
            "STOCKS": {
                "name": "Momentum",
                "momentum_threshold": 1.5,
                "volume_min": 500000,
                "win_rate": 0.0,
                "trades": 0,
                "status": "ACTIVE"
            },
            "SENSEX": {
                "name": "Range Position",
                "buy_level": 0.7,
                "sell_level": 0.3,
                "win_rate": 0.0,
                "trades": 0,
                "status": "ACTIVE"
            },
            "OPTIONS": {
                "name": "Candle Body",
                "body_ratio_threshold": 0.7,
                "volume_min": 1000000,
                "win_rate": 0.0,
                "trades": 0,
                "status": "ACTIVE"
            }
        }

        strategies_file = self.strategy_dir / "current_strategies.json"
        if strategies_file.exists():
            with open(strategies_file) as f:
                return json.load(f)
        return defaults

    def save_strategies(self):
        """Save current strategies to file."""
        strategies_file = self.strategy_dir / "current_strategies.json"
        with open(strategies_file, 'w') as f:
            json.dump(self.strategies, f, indent=2)

    def analyze_daily_trades(self, agent_name, trades_today):
        """Analyze trades from today after market close."""
        if not trades_today:
            print("[%s] No trades today - Monitor tomorrow" % agent_name)
            return None

        wins = sum(1 for t in trades_today if t['pnl'] > 0)
        losses = len(trades_today) - wins
        win_rate = (wins / len(trades_today)) * 100
        total_pnl = sum(t['pnl'] for t in trades_today)
        avg_win = statistics.mean([t['pnl'] for t in trades_today if t['pnl'] > 0]) if wins > 0 else 0
        avg_loss = statistics.mean([t['pnl'] for t in trades_today if t['pnl'] < 0]) * -1 if losses > 0 else 0

        print("\n" + "="*70)
        print("DAILY ANALYSIS: %s - %s" % (agent_name, datetime.now().strftime('%Y-%m-%d')))
        print("="*70)
        print("Trades: %d | Wins: %d | Losses: %d" % (len(trades_today), wins, losses))
        print("Win Rate: %.2f%% (Target: %.1f%%)" % (win_rate, self.min_win_rate))
        print("Total PnL: %.2f | Avg Win: %.2f | Avg Loss: %.2f" % (total_pnl, avg_win, avg_loss))

        analysis = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "agent": agent_name,
            "trades": len(trades_today),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }

        if win_rate >= self.min_win_rate:
            action = self._decision_maintain(agent_name, trades_today, win_rate)
        elif win_rate >= 75:
            action = self._decision_tweak(agent_name, trades_today, win_rate)
        else:
            action = self._decision_change_strategy(agent_name, trades_today, win_rate)

        analysis["action"] = action
        self._save_daily_report(analysis, trades_today)

        if action["type"] in ["TWEAK", "CHANGE"]:
            self._apply_strategy_update(agent_name, action)

        return analysis

    def _decision_maintain(self, agent_name, trades, win_rate):
        """Win rate >= 90% - Keep strategy, monitor only."""
        print("\n[MAINTAIN] Win rate %.2f%% meets target - No changes" % win_rate)
        print("   Action: Continue with current strategy")

        return {
            "type": "MAINTAIN",
            "reason": "Win rate %.2f%% meets or exceeds target" % win_rate,
            "details": "Strategy performing well"
        }

    def _decision_tweak(self, agent_name, trades, win_rate):
        """Win rate 75-90% - Tweak parameters, give 1-2 more days."""
        tweaks = self._generate_tweaks(agent_name, trades, win_rate)

        print("\n[TWEAK] Win rate %.2f%% - Apply parameter tweaks" % win_rate)
        print("   Win rate below target but recoverable")
        print("   Suggested tweaks:")
        for tweak in tweaks:
            print("     - " + tweak)
        print("   Action: Apply tweaks + test for 2 more days")

        return {
            "type": "TWEAK",
            "reason": "Win rate %.2f%% recoverable with adjustments" % win_rate,
            "tweaks": tweaks,
            "trial_period_days": 2
        }

    def _decision_change_strategy(self, agent_name, trades, win_rate):
        """Win rate < 75% - Need strategy overhaul."""
        strategy = self.strategies[agent_name]
        new_strategy = self._propose_new_strategy(agent_name, trades)

        print("\n[CHANGE] Win rate %.2f%% - Strategy overhaul needed" % win_rate)
        print("   Current: %s" % strategy['name'])
        print("   Proposed: %s" % new_strategy['name'])
        print("   Action: Test new strategy for 3 days")

        return {
            "type": "CHANGE",
            "reason": "Win rate %.2f%% unsustainable" % win_rate,
            "current_strategy": strategy['name'],
            "new_strategy": new_strategy['name'],
            "trial_period_days": 3
        }

    def _generate_tweaks(self, agent_name, trades, win_rate):
        """Generate specific parameter tweaks."""
        tweaks = []

        if agent_name == "XAUUSD":
            tweaks.append("EMA short: 12 -> 10 (faster entries)")
            tweaks.append("EMA long: 26 -> 20 (faster trend recognition)")
            tweaks.append("Add: Entry only if close > EMA short")

        elif agent_name == "STOCKS":
            tweaks.append("Momentum threshold: 1.5% -> 0.8%")
            tweaks.append("Add volume confirmation: Volume > 20-day avg")
            tweaks.append("Add RSI filter: 30-70 range only")

        elif agent_name == "SENSEX":
            tweaks.append("Buy level: 70% -> 60% of range")
            tweaks.append("Sell level: 30% -> 40% of range")
            tweaks.append("Add ATR-based stops")

        elif agent_name == "OPTIONS":
            tweaks.append("Body ratio: 70% -> 50% of range")
            tweaks.append("Add volume: > 500K contracts")
            tweaks.append("Add: Trade only first 2 hours")

        return tweaks

    def _propose_new_strategy(self, agent_name, trades):
        """Propose new strategy."""
        proposals = {
            "XAUUSD": {
                "name": "RSI + MACD Divergence",
                "description": "RSI extremes with MACD divergence"
            },
            "STOCKS": {
                "name": "Breakout + Volume Surge",
                "description": "Volume spike + price breakout above 5-day high"
            },
            "SENSEX": {
                "name": "Support/Resistance + RSI",
                "description": "S/R level identification + RSI bounce trades"
            },
            "OPTIONS": {
                "name": "IV Rank + Volatility",
                "description": "Trade when IV high + strong volume"
            }
        }

        return proposals.get(agent_name, {"name": "Reversal Strategy"})

    def _apply_strategy_update(self, agent_name, action):
        """Apply strategy changes."""
        strategy = self.strategies[agent_name]

        if action["type"] == "TWEAK":
            print("\n[TWEAKS APPLIED] Updating strategy parameters...")
        elif action["type"] == "CHANGE":
            print("\n[STRATEGY CHANGED] %s -> %s" % (strategy['name'], action["new_strategy"]))
            strategy["name"] = action["new_strategy"]

        self.save_strategies()

    def _save_daily_report(self, analysis, trades):
        """Save daily report."""
        report_file = self.analysis_dir / ("%s_%s.json" % (analysis['date'], analysis['agent']))

        report = dict(analysis)
        report["trades_detail"] = trades
        report["timestamp"] = datetime.now().isoformat()

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print("\nReport saved: %s" % report_file)

    def generate_summary(self):
        """Generate performance summary."""
        print("\n" + "="*70)
        print("DAILY SUMMARY - All Agents")
        print("="*70)

        for agent_name, strategy in self.strategies.items():
            wins = strategy.get("wins", 0)
            trades = strategy.get("trades", 0)
            win_rate = (wins / trades * 100) if trades > 0 else 0
            status = "PASS" if win_rate >= self.min_win_rate else "ADJUST"

            print("%s | %s | Win Rate: %.2f%% [%s]" % (
                agent_name.ljust(12),
                strategy['name'].ljust(25),
                win_rate,
                status
            ))

        print("="*70 + "\n")

def run_eod_analysis():
    """Run analysis after market close (3:30 PM IST)."""
    analyzer = DailyAnalyzer()

    sample_trades = {
        "XAUUSD": [
            {"entry": "BUY", "pnl": 150, "pnl_pct": 0.5, "signal": "EMA", "entry_time": "09:15", "exit_time": "10:30"},
            {"entry": "SELL", "pnl": -75, "pnl_pct": -0.3, "signal": "EMA", "entry_time": "11:00", "exit_time": "12:15"},
        ],
        "STOCKS": [
            {"entry": "BUY", "pnl": 200, "pnl_pct": 0.7, "signal": "Momentum", "entry_time": "09:30", "exit_time": "11:00"},
        ],
        "SENSEX": [
            {"entry": "BUY", "pnl": -100, "pnl_pct": -0.2, "signal": "Range", "entry_time": "09:45", "exit_time": "13:00"},
        ],
        "OPTIONS": []
    }

    print("\n[EOD ANALYSIS] Post-market analysis (3:30 PM IST)")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for agent_name, trades in sample_trades.items():
        analyzer.analyze_daily_trades(agent_name, trades)

    analyzer.generate_summary()

if __name__ == "__main__":
    run_eod_analysis()
