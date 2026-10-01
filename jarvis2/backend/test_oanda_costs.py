"""Focused, non-network tests for cached OANDA cost metadata."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.oanda_costs import (
    FINANCING_DOC_URL,
    OandaCostMetadataProvider,
)
from trading.charges import _safe_oanda_metadata


class FakeResponse:
    def __init__(self, body=None, status_code=200):
        self._body = body
        self.status_code = status_code
        self.json_calls = 0

    def json(self):
        self.json_calls += 1
        return deepcopy(self._body)


def instrument_response(*, financing=True, commission=True):
    instrument = {"name": "XAU_USD"}
    if commission:
        instrument["commission"] = {
            "commission": "2",
            "unitsTraded": "1000000",
            "minimumCommission": "0",
        }
    if financing:
        instrument["financing"] = {
            "longRate": "0.05",
            "shortRate": "-0.025",
            "financingDaysOfWeek": [
                {"dayOfWeek": "THURSDAY", "daysCharged": 1},
                {"dayOfWeek": "WEDNESDAY", "daysCharged": 3},
                {"dayOfWeek": "MONDAY", "daysCharged": 1},
            ],
        }
    return {"instruments": [instrument]}


class FakeSession:
    def __init__(self, response=None, *, responses=None, failures=0, status_code=200):
        self.response = response or FakeResponse(
            instrument_response(), status_code=status_code
        )
        self.responses = list(responses) if responses is not None else [self.response]
        self.failures = failures
        self.calls = 0
        self.last_timeout = None
        self.query_presence = []

    def get(self, _url, *, headers, timeout, params=None):
        self.calls += 1
        self.last_timeout = timeout
        self.query_presence.append(params is not None)
        if self.failures:
            self.failures -= 1
            raise requests.Timeout("synthetic timeout")
        return self.responses.pop(0) if self.responses else self.response


class FakeOandaClient:
    def __init__(self, session=None, *, configured=True):
        self.access_token = "synthetic-test-value"
        self.account_id = "synthetic-test-value"
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        self.configured = configured
        self._session = session or FakeSession()
        self.discover_calls = 0
        self._cooldown_until = 0

    def _discover_account(self):
        self.discover_calls += 1


class TestOandaCostMetadataProvider:
    def setup_method(self):
        self.now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    def test_parses_verified_financing_and_actual_schedule_but_not_unverified_commission(self):
        client = FakeOandaClient()
        provider = OandaCostMetadataProvider(client)
        snapshot = provider.refresh(now=self.now)

        assert snapshot["status"] == "available"
        assert snapshot["verified"] is True
        assert snapshot["instrument"] == "XAU_USD"
        assert snapshot["currency"] == "USD"
        assert snapshot["as_of"] == self.now.isoformat()
        assert snapshot["long_financing_annual_pct"] == 5.0
        assert snapshot["short_financing_annual_pct"] == -2.5
        assert snapshot["financing_day_basis"] == 365
        assert snapshot["weekday_schedule"] == [
            {"day_of_week": "MONDAY", "weekday": 0, "days_charged": 1},
            {"day_of_week": "WEDNESDAY", "weekday": 2, "days_charged": 3},
            {"day_of_week": "THURSDAY", "weekday": 3, "days_charged": 1},
        ]
        assert snapshot["triple_rollover_weekday"] == 2
        assert snapshot["rollover_time_local"] == "17:00"
        assert snapshot["rollover_timezone"] == "America/New_York"
        assert snapshot["source"]["name"] == "OANDA account instrument metadata"
        assert snapshot["source"]["url"] == FINANCING_DOC_URL
        assert _safe_oanda_metadata(snapshot) == snapshot
        assert snapshot["commission_status"] == "unsupported"
        assert snapshot["commission_reason"] == "account_home_currency_not_verified"
        assert "commission_usd_per_million_side" not in snapshot
        assert client._session.calls == 1
        assert client.discover_calls == 1

    def test_cached_reads_do_not_make_http_requests_and_expire_by_freshness(self):
        client = FakeOandaClient()
        provider = OandaCostMetadataProvider(client, max_age_seconds=60)
        provider.refresh(now=self.now)
        calls_after_refresh = client._session.calls

        fresh = provider.get_snapshot(now=self.now + timedelta(seconds=60))
        self.assert_metadata_available(fresh)
        stale = provider.get_snapshot(now=self.now + timedelta(seconds=61))
        assert stale["status"] == "stale"
        assert stale["verified"] is False
        assert stale["reason"] == "metadata_stale"
        assert client._session.calls == calls_after_refresh

    def test_missing_fields_are_unknown_not_zero(self):
        session = FakeSession(response=FakeResponse(instrument_response(
            financing=False,
            commission=False,
        )))
        snapshot = OandaCostMetadataProvider(FakeOandaClient(session)).refresh(now=self.now)

        assert snapshot["status"] == "available"
        assert snapshot["verified"] is True
        assert snapshot["commission_status"] == "unsupported"
        assert snapshot["commission_reason"] == "commission_schedule_not_returned"
        assert "commission_usd_per_million_side" not in snapshot
        assert snapshot["long_financing_annual_pct"] is None
        assert snapshot["short_financing_annual_pct"] is None
        assert snapshot["financing_rate_status"] == "unknown"
        assert snapshot["financing_days_of_week"] is None
        assert snapshot["triple_rollover_weekday"] is None

    def test_filtered_404_uses_one_unfiltered_fallback_and_selects_xau_locally(self):
        filtered_failure = FakeResponse(status_code=404)
        unfiltered_result = FakeResponse({
            "instruments": [
                {"name": "EUR_USD"},
                instrument_response()["instruments"][0],
            ],
        })
        session = FakeSession(responses=[filtered_failure, unfiltered_result])
        snapshot = OandaCostMetadataProvider(
            FakeOandaClient(session)
        ).refresh(now=self.now)

        assert snapshot["status"] == "available"
        assert snapshot["instrument"] == "XAU_USD"
        assert snapshot["long_financing_annual_pct"] == 5.0
        assert session.calls == 2
        assert session.query_presence == [True, False]
        assert filtered_failure.json_calls == 0
        assert unfiltered_result.json_calls == 1

    def test_unfiltered_response_without_xau_remains_unknown(self):
        filtered_failure = FakeResponse(status_code=404)
        unfiltered_result = FakeResponse({
            "instruments": [{"name": "EUR_USD"}],
        })
        session = FakeSession(responses=[filtered_failure, unfiltered_result])
        snapshot = OandaCostMetadataProvider(
            FakeOandaClient(session)
        ).refresh(now=self.now)

        assert snapshot["status"] == "unavailable"
        assert snapshot["verified"] is False
        assert snapshot["reason"] == "instrument_not_returned"
        assert session.calls == 2
        assert session.query_presence == [True, False]
        assert filtered_failure.json_calls == 0
        assert unfiltered_result.json_calls == 1

    def test_ambiguous_or_invalid_schedule_never_infers_triple_day(self):
        body = instrument_response()
        body["instruments"][0]["financing"]["financingDaysOfWeek"] = [
            {"dayOfWeek": "WEDNESDAY", "daysCharged": 3},
            {"dayOfWeek": "THURSDAY", "daysCharged": 3},
        ]
        snapshot = OandaCostMetadataProvider(
            FakeOandaClient(FakeSession(response=FakeResponse(body)))
        ).refresh(now=self.now)
        assert snapshot["weekday_schedule"] is not None
        assert snapshot["triple_rollover_weekday"] is None

        body["instruments"][0]["financing"]["financingDaysOfWeek"][1]["dayOfWeek"] = "NOT_A_WEEKDAY"
        invalid = OandaCostMetadataProvider(
            FakeOandaClient(FakeSession(response=FakeResponse(body)))
        ).refresh(now=self.now)
        assert invalid["weekday_schedule"] is None
        assert invalid["triple_rollover_weekday"] is None

    def test_transient_timeout_retries_once_and_http_error_body_is_not_read(self):
        session = FakeSession(failures=1)
        provider = OandaCostMetadataProvider(FakeOandaClient(session))
        result = provider.refresh(now=self.now)
        assert result["status"] == "available"
        assert session.calls == 2
        assert 0 < session.last_timeout[0] <= session.last_timeout[1]

        unauthorized = FakeResponse(status_code=401)
        client = FakeOandaClient(FakeSession(response=unauthorized))
        unavailable = OandaCostMetadataProvider(client).refresh(now=self.now)
        assert unavailable["status"] == "unavailable"
        assert unavailable["reason"] == "provider_http_401"
        assert unauthorized.json_calls == 0

    def test_retries_are_bounded_and_cached_failure_reason_is_safe(self):
        session = FakeSession(status_code=503)
        provider = OandaCostMetadataProvider(FakeOandaClient(session))
        failed = provider.refresh(now=self.now)
        assert failed["status"] == "unavailable"
        assert failed["reason"] == "provider_http_503"
        assert session.calls == 2
        cached = provider.get_snapshot(now=self.now)
        assert cached["reason"] == "provider_http_503"
        assert session.calls == 2

    def test_rate_limit_sets_shared_cooldown_and_prevents_another_request(self):
        session = FakeSession(status_code=429)
        client = FakeOandaClient(session)
        provider = OandaCostMetadataProvider(client)
        first = provider.refresh(now=self.now)
        second = provider.refresh(now=self.now)
        assert first["reason"] == "rate_limited"
        assert second["reason"] == "rate_limited"
        assert session.calls == 1
        assert session.response.json_calls == 0

    def test_unconfigured_client_fails_closed_without_request(self):
        client = FakeOandaClient(configured=False)
        snapshot = OandaCostMetadataProvider(client).refresh(now=self.now)
        assert snapshot["status"] == "unavailable"
        assert snapshot["verified"] is False
        assert snapshot["reason"] == "credentials_or_environment_missing"
        assert client._session.calls == 0

    @staticmethod
    def assert_metadata_available(snapshot):
        assert snapshot["status"] == "available"
        assert snapshot["verified"] is True