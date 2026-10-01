"""Deterministic synthetic software tests; fixtures are not market evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import agents.xauusd_multiframe as multiframe
from agents.base import Signal
from agents.xauusd_multiframe import (
    MULTIFRAME_PARAMETERS,
    XAUUSDMultiframeResearchAgent,
    _bar_metrics,
)


UTC = timezone.utc
START = datetime(2026, 6, 8, 10, 0, tzinfo=UTC)


def _clock(monkeypatch, instant):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz is None else instant.astimezone(tz)

    monkeypatch.setattr(multiframe, "datetime", FrozenDateTime)


def _iso(stamp):
    return stamp.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _synthetic_bar(frame, observed_at, close, direction, *, touch=False):
    interval = {"M3": 3, "M15": 15, "H4": 240}[frame]
    body = 0.02 if direction == Signal.BUY.value else -0.02
    opening = close - body
    high = max(opening, close) + 0.2
    low = min(opening, close) - 0.2
    return {
        "bar_open_time": _iso(observed_at - timedelta(minutes=interval)),
        "observed_at": _iso(observed_at),
        "open": opening,
        "high": high,
        "low": low,
        "close": close,
        "bid_close": close - 0.05,
        "ask_close": close + 0.05,
        "complete": True,
        "provider": "OANDA",
        "environment": "practice",
        "bar_interval_minutes": interval,
    }


def _trend_frame(frame, count, final_close_at, direction, *, touch=True):
    interval = {"M3": 3, "M15": 15, "H4": 240}[frame]
    closes = []
    for index in range(count):
        step = 0.1 * index
        if direction == Signal.BUY.value:
            close = 2_500.0 + step
        else:
            close = 2_500.0 - step
        closes.append(close)
    if frame == "M3":
        closes[-1] += 0.6 if direction == Signal.BUY.value else -0.6

    first_close_at = final_close_at - timedelta(minutes=interval * (count - 1))
    bars = [
        _synthetic_bar(
            frame,
            first_close_at + timedelta(minutes=interval * index),
            close,
            direction,
        )
        for index, close in enumerate(closes)
    ]
    if frame == "M15" and touch:
        ema = _bar_metrics(bars)["ema20_series"]
        if direction == Signal.BUY.value:
            bars[-1]["low"] = ema[-1]
        else:
            bars[-1]["high"] = ema[-1]
    return bars


def synthetic_snapshot(now=START, direction=Signal.BUY.value, *, touch=True):
    """Explicitly synthetic deterministic closed-candle fixture, not market evidence."""
    latest_m15 = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    latest_h4 = now.replace(
        hour=(now.hour // 4) * 4, minute=0, second=0, microsecond=0
    )
    return {
        "fetched_at": _iso(now),
        "environment": "practice",
        "frames": {
            "M3": _trend_frame(
                "M3", 50, now, direction, touch=touch
            ),
            "M15": _trend_frame(
                "M15", 50, latest_m15, direction, touch=touch
            ),
            "H4": _trend_frame(
                "H4", 101, latest_h4, direction, touch=touch
            ),
        },
    }


def synthetic_quote(now, **overrides):
    return {
        "source": "OANDA",
        "instrument": "XAU_USD",
        "environment": "practice",
        "tradeable": True,
        "provider_timestamp": _iso(now),
        "bid": 2_500.0,
        "ask": 2_500.1,
        **overrides,
    }


@pytest.mark.parametrize("direction", [Signal.BUY.value, Signal.SELL.value])
def test_synthetic_causal_h4_m15_m3_confirmations_suppress_startup_then_signal(
    monkeypatch, direction
):
    """Synthetic software-only setup; it is not a performance result."""
    _clock(monkeypatch, START + timedelta(minutes=3))
    agent = XAUUSDMultiframeResearchAgent()
    first = synthetic_snapshot(START, direction)
    assert agent.update_candles(first)

    assert agent.analyze(synthetic_quote(START)) == Signal.HOLD
    first_decision = agent.get_diagnostics()
    assert first_decision["candidate_signal"] == direction
    assert first_decision["startup_historical_call_suppressed"] is True
    assert first_decision["h4_direction"] == direction
    assert first_decision["m15_direction"] == direction
    assert first_decision["m3_direction"] == direction
    assert first_decision["m15_pullback_touch"] is True

    next_at = START + timedelta(minutes=3)
    second = synthetic_snapshot(next_at, direction)
    assert agent.update_candles(second)
    assert agent.analyze(synthetic_quote(next_at)) == Signal(direction)
    assert agent.get_diagnostics()["startup_historical_call_suppression"] is True
    assert agent.get_diagnostics()["actionable_count"] == 1


def test_synthetic_no_touch_and_misaligned_timeframes_fail_closed():
    """Synthetic indicator tests are software fixtures, never performance evidence."""
    clean = synthetic_snapshot(START, Signal.BUY.value, touch=False)["frames"]
    h4, m15, m3, reasons = XAUUSDMultiframeResearchAgent._directions(clean)
    assert h4["direction"] == m15["direction"] == m3["direction"] == Signal.BUY.value
    assert m15["pullback_touch"] is False
    assert "M15_latest_three_bars_have_no_EMA20_touch" in reasons

    misaligned = synthetic_snapshot(START, Signal.BUY.value)["frames"]
    misaligned["M15"] = _trend_frame("M15", 50, START, Signal.SELL.value)
    h4, m15, m3, reasons = XAUUSDMultiframeResearchAgent._directions(misaligned)
    assert h4["direction"] == m3["direction"] == Signal.BUY.value
    assert m15["direction"] == Signal.SELL.value
    assert "H4_M15_directions_disagree" in reasons


def test_empty_and_short_synthetic_frames_do_not_crash_direction_checks():
    empty = {frame: [] for frame in ("H4", "M15", "M3")}
    directions = XAUUSDMultiframeResearchAgent._directions(empty)
    assert all(item["direction"] == "MIXED" for item in directions[:3])

    partial = {
        "H4": _trend_frame("H4", 3, START, Signal.BUY.value),
        "M15": _trend_frame("M15", 2, START, Signal.BUY.value),
        "M3": _trend_frame("M3", 1, START, Signal.BUY.value),
    }
    directions = XAUUSDMultiframeResearchAgent._directions(partial)
    assert all(item["direction"] in (Signal.BUY.value, Signal.SELL.value, "MIXED")
               for item in directions[:3])


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda snapshot: snapshot["frames"]["M3"][-1].update(complete=False),
         "not explicitly complete"),
        (lambda snapshot: snapshot["frames"]["M3"][-1].update(high=1.0),
         "inconsistent OHLC"),
        (lambda snapshot: snapshot["frames"]["M3"][-1].update(
            observed_at=_iso(START + timedelta(minutes=4)),
            bar_open_time=_iso(START + timedelta(minutes=1)),
        ), "snapshot future"),
    ],
)
def test_malformed_incomplete_and_future_synthetic_candles_are_rejected(
    monkeypatch, mutation, error
):
    """Invalid synthetic input verifies fail-closed validation only."""
    _clock(monkeypatch, START)
    agent = XAUUSDMultiframeResearchAgent()
    snapshot = synthetic_snapshot()
    mutation(snapshot)
    assert agent.update_candles(snapshot) is False
    assert error in agent.get_diagnostics()["snapshot_error"]


def test_empty_synthetic_snapshot_and_short_warmup_return_hold_without_crash(
    monkeypatch,
):
    _clock(monkeypatch, START)
    agent = XAUUSDMultiframeResearchAgent()
    empty = {
        "fetched_at": _iso(START),
        "environment": "practice",
        "frames": {"M3": [], "M15": [], "H4": []},
    }
    assert agent.update_candles(empty)
    assert agent.analyze(synthetic_quote(START)) == Signal.HOLD
    assert agent.get_history_status()["status"] == "WARMUP"

    short = synthetic_snapshot()
    short["frames"]["M3"] = _trend_frame("M3", 3, START, Signal.BUY.value)
    short["frames"]["M15"] = _trend_frame("M15", 2, START, Signal.BUY.value)
    short["frames"]["H4"] = _trend_frame("H4", 3, START, Signal.BUY.value)
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(short)
    assert agent.analyze(synthetic_quote(START)) == Signal.HOLD
    assert agent.get_diagnostics()["status"] == "WARMUP"


def test_fresh_quote_cannot_rescue_stale_snapshot_or_untradeable_wrong_instrument_quote(
    monkeypatch,
):
    _clock(monkeypatch, START)
    agent = XAUUSDMultiframeResearchAgent()
    stale = synthetic_snapshot(START - timedelta(seconds=211))
    assert agent.update_candles(stale) is False
    assert agent.analyze(synthetic_quote(START)) == Signal.HOLD
    assert agent.get_history_status()["status"] == "INVALID"

    fresh = synthetic_snapshot()
    assert agent.update_candles(fresh)
    for quote, expected in (
        (synthetic_quote(START, instrument="XAUUSD"), "quote_instrument_must_be_XAU_USD"),
        (synthetic_quote(START, tradeable=False), "OANDA_instrument_not_tradeable"),
    ):
        assert agent.analyze(quote) == Signal.HOLD
        assert expected in agent.get_diagnostics()["reasons"]


def test_snapshot_age_and_provider_quote_age_or_future_skew_are_enforced(monkeypatch):
    _clock(monkeypatch, START)
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(synthetic_snapshot())
    for quote in (
        synthetic_quote(START - timedelta(seconds=211)),
        synthetic_quote(START + timedelta(seconds=3)),
    ):
        assert agent.analyze(quote) == Signal.HOLD


def test_previously_valid_snapshot_expires_even_with_fresh_m3_and_quote(monkeypatch):
    """Synthetic safety regression; not evidence of trading outcomes."""
    _clock(monkeypatch, START)
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(synthetic_snapshot())
    _clock(monkeypatch, START + timedelta(seconds=211))
    # Keep M3 recent to isolate snapshot age from candle age.
    agent._snapshot["frames"]["M3"][-1]["observed_at"] = START + timedelta(seconds=180)
    assert agent.analyze(synthetic_quote(START + timedelta(seconds=211))) == Signal.HOLD
    assert "candle_snapshot_stale" in agent.get_diagnostics()["reasons"]
    assert agent.get_diagnostics()["checked_count"] == 0


def test_duplicate_and_out_of_order_decisions_survive_rolling_snapshot_refresh(
    monkeypatch,
):
    """Synthetic rolling refresh tests preserve decision state without market claims."""
    _clock(monkeypatch, START + timedelta(minutes=3))
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(synthetic_snapshot())
    assert agent.analyze(synthetic_quote(START)) == Signal.HOLD
    assert agent.update_candles(synthetic_snapshot(START + timedelta(minutes=3)))
    assert agent.analyze(synthetic_quote(START + timedelta(minutes=3))) == Signal.BUY
    assert agent.analyze(synthetic_quote(START + timedelta(minutes=3))) == Signal.HOLD
    assert agent.get_diagnostics()["checked_count"] == 2
    assert "M3_close_already_evaluated" in agent.get_diagnostics()["reasons"]

    older = synthetic_snapshot(START)
    older["fetched_at"] = _iso(START + timedelta(minutes=3))
    assert agent.update_candles(older)
    assert agent.analyze(synthetic_quote(START + timedelta(minutes=3))) == Signal.HOLD
    assert "out_of_order_M3_close" in agent.get_diagnostics()["reasons"]
    assert agent.get_diagnostics()["checked_count"] == 2


def test_incremental_ema_seed_matches_full_history_after_rolling_refresh():
    """Synthetic unit verifies EMA continuity across a moving feed window only."""
    agent = XAUUSDMultiframeResearchAgent()
    h4_bars = _trend_frame("H4", 101, START, Signal.BUY.value)
    initial = {frame: [] for frame in ("M3", "M15", "H4")}
    initial["H4"] = h4_bars
    metrics, coherent = agent._advance_ema_history(initial)
    assert coherent

    next_close_at = datetime.fromisoformat(
        h4_bars[-1]["observed_at"].replace("Z", "+00:00")
    ) + timedelta(hours=4)
    appended = _synthetic_bar(
        "H4", next_close_at, h4_bars[-1]["close"] + 0.1, Signal.BUY.value
    )
    rolled = {frame: [] for frame in ("M3", "M15", "H4")}
    rolled["H4"] = h4_bars[1:] + [appended]
    rolled_metrics, coherent = agent._advance_ema_history(rolled)
    full_metrics = _bar_metrics(h4_bars + [appended])

    assert coherent
    assert rolled_metrics["H4"]["ema20"] == pytest.approx(full_metrics["ema20"])
    assert rolled_metrics["H4"]["ema50"] == pytest.approx(full_metrics["ema50"])
    assert rolled_metrics["H4"]["ema20_slope_3"] == pytest.approx(
        full_metrics["ema20_slope_3"]
    )


def test_stale_h4_m15_fail_closed_but_weekend_only_h4_gap_is_allowed(monkeypatch):
    monday_morning = datetime(2026, 6, 8, 7, 0, tzinfo=UTC)
    _clock(monkeypatch, monday_morning)
    weekend_h4_close = datetime(2026, 6, 5, 20, 0, tzinfo=UTC)
    snapshot = synthetic_snapshot(monday_morning)
    snapshot["frames"]["H4"] = _trend_frame(
        "H4", 101, weekend_h4_close, Signal.BUY.value
    )
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.update_candles(snapshot)
    assert agent._stale_frame_reasons(agent._snapshot["frames"], monday_morning) == []
    assert agent.analyze(synthetic_quote(monday_morning)) == Signal.HOLD
    assert agent.get_diagnostics()["candidate_signal"] == Signal.BUY.value
    assert "latest_H4_close_stale" not in agent.get_diagnostics()["blockers"]

    stale_m15 = _trend_frame(
        "M15", 50, monday_morning - timedelta(minutes=45), Signal.BUY.value
    )
    stale_snapshot = {
        **snapshot,
        "frames": {**snapshot["frames"], "M15": stale_m15},
    }
    assert agent.update_candles(stale_snapshot)
    assert agent.get_history_status()["status"] == "WAIT"
    assert "latest_M15_close_stale" in agent._stale_frame_reasons(
        agent._snapshot["frames"], monday_morning
    )
    stale_agent = XAUUSDMultiframeResearchAgent()
    assert stale_agent.update_candles(stale_snapshot)
    assert stale_agent.analyze(synthetic_quote(monday_morning)) == Signal.HOLD
    assert "latest_M15_close_stale" in stale_agent.get_diagnostics()["blockers"]

    weekday_old_h4 = _trend_frame(
        "H4", 101, datetime(2026, 6, 4, 20, 0, tzinfo=UTC), Signal.BUY.value
    )
    weekday_stale = {
        **snapshot,
        "frames": {**snapshot["frames"], "H4": weekday_old_h4},
    }
    assert agent.update_candles(weekday_stale)
    assert agent.get_history_status()["status"] == "WAIT"
    assert "latest_H4_close_stale" in agent._stale_frame_reasons(
        agent._snapshot["frames"], monday_morning
    )
    stale_agent = XAUUSDMultiframeResearchAgent()
    assert stale_agent.update_candles(weekday_stale)
    assert stale_agent.analyze(synthetic_quote(monday_morning)) == Signal.HOLD
    assert "latest_H4_close_stale" in stale_agent.get_diagnostics()["blockers"]


def test_provider_time_entry_cap_holding_rollover_and_frozen_150_risk():
    agent = XAUUSDMultiframeResearchAgent()
    assert agent.position_quantity_units == 100
    assert agent.risk_per_trade == 150.0
    assert MULTIFRAME_PARAMETERS["stop_loss_usd_per_oz"] * agent.position_quantity_units == 150.0
    with pytest.raises(ValueError, match="frozen"):
        XAUUSDMultiframeResearchAgent({"stop_loss_usd_per_oz": 1.51})

    entry = datetime(2026, 6, 8, 14, 0, tzinfo=UTC)
    for minute in range(3):
        provider_time = entry + timedelta(minutes=minute)
        assert agent.register_research_entry(provider_time)
        assert agent.daily_entry_count == minute + 1
        assert agent.register_research_entry(provider_time) is False
        if minute < 2:
            agent.mark_research_position_closed()
    agent.mark_research_position_closed()
    assert agent.register_research_entry(entry + timedelta(minutes=3)) is False
    assert agent.daily_entry_count == 3

    # Closed position state can roll to a new provider UTC date, not host date.
    agent.mark_research_position_closed()
    next_provider_day = datetime(2026, 6, 9, 10, 0, tzinfo=UTC)
    # The signal/decision can belong to the prior UTC day; accepted fills roll
    # the risk counter using the actual provider entry timestamp.
    agent.highwin_state["last_utc_day"] = entry.date()
    agent.highwin_state["daily_entry_count"] = 3
    assert agent.register_research_entry(next_provider_day)
    assert agent.daily_entry_count == 1
    assert not agent.research_entry_policy_allows(
        datetime(2026, 6, 9, 15, 36, tzinfo=UTC)
    )

    assert agent.should_force_research_time_exit(next_provider_day + timedelta(minutes=25))
    assert agent.should_force_research_time_exit(next_provider_day + timedelta(days=1))
    agent.mark_research_position_closed()
    assert not agent.should_force_research_time_exit(next_provider_day + timedelta(minutes=26))


def test_agent_requires_100_h4_startup_bars():
    minimums = MULTIFRAME_PARAMETERS["minimum_completed_candles"]
    assert minimums["H4"] == 100