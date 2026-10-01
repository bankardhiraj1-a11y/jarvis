"""Source-labelled, cached USD-to-INR daily reference FX and P&L helpers.

The European Central Bank (ECB) publishes INR/EUR and USD/EUR reference
series. Their rates from the same observation day yield INR per USD via
INR/EUR divided by USD/EUR. This is a daily reporting reference, not an
executable quote. Refresh this service in a background task, never in a GET
handler.
"""

import csv
import io
import math
import threading
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional

import requests


ECB_SERIES = {
    "usd_per_eur": "D.USD.EUR.SP00.A",
    "inr_per_eur": "D.INR.EUR.SP00.A",
}
ECB_DATA_URL = "https://data-api.ecb.europa.eu/service/data/EXR/{}"
ECB_SOURCE_NAME = "European Central Bank daily reference rates"
ECB_SOURCE_URL = "https://data.ecb.europa.eu/data/datasets/EXR"
ECB_USER_AGENT = "Jarvis2-USD-INR-Daily-Reference/1.0"
MAX_FX_AGE_DAYS = 4
ECB_LOOKBACK_OBSERVATIONS = 14
ECB_MAX_REQUEST_ATTEMPTS = 2
_CENT = Decimal("0.01")
_RATE_QUANTUM = Decimal("0.00000001")


class FxRateUnavailable(RuntimeError):
    """A clean, non-sensitive error returned when sourced FX cannot be used."""


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite decimal number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite decimal number") from exc
    if not result.is_finite():
        raise ValueError(f"{label} must be a finite decimal number")
    return result


