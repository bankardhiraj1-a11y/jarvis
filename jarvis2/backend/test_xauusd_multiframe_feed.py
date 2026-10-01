from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from data.oanda_pricing import OandaCandleError, OandaPricingClient
from data.xauusd_multiframe_feed import XauusdFeedError, XauusdMultiFrameFeed


def candle(opened, *, complete=True, instrument=None, granularity=None, invalid=False):
    bid_open = 2500.0
    bid = {"o": bid_open, "h": 2502.0, "l": 2499.0, "c": 2501.0}
    ask = {"o": 2501.0, "h": 2503.0, "l": 2500.0, "c": 2502.0}
    if invalid:
        bid["l"] = 2501.5
    row = {
        "time": opened.isoformat().replace("+00:00", "Z"),
        "complete": complete,
        "bid": bid,
        "ask": ask,
    }
    if instrument is not None:
        row["instrument"] = instrument
    if granularity is not None:
        row["granularity"] = granularity
    return row


class FakeClient:
    environment = "practice"

    def __init__(self, **candles_by_granularity):
        self.candles_by_granularity = candles_by_granularity
        self.calls = []

    def get_completed_candles(self, granularity, count):
        self.calls.append((granularity, count))
        return self.candles_by_granularity.get(granularity, [])


def make_feed(m1, m15=None, h4=None):
    return XauusdMultiFrameFeed(FakeClient(M1=m1, M15=m15 or [], H4=h4 or []))


def test_m3_is_constructed_from_three_contiguous_completed_m1_bars():
    now = datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc)
    source = [candle(now - timedelta(minutes=3 - offset)) for offset in range(3)]
    client = FakeClient(M1=source)

    snapshot = XauusdMultiFrameFeed(client).refresh(now=now)

    bar = snapshot["frames"]["M3"][0]
    assert bar == {
        "bar_open_time": "2025-02-03T12:00:00.000000Z",
        "observed_at": "2025-02-03T12:03:00.000000Z",
        "open": 2500.5,
        "high": 2502.5,
        "low": 2499.5,
        "close": 2501.5,
        "bid_close": 2501.0,
        "ask_close": 2502.0,
        "complete": True,
        "provider": "OANDA",
        "environment": "practice",
        "bar_interval_minutes": 3,
    }
    assert client.calls == [("M1", 240), ("M15", 100), ("H4", 100)]
    assert snapshot["source"] == "OANDA"
    assert snapshot["fetched_at"] == "2025-02-03T12:03:00.000000Z"


def test_missing_m1_minute_does_not_create_m3_bar():
    now = datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc)
    source = [
        candle(now - timedelta(minutes=3)),
        candle(now - timedelta(minutes=1)),
    ]

    assert make_feed(source).refresh(now=now)["frames"]["M3"] == []


def test_native_frames_are_returned_only_when_closed_with_close_time_observation():
    now = datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc)
    m15 = [candle(datetime(2025, 2, 3, 11, 45, tzinfo=timezone.utc))]
    h4 = [candle(datetime(2025, 2, 3, 8, 0, tzinfo=timezone.utc))]

    frames = make_feed([], m15=m15, h4=h4).refresh(now=now)["frames"]

    assert frames["M15"][0]["observed_at"] == "2025-02-03T12:00:00.000000Z"
    assert frames["H4"][0]["observed_at"] == "2025-02-03T12:00:00.000000Z"
    assert frames["M15"][0]["bar_interval_minutes"] == 15
    assert frames["H4"][0]["bar_interval_minutes"] == 240


def test_incomplete_and_not_yet_closed_m1_candles_are_not_used():
    now = datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc)
    incomplete = [
        candle(now - timedelta(minutes=3)),
        candle(now - timedelta(minutes=2), complete=False),
        candle(now - timedelta(minutes=1)),
    ]
    future = [
        candle(now - timedelta(minutes=2)),
        candle(now - timedelta(minutes=1)),
        candle(now),
    ]

    assert make_feed(incomplete).refresh(now=now)["frames"]["M3"] == []
    assert make_feed(future).refresh(now=now)["frames"]["M3"] == []


