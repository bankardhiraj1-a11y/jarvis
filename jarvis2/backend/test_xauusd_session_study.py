from datetime import datetime, timedelta, timezone

from agents.base import Signal
from agents.xauusd import (
    XAUUSDResearchAgent,
    STRATEGY_PARAMETERS,
    advance_completed_bar,
    entry_holding_exit_reason,
    entry_holding_policy_allows,
    entry_window_intervals_utc,
    initial_strategy_state,
    normalize_entry_window,
    normalize_parameters,
)
from agents.xauusd_highwin import (
    XAUUSDHighWinResearchAgent,
    advance_highwin_bar,
    initial_highwin_state,
    normalize_highwin_parameters,
)
from backtest.xauusd_session_study import (
    MAX_HOLD_MINUTES,
    SESSION_WINDOWS,
    _can_enter,
    fixed_strategies,
    preregistered_candidates,
)


def _window(name: str):
    return next(window for window in SESSION_WINDOWS if window["name"] == name)


def test_fixed_comparison_is_exactly_two_strategies_by_six_windows():
    candidates = preregistered_candidates()
    assert len(candidates) == 12
    assert len({item["candidate_id"] for item in candidates}) == 12
    assert len(fixed_strategies()) == 2
    assert {item["window"]["name"] for item in candidates} == {
        window["name"] for window in SESSION_WINDOWS
    }
    assert all(item["parameters"]["max_hold_minutes"] == MAX_HOLD_MINUTES for item in candidates)
    assert all(item["parameters"]["allow_overnight"] is False for item in candidates)


def test_iana_timezone_schedules_use_sample_dst_and_winter_offsets():
    london = normalize_entry_window(_window("Europe_London_08_17"))
    london_summer = entry_window_intervals_utc(datetime(2026, 7, 6).date(), london)
    london_winter = entry_window_intervals_utc(datetime(2026, 1, 5).date(), london)
    assert london_summer[0] == (
        datetime(2026, 7, 6, 7, tzinfo=timezone.utc),
        datetime(2026, 7, 6, 16, tzinfo=timezone.utc),
    )
    assert london_winter[0] == (
        datetime(2026, 1, 5, 8, tzinfo=timezone.utc),
        datetime(2026, 1, 5, 17, tzinfo=timezone.utc),
    )

    new_york = normalize_entry_window(_window("US_New_York_08_17"))
    assert entry_window_intervals_utc(datetime(2026, 7, 6).date(), new_york)[0] == (
        datetime(2026, 7, 6, 12, tzinfo=timezone.utc),
        datetime(2026, 7, 6, 21, tzinfo=timezone.utc),
    )
    assert entry_window_intervals_utc(datetime(2026, 1, 5).date(), new_york)[0] == (
        datetime(2026, 1, 5, 13, tzinfo=timezone.utc),
        datetime(2026, 1, 5, 22, tzinfo=timezone.utc),
    )

    overlap = normalize_entry_window(_window("EU_US_Overlap"))
    union = normalize_entry_window(_window("EU_US_Union"))
    assert entry_window_intervals_utc(datetime(2026, 7, 6).date(), overlap)[0] == (
        datetime(2026, 7, 6, 12, tzinfo=timezone.utc),
        datetime(2026, 7, 6, 16, tzinfo=timezone.utc),
    )
    assert entry_window_intervals_utc(datetime(2026, 1, 5).date(), overlap)[0] == (
        datetime(2026, 1, 5, 13, tzinfo=timezone.utc),
        datetime(2026, 1, 5, 17, tzinfo=timezone.utc),
    )
    assert entry_window_intervals_utc(datetime(2026, 7, 6).date(), union) == [
        (datetime(2026, 7, 6, 7, tzinfo=timezone.utc), datetime(2026, 7, 6, 21, tzinfo=timezone.utc))
    ]
    assert entry_window_intervals_utc(datetime(2026, 1, 5).date(), union) == [
        (datetime(2026, 1, 5, 8, tzinfo=timezone.utc), datetime(2026, 1, 5, 22, tzinfo=timezone.utc))
    ]


