"""Read-only DhanHQ historical OHLCV and rolling expired-option data helpers."""

import csv
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests


BASE_URL = "https://api.dhan.co/v2"
REQUEST_TIMEOUT_SECONDS = 20
MAX_INTRADAY_RANGE_DAYS = 90
MAX_ROLLING_OPTION_RANGE_DAYS = 30
_SEGMENTS = {
    "NSE_EQ",
    "NSE_FNO",
    "BSE_EQ",
    "BSE_FNO",
    "MCX_COMM",
    "IDX_I",
}
_DAILY_INSTRUMENTS = {
    "EQUITY",
    "INDEX",
    "FUTIDX",
    "OPTIDX",
    "FUTSTK",
    "OPTSTK",
    "FUTCOM",
}
_INTRADAY_INTERVALS = {"1", "5", "15", "30", "60"}
_ROLLING_INTERVALS = {"1", "5", "15", "25", "60"}
_ROLLING_DATA = {"open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"}


class DhanHistoryError(RuntimeError):
    """Sanitized error raised when Dhan historical data is unavailable/invalid."""


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"{field} must be a date or YYYY-MM-DD string")


def _instrument_values(
    security_id: Any, exchange_segment: str, instrument: str
) -> tuple:
    try:
        normalized_id = str(int(str(security_id).strip()))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("security_id must be a positive integer") from None
    if int(normalized_id) <= 0:
        raise ValueError("security_id must be a positive integer")
    segment = str(exchange_segment or "").strip().upper()
    if segment not in _SEGMENTS:
        raise ValueError("exchange_segment is not a supported Dhan segment")
    kind = str(instrument or "").strip().upper()
    if kind not in _DAILY_INSTRUMENTS:
        raise ValueError("instrument is not a supported Dhan historical instrument")
    return normalized_id, segment, kind


def _parse_candles(body: Any) -> List[Dict[str, Any]]:
    """Validate Dhan's parallel OHLCV arrays; do not manufacture missing bars."""
    if not isinstance(body, dict):
        raise DhanHistoryError("Dhan historical response was not an object")
    if body.get("status") is not None and str(body.get("status")).lower() != "success":
        raise DhanHistoryError("Dhan historical API reported a failure")
    payload = body.get("data", body)
    if not isinstance(payload, dict):
        raise DhanHistoryError("Dhan historical response did not contain candle arrays")

    names = ("open", "high", "low", "close", "volume", "timestamp")
    arrays = {name: payload.get(name) for name in names}
    if any(not isinstance(value, list) for value in arrays.values()):
        raise DhanHistoryError("Dhan historical response omitted required candle arrays")
    count = len(arrays["timestamp"])
    if any(len(value) != count for value in arrays.values()):
        raise DhanHistoryError("Dhan historical candle arrays have mismatched lengths")
    interest = payload.get("open_interest")
    if interest == []:
        interest = None
    if interest is not None and (not isinstance(interest, list) or len(interest) != count):
        raise DhanHistoryError("Dhan historical open-interest array has invalid length")

    rows = []
    previous_epoch = None
    for index in range(count):
        try:
            epoch_value = float(arrays["timestamp"][index])
            if (
                not math.isfinite(epoch_value)
                or epoch_value < 0
                or not epoch_value.is_integer()
            ):
                raise ValueError
            epoch = int(epoch_value)
            timestamp = datetime.fromtimestamp(epoch, timezone.utc).isoformat()
            prices = {
                name: float(arrays[name][index])
                for name in ("open", "high", "low", "close")
            }
            volume = float(arrays["volume"][index])
        except (TypeError, ValueError, OverflowError):
            raise DhanHistoryError("Dhan historical response contains invalid candle values") from None
        if (
            any(not math.isfinite(value) or value <= 0 for value in prices.values())
            or prices["low"] > min(prices["open"], prices["close"])
            or prices["high"] < max(prices["open"], prices["close"])
            or prices["low"] > prices["high"]
            or not math.isfinite(volume)
            or volume < 0
            or not volume.is_integer()
            or (previous_epoch is not None and epoch <= previous_epoch)
        ):
            raise DhanHistoryError("Dhan historical response contains invalid candle values")
        previous_epoch = epoch
        row = {
            **prices,
            "volume": int(volume),
            "timestamp_epoch": epoch,
            "timestamp": timestamp,
            "data_source": "DHAN_HISTORICAL",
        }
        if interest is not None:
            try:
                oi = float(interest[index])
            except (TypeError, ValueError, OverflowError):
                raise DhanHistoryError("Dhan historical open interest is invalid") from None
            if not math.isfinite(oi) or oi < 0 or not oi.is_integer():
                raise DhanHistoryError("Dhan historical open interest is invalid")
            row["open_interest"] = int(oi)
        rows.append(row)
    return rows


