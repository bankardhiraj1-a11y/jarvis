#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest SENSEX Scalping Agent Strategy
"""
import json
from datetime import datetime, timedelta
from agents.sensex_scalping import SensexScalpingAgent

def generate_mock_3min_candles(num_candles=500):
    """Generate realistic 3-minute candle data"""
    candles = []
    base_price = 22500

    for i in range(num_candles):
        trend = 1 if i % 100 < 60 else -1
        volatility = 50

        open_price = base_price + (i % 5 - 2) * 10 * trend
        close_price = open_price + (i % 7 - 3) * 15 * trend
        high_price = max(open_price, close_price) + volatility
        low_price = min(open_price, close_price) - volatility

        candles.append({
            "open": round(open_price, 2),
            "close": round(close_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "volume": 10000 + (i % 5000),
            "timestamp": datetime.now() - timedelta(minutes=(num_candles-i)*3)
        })

        base_price = close_price

    return candles

def run_backtest():
    """Run backtest and report results"""
    print("\n" + "="*70)
    print("SENSEX SCALPING AGENT - BACKTEST REPORT")
    print("="*70 + "\n")

    agent = SensexScalpingAgent()
    print(f"Agent: {agent.name}")
    print(f"Timeframe: {agent.timeframe}")
    print(f"Quantity per trade: {agent.quantity}")
    print(f"Take Profit: {agent.take_profit_points} points")
    print(f"Strategy: 2-Candle trend confirmation (green/red)\n")

    print("Generating 500 3-minute candles (~2500 minutes = 42 hours)...")
    candles = generate_mock_3min_candles(500)
    print(f"✓ Generated {len(candles)} candles\n")

    print("Running backtest...")
    results = agent.backtest(candles)

    print("\n" + "-"*70)
    print("BACKTEST RESULTS")
    print("-"*70)
    print(f"Total Trades: {results['total_trades']}")
    print(f"Winning Trades: {results['winning_trades']}")
    print(f"Losing Trades: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Avg Win: ₹{results['avg_win']:.2f}")
    print(f"Avg Loss: ₹{results['avg_loss']:.2f}")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Total P&L: ₹{results['total_pnl']:.2f}")
    print("-"*70 + "\n")

    win_rate = results['win_rate']
    pf = results['profit_factor']
    pnl = results['total_pnl']

    print("ACCEPTANCE CRITERIA:")
    print(f"  ✓ Win Rate >= 75%: {win_rate:.2f}% {'✅ PASS' if win_rate >= 75 else '❌ FAIL'}")
    print(f"  ✓ Profitable (PnL > 0): ₹{pnl:.2f} {'✅ PASS' if pnl > 0 else '❌ FAIL'}")
    print(f"  ✓ Sustainable Growth: {'✅ YES' if win_rate >= 75 and pnl > 0 else '❌ NO'}\n")

    if win_rate >= 75 and pnl > 0:
        print("✅ STRATEGY APPROVED FOR LIVE TRADING")
        print("   - Win rate exceeds 75% target")
        print("   - Strategy is profitable")
        print("   - Ready to wire into main system")
        print("   - Will trade independently with separate tracking")
        return True
    else:
        print("❌ STRATEGY REJECTED FOR LIVE TRADING")
        if win_rate < 75:
            print(f"   - Win rate {win_rate:.2f}% < 75% required")
        if pnl <= 0:
            print(f"   - Not profitable (P&L: ₹{pnl:.2f})")
        return False

if __name__ == "__main__":
    success = run_backtest()
    exit(0 if success else 1)
