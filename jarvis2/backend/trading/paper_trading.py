from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from config import get_settings

settings = get_settings()

class TradeSignal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class PaperTradingEngine:
    """Autonomous paper trading with real market data and live P&L"""

    def __init__(self):
        self.positions: Dict[str, Dict] = {}  # {symbol: {shares, entry_price, entry_time}}
        self.trades_executed: List[Dict] = []
        self.agent_capital = {
            "STOCKS": settings.ALLOCATION_STOCKS,
            "SENSEX": settings.ALLOCATION_SENSEX,
            "OPTIONS": settings.ALLOCATION_OPTIONS,
            "CANDLE": settings.ALLOCATION_CANDLE,
            "XAUUSD": settings.ALLOCATION_XAUUSD,
        }
        self.agent_pnl = {agent: 0.0 for agent in self.agent_capital.keys()}
        self.total_pnl = 0.0

    def execute_trade(self, agent: str, symbol: str, signal: TradeSignal,
                     current_price: float, quantity: int = 100) -> Dict:
        """Execute paper trade with real market price"""

        if not settings.PAPER_TRADING_ENABLED:
            return {"status": "disabled"}

        trade = {
            "agent": agent,
            "symbol": symbol,
            "signal": signal.value,
            "price": current_price,
            "quantity": quantity,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "EXECUTED_PAPER"
        }

        if signal == TradeSignal.BUY:
            position_key = f"{agent}:{symbol}"
            if position_key not in self.positions:
                self.positions[position_key] = {
                    "symbol": symbol,
                    "agent": agent,
                    "shares": quantity,
                    "entry_price": current_price,
                    "entry_time": datetime.utcnow(),
                    "current_price": current_price
                }
                trade["status"] = "BUY_EXECUTED"

        elif signal == TradeSignal.SELL:
            position_key = f"{agent}:{symbol}"
            if position_key in self.positions:
                pos = self.positions[position_key]
                exit_price = current_price
                profit_loss = (exit_price - pos["entry_price"]) * pos["shares"]

                self.agent_pnl[agent] += profit_loss
                self.total_pnl += profit_loss

                trade["pnl"] = profit_loss
                trade["pnl_percent"] = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100
                trade["status"] = "SELL_EXECUTED"

                del self.positions[position_key]

        self.trades_executed.append(trade)
        return trade

    def get_live_pnl(self, current_prices: Dict[str, float]) -> Dict:
        """Calculate live P&L across all positions"""
        live_pnl = {"unrealized": 0.0, "realized": self.total_pnl}

        for position_key, pos in self.positions.items():
            if pos["symbol"] in current_prices:
                current = current_prices[pos["symbol"]]
                unrealized = (current - pos["entry_price"]) * pos["shares"]
                live_pnl["unrealized"] += unrealized

        live_pnl["total"] = live_pnl["realized"] + live_pnl["unrealized"]
        live_pnl["agents"] = self.agent_pnl.copy()

        return live_pnl

    def get_agent_allocation(self, agent: str) -> Dict:
        """Get allocated capital and current status for agent"""
        return {
            "agent": agent,
            "allocated_capital": self.agent_capital.get(agent, 0),
            "current_pnl": self.agent_pnl.get(agent, 0),
            "active_positions": sum(1 for k in self.positions.keys() if k.startswith(agent)),
            "trades_count": len([t for t in self.trades_executed if t["agent"] == agent])
        }

    def allocate_funds(self, agent: str, amount: float) -> bool:
        """Update capital allocation for agent"""
        if agent in self.agent_capital:
            self.agent_capital[agent] = amount
            return True
        return False

# Global instance
paper_engine = PaperTradingEngine()