def test_session_entry_cutoff_reserves_full_maximum_hold():
    summer_london = normalize_entry_window(_window("Europe_London_08_17"))
    assert _can_enter(datetime(2026, 7, 6, 15, 34, tzinfo=timezone.utc), summer_london)
    assert not _can_enter(datetime(2026, 7, 6, 15, 36, tzinfo=timezone.utc), summer_london)
    union = normalize_entry_window(_window("EU_US_Union"))
    assert _can_enter(datetime(2026, 7, 6, 20, 34, tzinfo=timezone.utc), union)
    assert not _can_enter(datetime(2026, 7, 6, 20, 36, tzinfo=timezone.utc), union)


def test_shared_holding_policy_reserves_one_minute_before_dst_aware_ny17():
    original = _window("original_utc_16_23")
    assert entry_holding_policy_allows(
        datetime(2026, 7, 6, 20, 34, tzinfo=timezone.utc), 25, original
    )
    assert not entry_holding_policy_allows(
        datetime(2026, 7, 6, 20, 35, tzinfo=timezone.utc), 25, original
    )
    assert entry_holding_policy_allows(
        datetime(2026, 1, 5, 21, 34, tzinfo=timezone.utc), 25, original
    )
    assert not entry_holding_policy_allows(
        datetime(2026, 1, 5, 21, 35, tzinfo=timezone.utc), 25, original
    )
    assert entry_holding_exit_reason(
        datetime(2026, 7, 6, 20, 34, tzinfo=timezone.utc),
        datetime(2026, 7, 6, 20, 59, tzinfo=timezone.utc),
        25,
        original,
    ) == "ny17_rollover_buffer_forced_exit"


def test_ema_runtime_and_shared_reducer_match_custom_window_and_default_is_unchanged():
    london_window = _window("Europe_London_08_17")
    configured = normalize_parameters(
        {
            **STRATEGY_PARAMETERS,
            "fast_ema": 2,
            "slow_ema": 3,
            "min_ema_separation_usd": 0.01,
            "confirmation_buffer_usd": 0,
            "confirmation_bars": 1,
            "entry_window": london_window,
        }
    )
    runtime = XAUUSDResearchAgent(configured)
    state = initial_strategy_state()
    emitted = []
    for minute, close in ((58, 100), (59, 101), (0, 102)):
        stamp = datetime(2026, 7, 6, 6 if minute >= 58 else 7, minute % 60, tzinfo=timezone.utc)
        bar = {
            "observed_at": stamp.isoformat(),
            "close": close,
            "high": close + 0.1,
            "low": close - 0.1,
        }
        expected = advance_completed_bar(state, bar, configured)
        actual = runtime.analyze_completed_bar(bar)
        emitted.append((expected, actual))
    assert emitted[-1][0] == Signal.BUY.value
    assert emitted[-1][1] is Signal.BUY

    defaulted = normalize_parameters(STRATEGY_PARAMETERS)
    assert defaulted["entry_window"]["name"] == "original_utc_16_23"
    assert defaulted["entry_window"]["clauses"] == [
        {"timezone": "UTC", "start": "16:00", "end": "23:00"}
    ]


def test_highwin_runtime_and_shared_reducer_match_custom_window():
    parameters = normalize_highwin_parameters(
        {
            "bar_interval_minutes": 1,
            "rsi_period": 7,
            "rsi_reentry_threshold": 20,
            "bollinger_period": 20,
            "bollinger_stddev": 2,
            "regime_fast_ema": 20,
            "regime_slow_ema": 50,
            "max_range_ema_separation_usd": 2,
            "stop_loss_usd_per_oz": 1.5,
            "take_profit_usd_per_oz": 3.75,
            "max_hold_minutes": 25,
            "allow_overnight": False,
            "max_trades_per_utc_day": 3,
            "entry_window": _window("US_New_York_08_17"),
        }
    )
    runtime = XAUUSDHighWinResearchAgent(parameters)
    state = initial_highwin_state()
    for index in range(200):
        close = 2400 + ((index % 37) - 18) * 0.08
        stamp = datetime(2026, 7, 6, 11, tzinfo=timezone.utc) + timedelta(
            minutes=index
        )
        bar = {
            "observed_at": stamp.isoformat(),
            "close": close,
            "high": close + 0.03,
            "low": close - 0.03,
        }
        expected = advance_highwin_bar(state, bar, parameters)
        actual = runtime.analyze_completed_bar(bar)
        assert (actual.value if actual is not Signal.HOLD else None) == expected