"""Read-only OANDA account pricing snapshots. No order API is implemented."""
import math
import os
import re
import time
from datetime import datetime, timezone

import requests


class OandaCandleError(Exception):
    """Sanitized failure while fetching read-only OANDA candle data."""


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
        self._account_lookup_after = 0
        self._session = requests.Session()

    @property
    def configured(self):
        return bool(self.access_token and re.fullmatch(r"[A-Za-z0-9-]+", self.account_id) and self.base_url)

    def _discover_account(self):
        """Resolve a single authorized account privately, only from a polling call."""
        if self.account_id or not self.access_token or not self.base_url:
            return
        now = time.monotonic()
        if now < self._account_lookup_after:
            return
        self._account_lookup_after = now + 60
        try:
            response = self._session.get(
                f"{self.base_url}/accounts",
                headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"},
                timeout=8,
            )
            if response.status_code != 200:
                self.last_error = f"account_lookup_http_{response.status_code}"
                return
            body = response.json()
            accounts = body.get("accounts", []) if isinstance(body, dict) else []
            if not isinstance(accounts, list):
                self.last_error = "invalid_account_response"
                return
            ids = [
                account["id"] for account in accounts
                if isinstance(account, dict)
                and isinstance(account.get("id"), str)
                and re.fullmatch(r"[A-Za-z0-9-]+", account["id"])
            ]
            if len(ids) != 1:
                self.last_error = "account_selection_required" if len(ids) > 1 else "account_unavailable"
                return
            self.account_id = ids[0]
            self.last_error = None
        except (requests.RequestException, ValueError, TypeError):
            self.last_error = "account_lookup_failed"

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
        self._discover_account()
        if not self.configured:
            return self._unavailable(symbol, self.last_error or "credentials_or_environment_missing")
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
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "timestamp_kind": "provider_quote",
                "environment": self.environment,
                "stale": False, "tradeable": True, "status": "live",
                "volume": 0,
            }
            self.latest_prices[symbol] = quote
            self.is_connected = True
            self.last_error = None
            return dict(quote)
        except (requests.RequestException, ValueError, TypeError, KeyError, StopIteration, AttributeError, OverflowError):
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

    def get_completed_candles(self, granularity, count):
        """Fetch bounded XAU_USD bid/ask candles without account metadata or orders."""
        if granularity not in ("M1", "M15", "H4"):
            raise OandaCandleError("Unsupported OANDA candle granularity")
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 500:
            raise OandaCandleError("OANDA candle count must be between 1 and 500")
        if not self.access_token or not self.base_url:
            raise OandaCandleError("OANDA candle credentials or environment are unavailable")

        params = {
            "granularity": granularity,
            "count": count,
            "price": "BA",
            "smooth": "false",
        }
        if granularity == "H4":
            params.update({
                "dailyAlignment": 17,
                "alignmentTimezone": "America/New_York",
            })

        try:
            response = self._session.get(
                f"{self.base_url}/instruments/XAU_USD/candles",
                headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"},
                params=params,
                timeout=15,
            )
        except requests.RequestException:
            raise OandaCandleError("OANDA candle request failed") from None
        except Exception:
            # Transport adapters must not leak request details or credentials.
            raise OandaCandleError("OANDA candle request failed") from None

        if response.status_code != 200:
            raise OandaCandleError(f"OANDA candle request rejected (HTTP {response.status_code})")
        try:
            payload = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            raise OandaCandleError("OANDA candle response was not valid JSON") from None
        except Exception:
            raise OandaCandleError("OANDA candle response was not valid JSON") from None

        if (
            not isinstance(payload, dict)
            or payload.get("instrument") != "XAU_USD"
            or payload.get("granularity") != granularity
            or not isinstance(payload.get("candles"), list)
        ):
            raise OandaCandleError("OANDA candle response failed provenance checks")

        previous = None
        for candle in payload["candles"]:
            if not isinstance(candle, dict):
                raise OandaCandleError("OANDA candle response contains an invalid candle")
            if candle.get("instrument", "XAU_USD") != "XAU_USD":
                raise OandaCandleError("OANDA candle instrument provenance mismatch")
            if candle.get("granularity", granularity) != granularity:
                raise OandaCandleError("OANDA candle granularity provenance mismatch")
            stamp = self._timestamp(candle.get("time"))
            if stamp is None:
                raise OandaCandleError("OANDA candle timestamp is invalid")
            if previous is not None and stamp <= previous:
                raise OandaCandleError("OANDA candles are duplicate or non-chronological")
            previous = stamp
        return payload["candles"]

    def close(self):
        self._session.close()