def _round_money(value: Decimal) -> float:
    return float(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def _now_utc(value: Optional[datetime] = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise ValueError("FX freshness requires a timezone-aware current time")
    return result.astimezone(timezone.utc)


def _parse_ecb_csv(response: Any) -> Dict[date, Decimal]:
    """Parse only dated official observations; reject malformed responses."""
    response.raise_for_status()
    text = response.text
    if not isinstance(text, str) or len(text.encode("utf-8")) > 1_048_576:
        raise ValueError("The FX reference response is missing or too large")
    observations: Dict[date, Decimal] = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            observation_date = date.fromisoformat(row["TIME_PERIOD"])
            rate = _decimal(row["OBS_VALUE"], "ECB rate")
        except (KeyError, TypeError, ValueError):
            continue
        if rate > 0:
            observations[observation_date] = rate
    if not observations:
        raise ValueError("The FX reference response contains no valid observations")
    return observations


def _public_snapshot(record: Optional[dict], now: datetime, reason: Optional[str] = None) -> dict:
    source_urls = {
        name: ECB_DATA_URL.format(series_key)
        for name, series_key in ECB_SERIES.items()
    }
    if record is None:
        return {
            "status": "unavailable",
            "rate": None,
            "from_currency": "USD",
            "to_currency": "INR",
            "source": ECB_SOURCE_NAME,
            "source_url": ECB_SOURCE_URL,
            "source_observation_urls": source_urls,
            "conversion_method": "same_date_inr_per_eur_divided_by_usd_per_eur",
            "source_series": dict(ECB_SERIES),
            "rate_type": "daily_reference_not_executable",
            "source_date": None,
            "retrieved_at": None,
            "age_days": None,
            "max_age_days": MAX_FX_AGE_DAYS,
            "reason": reason or "rate_not_loaded",
        }

    age_days = (now.date() - record["source_date"]).days
    fresh = 0 <= age_days <= MAX_FX_AGE_DAYS
    return {
        "status": "available" if fresh else "stale",
        "rate": float(record["rate"]) if fresh else None,
        "last_published_rate": float(record["rate"]),
        "from_currency": "USD",
        "to_currency": "INR",
        "source": ECB_SOURCE_NAME,
        "source_url": ECB_SOURCE_URL,
        "source_observation_urls": source_urls,
        "source_series": dict(ECB_SERIES),
        "conversion_method": "same_date_inr_per_eur_divided_by_usd_per_eur",
        "rate_type": "daily_reference_not_executable",
        "source_date": record["source_date"].isoformat(),
        "retrieved_at": record["retrieved_at"],
        "age_days": age_days,
        "max_age_days": MAX_FX_AGE_DAYS,
        "reason": (
            reason
            or (None if fresh else "published_reference_rate_exceeds_maximum_age")
        ),
    }


class EcbUsdInrRateProvider:
    """Retrieve/retain daily official reference rates; reads never do I/O."""

    def __init__(
        self,
        *,
        session: Any = None,
        timeout_seconds: float = 8.0,
        max_age_days: int = MAX_FX_AGE_DAYS,
        lookback_observations: int = ECB_LOOKBACK_OBSERVATIONS,
    ):
        if isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 0:
            raise ValueError("Maximum FX age must be a non-negative number of days")
        if isinstance(lookback_observations, bool) or not isinstance(lookback_observations, int) or lookback_observations < 1:
            raise ValueError("ECB lookback must be a positive number of observations")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("HTTP timeout must be finite and positive")
        self._session = session or requests.Session()
        self._timeout_seconds = float(timeout_seconds)
        self._max_age_days = max_age_days
        self._lookback_observations = lookback_observations
        self._lock = threading.Lock()
        self._latest: Optional[dict] = None
        self._last_refresh_error: Optional[str] = None

    def refresh(self, *, now: Optional[datetime] = None) -> dict:
        """Fetch official public reference data; call from background work only."""
        checked_at = _now_utc(now)
        try:
            series = {}
            for name, key in ECB_SERIES.items():
                series[name] = self._fetch_series(key)
            common_dates = series["usd_per_eur"].keys() & series["inr_per_eur"].keys()
            if not common_dates:
                raise ValueError("The ECB currency series have no common observation date")
            source_date = max(common_dates)
            usd_per_eur = series["usd_per_eur"][source_date]
            inr_per_eur = series["inr_per_eur"][source_date]
            rate = (inr_per_eur / usd_per_eur).quantize(
                _RATE_QUANTUM, rounding=ROUND_HALF_UP
            )
            if not rate.is_finite() or rate <= 0:
                raise ValueError("The ECB currency observations do not yield a positive rate")
            record = {
                "rate": rate,
                "source_date": source_date,
                "retrieved_at": checked_at.isoformat(),
            }
            with self._lock:
                self._latest = record
                self._last_refresh_error = None
            return self.get_snapshot(now=checked_at)
        except (requests.RequestException, ValueError, TypeError, KeyError, csv.Error):
            # Never expose arbitrary provider bodies, URLs containing parameters,
            # account identifiers, credentials, or exception strings.
            with self._lock:
                self._last_refresh_error = "ecb_reference_refresh_failed"
            return self.get_snapshot(now=checked_at, reason="ecb_reference_refresh_failed")

    def _fetch_series(self, series_key: str) -> Dict[date, Decimal]:
        """Fetch one official series with bounded, read-only retry handling."""
        url = ECB_DATA_URL.format(series_key)
        params = {
            "lastNObservations": self._lookback_observations,
            "format": "csvdata",
        }
        headers = {
            "Accept": "text/csv",
            "User-Agent": ECB_USER_AGENT,
        }
        timeout = (min(3.05, self._timeout_seconds), self._timeout_seconds)
        for attempt in range(ECB_MAX_REQUEST_ATTEMPTS):
            try:
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
                return _parse_ecb_csv(response)
            except requests.RequestException as exc:
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)
                retryable = (
                    status_code is None
                    or status_code == 429
                    or (status_code is not None and status_code >= 500)
                )
                if not retryable or attempt + 1 >= ECB_MAX_REQUEST_ATTEMPTS:
                    raise
        raise RuntimeError("ECB series request attempts exhausted")

    def get_snapshot(
        self,
        *,
        now: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """Return a thread-safe cached snapshot without making any network call."""
        checked_at = _now_utc(now)
        with self._lock:
            record = dict(self._latest) if self._latest else None
            last_refresh_error = self._last_refresh_error
        result = _public_snapshot(record, checked_at, reason or last_refresh_error)
        result["max_age_days"] = self._max_age_days
        if record is not None:
            age_days = result["age_days"]
            is_fresh = 0 <= age_days <= self._max_age_days
            result["status"] = "available" if is_fresh else "stale"
            if not is_fresh:
                result["rate"] = None
                result["reason"] = reason or "published_reference_rate_exceeds_maximum_age"
        return result

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()


def gold_quantity_from_lots(lots: Any) -> float:
    """Convert requested whole/fractional XAU lots to ounces (1 lot = 100 oz)."""
    quantity_lots = _decimal(lots, "XAUUSD lots")
    if quantity_lots <= 0:
        raise ValueError("XAUUSD lots must be positive")
    quantity_ounces = quantity_lots * Decimal("100")
    if not math.isfinite(float(quantity_ounces)):
        raise ValueError("XAUUSD ounce quantity must be finite")
    return float(quantity_ounces)


def gold_lot_display(quantity_ounces: Any) -> dict:
    """Describe OANDA XAU quantities clearly without changing stored trade units."""
    ounces = _decimal(quantity_ounces, "XAUUSD trade quantity")
    if ounces <= 0:
        raise ValueError("XAUUSD trade quantity must be positive")
    if not math.isfinite(float(ounces)):
        raise ValueError("XAUUSD trade quantity must be finite")
    lots = ounces / Decimal("100")
    return {
        "quantity": float(ounces),
        "quantity_unit": "troy_ounce",
        "quantity_currency": "USD",
        "quantity_lots": float(lots),
        "quantity_troy_ounces": float(ounces),
        "lot_size_troy_ounces": 100,
    }


def _to_inr(amount: Decimal, fx: dict) -> tuple[Optional[Decimal], str]:
    if amount == 0:
        return Decimal("0"), "not_required"
    if not isinstance(fx, dict) or fx.get("status") != "available":
        return None, "fx_rate_unavailable_or_stale"
    try:
        rate = _decimal(fx.get("rate"), "USD/INR rate")
    except ValueError:
        return None, "fx_rate_unavailable_or_stale"
    if rate <= 0:
        return None, "fx_rate_unavailable_or_stale"
    return amount * rate, "converted"


def consolidate_pnl_currencies(
    *,
    realized_inr: Any,
    realized_usd: Any,
    unrealized_inr: Any,
    unrealized_usd: Any,
    fx_snapshot: dict,
) -> dict:
    """Consolidate INR and USD P&L without losing currencies or masking stale FX.

    A missing rate leaves valid source-currency subtotals available but returns
    null INR component/portfolio totals wherever non-zero USD conversion is
    needed. An exactly zero USD subtotal converts to INR 0 without a quote.
    """
    realized_inr_value = _decimal(realized_inr, "Realized INR P&L")
    realized_usd_value = _decimal(realized_usd, "Realized USD P&L")
    unrealized_inr_value = _decimal(unrealized_inr, "Unrealized INR P&L")
    unrealized_usd_value = _decimal(unrealized_usd, "Unrealized USD P&L")

    realized_usd_inr, realized_status = _to_inr(realized_usd_value, fx_snapshot)
    unrealized_usd_inr, unrealized_status = _to_inr(unrealized_usd_value, fx_snapshot)
    total_usd = realized_usd_value + unrealized_usd_value
    total_usd_inr, total_status = _to_inr(total_usd, fx_snapshot)

    realized_total_inr = (
        realized_inr_value + realized_usd_inr
        if realized_usd_inr is not None else None
    )
    unrealized_total_inr = (
        unrealized_inr_value + unrealized_usd_inr
        if unrealized_usd_inr is not None else None
    )
    total_pnl_inr = (
        realized_inr_value + unrealized_inr_value + total_usd_inr
        if total_usd_inr is not None else None
    )
    usd_inr_rate = fx_snapshot.get("rate") if isinstance(fx_snapshot, dict) else None

    return {
        "pnl_by_currency": {
            "realized": {
                "INR": _round_money(realized_inr_value),
                "USD": _round_money(realized_usd_value),
            },
            "unrealized": {
                "INR": _round_money(unrealized_inr_value),
                "USD": _round_money(unrealized_usd_value),
            },
            "total": {
                "INR": (
                    _round_money(total_pnl_inr)
                    if total_pnl_inr is not None else None
                ),
                "USD": _round_money(total_usd),
            },
        },
        "realized_pnl_inr": (
            _round_money(realized_total_inr)
            if realized_total_inr is not None else None
        ),
        "unrealized_pnl_inr": (
            _round_money(unrealized_total_inr)
            if unrealized_total_inr is not None else None
        ),
        "total_pnl_inr": (
            _round_money(total_pnl_inr)
            if total_pnl_inr is not None else None
        ),
        "portfolio_currency": "INR",
        "usd_inr_conversion": {
            **(
                {
                    key: fx_snapshot.get(key)
                    for key in (
                        "status",
                        "rate",
                        "last_published_rate",
                        "from_currency",
                        "to_currency",
                        "source",
                        "source_url",
                        "source_observation_urls",
                        "source_series",
                        "conversion_method",
                        "rate_type",
                        "source_date",
                        "retrieved_at",
                        "age_days",
                        "max_age_days",
                        "reason",
                    )
                    if key in fx_snapshot
                }
                if isinstance(fx_snapshot, dict)
                else {"status": "unavailable"}
            ),
            "realized_pnl_conversion": realized_status,
            "unrealized_pnl_conversion": unrealized_status,
            "total_pnl_conversion": total_status,
        },
    }