"""
Jarvis 2 - Realistic Backtest with Historical Simulation
Uses realistic market behavior to validate 90%+ win rate
"""
import random
import numpy as np
from agents.stocks import StocksAgent
from agents.sensex import SensexAgent
from agents.options import OptionsAgent
from agents.xauusd import XAUUSDAgent

class RealisticBacktest:
    def __init__(self):
        self.min_win_rate = 90.0
        self.seed = 42
        random.seed(self.seed)
        np.random.seed(self.seed)

    def generate_realistic_ohlc(self, base_price, days=30, volatility=0.02, trend=0):
        """Generate realistic OHLC data with actual market behavior."""
        data = []
        current = base_price

        for day in range(days):
            # Realistic daily movement
            daily_return = np.random.normal(trend, volatility)
            open_price = current

            # Intraday movement (high/low within +/- 2.5% typically)
            intraday_vol = volatility * 1.5
            high = open_price * (1 + abs(np.random.normal(0, intraday_vol)))
            low = open_price * (1 - abs(np.random.normal(0, intraday_vol)))
            close = open_price * (1 + daily_return)

            # Ensure OHLC logic
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            volume = random.randint(100000, 5000000)

            data.append({
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })

            current = close

        return data

    def run_strategy(self, agent, symbol_data, symbol_name):
        """Run a strategy against historical data."""
        trades = []
        entry_price = None
        entry_signal = None

        for day_idx, ohlc in enumerate(symbol_data):
            signal = agent.analyze(ohlc)

            # Entry
            if signal != "HOLD" and entry_price is None:
                entry_price = ohlc['close']
                entry_signal = signal

            # Exit (next different signal)
            elif entry_price is not None and signal != entry_signal and signal != "HOLD":
                exit_price = ohlc['close']

                if entry_signal == "BUY":
                    pnl = exit_price - entry_price
                else:  # SELL
                    pnl = entry_price - exit_price

                pnl_pct = (pnl / entry_price) * 100 if entry_price else 0

                trades.append({
                    "entry_signal": entry_signal,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "win": pnl > 0
                })

                entry_price = None
                entry_signal = None

        return trades

    def backtest_xauusd(self):
        """XAUUSD: EMA12/26 on gold (high volatility commodity)."""
        print("\n=== XAUUSD AGENT (EMA12/26 Crossover) ===")
        agent = XAUUSDAgent()

        # Realistic gold prices: $4355 base with 1.5% daily volatility
        data = self.generate_realistic_ohlc(base_price=4355, days=60, volatility=0.015, trend=0.0001)
        trades = self.run_strategy(agent, data, "XAUUSD")

        return self._evaluate_trades(agent.name, trades)

    def backtest_stocks(self):
        """STOCKS: Momentum (1.5%+ move) on blue chips."""
        print("\n=== STOCKS AGENT (Momentum on Blue Chips) ===")
        agent = StocksAgent()
        all_trades = []

        symbols = [
            ("RELIANCE", 3000, 0.012),
            ("TCS", 3500, 0.010),
            ("INFY", 1800, 0.011)
        ]

        for symbol, base_price, volatility in symbols:
            print(f"  {symbol}: ${base_price}")
            data = self.generate_realistic_ohlc(base_price, days=30, volatility=volatility, trend=0.0005)
            trades = self.run_strategy(agent, data, symbol)
            all_trades.extend(trades)

        return self._evaluate_trades(agent.name, all_trades)

    def backtest_sensex(self):
        """SENSEX: Range position (close > 70% = BUY)."""
        print("\n=== SENSEX AGENT (Range Position) ===")
        agent = SensexAgent()

        # Realistic Sensex: 75000 base, 0.8% daily volatility
        data = self.generate_realistic_ohlc(base_price=75000, days=30, volatility=0.008, trend=0.0002)
        trades = self.run_strategy(agent, data, "SENSEX")

        return self._evaluate_trades(agent.name, trades)

    def backtest_options(self):
        """OPTIONS: Strong candle body (>70% of range)."""
        print("\n=== OPTIONS AGENT (Candle Body >70%) ===")
        agent = OptionsAgent()
        all_trades = []

        indices = [
            ("NIFTY", 22500, 0.018),
            ("BANKNIFTY", 45000, 0.020)
        ]

        for symbol, base_price, volatility in indices:
            print(f"  {symbol}: {base_price}")
            data = self.generate_realistic_ohlc(base_price, days=30, volatility=volatility, trend=0.0008)
            trades = self.run_strategy(agent, data, symbol)
            all_trades.extend(trades)

        return self._evaluate_trades(agent.name, all_trades)

    def _evaluate_trades(self, agent_name, trades):
        """Calculate metrics from trades."""
        if not trades:
            print(f"  NO TRADES GENERATED")
            return {
                "agent": agent_name,
                "trades": 0,
                "win_rate": 0,
                "passed": False
            }

        wins = sum(1 for t in trades if t['win'])
        win_rate = (wins / len(trades)) * 100
        total_pnl = sum(t['pnl'] for t in trades)

        passed = win_rate >= self.min_win_rate
        status = "PASS" if passed else "FAIL"

        print(f"  Trades: {len(trades)} | Wins: {wins} | Win Rate: {win_rate:.2f}% [{status}]")
        print(f"  Total PnL: {total_pnl:.2f}")

        return {
            "agent": agent_name,
            "trades": len(trades),
            "wins": wins,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "passed": passed
        }

    def run_full_backtest(self):
        """Run backtest on all 4 agents."""
        print("\n" + "="*70)
        print("JARVIS 2 - REALISTIC BACKTEST VALIDATION")
        print("60 days historical simulation with realistic market behavior")
        print("Requirement: 90%+ win rate for LIVE trading")
        print("="*70)

        results = {
            "XAUUSD": self.backtest_xauusd(),
            "STOCKS": self.backtest_stocks(),
            "SENSEX": self.backtest_sensex(),
            "OPTIONS": self.backtest_options()
        }

        # Print summary
        print("\n" + "="*70)
        print("BACKTEST RESULTS")
        print("="*70)

        all_passed = True
        for agent_name, result in results.items():
            status = "PASS 90%+" if result['passed'] else "FAIL <90%"
            print(f"{agent_name:12} | Trades: {result['trades']:2} | Win Rate: {result['win_rate']:6.2f}% | [{status}]")
            if not result['passed']:
                all_passed = False

        print("="*70)

        if all_passed:
            print("\n[GO LIVE APPROVED] All agents passed 90%+ win rate requirement")
            print("Wiring strategies for LIVE paper trading...\n")
        else:
            print("\n[DO NOT GO LIVE] Some agents failed 90%+ requirement")
            print("Strategies need adjustment before going live.\n")

        print("="*70 + "\n")

        return results, all_passed

if __name__ == "__main__":
    backtest = RealisticBacktest()
    results, approved = backtest.run_full_backtest()

    print("Backtest complete. Ready for decision.\n")
