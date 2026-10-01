"""
XAUUSD_SWING Agent - Gold Spot Swing Trading
Strategy: 10 oz lots, $5 target, $2.50 stop-loss, 75%+ win rate
Paper trading only - no live orders
"""

import json
import time
from datetime import datetime

class XAUUSDAgent:
    """XAUUSD Swing Trading Agent"""

    def __init__(self, state_file="xauusd_state.json"):
        self.symbol = "XAUUSD"
        self.agent_name = "XAUUSD_SWING"
        self.contract_name = "GOLD 5MIN SWING"

        # Strategy Parameters
        self.lot_size = 0.10  # 10 oz
        self.target_pips = 5.00  # $5 per oz
        self.stop_loss_pips = 2.50  # $2.50 per oz
        self.risk_per_trade = 25.00  # $25 max risk
        self.max_trades_per_day = 3
        self.min_win_rate = 0.75  # 75% required

        # Trading Rules
        self.min_price = 2300  # Reasonable gold floor
        self.max_price = 2600  # Reasonable gold ceiling
        self.trading_hours = {
            "start": "00:00",  # Gold trades 24/5
            "end": "23:59"
        }

        self.state_file = state_file
        self.trades = self._load_state()
        self.status = "IDLE"
        self.last_entry = None

    def _load_state(self):
        """Load trades from file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"open": [], "closed": []}

    def _save_state(self):
        """Save trades to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.trades, f, indent=2)

    def scan_entry(self, current_price, bid, ask):
        """
        Scan for swing trading entry on XAUUSD.

        Entry Logic (simplified for demo):
        - Price between min/max levels
        - Not too many open trades already
        - At least 30 seconds since last trade

        Returns: (should_enter, entry_price)
        """
        if not self.min_price <= current_price <= self.max_price:
            return False, None

        open_count = len(self.trades.get("open", []))
        if open_count >= self.max_trades_per_day:
            return False, None

        # Throttle: don't enter too frequently
        if self.last_entry:
            if time.time() - self.last_entry < 30:
                return False, None

        # Entry at ask price for buy signals
        return True, ask

    def calculate_sl_tp(self, entry_price, direction="BUY"):
        """Calculate stop loss and take profit"""
        if direction == "BUY":
            tp = entry_price + self.target_pips
            sl = entry_price - self.stop_loss_pips
        else:  # SELL
            tp = entry_price - self.target_pips
            sl = entry_price + self.stop_loss_pips

        return sl, tp

    def open_trade(self, entry_price, direction="BUY"):
        """Open a swing trade"""
        sl, tp = self.calculate_sl_tp(entry_price, direction)

        trade = {
            "id": len(self.trades["open"]),
            "symbol": self.symbol,
            "contract_name": self.contract_name,
            "direction": direction,
            "lot_size": self.lot_size,
            "entry_price": round(entry_price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "entry_time": datetime.now().isoformat(),
            "status": "OPEN"
        }

        self.trades["open"].append(trade)
        self.last_entry = time.time()
        self._save_state()

        return trade

    def close_trade(self, trade_id, exit_price, exit_reason):
        """Close a trade"""
        for i, trade in enumerate(self.trades["open"]):
            if trade["id"] == trade_id:
                # Calculate P&L
                if trade["direction"] == "BUY":
                    gross_pnl = (exit_price - trade["entry_price"]) * self.lot_size * 100
                else:
                    gross_pnl = (trade["entry_price"] - exit_price) * self.lot_size * 100

                # Add charges (from ChargesCalculator)
                if gross_pnl > 0:
                    charges = 1.20  # $1.20 for 0.10 oz from backtest
                else:
                    charges = 1.20

                net_pnl = gross_pnl - charges

                closed_trade = {
                    **trade,
                    "exit_price": round(exit_price, 2),
                    "exit_time": datetime.now().isoformat(),
                    "exit_reason": exit_reason,
                    "gross_pnl": round(gross_pnl, 2),
                    "charges": round(charges, 2),
                    "net_pnl": round(net_pnl, 2),
                    "status": "CLOSED"
                }

                self.trades["closed"].append(closed_trade)
                self.trades["open"].pop(i)
                self._save_state()

                return closed_trade

        return None

    def update_live_pnl(self, current_price):
        """Update unrealized P&L for open trades"""
        for trade in self.trades["open"]:
            if trade["direction"] == "BUY":
                gross_pnl = (current_price - trade["entry_price"]) * self.lot_size * 100
            else:
                gross_pnl = (trade["entry_price"] - current_price) * self.lot_size * 100

            charges = 1.20  # Fixed for 0.10 oz
            trade["current_pnl"] = round(gross_pnl - charges, 2)

    def get_summary(self):
        """Get agent summary"""
        open_trades = self.trades.get("open", [])
        closed_trades = self.trades.get("closed", [])

        if closed_trades:
            wins = sum(1 for t in closed_trades if t.get("net_pnl", 0) > 0)
            total_pnl = sum(t.get("net_pnl", 0) for t in closed_trades)
            win_rate = (wins / len(closed_trades)) * 100 if closed_trades else 0
        else:
            total_pnl = 0
            win_rate = 0

        return {
            "agent": self.agent_name,
            "symbol": self.symbol,
            "status": "ACTIVE" if self.status == "ACTIVE" else "IDLE",
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 1),
            "lot_size": self.lot_size,
            "target": f"${self.target_pips}",
            "stop_loss": f"${self.stop_loss_pips}"
        }


if __name__ == "__main__":
    # Test
    agent = XAUUSDAgent()

    # Simulate a winning trade
    should_enter, entry = agent.scan_entry(2450.00, 2449.95, 2450.05)
    if should_enter:
        trade = agent.open_trade(entry, "BUY")
        print(f"[OPEN] {trade['contract_name']} @ ${trade['entry_price']}")
        print(f"  SL: ${trade['sl']} | TP: ${trade['tp']}")

        # Simulate price movement to TP
        closed = agent.close_trade(trade["id"], 2455.00, "TP_HIT")
        print(f"\n[CLOSED] {closed['contract_name']}")
        print(f"  Exit: ${closed['exit_price']} ({closed['exit_reason']})")
        print(f"  Gross P&L: ${closed['gross_pnl']}")
        print(f"  Charges: ${closed['charges']}")
        print(f"  NET P&L: ${closed['net_pnl']}")

    # Show summary
    print(f"\n{agent.get_summary()}")
