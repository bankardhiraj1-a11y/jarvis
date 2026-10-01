from agents.base import BaseAgent, Signal
from typing import Dict, List

class CandleAgent(BaseAgent):
    def __init__(self):
        super().__init__("CANDLE")
        self.symbols = ["RELIANCE", "TCS", "INFY", "NIFTY", "BANKNIFTY"]
        self.prev_close = {}

    def get_symbols(self) -> List[str]:
        return self.symbols

    def analyze(self, market_data: Dict) -> Signal:
        if not market_data or "symbol" not in market_data:
            return Signal.HOLD

        symbol = market_data.get("symbol", "")
        close = market_data.get("close", 0)
        open_price = market_data.get("open", 0)

        if open_price == 0:
            return Signal.HOLD

        if symbol not in self.prev_close:
            self.prev_close[symbol] = close
            return Signal.HOLD

        prev = self.prev_close[symbol]
        self.prev_close[symbol] = close

        if close > open_price and close > prev:
            return Signal.BUY
        elif close < open_price and close < prev:
            return Signal.SELL
        else:
            return Signal.HOLD
