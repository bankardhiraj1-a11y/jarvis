from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest
import requests

from agents.base import Signal
from agents.xauusd_multiframe import XAUUSDMultiframeResearchAgent
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


def h4_history(count=100, last_open=None):
    if last_open is None:
        last_open = datetime(2025, 2, 3, 6, tzinfo=timezone.utc)
    first_open = last_open - timedelta(hours=4 * (count - 1))
    return [
        candle(first_open + timedelta(hours=4 * index))
        for index in range(count)
    ]


def make_feed(m1, m15=None, h4=None):
    h4 = list(h4) if h4 is not None else []
    if len(h4) < 100:
        last_open = (
            datetime.fromisoformat(h4[0]["time"].replace("Z", "+00:00"))
            if h4 else datetime(2025, 2, 3, 6, tzinfo=timezone.utc)
        )
        missing = 100 - len(h4)
        h4 = h4_history(missing, last_open - timedelta(hours=4)) + h4
    return XauusdMultiFrameFeed(FakeClient(M1=m1, M15=m15 or [], H4=h4))


def _provider_fixture(rows, granularity):
    return [
        {
            **candle(
                opened,
                instrument="XAU_USD",
                granularity=granularity,
            ),
            "environment": "practice",
        }
        for opened in rows
    ]


def _aligned_h4_provider_fixture(now, through, count=101):
    alignment_timezone = ZoneInfo("America/New_York")
    openings = []
    for days_ago in range(40):
        day = now.astimezone(alignment_timezone).date() - timedelta(days=days_ago)
        for hour in (1, 5, 9, 13, 17, 21):
            local_open = datetime(
                day.year, day.month, day.day, hour, tzinfo=alignment_timezone
            )
            opened = local_open.astimezone(timezone.utc)
            if opened + timedelta(hours=4) <= through:
                openings.append(opened)
    openings = sorted(set(openings))[-count:]
    assert len(openings) == count
    assert all(
        opened.astimezone(alignment_timezone).minute == 0
        and (opened.astimezone(alignment_timezone).hour - 17) % 4 == 0
        for opened in openings
    )
    return _provider_fixture(openings, "H4")


