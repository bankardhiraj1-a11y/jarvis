"""Onda Trading API client for XAUUSD and forex data."""
import os
import time
from datetime import datetime
from typing import Dict, Optional
import requests

class OndaClient:
    """
    OANDA API integration for live XAUUSD pricing (forex/commodities).
    Requires: ONDA_ACCESS_TOKEN environment variable
    """

    def __init__(self):
        self.access_token = os.getenv("ONDA_ACCESS_TOKEN", "")
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        self.rate_limit_cooldowns = {}
        self.last_fetch = {}
        self.is_connected = False
        if self.access_token:
            self.is_connected = True

    def get_live_data(self, symbol: str, quote_type: str = "XAUUSD") -> Dict:
        """
        Fetch live XAUUSD price from OANDA API.

        Args:
            symbol: Trading symbol (XAUUSD, EURUSD, etc.)
            quote_type: Quote type (not used with OANDA)

        Returns:
            Dict with symbol, OHLC data, timestamp
        """

        # Check if credentials configured
        if not self.access_token:
            return {
                "symbol": symbol,
                "close": 0,
                "status": "credentials_missing",
                "note": "OANDA_ACCESS_TOKEN not configured"
            }

        # Check cooldown from rate limiting
        if symbol in self.rate_limit_cooldowns:
            if time.time() < self.rate_limit_cooldowns[symbol]:
                return {"symbol": symbol, "close": 0, "status": "rate_limited"}
            del self.rate_limit_cooldowns[symbol]

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # OANDA candles endpoint - get latest 1-minute candle
            instrument = "XAU_USD" if symbol == "XAUUSD" else symbol
            url = f"{self.base_url}/instruments/{instrument}/candles"
            params = {"granularity": "M1", "count": 1}

            response = requests.get(url, headers=headers, params=params, timeout=5)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 120))
                self.rate_limit_cooldowns[symbol] = time.time() + retry_after
                return {"symbol": symbol, "close": 0, "status": "rate_limited"}

            response.raise_for_status()
            data = response.json()

            # Parse OANDA candle response
            if data.get("candles") and len(data["candles"]) > 0:
                candle = data["candles"][0]
                mid = candle.get("mid", {})

                if mid.get("c"):
                    return {
                        "symbol": symbol,
                        "close": float(mid.get("c", 0)),
                        "open": float(mid.get("o", 0)),
                        "high": float(mid.get("h", 0)),
                        "low": float(mid.get("l", 0)),
                        "volume": int(candle.get("volume", 0)),
                        "timestamp": candle.get("time", datetime.utcnow().isoformat()),
                        "exchange": "OANDA",
                        "currency": "USD",
                        "status": "ok"
                    }

            return {"symbol": symbol, "close": 0, "status": "no_data"}

        except requests.exceptions.RequestException as e:
            return {"symbol": symbol, "close": 0, "status": "connection_error", "error": str(e)[:50]}
        except Exception as e:
            return {"symbol": symbol, "close": 0, "status": "error", "error": str(e)[:50]}

    def get_xauusd_price(self) -> float:
        """
        Get current XAUUSD (Gold in USD) price.

        Returns:
            Float price in USD, or 0 if unavailable
        """
        data = self.get_live_data("XAUUSD")
        return data.get("close", 0)

    def get_multiple_prices(self, symbols: list) -> Dict:
        """
        Get prices for multiple forex/commodity symbols.

        Args:
            symbols: List of symbols (XAUUSD, EURUSD, GBPUSD, etc.)

        Returns:
            Dict mapping symbol -> price
        """
        result = {}
        for symbol in symbols:
            data = self.get_live_data(symbol)
            result[symbol] = data.get("close", 0)
        return result
