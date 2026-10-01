"""Read-only cached OANDA XAU_USD account/instrument cost metadata."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import threading
import time
from typing import Any, Optional

import requests


INSTRUMENT = "XAU_USD"
SOURCE_NAME = "OANDA account instrument metadata"
FINANCING_DOC_URL = "https://www.oanda.com/us-en/trading/financing-fees/"
ACCOUNT_API_DOC_URL = "https://developer.oanda.com/rest-live-v20/account-ep/"
INSTRUMENT_SCHEMA_DOC_URL = "https://developer.oanda.com/rest-live-v20/primitives-df/"
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60
MAX_REQUEST_ATTEMPTS = 2
_CONNECT_TIMEOUT_SECONDS = 3.05
_WEEKDAYS = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def _utc_now(value: Optional[datetime] = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise ValueError("Cost metadata freshness requires a timezone-aware time")
    return result.astimezone(timezone.utc)


def _finite_decimal(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None
    if not number.is_finite():
        return None
    try:
        if not math.isfinite(float(number)):
            return None
    except (OverflowError, ValueError):
        return None
    return number


def _annual_percentage(value: Any) -> Optional[float]:
    """OANDA documents financing rates as decimal annual rates (5% = 0.05)."""
    rate = _finite_decimal(value)
    if rate is None:
        return None
    percent = rate * Decimal("100")
    return float(percent) if math.isfinite(float(percent)) else None


def _weekday_schedule(financing: Any) -> tuple[Optional[list[dict]], Optional[int]]:
    if not isinstance(financing, dict) or "financingDaysOfWeek" not in financing:
        return None, None
    source_days = financing.get("financingDaysOfWeek")
    if not isinstance(source_days, list):
        return None, None

    schedule = []
    observed_days = set()
    for item in source_days:
        if not isinstance(item, dict):
            return None, None
        day = item.get("dayOfWeek")
        charged = item.get("daysCharged")
        if (
            not isinstance(day, str)
            or day not in _WEEKDAYS
            or isinstance(charged, bool)
            or not isinstance(charged, int)
            or not 0 <= charged <= 7
            or day in observed_days
        ):
            return None, None
        observed_days.add(day)
        schedule.append({
            "day_of_week": day,
            "weekday": _WEEKDAYS[day],
            "days_charged": charged,
        })

    schedule.sort(key=lambda entry: entry["weekday"])
    triple_days = [
        entry["weekday"]
        for entry in schedule
        if entry["days_charged"] == 3
    ]
    triple_weekday = triple_days[0] if len(triple_days) == 1 else None
    return schedule, triple_weekday


def _base_snapshot(reason: str) -> dict:
    return {
        "status": "unavailable",
        "verified": False,
        "instrument": INSTRUMENT,
        "currency": "USD",
        "source": {
            "name": SOURCE_NAME,
            "url": FINANCING_DOC_URL,
            "account_api_documentation_url": ACCOUNT_API_DOC_URL,
            "instrument_schema_documentation_url": INSTRUMENT_SCHEMA_DOC_URL,
            "financing_documentation_url": FINANCING_DOC_URL,
        },
        "as_of": None,
        "age_seconds": None,
        "max_age_seconds": DEFAULT_MAX_AGE_SECONDS,
        "reason": reason,
        "refresh_warning": None,
        "commission_status": "unsupported",
        "commission_reason": "commission_schedule_not_verified",
        "long_financing_annual_pct": None,
        "short_financing_annual_pct": None,
        "financing_rate_status": "unknown",
        "financing_day_basis": 365,
        "financing_days_of_week": None,
        "weekday_schedule": None,
        "triple_rollover_weekday": None,
        "rollover_time_local": "17:00",
        "rollover_timezone": "America/New_York",
    }


class OandaCostMetadataProvider:
    """Fetch account-specific instrument metadata; cached reads never do I/O."""

    def __init__(
        self,
        client: Any,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("HTTP timeout must be finite and positive")
        if (
            isinstance(max_age_seconds, bool)
            or not isinstance(max_age_seconds, int)
            or max_age_seconds < 0
        ):
            raise ValueError("Maximum metadata age must be a non-negative number of seconds")
        self._client = client
        self._timeout_seconds = float(timeout_seconds)
        self._max_age_seconds = max_age_seconds
        self._lock = threading.Lock()
        self._latest: Optional[dict] = None
        self._last_refresh_error: Optional[str] = None

    def refresh(self, *, now: Optional[datetime] = None) -> dict:
        """Resolve the configured account and request only XAU_USD instruments."""
        checked_at = _utc_now(now)
        try:
            self._client._discover_account()
            if not self._client.configured:
                return self._failed_snapshot("credentials_or_environment_missing", checked_at)
            if time.monotonic() < getattr(self._client, "_cooldown_until", 0):
                return self._failed_snapshot("rate_limited", checked_at)

            url = (
                f"{self._client.base_url}/accounts/"
                f"{self._client.account_id}/instruments"
            )
            headers = {
                "Authorization": f"Bearer {self._client.access_token}",
                "Accept": "application/json",
            }
            timeout = (
                min(_CONNECT_TIMEOUT_SECONDS, self._timeout_seconds),
                self._timeout_seconds,
            )
            response = self._request_instrument_metadata(
                url,
                headers,
                timeout,
                include_instrument_filter=True,
            )
            if getattr(response, "status_code", None) == 404:
                # Some OANDA hosts reject the filtered form even though the
                # documented account instruments resource itself is available.
                # Make one bounded, unfiltered read and select XAU_USD locally.
                response = self._request_instrument_metadata(
                    url,
                    headers,
                    timeout,
                    include_instrument_filter=False,
                    max_attempts=1,
                )
            status_code = getattr(response, "status_code", None)
            if status_code != 200:
                if status_code == 429:
                    try:
                        self._client._cooldown_until = time.monotonic() + 60
                    except AttributeError:
                        pass
                    return self._failed_snapshot("rate_limited", checked_at)
                reason = (
                    f"provider_http_{status_code}"
                    if isinstance(status_code, int) and not isinstance(status_code, bool)
                    else "provider_http_error"
                )
                return self._failed_snapshot(reason, checked_at)

            body = response.json()
            instruments = body.get("instruments") if isinstance(body, dict) else None
            if not isinstance(instruments, list):
                return self._failed_snapshot("instrument_response_invalid", checked_at)
            instrument = next(
                (
                    entry for entry in instruments
                    if isinstance(entry, dict) and entry.get("name") == INSTRUMENT
                ),
                None,
            )
            if instrument is None:
                return self._failed_snapshot("instrument_not_returned", checked_at)

            financing = instrument.get("financing")
            long_rate = _annual_percentage(
                financing.get("longRate") if isinstance(financing, dict) else None
            )
            short_rate = _annual_percentage(
                financing.get("shortRate") if isinstance(financing, dict) else None
            )
            schedule, triple_weekday = _weekday_schedule(financing)
            rates_verified = long_rate is not None and short_rate is not None

            commission = instrument.get("commission")
            commission_reason = (
                "account_home_currency_not_verified"
                if isinstance(commission, dict)
                else "commission_schedule_not_returned"
            )
            snapshot = {
                "status": "available",
                "verified": True,
                "instrument": INSTRUMENT,
                "currency": "USD",
                "source": {
                    "name": SOURCE_NAME,
                    "url": FINANCING_DOC_URL,
                    "account_api_documentation_url": ACCOUNT_API_DOC_URL,
                    "instrument_schema_documentation_url": INSTRUMENT_SCHEMA_DOC_URL,
                    "financing_documentation_url": FINANCING_DOC_URL,
                },
                "as_of": checked_at.isoformat(),
                "age_seconds": 0,
                "max_age_seconds": self._max_age_seconds,
                "reason": None,
                "refresh_warning": None,
                # OANDA specifies this amount in the account home currency.
                # The instruments response alone does not prove that currency is USD.
                # Omit commission_usd_per_million_side unless that is verifiable.
                "commission_status": "unsupported",
                "commission_reason": commission_reason,
                "long_financing_annual_pct": long_rate,
                "short_financing_annual_pct": short_rate,
                "financing_rate_status": "verified" if rates_verified else "unknown",
                "financing_day_basis": 365,
                "financing_days_of_week": deepcopy(schedule),
                "weekday_schedule": deepcopy(schedule),
                "triple_rollover_weekday": triple_weekday,
                "rollover_time_local": "17:00",
                "rollover_timezone": "America/New_York",
            }
            with self._lock:
                self._latest = snapshot
                self._last_refresh_error = None
            return self.get_snapshot(now=checked_at)
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OverflowError):
            return self._failed_snapshot("oanda_instrument_refresh_failed", checked_at)

    def _request_instrument_metadata(
        self,
        url: str,
        headers: dict,
        timeout: tuple,
        *,
        include_instrument_filter: bool,
        max_attempts: int = MAX_REQUEST_ATTEMPTS,
    ) -> Any:
        """Make at most two read-only GET attempts; never expose request details."""
        attempt_limit = min(max_attempts, MAX_REQUEST_ATTEMPTS)
        for attempt in range(attempt_limit):
            try:
                request_options = {"headers": headers, "timeout": timeout}
                if include_instrument_filter:
                    request_options["params"] = {"instruments": INSTRUMENT}
                response = self._client._session.get(url, **request_options)
            except requests.RequestException:
                if attempt + 1 >= attempt_limit:
                    raise
                continue

            status_code = getattr(response, "status_code", None)
            if status_code == 200:
                return response
            if isinstance(status_code, int) and status_code >= 500:
                if attempt + 1 < attempt_limit:
                    continue
            return response
        raise requests.RequestException("OANDA instrument request attempts exhausted")

    def _failed_snapshot(self, reason: str, now: datetime) -> dict:
        with self._lock:
            self._last_refresh_error = reason
            has_cached = self._latest is not None
        if has_cached:
            return self.get_snapshot(now=now)
        result = _base_snapshot(reason)
        result["max_age_seconds"] = self._max_age_seconds
        return result

    def get_snapshot(self, *, now: Optional[datetime] = None) -> dict:
        """Return only sanitized cached metadata, without reading the network."""
        checked_at = _utc_now(now)
        with self._lock:
            record = deepcopy(self._latest) if self._latest is not None else None
            refresh_error = self._last_refresh_error
        if record is None:
            result = _base_snapshot(refresh_error or "metadata_not_loaded")
            result["max_age_seconds"] = self._max_age_seconds
            return result

        try:
            source_time = datetime.fromisoformat(record["as_of"])
            age = (checked_at - source_time).total_seconds()
        except (KeyError, TypeError, ValueError):
            age = math.inf
        record["age_seconds"] = age if math.isfinite(age) else None
        record["max_age_seconds"] = self._max_age_seconds
        if not 0 <= age <= self._max_age_seconds:
            record["status"] = "stale"
            record["verified"] = False
            record["reason"] = "metadata_stale"
        elif refresh_error:
            record["refresh_warning"] = refresh_error
        return record