def _feed_agent_parity_fixture(now):
    m3_close = datetime.fromtimestamp(
        int(now.timestamp() // 180) * 180, timezone.utc
    )
    m1_latest_open = m3_close - timedelta(minutes=1)
    m1_openings = [
        m1_latest_open - timedelta(minutes=240 - index)
        for index in range(241)
    ]

    m15_close = datetime.fromtimestamp(
        int(now.timestamp() // 900) * 900, timezone.utc
    )
    m15_latest_open = m15_close - timedelta(minutes=15)
    m15_openings = [
        m15_latest_open - timedelta(minutes=15 * (100 - index))
        for index in range(101)
    ]

    client = FakeClient(
        M1=_provider_fixture(m1_openings, "M1"),
        M15=_provider_fixture(m15_openings, "M15"),
        H4=_aligned_h4_provider_fixture(now, m3_close),
    )
    return XauusdMultiFrameFeed(client), m3_close


def test_m3_is_constructed_from_three_contiguous_completed_m1_bars():
    now = datetime(2025, 2, 3, 12, 3, tzinfo=timezone.utc)
    source = [candle(now - timedelta(minutes=3 - offset)) for offset in range(3)]
    client = FakeClient(M1=source, H4=h4_history())

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
    assert client.calls == [("M1", 241), ("M15", 101), ("H4", 101)]
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
    h4 = [candle(datetime(2025, 2, 3, 6, 0, tzinfo=timezone.utc))]

    frames = make_feed([], m15=m15, h4=h4).refresh(now=now)["frames"]

    assert frames["M15"][0]["observed_at"] == "2025-02-03T12:00:00.000000Z"
    assert frames["H4"][-1]["observed_at"] == "2025-02-03T10:00:00.000000Z"
    assert frames["M15"][0]["bar_interval_minutes"] == 15
    assert frames["H4"][0]["bar_interval_minutes"] == 240


@pytest.mark.parametrize(
    ("opened", "now"),
    [
        # OANDA's 17:00 New York alignment is UTC-5 in winter and UTC-4 in summer.
        (datetime(2025, 1, 15, 10, tzinfo=timezone.utc),
         datetime(2025, 1, 15, 14, tzinfo=timezone.utc)),
        (datetime(2025, 7, 15, 9, tzinfo=timezone.utc),
         datetime(2025, 7, 15, 13, tzinfo=timezone.utc)),
    ],
)
def test_h4_open_alignment_tracks_new_york_dst(opened, now):
    history = h4_history(100, last_open=opened)

    bars = make_feed([], h4=history).refresh(now=now)["frames"]["H4"]

    assert len(bars) == 100
    assert bars[-1]["bar_open_time"] == opened.isoformat().replace("+00:00", ".000000Z")
    assert opened.hour % 4 != 0


def test_h4_rejects_utc_modulo_boundary_that_is_not_oanda_ny17_aligned():
    now = datetime(2025, 2, 3, 12, tzinfo=timezone.utc)
    history = h4_history(99, last_open=datetime(2025, 2, 3, 6, tzinfo=timezone.utc))
    history.append(candle(datetime(2025, 2, 3, 8, tzinfo=timezone.utc)))

    with pytest.raises(XauusdFeedError, match="granularity"):
        make_feed([], h4=history).refresh(now=now)


def test_h4_requests_extra_candle_and_returns_100_complete_warmup_bars():
    now = datetime(2025, 2, 3, 12, tzinfo=timezone.utc)
    history = h4_history()
    history.append(candle(datetime(2025, 2, 3, 10, tzinfo=timezone.utc), complete=False))
    client = FakeClient(M1=[], M15=[], H4=history)

    snapshot = XauusdMultiFrameFeed(client).refresh(now=now)

    assert client.calls == [("M1", 241), ("M15", 101), ("H4", 101)]
    assert len(snapshot["frames"]["H4"]) == 100
    assert snapshot["frames"]["H4"][-1]["bar_open_time"] == "2025-02-03T06:00:00.000000Z"


def test_h4_fails_closed_when_extra_row_still_leaves_fewer_than_100_complete():
    now = datetime(2025, 2, 3, 12, tzinfo=timezone.utc)
    history = h4_history(99)
    history.append(candle(datetime(2025, 2, 3, 10, tzinfo=timezone.utc), complete=False))
    client = FakeClient(M1=[], M15=[], H4=history)

    with pytest.raises(XauusdFeedError, match="fewer than 100 complete H4"):
        XauusdMultiFrameFeed(client).refresh(now=now)


def test_h4_refresh_uses_a_fixed_deterministic_100_bar_history_window():
    now = datetime(2025, 2, 3, 12, tzinfo=timezone.utc)
    client = FakeClient(M1=[], M15=[], H4=h4_history(101))
    feed = XauusdMultiFrameFeed(client)

    first = feed.refresh(now=now)["frames"]["H4"]
    second = feed.refresh(now=now)["frames"]["H4"]

    assert len(first) == 100
    assert first == second
    expected_open = datetime.fromisoformat(
        h4_history(101)[1]["time"].replace("Z", "+00:00")
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    assert first[0]["bar_open_time"] == expected_open


def test_feed_does_not_leak_provider_exception_details():
    client = FakeClient()
    client.get_completed_candles = Mock(
        side_effect=OandaCandleError("provider body private-fixture-token")
    )

    with pytest.raises(XauusdFeedError) as failure:
        XauusdMultiFrameFeed(client).refresh(
            now=datetime(2025, 2, 3, 12, tzinfo=timezone.utc)
        )

    assert "private-fixture-token" not in str(failure.value)


def test_feed_snapshot_updates_multiframe_agent_with_ready_practice_warmup_and_safe_hold():
    """Synthetic provider-shaped rows exercise plumbing only, not market evidence."""
    now = datetime.now(timezone.utc)
    feed, latest_m3_close = _feed_agent_parity_fixture(now)

    snapshot = feed.refresh(now=now)

    assert snapshot["source"] == "OANDA"
    assert snapshot["environment"] == "practice"
    assert len(snapshot["frames"]["M3"]) >= 50
    assert len(snapshot["frames"]["M15"]) >= 50
    assert len(snapshot["frames"]["H4"]) >= 100
    assert all(
        bar["provider"] == "OANDA"
        and bar["environment"] == "practice"
        and bar["complete"] is True
        for frame in snapshot["frames"].values()
        for bar in frame
    )
    assert snapshot["frames"]["M3"][-1]["observed_at"] == (
        latest_m3_close.isoformat(timespec="microseconds").replace("+00:00", "Z")
    )

    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(snapshot) is True
    history_status = agent.get_history_status()
    assert history_status["status"] == "READY"
    assert history_status["minimum_completed_candles"] == {
        "M3": 50,
        "M15": 50,
        "H4": 100,
    }

    quote_time = datetime.now(timezone.utc)
    signal = agent.analyze({
        "source": "OANDA",
        "instrument": "XAU_USD",
        "environment": "practice",
        "tradeable": True,
        "bid": 2501.0,
        "ask": 2502.0,
        "provider_timestamp": quote_time.isoformat(),
    })
    diagnostics = agent.get_diagnostics()
    assert signal is Signal.HOLD
    assert diagnostics["candidate_signal"] == Signal.HOLD.value
    assert diagnostics["actionable_signal"] == Signal.HOLD.value
    assert diagnostics["startup_historical_call_suppressed"] is True
    assert "startup_historical_M3_signal_suppressed" in diagnostics["blockers"]
    assert diagnostics["actionable_count"] == 0
    assert diagnostics["accepted_trades"] == 0


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


def test_h4_transport_pins_oanda_default_ny17_alignment():
    client = _pricing_client()
    client._session.get.return_value = Mock(
        status_code=200,
        json=lambda: {
            "instrument": "XAU_USD",
            "granularity": "H4",
            "candles": [],
        },
    )

    client.get_completed_candles("H4", 101)

    assert client._session.get.call_args.kwargs["params"] == {
        "granularity": "H4",
        "count": 101,
        "price": "BA",
        "smooth": "false",
        "dailyAlignment": 17,
        "alignmentTimezone": "America/New_York",
    }


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