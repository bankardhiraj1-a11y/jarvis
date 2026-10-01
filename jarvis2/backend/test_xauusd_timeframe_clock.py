"""Synthetic timing fixtures only; no trading evidence."""

from datetime import timedelta

from backtest.xauusd_optimization import _prepare
from backtest.xauusd_evidence import _within_entry_session


def prepared(stamp, minutes):
    bar = {"time": stamp, "bid_close": 2500.0, "ask_close": 2500.2}
    return _prepare([bar], timeframe_minutes=minutes)[0]


def test_m5_closes_become_observable_at_16_not_1556():
    row = prepared("2026-09-01T15:55:00Z", 5)
    assert row["observed_at"] - row["open_time"] == timedelta(minutes=5)
    assert row["observed_at"].hour == 16
    assert row["observed_at"].minute == 0
    assert _within_entry_session(row["observed_at"].isoformat()) is True


def test_m5_close_at_23_is_not_an_entry_observation():
    row = prepared("2026-09-01T22:55:00Z", 5)
    assert row["observed_at"].hour == 23
    assert _within_entry_session(row["observed_at"].isoformat()) is False


def test_m1_clock_keeps_actual_one_minute_completion():
    row = prepared("2026-09-01T15:59:00Z", 1)
    assert row["observed_at"] - row["open_time"] == timedelta(minutes=1)
    assert _within_entry_session(row["observed_at"].isoformat()) is True


def test_m5_completed_candle_sets_next_utc_day():
    row = prepared("2026-09-01T23:55:00Z", 5)
    assert row["utc_day"].isoformat() == "2026-09-02"