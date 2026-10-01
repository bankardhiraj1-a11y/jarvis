from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List

class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class BaseAgent(ABC):
    def __init__(self, name: str, risk_per_trade: float = 3500):
        self.name = name
        self.risk_per_trade = risk_per_trade
        self.trades = []
        self.positions = {}
        self.total_pnl = 0.0
        self.win_rate = 0.0

    @abstractmethod
    def analyze(self, market_data: Dict) -> Signal:
        pass

    @abstractmethod
    def get_symbols(self) -> List[str]:
        pass

    def execute_trade(self, symbol: str, signal: Signal, price: float, quantity: float):
        if signal == Signal.HOLD:
            return None

        trade = {
            "agent": self.name,
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "quantity": quantity,
            "timestamp": datetime.utcnow(),
            "status": "PENDING"
        }
        self.trades.append(trade)
        return trade

    def calculate_metrics(self):
        if not self.trades:
            return

        closed_trades = [t for t in self.trades if t.get("pnl") is not None]
        if closed_trades:
            wins = len([t for t in closed_trades if t["pnl"] > 0])
            self.win_rate = (wins / len(closed_trades)) * 100
            self.total_pnl = sum(t["pnl"] for t in closed_trades)
