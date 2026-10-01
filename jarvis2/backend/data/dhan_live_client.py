"""Read-only DhanHQ market-data client.

Only Dhan market-feed quote and option-chain endpoints are used here. This
client deliberately has no order-entry methods or order endpoints.
"""

import math
import os
import time
from datetime import date, datetime, timezone
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests


BASE_URL = "https://api.dhan.co/v2"
REQUEST_TIMEOUT_SECONDS = 10
# Allow for network jitter: exact documented boundaries caused intermittent 429s.
QUOTE_MIN_INTERVAL_SECONDS = 1.25
OPTION_MIN_INTERVAL_SECONDS = 3.25
EXPIRY_CACHE_SECONDS = 60 * 60

_SEGMENTS = {
    "IDX_I": "IDX_I",
    "NSE_EQ": "NSE_EQ",
    "NSE_FNO": "NSE_FNO",
    "NSE_FO": "NSE_FNO",
    "BSE_EQ": "BSE_EQ",
    "BSE_FNO": "BSE_FNO",
    "MCX_COMM": "MCX_COMM",
    "NSE_CURRENCY": "NSE_CURRENCY",
    "BSE_CURRENCY": "BSE_CURRENCY",
}


def _positive_number(value: Any) -> Optional[float]:
    """Return a finite positive number, or None for unusable market data."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _non_negative_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _canonical_strike(value: Any) -> Optional[str]:
    number = _positive_number(value)
    if number is None:
        return None
    return f"{number:.6f}".rstrip("0").rstrip(".")


class DhanLiveClient:
    """Fetch and cache real Dhan quotes without placing or modifying orders."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        *,
        quote_max_age_seconds: float = 15.0,
        option_max_age_seconds: float = 15.0,
    ):
        # Keep credentials private and in memory only. They are never included
        # in logs, snapshots, error strings, or cached market-data records.
        self._configured_client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
        self._client_id = self._configured_client_id
        self._access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
        self._profile_attempted_at: Optional[float] = None
        self._profile_identity_verified = False
        self._configured_client_id_rejected = False
        self._session = session or requests.Session()

        self.quote_max_age_seconds = max(0.0, float(quote_max_age_seconds))
        self.option_max_age_seconds = max(0.0, float(option_max_age_seconds))

        self.latest_prices: Dict[str, Dict[str, Any]] = {}
        # Each expiry is a separate snapshot. In particular, refreshing the
        # nearest expiry must not evict the chain for an open older-expiry trade.
        self.option_chains: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._latest_option_expiry: Dict[str, str] = {}
        self._option_contract_quotes: Dict[
            Tuple[str, str, str, str], Dict[str, Any]
        ] = {}
        self.subscribed = False
        self.last_error: Optional[str] = None

        self._quote_received_at: Dict[str, float] = {}
        self._option_received_at: Dict[Tuple[str, str], float] = {}
        self._option_quote_received_at: Dict[
            Tuple[str, str, str, str], float
        ] = {}
        self._option_quote_attempted_at: Dict[
            Tuple[str, str, str, str], float
        ] = {}
        self._invalid_quotes = set()
        self._instrument_meta: Dict[str, Dict[str, str]] = {}
        self._subscribed_instruments: List[Dict[str, str]] = []
        self._expiry_cache: Dict[Tuple[str, str, str], Tuple[List[str], float]] = {}

        self._monotonic = time.monotonic
        self._sleep = time.sleep
        self._quote_lock = Lock()
        self._credential_lock = Lock()
        self._option_lock = Lock()
        self._quote_rate_lock = Lock()
        self._option_rate_lock = Lock()
        self._last_quote_request_at: Optional[float] = None
        self._last_option_request_at: Optional[float] = None

    @property
    def _has_credentials(self) -> bool:
        self._resolve_client_id()
        return bool(self._client_id and self._access_token)

    @property
    def _cached_has_credentials(self) -> bool:
        """Cache reads must never trigger profile HTTP or credential resolution."""
        return bool(self._client_id and self._access_token)

    def _resolve_client_id(self) -> None:
        # Quote and chain collectors start concurrently. Both must wait for the
        # authenticated identity before either can send a configured fallback.
        with self._credential_lock:
            self._resolve_client_id_locked()

    def _resolve_client_id_locked(self) -> None:
        """Prefer the client identity authenticated by the access token.

        A configured ID remains a compatibility fallback when the profile
        endpoint is unavailable, but a token-verified profile ID is authoritative.
        """
        if not self._access_token or self._profile_identity_verified:
            return
        now = self._monotonic()
        if (
            self._profile_attempted_at is not None
            and now - self._profile_attempted_at < 60
        ):
            return
        self._profile_attempted_at = now
        try:
            response = self._session.get(
                f"{BASE_URL}/profile",
                headers={
                    "access-token": self._access_token,
                    "Accept": "application/json",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if getattr(response, "status_code", None) != 200:
                return
            body = response.json()
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return
        except Exception:
            return
        if not isinstance(body, dict):
            return
        client_id = body.get("dhanClientId")
        if isinstance(client_id, str):
            client_id = client_id.strip()
        else:
            client_id = ""
        # Header values must be a simple single-line identifier. Keep it only
        # in memory; never copy profile content or the ID into status/error data.
        if (
            client_id
            and len(client_id) <= 64
            and "\r" not in client_id
            and "\n" not in client_id
        ):
            self._client_id = client_id
            self._profile_identity_verified = True
            return

        # A configured ID is usable as a fallback only until the market API
        # rejects it. Never keep retrying a known-bad ID if profile lookup is
        # unavailable.
        if not self._client_id and not self._configured_client_id_rejected:
            self._client_id = self._configured_client_id

    def _set_error(self, message: Optional[str]) -> None:
        self.last_error = message

    def _wait_for_rate_limit(self, endpoint: str) -> None:
        """Enforce Dhan's independent quote and global option-chain intervals."""
        is_option_request = endpoint == "option"
        lock = self._option_rate_lock if is_option_request else self._quote_rate_lock
        interval = (
            OPTION_MIN_INTERVAL_SECONDS
            if is_option_request
            else QUOTE_MIN_INTERVAL_SECONDS
        )
        attribute = (
            "_last_option_request_at"
            if is_option_request
            else "_last_quote_request_at"
        )

        with lock:
            now = self._monotonic()
            last_request = getattr(self, attribute)
            if last_request is not None:
                remaining = interval - (now - last_request)
                if remaining > 0:
                    self._sleep(remaining)
            setattr(self, attribute, self._monotonic())

    def _post_json(
        self, path: str, payload: Dict[str, Any], *, endpoint: str
    ) -> Optional[Dict[str, Any]]:
        if not self._has_credentials:
            self._set_error("Dhan credentials are not configured")
            return None

        self._wait_for_rate_limit(endpoint)
        headers = {
            "access-token": self._access_token,
            "client-id": self._client_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            response = self._session.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            self._set_error("Dhan market-data request failed")
            return None
        except Exception:
            self._set_error("Dhan market-data request failed")
            return None

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or not 200 <= status_code < 300:
            if status_code == 401:
                attempted_client_id = headers["client-id"]
                with self._credential_lock:
                    # A late failure from an old request cannot erase a newly
                    # resolved identity used by another background collector.
                    if self._client_id == attempted_client_id:
                        self._client_id = ""
                    if attempted_client_id == self._configured_client_id:
                        self._configured_client_id_rejected = True
            self._set_error(
                f"Dhan market-data request returned HTTP {status_code}"
                if isinstance(status_code, int)
                else "Dhan market-data request returned an invalid response"
            )
            return None

        try:
            body = response.json()
        except (ValueError, TypeError):
            self._set_error("Dhan market-data response was not valid JSON")
            return None

        if not isinstance(body, dict) or str(body.get("status", "")).lower() != "success":
            self._set_error("Dhan market-data API reported a failure")
            return None
        return body

    @staticmethod
    def _instrument_values(instrument: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        segment = (
            instrument.get("ExchangeSegment")
            or instrument.get("exchange_segment")
            or instrument.get("segment")
            or "NSE_EQ"
        )
        security_id = (
            instrument.get("SecurityId")
            or instrument.get("security_id")
            or instrument.get("securityId")
        )
        canonical_segment = _SEGMENTS.get(str(segment).strip().upper())
        try:
            parsed_id = str(int(str(security_id).strip()))
        except (TypeError, ValueError, OverflowError):
            return canonical_segment, None
        if int(parsed_id) <= 0:
            return canonical_segment, None
        return canonical_segment, parsed_id

    @staticmethod
    def _exchange_timestamp(value: Any) -> Optional[str]:
        """Normalize Dhan's exchange trade time; never substitute receipt time."""
        if not isinstance(value, str) or not value.strip():
            return None
        raw = value.strip()
        parsed = None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
        if parsed is None or parsed.year <= 1980:
            return None
        if parsed.tzinfo is None:
            # Dhan documents last_trade_time as exchange-local time.
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _normalize_quote(
        record: Dict[str, Any], *, symbol: str, segment: str, received_at: str
    ) -> Optional[Dict[str, Any]]:
        last_price = _positive_number(record.get("last_price"))
        if last_price is None:
            return None

        ohlc = record.get("ohlc")
        if not isinstance(ohlc, dict):
            ohlc = {}

        prices: Dict[str, Optional[float]] = {}
        for key in ("open", "high", "low"):
            value = record.get(key, ohlc.get(key))
            if value is None:
                prices[key] = None
            else:
                prices[key] = _positive_number(value)
                if prices[key] is None:
                    return None

        if prices["high"] is not None and prices["low"] is not None:
            if prices["low"] > prices["high"]:
                return None

        volume = _non_negative_number(record.get("volume"))
        if record.get("volume") is not None and volume is None:
            return None

        depth = record.get("depth")
        if not isinstance(depth, dict):
            depth = {}

        def best_depth(side: str) -> Tuple[Optional[float], Optional[int]]:
            levels = depth.get(side)
            if not isinstance(levels, list):
                return None, None
            for level in levels:
                if not isinstance(level, dict):
                    continue
                price = _positive_number(level.get("price"))
                quantity = _non_negative_number(level.get("quantity"))
                if price is not None and quantity is not None and quantity > 0:
                    return price, int(quantity)
            return None, None

        bid, bid_quantity = best_depth("buy")
        ask, ask_quantity = best_depth("sell")
        if bid is not None and ask is not None and bid > ask:
            bid, bid_quantity, ask, ask_quantity = None, None, None, None

        exchange_timestamp = DhanLiveClient._exchange_timestamp(
            record.get("last_trade_time")
        )
        return {
            "symbol": symbol,
            "segment": segment,
            "open": prices["open"],
            "high": prices["high"],
            "low": prices["low"],
            "close": last_price,
            "bid": bid,
            "ask": ask,
            "bid_quantity": bid_quantity,
            "ask_quantity": ask_quantity,
            "volume": int(volume) if volume is not None else None,
            # This is the exchange's last-trade timestamp, if supplied.
            "timestamp": exchange_timestamp,
            "timestamp_basis": "exchange" if exchange_timestamp else None,
            "timestamp_kind": "exchange_trade" if exchange_timestamp else None,
            # Receipt time is useful for diagnostics only, never execution
            # provenance or a substitute for missing exchange trade time.
            "received_at_timestamp": received_at,
            # Keep local observation separate from the exchange's last-trade
            # timestamp above; neither field describes when depth changed.
            "observed_at": received_at,
        }

    def refresh_quotes(self, instruments: Iterable[Dict[str, Any]]) -> bool:
        """Refresh one batch of market quotes; return False unless all are valid."""
        if not self._has_credentials:
            self._set_error("Dhan credentials are not configured")
            return False

        try:
            instrument_list = list(instruments or [])
        except TypeError:
            self._set_error("Dhan quote instruments are invalid")
            return False

        if not instrument_list:
            self._set_error("No Dhan quote instruments were supplied")
            return False

        requested: Dict[Tuple[str, str], Dict[str, str]] = {}
        payload: Dict[str, List[int]] = {}
        for instrument in instrument_list:
            if not isinstance(instrument, dict):
                self._set_error("Dhan quote instruments are invalid")
                return False
            segment, security_id = self._instrument_values(instrument)
            if segment is None or security_id is None:
                self._set_error("Dhan quote instrument has an invalid segment or security ID")
                return False

            symbol = str(
                instrument.get("Symbol")
                or instrument.get("symbol")
                or security_id
            ).strip()
            if not symbol:
                self._set_error("Dhan quote instrument has an invalid symbol")
                return False
            requested[(segment, security_id)] = {
                "symbol": symbol,
                "segment": segment,
            }
            payload.setdefault(segment, [])
            numeric_id = int(security_id)
            if numeric_id not in payload[segment]:
                payload[segment].append(numeric_id)

        body = self._post_json(
            "/marketfeed/quote",
            payload,
            endpoint="quote",
        )
        if body is None:
            self._invalidate_quotes(
                security_id for _, security_id in requested
            )
            return False

        data = body.get("data")
        if not isinstance(data, dict):
            self._set_error("Dhan quote response did not contain market data")
            self._invalidate_quotes(
                security_id for _, security_id in requested
            )
            return False

        received_at = self._monotonic()
        received_timestamp = datetime.now(timezone.utc).isoformat()
        parsed: Dict[str, Dict[str, Any]] = {}
        missing = []
        for (segment, security_id), metadata in requested.items():
            segment_data = data.get(segment)
            if not isinstance(segment_data, dict):
                missing.append(security_id)
                continue
            record = segment_data.get(security_id)
            if not isinstance(record, dict):
                missing.append(security_id)
                continue
            quote = self._normalize_quote(
                record,
                symbol=metadata["symbol"],
                segment=segment,
                received_at=received_timestamp,
            )
            if quote is None:
                missing.append(security_id)
                continue
            parsed[security_id] = quote

        if missing:
            self._set_error("Dhan quote response was incomplete or contained invalid prices")
            self._invalidate_quotes(
                security_id for _, security_id in requested
            )
            return False

        with self._quote_lock:
            self.latest_prices.update(parsed)
            for (segment, security_id), metadata in requested.items():
                self._quote_received_at[security_id] = received_at
                self._instrument_meta[security_id] = metadata
                self._invalid_quotes.discard(security_id)

        self.subscribed = True
        self._set_error(None)
        return True

    def _invalidate_quotes(self, security_ids: Iterable[str]) -> None:
        with self._quote_lock:
            for security_id in security_ids:
                key = str(security_id)
                self.latest_prices.pop(key, None)
                self._quote_received_at.pop(key, None)
                self._invalid_quotes.add(key)
            self.subscribed = False

    def subscribe(self, instruments: List[Dict[str, Any]]) -> bool:
        """Compatibility shim for existing callers; fetches an initial quote batch."""
        self._subscribed_instruments = list(instruments or [])
        result = self.refresh_quotes(self._subscribed_instruments)
        self.subscribed = result
        return result

    def _quote_age(self, security_id: str) -> Optional[float]:
        received_at = self._quote_received_at.get(str(security_id))
        if received_at is None:
            return None
        return max(0.0, self._monotonic() - received_at)

    def get_live_data(
        self, security_id: Any, symbol: str = "", segment: str = "NSE_EQ"
    ) -> Dict[str, Any]:
        """Return the latest observed quote, explicitly marking missing/stale data."""
        key = str(security_id)
        with self._quote_lock:
            stored = self.latest_prices.get(key)
            received_at = self._quote_received_at.get(key)
            metadata = dict(self._instrument_meta.get(key, {}))
            invalid = key in self._invalid_quotes

        if (
            not self._cached_has_credentials
            or invalid
            or not isinstance(stored, dict)
            or received_at is None
        ):
            return {
                "symbol": symbol or metadata.get("symbol", ""),
                "segment": _SEGMENTS.get(str(segment).upper(), str(segment)),
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
                "timestamp": None,
                "age_seconds": None,
                "stale": True,
            }

        receipt_age = self._monotonic() - received_at
        quote = dict(stored)
        quote["symbol"] = symbol or quote.get("symbol", "")
        quote["segment"] = _SEGMENTS.get(
            str(segment).upper(), quote.get("segment", str(segment))
        )
        quote["receipt_age_seconds"] = round(max(0.0, receipt_age), 3)
        exchange_timestamp = self._exchange_timestamp(quote.get("timestamp"))
        exchange_age = None
        if exchange_timestamp is not None:
            parsed = datetime.fromisoformat(exchange_timestamp)
            exchange_age = (
                datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
            ).total_seconds()
        # Both the HTTP observation and the provider's actual trade must be
        # recent. Missing/sentinel/future exchange times are not executable.
        fresh_exchange_time = (
            exchange_age is not None
            and 0 <= exchange_age <= self.quote_max_age_seconds
        )
        quote["age_seconds"] = round(
            max(max(0.0, receipt_age), max(0.0, exchange_age or 0.0)), 3
        )
        quote["exchange_age_seconds"] = (
            round(exchange_age, 3) if exchange_age is not None else None
        )
        quote["stale"] = (
            receipt_age < 0
            or receipt_age > self.quote_max_age_seconds
            or not fresh_exchange_time
        )
        if quote["stale"]:
            # Preserve the observation time and age for diagnostics, but do not
            # expose an old price as usable market data to a trading caller.
            quote.update(
                {
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "bid": None,
                    "ask": None,
                    "bid_quantity": None,
                    "ask_quantity": None,
                    "volume": None,
                }
            )
        return quote

    @staticmethod
    def _normalize_underlying(
        underlying_id: Any, underlying_segment: str
    ) -> Tuple[Optional[int], Optional[str]]:
        try:
            parsed_id = int(str(underlying_id).strip())
        except (TypeError, ValueError, OverflowError):
            return None, None
        segment = _SEGMENTS.get(str(underlying_segment).strip().upper())
        if parsed_id <= 0 or segment is None:
            return None, None
        return parsed_id, segment

    def _get_expiry_list(
        self, symbol: str, underlying_id: int, underlying_segment: str
    ) -> Optional[List[str]]:
        cache_key = (symbol.upper(), str(underlying_id), underlying_segment)
        now = self._monotonic()
        cached = self._expiry_cache.get(cache_key)
        if cached and now - cached[1] <= EXPIRY_CACHE_SECONDS:
            return list(cached[0])

        body = self._post_json(
            "/optionchain/expirylist",
            {
                "UnderlyingScrip": underlying_id,
                "UnderlyingSeg": underlying_segment,
            },
            endpoint="option",
        )
        if body is None:
            return None
        raw_expiries = body.get("data")
        if not isinstance(raw_expiries, list):
            self._set_error("Dhan expiry response did not contain an expiry list")
            return None

        expiries = []
        for value in raw_expiries:
            if not isinstance(value, str):
                continue
            try:
                date.fromisoformat(value)
            except ValueError:
                continue
            if value not in expiries:
                expiries.append(value)
        expiries.sort()
        if not expiries:
            self._set_error("Dhan did not return any valid option expiries")
            return None

        self._expiry_cache[cache_key] = (expiries, self._monotonic())
        return list(expiries)

    def get_expiry_list(
        self,
        symbol: str,
        underlying_id: Any,
        underlying_segment: str = "IDX_I",
    ) -> Optional[List[str]]:
        """Return Dhan's valid expiry dates, cached for up to one hour."""
        parsed_id, segment = self._normalize_underlying(
            underlying_id, underlying_segment
        )
        if parsed_id is None or segment is None or not str(symbol).strip():
            self._set_error("Dhan option underlying is invalid")
            return None
        if not self._has_credentials:
            self._set_error("Dhan credentials are not configured")
            return None
        return self._get_expiry_list(str(symbol).strip(), parsed_id, segment)

    @staticmethod
    def _normalize_contract(record: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(record, dict):
            return None
        try:
            security_id = int(str(record.get("security_id", "")).strip())
        except (TypeError, ValueError, OverflowError):
            return None
        if security_id <= 0:
            return None

        def optional_price(key: str) -> Optional[float]:
            raw = record.get(key)
            if raw is None:
                return None
            return _positive_number(raw)

        last_price = optional_price("last_price")
        bid = optional_price("top_bid_price")
        ask = optional_price("top_ask_price")
        if bid is not None and ask is not None and bid > ask:
            bid, ask = None, None

        volume = _non_negative_number(record.get("volume"))
        open_interest = _non_negative_number(record.get("oi"))
        raw_greeks = record.get("greeks")
        greeks: Dict[str, Optional[float]] = {}
        if isinstance(raw_greeks, dict):
            for key in ("delta", "theta", "gamma", "vega"):
                value = raw_greeks.get(key)
                if value is None:
                    greeks[key] = None
                    continue
                try:
                    parsed = float(value)
                except (TypeError, ValueError, OverflowError):
                    parsed = None
                greeks[key] = (
                    parsed if parsed is not None and math.isfinite(parsed) else None
                )

        return {
            "security_id": security_id,
            "last_price": last_price,
            "top_bid_price": bid,
            "top_ask_price": ask,
            "volume": int(volume) if volume is not None else None,
            "oi": int(open_interest) if open_interest is not None else None,
            "greeks": greeks,
        }

    @staticmethod
    def _valid_option_quote(contract: Any) -> bool:
        if not isinstance(contract, dict):
            return False
        try:
            security_id = int(contract.get("security_id", 0))
        except (TypeError, ValueError, OverflowError):
            return False
        last_price = _positive_number(contract.get("last_price"))
        bid = _positive_number(contract.get("top_bid_price"))
        ask = _positive_number(contract.get("top_ask_price"))
        return bool(
            security_id > 0
            and last_price is not None
            and bid is not None
            and ask is not None
            and bid <= ask
        )

    @staticmethod
    def _option_identity(contract: Any) -> Optional[int]:
        """Return the chain contract security ID when its identity is valid."""
        if not isinstance(contract, dict):
            return None
        try:
            security_id = int(contract.get("security_id", 0))
        except (TypeError, ValueError, OverflowError):
            return None
        return security_id if security_id > 0 else None

    def refresh_option_chain(
        self,
        symbol: str,
        underlying_id: Any,
        underlying_segment: str = "IDX_I",
        expiry: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a normalized live option chain for one underlying and expiry."""
        normalized_symbol = str(symbol or "").strip().upper()
        parsed_id, segment = self._normalize_underlying(
            underlying_id, underlying_segment
        )
        if not normalized_symbol or parsed_id is None or segment is None:
            self._set_error("Dhan option underlying is invalid")
            return None
        if not self._has_credentials:
            self._set_error("Dhan credentials are not configured")
            return None

        use_default_expiry = expiry is None
        selected_expiry = expiry
        if selected_expiry is None:
            expiries = self._get_expiry_list(normalized_symbol, parsed_id, segment)
            if not expiries:
                return None
            today = date.today().isoformat()
            selected_expiry = next(
                (item for item in expiries if item >= today),
                None,
            )
            if selected_expiry is None:
                self._set_error("Dhan returned no unexpired option expiry")
                return None
        else:
            if not isinstance(selected_expiry, str):
                self._set_error("Dhan option expiry is invalid")
                return None
            try:
                expiry_date = date.fromisoformat(selected_expiry)
            except ValueError:
                self._set_error("Dhan option expiry is invalid")
                return None
            if expiry_date < date.today():
                self._set_error("Dhan option expiry has already passed")
                return None

        body = self._post_json(
            "/optionchain",
            {
                "UnderlyingScrip": parsed_id,
                "UnderlyingSeg": segment,
                "Expiry": selected_expiry,
            },
            endpoint="option",
        )
        if body is None:
            return None

        data = body.get("data")
        if not isinstance(data, dict):
            self._set_error("Dhan option-chain response did not contain market data")
            return None
        underlying_price = _positive_number(data.get("last_price"))
        raw_options = data.get("oc")
        if underlying_price is None or not isinstance(raw_options, dict):
            self._set_error("Dhan option-chain response contained invalid prices")
            return None

        options: Dict[str, Dict[str, Any]] = {}
        for raw_strike, raw_sides in raw_options.items():
            strike_key = _canonical_strike(raw_strike)
            if strike_key is None or not isinstance(raw_sides, dict):
                continue
            strike = float(strike_key)
            sides: Dict[str, Any] = {"strike": strike}
            for option_type, raw_key in (("CE", "ce"), ("PE", "pe")):
                contract = self._normalize_contract(raw_sides.get(raw_key))
                if contract is not None:
                    sides[option_type] = contract
            if "CE" in sides or "PE" in sides:
                options[strike_key] = sides

        if not options:
            self._set_error("Dhan option-chain response contained no valid contracts")
            return None

        received_at = self._monotonic()
        observed_at = datetime.now(timezone.utc).isoformat()
        chain = {
            "symbol": normalized_symbol,
            "underlying_id": parsed_id,
            "underlying_segment": segment,
            "expiry": selected_expiry,
            "underlying_price": underlying_price,
            # The option-chain endpoint does not document an exchange trade
            # timestamp. Keep its local response receipt separate and do not
            # use it as option-price provenance.
            "timestamp": None,
            "timestamp_basis": "receipt",
            "received_at_timestamp": observed_at,
            "observed_at": observed_at,
            "options": options,
        }
        with self._option_lock:
            chain_key = (normalized_symbol, selected_expiry)
            self.option_chains[chain_key] = chain
            self._option_received_at[chain_key] = received_at
            if use_default_expiry:
                self._latest_option_expiry[normalized_symbol] = selected_expiry
        self._set_error(None)
        return self._chain_with_age(normalized_symbol, selected_expiry)

    def _chain_with_age(
        self, symbol: str, expiry: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        key = str(symbol or "").strip().upper()
        with self._option_lock:
            selected_expiry = expiry or self._latest_option_expiry.get(key)
            if selected_expiry is None:
                cached_expiries = sorted(
                    cached_expiry
                    for cached_symbol, cached_expiry in self.option_chains
                    if cached_symbol == key
                )
                selected_expiry = next(
                    (item for item in cached_expiries if item >= date.today().isoformat()),
                    None,
                )
            chain_key = (key, selected_expiry) if selected_expiry else None
            stored = self.option_chains.get(chain_key) if chain_key else None
            received_at = self._option_received_at.get(chain_key) if chain_key else None
            chain = dict(stored) if isinstance(stored, dict) else None
        if chain is None or received_at is None:
            return None
        age = max(0.0, self._monotonic() - received_at)
        chain["age_seconds"] = round(age, 3)
        chain["stale"] = age > self.option_max_age_seconds
        return chain

    def _find_option(
        self,
        symbol: str,
        strike: Any,
        option_type: str,
        expiry: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        chain = self._chain_with_age(symbol, expiry)
        if (
            chain is None
            or chain.get("stale")
        ):
            return None
        strike_key = _canonical_strike(strike)
        if strike_key is None:
            return None
        normalized_type = str(option_type or "").strip().upper()
        normalized_type = {
            "CALL": "CE",
            "PUT": "PE",
        }.get(normalized_type, normalized_type)
        if normalized_type not in ("CE", "PE"):
            return None
        strike_row = chain.get("options", {}).get(strike_key)
        if not isinstance(strike_row, dict):
            return None
        contract = strike_row.get(normalized_type)
        security_id = self._option_identity(contract)
        if security_id is None:
            return None
        quote = self._cached_option_quote(
            symbol=chain["symbol"],
            expiry=chain["expiry"],
            strike=strike_key,
            option_type=normalized_type,
            expected_security_id=security_id,
        )
        return quote if quote and not quote.get("stale") else None

    def _cached_option_quote(
        self,
        *,
        symbol: str,
        expiry: str,
        strike: str,
        option_type: str,
        expected_security_id: int,
    ) -> Optional[Dict[str, Any]]:
        cache_key = (symbol.upper(), expiry, strike, option_type)
        with self._option_lock:
            stored = self._option_contract_quotes.get(cache_key)
            received_at = self._option_quote_received_at.get(cache_key)
            quote = dict(stored) if isinstance(stored, dict) else None
        if (
            quote is None
            or received_at is None
            or quote.get("security_id") != expected_security_id
        ):
            return None

        receipt_age = self._monotonic() - received_at
        timestamp = self._exchange_timestamp(quote.get("timestamp"))
        exchange_age = None
        if timestamp is not None:
            parsed = datetime.fromisoformat(timestamp)
            exchange_age = (
                datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
            ).total_seconds()
        if (
            receipt_age < 0
            or receipt_age > self.option_max_age_seconds
            or exchange_age is None
            or exchange_age < 0
            or exchange_age > self.option_max_age_seconds
        ):
            quote.update(
                {
                    "close": None,
                    "bid": None,
                    "ask": None,
                    "stale": True,
                }
            )
            return quote
        quote["receipt_age_seconds"] = round(receipt_age, 3)
        quote["exchange_age_seconds"] = round(exchange_age, 3)
        quote["age_seconds"] = round(max(receipt_age, exchange_age), 3)
        quote["stale"] = False
        return quote

    def refresh_option_quote(
        self,
        symbol: str,
        strike: Any,
        option_type: str,
        expiry: str,
    ) -> Optional[Dict[str, Any]]:
        """Refresh an exact contract, keeping trade time distinct from observation.

        Dhan's quote record supplies a last-trade timestamp, not a depth-update
        timestamp. ``observed_at`` records when this client received the data.
        """
        normalized_symbol = str(symbol or "").strip().upper()
        normalized_type = str(option_type or "").strip().upper()
        strike_key = _canonical_strike(strike)
        chain = self._chain_with_age(normalized_symbol, expiry)
        if (
            chain is None
            or chain.get("stale")
            or strike_key is None
            or normalized_type not in {"CE", "PE"}
        ):
            return None
        contract = (
            chain.get("options", {})
            .get(strike_key, {})
            .get(normalized_type)
        )
        security_id = self._option_identity(contract)
        if security_id is None:
            return None

        option_segment = (
            "BSE_FNO"
            if chain.get("underlying_segment") == "BSE_I"
            or normalized_symbol == "SENSEX"
            else "NSE_FNO"
        )
        cache_key = (normalized_symbol, expiry, strike_key, normalized_type)
        with self._option_lock:
            self._option_quote_attempted_at[cache_key] = self._monotonic()
        body = self._post_json(
            "/marketfeed/quote",
            {option_segment: [security_id]},
            endpoint="quote",
        )
        if body is None:
            with self._option_lock:
                self._option_contract_quotes.pop(cache_key, None)
                self._option_quote_received_at.pop(cache_key, None)
            return None
        data = body.get("data")
        segment_data = data.get(option_segment) if isinstance(data, dict) else None
        record = segment_data.get(str(security_id)) if isinstance(segment_data, dict) else None
        if not isinstance(record, dict):
            self._set_error("Dhan option quote response omitted the requested contract")
            with self._option_lock:
                self._option_contract_quotes.pop(cache_key, None)
                self._option_quote_received_at.pop(cache_key, None)
            return None

        received_at_timestamp = datetime.now(timezone.utc).isoformat()
        quote = self._normalize_quote(
            record,
            symbol=normalized_symbol,
            segment=option_segment,
            received_at=received_at_timestamp,
        )
        if quote is None:
            self._set_error("Dhan option quote response contained invalid prices")
            with self._option_lock:
                self._option_contract_quotes.pop(cache_key, None)
                self._option_quote_received_at.pop(cache_key, None)
            return None
        quote.update(
            {
                "security_id": security_id,
                "underlying_id": chain["underlying_id"],
                "underlying_segment": chain["underlying_segment"],
                "underlying_price": chain["underlying_price"],
                "strike": float(strike_key),
                "option_type": normalized_type,
                "expiry": expiry,
            }
        )
        with self._option_lock:
            self._option_contract_quotes[cache_key] = quote
            self._option_quote_received_at[cache_key] = self._monotonic()
            self._option_quote_attempted_at[cache_key] = self._option_quote_received_at[
                cache_key
            ]
        refreshed = self._cached_option_quote(
            symbol=normalized_symbol,
            expiry=expiry,
            strike=strike_key,
            option_type=normalized_type,
            expected_security_id=security_id,
        )
        return refreshed if refreshed and not refreshed.get("stale") else None

    def select_atm_option(
        self, symbol: str, direction: str
    ) -> Optional[Dict[str, Any]]:
        """Select an exact ATM contract identity from the cached option chain.

        This method is deliberately cache-only. Its result identifies a chain
        contract but is not an exchange-timed quote; call
        :meth:`refresh_option_quote` explicitly to obtain a live mark.
        """
        chain = self._chain_with_age(symbol)
        if chain is None or chain.get("stale"):
            return None
        option_type = {"BUY": "CE", "SELL": "PE"}.get(
            str(direction or "").strip().upper()
        )
        if option_type is None:
            return None

        candidates = []
        for strike_key, strike_row in chain.get("options", {}).items():
            if not isinstance(strike_row, dict):
                continue
            try:
                strike = float(strike_key)
            except (TypeError, ValueError):
                continue
            contract = strike_row.get(option_type)
            if self._option_identity(contract) is not None:
                candidates.append((abs(strike - chain["underlying_price"]), strike))
        if not candidates:
            return None
        _, strike = min(candidates, key=lambda item: (item[0], item[1]))
        strike_key = _canonical_strike(strike)
        contract = (
            chain.get("options", {})
            .get(strike_key, {})
            .get(option_type)
        )
        security_id = self._option_identity(contract)
        if security_id is None:
            return None
        return {
            "symbol": chain["symbol"],
            "security_id": security_id,
            "underlying_id": chain["underlying_id"],
            "underlying_segment": chain["underlying_segment"],
            "underlying_price": chain["underlying_price"],
            "strike": float(strike_key),
            "option_type": option_type,
            "expiry": chain["expiry"],
            "source": "option_chain",
            "chain_observed_at": chain.get("observed_at")
            or chain.get("received_at_timestamp"),
            "chain_age_seconds": chain.get("age_seconds"),
        }

    def get_option_quote(
        self,
        symbol: str,
        strike: Any,
        option_type: str,
        expiry: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a fresh exact-contract quote from cache, without network I/O.

        Use :meth:`refresh_option_quote` explicitly when a missing or stale
        cached mark needs refreshing.
        """
        return self._find_option(symbol, strike, option_type, expiry)

    def get_market_snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot with no credential material."""
        prices: Dict[str, Dict[str, Any]] = {}
        with self._quote_lock:
            instrument_meta = list(self._instrument_meta.items())
        for security_id, metadata in instrument_meta:
            quote = self.get_live_data(
                security_id,
                metadata.get("symbol", ""),
                metadata.get("segment", "NSE_EQ"),
            )
            prices[metadata.get("symbol") or security_id] = quote

        chains: Dict[str, Dict[str, Any]] = {}
        with self._option_lock:
            chain_keys = list(self.option_chains)
        for symbol, expiry in chain_keys:
            chain = self._chain_with_age(symbol, expiry)
            if chain is not None:
                chains[f"{symbol}:{expiry}"] = chain

        has_fresh_market_data = any(
            not quote["stale"] and quote["close"] is not None
            for quote in prices.values()
        ) or any(not chain["stale"] for chain in chains.values())
        has_cached_data = bool(prices or chains)
        if not self._cached_has_credentials:
            status = "credentials_missing"
        elif has_fresh_market_data:
            status = "live"
        elif has_cached_data:
            status = "stale"
        else:
            status = "waiting_for_data"

        return {
            "source": "DhanHQ",
            "status": status,
            "connected": status == "live",
            "last_error": self.last_error,
            "prices": prices,
            "option_chains": chains,
        }

    def close(self) -> None:
        """Compatibility no-op; REST requests do not keep a streaming session."""
        self.subscribed = False
        close = getattr(self._session, "close", None)
        if callable(close):
            close()