class DhanHistoryClient:
    """Fetch authentic Dhan historical data; contains no trading operations."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        *,
        access_token: Optional[str] = None,
    ):
        self._access_token = (
            os.getenv("DHAN_ACCESS_TOKEN", "").strip()
            if access_token is None
            else str(access_token).strip()
        )
        self._session = session or requests.Session()
        self.last_error: Optional[str] = None

    def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._access_token:
            self.last_error = "Dhan access token is not configured"
            return None
        try:
            response = self._session.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers={
                    "access-token": self._access_token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            self.last_error = "Dhan historical-data request failed"
            return None
        except Exception:
            self.last_error = "Dhan historical-data request failed"
            return None
        code = getattr(response, "status_code", None)
        if not isinstance(code, int) or not 200 <= code < 300:
            self.last_error = (
                f"Dhan historical-data request returned HTTP {code}"
                if isinstance(code, int)
                else "Dhan historical-data request returned an invalid response"
            )
            return None
        try:
            body = response.json()
        except (ValueError, TypeError):
            self.last_error = "Dhan historical-data response was not valid JSON"
            return None
        self.last_error = None
        return body if isinstance(body, dict) else None

    def fetch_daily(
        self,
        security_id: Any,
        exchange_segment: str,
        instrument: str,
        from_date: Any,
        to_date: Any,
        *,
        expiry_code: int = 0,
        oi: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch daily candles; to_date follows Dhan's non-inclusive semantics."""
        normalized_id, segment, kind = _instrument_values(
            security_id, exchange_segment, instrument
        )
        start = _date_value(from_date, "from_date")
        end = _date_value(to_date, "to_date")
        if end <= start:
            raise ValueError("to_date must be after from_date")
        if isinstance(expiry_code, bool) or not isinstance(expiry_code, int) or expiry_code < 0:
            raise ValueError("expiry_code must be a non-negative integer")
        body = self._post(
            "/charts/historical",
            {
                "securityId": normalized_id,
                "exchangeSegment": segment,
                "instrument": kind,
                "expiryCode": expiry_code,
                "oi": bool(oi),
                "fromDate": start.isoformat(),
                "toDate": end.isoformat(),
            },
        )
        if body is None:
            raise DhanHistoryError(self.last_error or "Dhan historical data unavailable")
        return _parse_candles(body)

    def fetch_intraday(
        self,
        security_id: Any,
        exchange_segment: str,
        instrument: str,
        interval: Any,
        from_date: Any,
        to_date: Any,
        *,
        oi: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch authentic 1/5/15/30/60-minute candles, at most 90 days per call."""
        normalized_id, segment, kind = _instrument_values(
            security_id, exchange_segment, instrument
        )
        normalized_interval = str(interval)
        if normalized_interval not in _INTRADAY_INTERVALS:
            raise ValueError("interval must be one of 1, 5, 15, 30, or 60 minutes")
        start = _date_value(from_date, "from_date")
        end = _date_value(to_date, "to_date")
        if end <= start:
            raise ValueError("to_date must be after from_date")
        if end - start > timedelta(days=MAX_INTRADAY_RANGE_DAYS):
            raise ValueError("intraday range cannot exceed Dhan's 90-day request window")
        body = self._post(
            "/charts/intraday",
            {
                "securityId": normalized_id,
                "exchangeSegment": segment,
                "instrument": kind,
                "interval": normalized_interval,
                "oi": bool(oi),
                "fromDate": start.isoformat(),
                "toDate": end.isoformat(),
            },
        )
        if body is None:
            raise DhanHistoryError(self.last_error or "Dhan intraday data unavailable")
        return _parse_candles(body)

    def fetch_expired_options(
        self,
        underlying_security_id: Any,
        exchange_segment: str,
        instrument: str,
        interval: Any,
        expiry_flag: str,
        expiry_code: int,
        strike: str,
        option_type: str,
        from_date: Any,
        to_date: Any,
        *,
        required_data: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch genuine rolling expired-option OHLC/IV/OI data (not bid/ask).

        Dhan's API returns minute bars identified by ATM-relative strike. It
        does not provide historical bid/ask quotes or guarantee a fixed-strike
        series, so these results cannot prove executable historical fills.
        """
        normalized_id, segment, kind = _instrument_values(
            underlying_security_id, exchange_segment, instrument
        )
        if segment not in {"NSE_FNO", "BSE_FNO"} or kind not in {"OPTIDX", "OPTSTK"}:
            raise ValueError("expired options require an F&O segment and OPTIDX/OPTSTK")
        normalized_interval = str(interval)
        if normalized_interval not in _ROLLING_INTERVALS:
            raise ValueError("expired-option interval must be 1, 5, 15, 25, or 60 minutes")
        normalized_flag = str(expiry_flag or "").strip().upper()
        if normalized_flag not in {"WEEK", "MONTH"}:
            raise ValueError("expiry_flag must be WEEK or MONTH")
        if isinstance(expiry_code, bool) or not isinstance(expiry_code, int) or expiry_code < 0:
            raise ValueError("expiry_code must be a non-negative Dhan derivative expiry code")
        normalized_strike = str(strike or "").strip().upper()
        if not re.fullmatch(r"ATM(?:[+-](?:[1-9]|10))?", normalized_strike):
            raise ValueError("strike must be ATM or an ATM-relative strike selector")
        if kind == "OPTSTK" and normalized_strike not in {"ATM", "ATM+1", "ATM-1", "ATM+2", "ATM-2", "ATM+3", "ATM-3"}:
            raise ValueError("stock options support only ATM through ATM +/- 3")
        normalized_type = str(option_type or "").strip().upper()
        if normalized_type not in {"CALL", "PUT"}:
            raise ValueError("option_type must be CALL or PUT")
        start = _date_value(from_date, "from_date")
        end = _date_value(to_date, "to_date")
        if end <= start:
            raise ValueError("to_date must be after from_date")
        if end - start > timedelta(days=MAX_ROLLING_OPTION_RANGE_DAYS):
            raise ValueError("expired-option range cannot exceed Dhan's 30-day request window")

        data_fields = [str(item).strip().lower() for item in (required_data or ("open", "high", "low", "close", "volume"))]
        if not data_fields or any(field not in _ROLLING_DATA for field in data_fields):
            raise ValueError("required_data contains an unsupported Dhan option data field")
        for field in ("open", "high", "low", "close", "volume"):
            if field not in data_fields:
                data_fields.append(field)
        body = self._post(
            "/charts/rollingoption",
            {
                "exchangeSegment": segment,
                "interval": normalized_interval,
                "securityId": int(normalized_id),
                "instrument": kind,
                "expiryFlag": normalized_flag,
                "expiryCode": expiry_code,
                "strike": normalized_strike,
                "drvOptionType": normalized_type,
                "requiredData": data_fields,
                "fromDate": start.isoformat(),
                "toDate": end.isoformat(),
            },
        )
        if body is None:
            raise DhanHistoryError(self.last_error or "Dhan expired-option data unavailable")
        data = body.get("data", body)
        side_key = "ce" if normalized_type == "CALL" else "pe"
        side_data = data.get(side_key) if isinstance(data, dict) else None
        if not isinstance(side_data, dict):
            raise DhanHistoryError("Dhan expired-option response omitted the requested option side")
        timestamps = side_data.get("timestamp")
        if not isinstance(timestamps, list):
            raise DhanHistoryError("Dhan expired-option response omitted timestamps")
        count = len(timestamps)
        arrays = {field: side_data.get(field) for field in data_fields}
        if any(not isinstance(values, list) or len(values) != count for values in arrays.values()):
            raise DhanHistoryError("Dhan expired-option arrays are incomplete or mismatched")
        rows = []
        previous_epoch = None
        for index, raw_epoch in enumerate(timestamps):
            try:
                epoch_num = float(raw_epoch)
                if (
                    not math.isfinite(epoch_num)
                    or epoch_num < 0
                    or not epoch_num.is_integer()
                ):
                    raise ValueError
                epoch = int(epoch_num)
                timestamp = datetime.fromtimestamp(epoch, timezone.utc).isoformat()
                row: Dict[str, Any] = {}
                for field, values in arrays.items():
                    value = float(values[index])
                    if not math.isfinite(value) or value < 0:
                        raise ValueError
                    if field in {"volume", "oi"} and not value.is_integer():
                        raise ValueError
                    row[field] = value if field in {"iv"} else int(value) if field in {"volume", "oi"} else value
                ohlc = {field: row[field] for field in ("open", "high", "low", "close")}
                if (
                    (previous_epoch is not None and epoch <= previous_epoch)
                    or any(value <= 0 for value in ohlc.values())
                    or ohlc["low"] > min(ohlc["open"], ohlc["close"])
                    or ohlc["high"] < max(ohlc["open"], ohlc["close"])
                    or ohlc["low"] > ohlc["high"]
                ):
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                raise DhanHistoryError("Dhan expired-option response contains invalid candle values") from None
            previous_epoch = epoch
            row.update(
                {
                    "timestamp_epoch": epoch,
                    "timestamp": timestamp,
                    "underlying_security_id": int(normalized_id),
                    "exchange_segment": segment,
                    "instrument": kind,
                    "expiry_flag": normalized_flag,
                    "expiry_code": expiry_code,
                    "strike_selector": normalized_strike,
                    "option_type": normalized_type,
                    "data_source": "DHAN_EXPIRED_OPTION_HISTORICAL",
                }
            )
            for optional_field in ("strike", "spot"):
                optional_array = side_data.get(optional_field)
                if isinstance(optional_array, list) and len(optional_array) == count:
                    try:
                        row[optional_field] = float(optional_array[index])
                    except (TypeError, ValueError, OverflowError):
                        row[optional_field] = None
            rows.append(row)
        return rows

    @staticmethod
    def export_csv(rows: Iterable[Dict[str, Any]], destination: Any) -> int:
        """Export fetched provider rows as CSV; returns the number of written rows."""
        materialized = list(rows)
        if not materialized:
            raise ValueError("No authentic historical rows are available to export")
        if any(not isinstance(row, dict) for row in materialized):
            raise ValueError("Historical export rows must be objects")
        fieldnames = list(dict.fromkeys(key for row in materialized for key in row))
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(materialized)
        return len(materialized)

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()