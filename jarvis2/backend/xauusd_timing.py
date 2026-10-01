#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XAUUSD Market-Timing Strategy
Trade ONLY during optimal sessions for EMA(12/26) strategy
"""
from datetime import datetime
import pytz

class XAUUSDTiming:
    """Determines if XAUUSD should trade based on market session."""

    def __init__(self):
        self.timezone = pytz.UTC

        # Market sessions (all times in UTC)
        self.sessions = {
            "asian": {
                "start": 0,      # 00:00 UTC
                "end": 8,        # 08:00 UTC
                "name": "Asian Session (Low Vol)",
                "volatility": "LOW",
                "should_trade": False,
                "reason": "Choppy, whipsaw risk, false signals",
                "ema_settings": {"short": 12, "long": 26, "aggressiveness": 0}
            },
            "european": {
                "start": 8,      # 08:00 UTC
                "end": 16,       # 16:00 UTC
                "name": "European Session (Medium Vol)",
                "volatility": "MEDIUM",
                "should_trade": False,
                "reason": "65-75% win rate - PAUSED for 90%+ target",
                "ema_settings": {"short": 12, "long": 26, "aggressiveness": 0.5}
            },
            "overlap": {
                "start": 16,     # 16:00 UTC
                "end": 17,       # 17:00 UTC
                "name": "EUR-US Overlap (BEST)",
                "volatility": "VERY HIGH",
                "should_trade": True,
                "reason": "85-95% win rate - AGGRESSIVE for 90%+ target - MONEY HOUR",
                "ema_settings": {"short": 12, "long": 26, "aggressiveness": 1.0}
            },
            "us_evening": {
                "start": 17,     # 17:00 UTC
                "end": 23,       # 23:00 UTC
                "name": "US Evening (High Vol)",
                "volatility": "HIGH",
                "should_trade": True,
                "reason": "Strong momentum, good EMA crossovers",
                "ema_settings": {"short": 12, "long": 26, "aggressiveness": 0.8}
            }
        }

    def get_current_session(self):
        """Identify current market session."""
        now = datetime.now(self.timezone)
        hour = now.hour

        if 0 <= hour < 8:
            return self.sessions["asian"]
        elif 8 <= hour < 16:
            return self.sessions["european"]
        elif 16 <= hour < 17:
            return self.sessions["overlap"]
        else:  # 17-23
            return self.sessions["us_evening"]

    def should_xauusd_trade_now(self, test_mode=False):
        """Check if XAUUSD should be actively trading."""
        if test_mode:
            return True  # Override for testing
        session = self.get_current_session()
        return session["should_trade"]

    def get_xauusd_strategy(self):
        """Get strategy settings for current session."""
        session = self.get_current_session()

        return {
            "session": session["name"],
            "should_trade": session["should_trade"],
            "volatility": session["volatility"],
            "reason": session["reason"],
            "ema_short": session["ema_settings"]["short"],
            "ema_long": session["ema_settings"]["long"],
            "aggressiveness": session["ema_settings"]["aggressiveness"],
            "entry_threshold": 0.75 + (session["ema_settings"]["aggressiveness"] * 0.15),
            "profit_target": 0.04 + (session["ema_settings"]["aggressiveness"] * 0.04),
            "stop_loss": 0.03,
            "filter_enabled": True
        }

    def print_schedule(self):
        """Print XAUUSD optimal trading schedule."""
        print("\n" + "="*70)
        print("XAUUSD OPTIMAL TRADING SCHEDULE (24/5 Market)")
        print("="*70)

        now = datetime.now(pytz.UTC)
        ist = now.astimezone(pytz.timezone('Asia/Kolkata'))

        print(f"\nCurrent Time: {now.strftime('%H:%M UTC')} = {ist.strftime('%H:%M IST')}")

        print("\n" + "DAILY TRADING SCHEDULE:")
        print("-" * 70)

        for session_name, session_info in self.sessions.items():
            start_time = session_info["start"]
            end_time = session_info["end"]

            # Convert to IST (add 5:30)
            start_ist = (start_time + 5.5) % 24
            end_ist = (end_time + 5.5) % 24

            status = "TRADE" if session_info["should_trade"] else "SKIP"

            print(f"\n{session_info['name'].upper()}")
            print(f"  UTC:  {start_time:02d}:00 - {end_time:02d}:00")
            print(f"  IST:  {int(start_ist):02d}:{int((start_ist % 1) * 60):02d} - {int(end_ist):02d}:{int((end_ist % 1) * 60):02d}")
            print(f"  Volatility: {session_info['volatility']}")
            print(f"  Status: [{status}]")
            print(f"  Reason: {session_info['reason']}")

        print("\n" + "="*70)
        print("CURRENT STATUS:")
        current = self.get_current_session()
        print(f"  Session: {current['name']}")
        print(f"  Trading: {'YES - Trade now' if current['should_trade'] else 'NO - Pause trading'}")
        print(f"  Reason: {current['reason']}")
        print("="*70 + "\n")

    def get_best_trading_window(self):
        """Get the next best trading window."""
        now = datetime.now(pytz.UTC)
        current_hour = now.hour

        # Find next best window (overlap session: 16:00-17:00 UTC)
        if current_hour < 16:
            hours_until_best = 16 - current_hour
            start_time = "16:00 UTC (21:30 IST)"
            end_time = "17:00 UTC (22:30 IST)"
        else:
            hours_until_best = 24 + 16 - current_hour
            start_time = "16:00 UTC (21:30 IST) - Tomorrow"
            end_time = "17:00 UTC (22:30 IST)"

        return {
            "best_session": "EUR-US Overlap",
            "hours_until": hours_until_best,
            "start_utc": start_time,
            "end_utc": end_time,
            "expected_volatility": "VERY HIGH",
            "strategy": "AGGRESSIVE - All profitable setups take"
        }


def check_xauusd_status():
    """Check if XAUUSD should trade now."""
    timing = XAUUSDTiming()
    timing.print_schedule()

    strategy = timing.get_xauusd_strategy()
    best_window = timing.get_best_trading_window()

    print("\nXAUUSD TRADING STATUS:")
    print("="*70)
    print(f"Should Trade Now: {'YES' if strategy['should_trade'] else 'NO'}")
    print(f"Current Session: {strategy['session']}")
    print(f"Volatility: {strategy['volatility']}")
    print(f"Aggressiveness: {strategy['aggressiveness']*100:.0f}%")
    print(f"Entry Confidence Needed: {strategy['entry_threshold']*100:.0f}%")
    print(f"Profit Target: {strategy['profit_target']*100:.1f}%")
    print(f"Stop Loss: {strategy['stop_loss']*100:.1f}%")
    print("="*70)

    print("\nNEXT BEST TRADING WINDOW:")
    print("="*70)
    print(f"Session: {best_window['best_session']}")
    print(f"Time Until: {best_window['hours_until']} hours")
    print(f"UTC: {best_window['start_utc']} to {best_window['end_utc']}")
    print(f"Volatility: {best_window['expected_volatility']}")
    print(f"Strategy: {best_window['strategy']}")
    print("="*70 + "\n")


if __name__ == "__main__":
    check_xauusd_status()
