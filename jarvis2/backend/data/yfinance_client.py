"""Yahoo Finance integration for real-time XAUUSD (gold) spot prices."""
import yfinance as yf
from datetime import datetime
from typing import Dict, Optional
import time

class YFinanceClient:
    """
    Real-time spot gold (XAUUSD) via Yahoo Finance GC=F futures.
    - No API key required
    - Real market data (bid/ask/last)
    - Volume and OHLC data available
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30  # Cache for 30 seconds to avoid rate limits
        self.last_fetch = {}

    def get_xauusd_price(self) -> float:
        """Get current XAUUSD spot price in USD."""
        data = self.get_live_data("GC=F")
        return data.get("close", 0)

    def get_live_data(self, symbol: str = "GC=F") -> Dict:
        """
        Fetch live gold price from Yahoo Finance.

        Args:
            symbol: Ticker (default: GC=F for gold futures = XAUUSD)

        Returns:
            Dict with: symbol, close (price), open, high, low, volume, bid, ask, timestamp, currency
        """
        try:
            # Check cache to avoid hammering API
            now = time.time()
            if symbol in self.cache and (now - self.last_fetch.get(symbol, 0)) < self.cache_ttl:
                return self.cache[symbol]

            # Fetch current day data
            ticker = yf.Ticker(symbol)

            # Get today's OHLCV
            hist = ticker.history(period="1d")
            if len(hist) == 0:
                print(f"⚠️ No data for {symbol}")
                return {"symbol": symbol, "close": 0, "currency": "USD", "status": "no_data"}

            row = hist.iloc[-1]

            # Get real-time bid/ask from info
            info = ticker.info
            bid = info.get('bid', row['Close'])
            ask = info.get('ask', row['Close'])

            result = {
                "symbol": symbol,
                "close": float(row['Close']),          # Last close
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "volume": int(row['Volume']),
                "bid": float(bid),
                "ask": float(ask),
                "spread": float(ask - bid),
                "timestamp": datetime.utcnow().isoformat(),
                "exchange": "YAHOO_FINANCE",
                "currency": "USD",
                "status": "success"
            }

            # Cache it
            self.cache[symbol] = result
            self.last_fetch[symbol] = now

            return result

        except Exception as e:
            print(f"⚠️ YFinance error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "close": 0,
                "currency": "USD",
                "status": "error",
                "error": str(e)
            }

    def get_multiple_prices(self, symbols: list) -> Dict:
        """Get prices for multiple symbols."""
        result = {}
        for symbol in symbols:
            data = self.get_live_data(symbol)
            result[symbol] = data.get("close", 0)
        return result
