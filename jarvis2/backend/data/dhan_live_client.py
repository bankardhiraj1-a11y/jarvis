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

import requests


BASE_URL = "https://api.dhan.co/v2"
REQUEST_TIMEOUT_SECONDS = 10
QUOTE_MIN_INTERVAL_SECONDS = 1.0
OPTION_MIN_INTERVAL_SECONDS = 3.0
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
        self._client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
        self._access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
        self._session = session or requests.Session()

        self.quote_max_age_seconds = max(0.0, float(quote_max_age_seconds))
        self.option_max_age_seconds = max(0.0, float(option_max_age_seconds))

        self.latest_prices: Dict[str, Dict[str, Any]] = {}
        self.option_chains: Dict[str, Dict[str, Any]] = {}
        self.subscribed = False
        self.last_error: Optional[str] = None

        self._quote_received_at: Dict[str, float] = {}
        self._option_received_at: Dict[str, float] = {}
        self._invalid_quotes = set()
        self._instrument_meta: Dict[str, Dict[str, str]] = {}
        self._subscribed_instruments: List[Dict[str, str]] = []
        self._expiry_cache: Dict[Tuple[str, str, str], Tuple[List[str], float]] = {}

        self._monotonic = time.monotonic
        self._sleep = time.sleep
        self._quote_lock = Lock()
        self._option_lock = Lock()
        self._quote_rate_lock = Lock()
        self._option_rate_lock = Lock()
        self._last_quote_request_at: Optional[float] = None
        self._last_option_request_at: Optional[float] = None

    @property
    def _has_credentials(self) -> bool:
        return bool(self._client_id and self._access_token)

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
    def _normalize_quote(
        record: Dict[str, Any], *, symbol: str, segment: str, timestamp: str
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

        return {
            "symbol": symbol,
            "segment": segment,
            "open": prices["open"],
            "high": prices["high"],
            "low": prices["low"],
            "close": last_price,
            "volume": int(volume) if volume is not None else None,
            "timestamp": timestamp,
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

        timestamp = datetime.now(timezone.utc).isoformat()
        received_at = self._monotonic()
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
                timestamp=timestamp,
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
            not self._has_credentials
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

        age = max(0.0, self._monotonic() - received_at)
        quote = dict(stored)
        quote["symbol"] = symbol or quote.get("symbol", "")
        quote["segment"] = _SEGMENTS.get(
            str(segment).upper(), quote.get("segment", str(segment))
        )
        quote["age_seconds"] = round(age, 3)
        quote["stale"] = age > self.quote_max_age_seconds
        if quote["stale"]:
            # Preserve the observation time and age for diagnostics, but do not
            # expose an old price as usable market data to a trading caller.
            quote.update(
                {
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
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
        chain = {
            "symbol": normalized_symbol,
            "underlying_id": parsed_id,
            "underlying_segment": segment,
            "expiry": selected_expiry,
            "underlying_price": underlying_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "options": options,
        }
        with self._option_lock:
            self.option_chains[normalized_symbol] = chain
            self._option_received_at[normalized_symbol] = received_at
        self._set_error(None)
        return self._chain_with_age(normalized_symbol)

    def _chain_with_age(self, symbol: str) -> Optional[Dict[str, Any]]:
        key = str(symbol or "").strip().upper()
        with self._option_lock:
            stored = self.option_chains.get(key)
            received_at = self._option_received_at.get(key)
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
        chain = self._chain_with_age(symbol)
        if (
            chain is None
            or chain.get("stale")
            or (expiry is not None and expiry != chain.get("expiry"))
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
        if not self._valid_option_quote(contract):
            return None
        return {
            **contract,
            "symbol": chain["symbol"],
            "underlying_id": chain["underlying_id"],
            "underlying_segment": chain["underlying_segment"],
            "underlying_price": chain["underlying_price"],
            "strike": float(strike_key),
            "option_type": normalized_type,
            "expiry": chain["expiry"],
            "timestamp": chain["timestamp"],
            "age_seconds": chain["age_seconds"],
            "stale": False,
        }

    def select_atm_option(
        self, symbol: str, direction: str
    ) -> Optional[Dict[str, Any]]:
        """Select a real, quoted ATM CE for BUY or PE for SELL."""
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
            if self._valid_option_quote(contract):
                candidates.append((abs(strike - chain["underlying_price"]), strike))
        if not candidates:
            return None
        _, strike = min(candidates, key=lambda item: (item[0], item[1]))
        return self._find_option(
            symbol,
            strike,
            option_type,
            expiry=chain.get("expiry"),
        )

    def get_option_quote(
        self,
        symbol: str,
        strike: Any,
        option_type: str,
        expiry: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return only a fresh, fully quoted contract from the current chain."""
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
            chain_symbols = list(self.option_chains)
        for symbol in chain_symbols:
            chain = self._chain_with_age(symbol)
            if chain is not None:
                chains[symbol] = chain

        has_fresh_market_data = any(
            not quote["stale"] and quote["close"] is not None
            for quote in prices.values()
        ) or any(not chain["stale"] for chain in chains.values())
        has_cached_data = bool(prices or chains)
        if not self._has_credentials:
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