@pytest.mark.parametrize(
    "row",
    [
        candle(datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc),
               instrument="EUR_USD"),
        candle(datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc),
               granularity="M5"),
    ],
)
def test_wrong_instrument_or_granularity_provenance_is_rejected(row):
    with pytest.raises(XauusdFeedError, match="provenance"):
        make_feed([row]).refresh(now=datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc))


def test_invalid_side_ohlc_is_rejected_without_producing_a_bar():
    now = datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc)
    source = [candle(now - timedelta(minutes=3 - i), invalid=(i == 0)) for i in range(3)]

    with pytest.raises(XauusdFeedError, match="OHLC"):
        make_feed(source).refresh(now=now)


def _pricing_client():
    with patch.dict("os.environ", {
        "OANDA_ACCESS_TOKEN": "private-fixture-token",
        "OANDA_ACCOUNT_ID": "",
        "OANDA_ENVIRONMENT": "practice",
    }):
        client = OandaPricingClient()
    client._session = Mock()
    return client


def test_read_only_candle_transport_uses_ba_unsmoothed_and_no_account_lookup():
    client = _pricing_client()
    client._session.get.return_value = Mock(
        status_code=200,
        json=lambda: {
            "instrument": "XAU_USD",
            "granularity": "M1",
            "candles": [candle(datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc))],
        },
    )

    result = client.get_completed_candles("M1", 240)

    call = client._session.get.call_args
    assert call.args[0].endswith("/instruments/XAU_USD/candles")
    assert call.kwargs["params"] == {
        "granularity": "M1", "count": 240, "price": "BA", "smooth": "false",
    }
    assert result[0]["complete"] is True
    assert client._session.get.call_count == 1
    assert "/accounts/" not in call.args[0]


def test_transport_provenance_and_http_failures_have_safe_diagnostics():
    client = _pricing_client()
    client._session.get.return_value = Mock(
        status_code=200,
        json=lambda: {
            "instrument": "EUR_USD",
            "granularity": "M1",
            "candles": [],
            "token": "private-fixture-token",
        },
    )
    with pytest.raises(OandaCandleError, match="provenance") as mismatch:
        client.get_completed_candles("M1", 240)
    assert "private-fixture-token" not in str(mismatch.value)

    client._session.get.return_value = Mock(
        status_code=401,
        text="provider body private-fixture-token",
    )
    with pytest.raises(OandaCandleError, match="HTTP 401") as rejected:
        client.get_completed_candles("M1", 240)
    diagnostic = str(rejected.value)
    assert "private-fixture-token" not in diagnostic
    assert "provider body" not in diagnostic


def test_transport_rejects_wrong_granularity_and_per_candle_instrument():
    client = _pricing_client()
    timestamp = datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc)
    wrong_granularity = {
        "instrument": "XAU_USD",
        "granularity": "M5",
        "candles": [],
    }
    wrong_candle_instrument = {
        "instrument": "XAU_USD",
        "granularity": "M1",
        "candles": [candle(timestamp, instrument="EUR_USD")],
    }
    for payload in (wrong_granularity, wrong_candle_instrument):
        client._session.get.return_value = Mock(status_code=200, json=lambda: payload)
        with pytest.raises(OandaCandleError, match="provenance"):
            client.get_completed_candles("M1", 240)


def test_transport_rejects_duplicate_or_out_of_order_timestamps():
    client = _pricing_client()
    timestamp = datetime(2025, 2, 3, 12, 0, tzinfo=timezone.utc)
    client._session.get.return_value = Mock(
        status_code=200,
        json=lambda: {
            "instrument": "XAU_USD",
            "granularity": "M1",
            "candles": [candle(timestamp), candle(timestamp)],
        },
    )

    with pytest.raises(OandaCandleError, match="duplicate"):
        client.get_completed_candles("M1", 240)


def test_transport_network_errors_do_not_leak_exception_details():
    client = _pricing_client()
    client._session.get.side_effect = requests.RequestException("private-fixture-token")

    with pytest.raises(OandaCandleError) as failure:
        client.get_completed_candles("M1", 240)

    assert "private-fixture-token" not in str(failure.value)
    assert "private-fixture-token" not in repr(failure.value.__cause__)