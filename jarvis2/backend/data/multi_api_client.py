"""
Multi-API Market Data Client for Jarvis 2
Integrates: DhanHQ + ONDA (Forex/Commodities)
"""

import os
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DhanHQClient:
    """DhanHQ API for Forex (XAUUSD) and Commodities"""

    def __init__(self):
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        self.client_id = os.getenv("DHAN_CLIENT_ID", "")
        self.base_url = "https://api.dhan.co"
        self.session = requests.Session()
        self.last_call = 0.0
        self.min_interval = 1.05  # Rate limit: 1 req/sec

    @property
    def headers(self) -> Dict:
        return {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.access_token and self.client_id)

    def _throttle(self):
        """Rate limit enforcement"""
        elapsed = time.monotonic() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.monotonic()

    def get_ltp(self, symbol: str, exchange: str = "FOREXCFD") -> Optional[Dict]:
        """Get Last Traded Price for a symbol"""
        if not self.is_configured():
            logger.warning("DhanHQ not configured")
            return None

        try:
            self._throttle()
            url = f"{self.base_url}/v2/marketfeed/ltp"

            payload = {
                "mode": "LTP",
                "exchangeTokens": {
                    exchange: [symbol]
                }
            }

            response = self.session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") == 200 and data.get("data"):
                ltp_data = data["data"][exchange][symbol]
                return {
                    "symbol": symbol,
                    "exchange": exchange,
                    "ltp": ltp_data.get("ltp", 0),
                    "close": ltp_data.get("close", 0),
                    "high": ltp_data.get("high", 0),
                    "low": ltp_data.get("low", 0),
                    "open": ltp_data.get("open", 0),
                    "volume": ltp_data.get("volume", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            return None

        except Exception as e:
            logger.error(f"DhanHQ LTP error for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str, exchange: str = "FOREXCFD") -> Optional[Dict]:
        """Get full quote with bid/ask spreads"""
        if not self.is_configured():
            return None

        try:
            self._throttle()
            url = f"{self.base_url}/v2/marketfeed/quote"

            payload = {
                "mode": "QUOTE",
                "exchangeTokens": {
                    exchange: [symbol]
                }
            }

            response = self.session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") == 200:
                return data.get("data", {}).get(exchange, {}).get(symbol)
            return None

        except Exception as e:
            logger.error(f"DhanHQ Quote error: {e}")
            return None


class OndaClient:
    """ONDA Trading API for Forex (XAUUSD) and Commodities"""

    def __init__(self):
        self.api_key = os.getenv("ONDA_API_KEY", "")
        self.access_token = os.getenv("ONDA_ACCESS_TOKEN", "")
        self.base_url = "https://api.onda.trading"  # Update with actual ONDA endpoint
        self.session = requests.Session()
        self.last_call = 0.0
        self.min_interval = 1.05  # Rate limit: 1 req/sec

    @property
    def headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key and self.access_token)

    def _throttle(self):
        """Rate limit enforcement"""
        elapsed = time.monotonic() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.monotonic()

    def get_ltp(self, symbol: str) -> Optional[Dict]:
        """Get Last Traded Price for a symbol"""
        if not self.is_configured():
            logger.warning("ONDA not configured")
            return None

        try:
            self._throttle()
            url = f"{self.base_url}/v1/marketfeed/ltp"

            payload = {"symbol": symbol}

            response = self.session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                quote_data = data["data"]
                return {
                    "symbol": symbol,
                    "source": "ONDA",
                    "ltp": quote_data.get("ltp", 0),
                    "close": quote_data.get("close", 0),
                    "high": quote_data.get("high", 0),
                    "low": quote_data.get("low", 0),
                    "open": quote_data.get("open", 0),
                    "volume": quote_data.get("volume", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            return None

        except Exception as e:
            logger.error(f"ONDA LTP error for {symbol}: {e}")
            return None


class MultiAPIClient:
    """Unified multi-API client for Jarvis 2"""

    def __init__(self):
        self.dhan = DhanHQClient()
        self.onda = OndaClient()

        # Symbol routing - DhanHQ (NSE, Forex, Commodities)
        self.dhan_nse_symbols = {
            "RELIANCE": "RELIANCE",
            "TCS": "TCS",
            "INFY": "INFY",
            "WIPRO": "WIPRO",
            "ICICIBANK": "ICICIBANK",
        }

        self.dhan_forex_symbols = {
            "XAUUSD": "XAUUSD",    # Gold (fallback for ONDA)
            "CRUDE": "CRUDEOIL",   # Oil
            "EURUSD": "EURUSD",    # EUR/USD
            "GBPUSD": "GBPUSD",    # GBP/USD
            "USDINR": "USDINR",    # USD/INR
        }

        self.onda_symbols = {
            "XAUUSD": "XAUUSD",  # Gold (primary)
        }

    def get_live_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get live market data from DhanHQ with exchange parameter"""

        # XAUUSD: Try ONDA first, fallback to DhanHQ
        if symbol in self.onda_symbols:
            data = self.onda.get_ltp(self.onda_symbols[symbol])
            if data:
                return data
            logger.info(f"ONDA unavailable for {symbol}, falling back to DhanHQ")
            return self.dhan.get_ltp(self.onda_symbols[symbol], "FOREXCFD")

        # NSE Equities via DhanHQ
        if symbol in self.dhan_nse_symbols:
            return self.dhan.get_ltp(self.dhan_nse_symbols[symbol], "NSE")

        # Forex/Commodities via DhanHQ
        if symbol in self.dhan_forex_symbols:
            return self.dhan.get_ltp(self.dhan_forex_symbols[symbol], "FOREXCFD")

        logger.warning(f"Unknown symbol: {symbol}")
        return None

    def get_status(self) -> Dict:
        """Get API connectivity status"""
        return {
            "onda_configured": self.onda.is_configured(),
            "dhan_configured": self.dhan.is_configured(),
            "xauusd_primary": "ONDA" if self.onda.is_configured() else "DhanHQ",
            "timestamp": datetime.utcnow().isoformat(),
        }


# Initialize global instance
multi_api_client = MultiAPIClient()
