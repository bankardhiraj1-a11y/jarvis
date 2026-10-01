"""Read-only OANDA account pricing snapshots. No order API is implemented."""
import math
import os
import re
import time
from datetime import datetime, timezone

import requests


class OandaPricingClient:
    MAX_QUOTE_AGE = 30
    HOSTS = {
        "practice": "https://api-fxpractice.oanda.com/v3",
        "live": "https://api-fxtrade.oanda.com/v3",
    }

    def __init__(self):
        self.access_token = os.getenv("OANDA_ACCESS_TOKEN", "") or os.getenv("ONDA_ACCESS_TOKEN", "")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID", "")
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice").lower()
        self.base_url = self.HOSTS.get(self.environment)
        self.latest_prices = {}
        self.last_error = None
        self.is_connected = False
        self._cooldown_until = 0
        self._session = requests.Session()

    @property
    def configured(self):
        return bool(self.access_token and re.fullmatch(r"[A-Za-z0-9-]+", self.account_id) and self.base_url)

    @staticmethod
    def _timestamp(value):
        try:
            stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return None
            return stamp.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    def _unavailable(self, symbol, status):
        self.latest_prices.pop(symbol, None)
        self.is_connected = False
        self.last_error = status
        return {"symbol": symbol, "source": "OANDA", "close": None,
                "stale": True, "status": status, "timestamp": None}

    def get_live_data(self, symbol="XAUUSD", quote_type=None):
        if symbol != "XAUUSD":
            return self._unavailable(symbol, "unsupported_instrument")
        if not self.configured:
            return self._unavailable(symbol, "credentials_or_environment_missing")
        if time.monotonic() < self._cooldown_until:
            return self._unavailable(symbol, "rate_limited")
        try:
            response = self._session.get(
                f"{self.base_url}/accounts/{self.account_id}/pricing",
                headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"},
                params={"instruments": "XAU_USD", "includeHomeConversions": "false"},
                timeout=8,
            )
            if response.status_code == 429:
                self._cooldown_until = time.monotonic() + 60
                return self._unavailable(symbol, "rate_limited")
            if response.status_code != 200:
                return self._unavailable(symbol, f"provider_http_{response.status_code}")
            body = response.json()
            price = next((p for p in body.get("prices", []) if p.get("instrument") == "XAU_USD"), None)
            if not price:
                return self._unavailable(symbol, "quote_missing")
            if price.get("tradeable") is not True or price.get("status") not in (None, "tradeable"):
                return self._unavailable(symbol, "market_not_tradeable")
            stamp = self._timestamp(price.get("time"))
            if stamp is None:
                return self._unavailable(symbol, "provider_timestamp_missing")
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            if not 0 <= age <= self.MAX_QUOTE_AGE:
                return self._unavailable(symbol, "stale_quote")
            bid = max(float(item["price"]) for item in price.get("bids", []))
            ask = min(float(item["price"]) for item in price.get("asks", []))
            if not all(math.isfinite(x) and x > 0 for x in (bid, ask)) or bid > ask:
                return self._unavailable(symbol, "invalid_bid_ask")
            quote = {
                "symbol": symbol, "instrument": "XAU_USD", "source": "OANDA",
                "exchange": "OANDA", "currency": "USD", "close": (bid + ask) / 2,
                "bid": bid, "ask": ask, "timestamp": stamp.isoformat(),
                "provider_timestamp": stamp.isoformat(), "age_seconds": age,
                "stale": False, "tradeable": True, "status": "live",
                "volume": 0,
            }
            self.latest_prices[symbol] = quote
            self.is_connected = True
            self.last_error = None
            return dict(quote)
        except (requests.RequestException, ValueError, TypeError, KeyError, StopIteration):
            # Never return request objects, headers, account IDs, or provider bodies.
            return self._unavailable(symbol, "pricing_request_failed")

    def get_cached_quote(self, symbol="XAUUSD"):
        quote = self.latest_prices.get(symbol)
        if not quote:
            return {}
        stamp = self._timestamp(quote.get("timestamp"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds() if stamp else math.inf
        if not 0 <= age <= self.MAX_QUOTE_AGE:
            return {}
        return {**quote, "age_seconds": age}

    def get_status(self):
        quote = self.get_cached_quote()
        return {
            "source": "OANDA", "configured": self.configured,
            "connected": bool(quote), "environment": self.environment,
            "status": "live" if quote else self.last_error or "waiting_for_data",
            "last_error": self.last_error, "last_update": quote.get("timestamp"),
            "prices": {"XAUUSD": quote} if quote else {},
        }

    def get_xauusd_price(self):
        return self.get_live_data().get("close")

    def close(self):
        self._session.close()