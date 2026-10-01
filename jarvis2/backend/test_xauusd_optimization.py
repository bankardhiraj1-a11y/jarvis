"""Synthetic software tests for the optimizer; never empirical trading evidence."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from agents.base import Signal
from agents.xauusd import (
    STRATEGY_PARAMETERS,
    XAUUSDAgent,
    XAUUSDResearchAgent,
    advance_confirmation,
    advance_completed_bar,
    initial_strategy_state,
    normalize_parameters,
    raw_trend_signal,
)
from agents.xauusd_baseline import XAUUSDBaselineAgent
from backtest.xauusd_optimization import (
    _aggregate_minutes,
    _holdout_passes,
    _metrics,
    _raw_split_before_entry_session,
    _simulate,
    candidate_grid,
    run_optimization,
)


def fixture_candle(stamp: datetime, price: float = 2_500.0) -> dict:
    """Clearly synthetic OHLC, constructed exclusively for deterministic unit tests."""
    return {
        "time": stamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "complete": True,
        "bid_open": price - 0.1,
        "bid_high": price,
        "bid_low": price - 0.2,
        "bid_close": price - 0.1,
        "ask_open": price + 0.1,
        "ask_high": price + 0.2,
        "ask_low": price,
        "ask_close": price + 0.1,
    }


def small_configuration(**overrides):
    config = {
        "fast_ema": 2,
        "slow_ema": 4,
        "min_ema_separation_usd": 0.5,
        "confirmation_buffer_usd": 0.1,
        "confirmation_bars": 2,
        "stop_loss_usd_per_oz": 1.0,
        "take_profit_usd_per_oz": 1.25,
        "max_trades_per_utc_day": 3,
        "entry_cooldown_seconds": 30,
        "position_quantity_units": 100,
    }
    config.update(overrides)
    return config


class TestStrategyConfiguration(unittest.TestCase):
    def test_grid_is_bounded_and_keeps_one_hundred_unit_lot(self):
        grid = candidate_grid()
        self.assertEqual(len(grid), 24)
        self.assertTrue(all(candidate["position_quantity_units"] == 100 for candidate in grid))
        self.assertTrue(all(candidate["confirmation_bars"] == 2 for candidate in grid))
        self.assertEqual({candidate["bar_interval_minutes"] for candidate in grid}, {1, 5})
        self.assertLessEqual(
            max(candidate["stop_loss_usd_per_oz"] for candidate in grid), 1.5
        )
        self.assertEqual(STRATEGY_PARAMETERS["position_quantity_units"], 100)

    def test_it_rejects_any_quantity_other_than_one_100_unit_lot(self):
        with self.assertRaisesRegex(ValueError, "100-unit"):
            normalize_parameters(small_configuration(position_quantity_units=50))

    def test_confirmation_requires_consecutive_bars_and_resets_after_hold(self):
        signal, previous, streak = advance_confirmation(Signal.BUY.value, None, 0, 2)
        self.assertIsNone(signal)
        self.assertEqual((previous, streak), (Signal.BUY.value, 1))
        signal, previous, streak = advance_confirmation(Signal.SELL.value, previous, streak, 2)
        self.assertIsNone(signal)
        self.assertEqual((previous, streak), (Signal.SELL.value, 1))
        signal, previous, streak = advance_confirmation(Signal.SELL.value, previous, streak, 2)
        self.assertEqual(signal, Signal.SELL.value)
        self.assertEqual((previous, streak), (None, 0))

    def test_runtime_uses_completed_bars_and_resets_entry_limit_by_utc_day(self):
        agent = XAUUSDResearchAgent(
            small_configuration(
                min_ema_separation_usd=0,
                confirmation_buffer_usd=0,
                max_trades_per_utc_day=1,
            )
        )
        origin = datetime(2026, 9, 28, 16, 0, tzinfo=timezone.utc)
        self.assertEqual(agent.analyze({"source": "OANDA", "bid": 100, "ask": 101}), Signal.HOLD)
        for index, price in enumerate([100, 110, 110, 110, 110]):
            signal = agent.analyze_completed_bar(
                {"close": price, "observed_at": (origin + timedelta(minutes=index)).isoformat()}
            )
            if index == 2:
                self.assertEqual(signal, Signal.BUY)
            elif index < 2:
                self.assertEqual(signal, Signal.HOLD)
            else:
                self.assertEqual(signal, Signal.HOLD)
        self.assertEqual(agent.open_trade_count, 1)
        next_day = origin + timedelta(days=1)
        self.assertEqual(agent.analyze_completed_bar({"close": 110, "observed_at": next_day.isoformat()}), Signal.HOLD)
        second = agent.analyze_completed_bar(
            {"close": 110, "observed_at": (next_day + timedelta(minutes=1)).isoformat()}
        )
        self.assertEqual(second, Signal.BUY)
        self.assertEqual(agent.open_trade_count, 1)
        self.assertEqual(agent.position_quantity_units, 100)
        self.assertEqual(agent.lot_size, 1.0)
        self.assertEqual(agent.take_profit_usd_per_oz, 1.25)

    def test_live_baseline_alias_is_kept_when_no_candidate_is_installed(self):
        self.assertIs(XAUUSDAgent, XAUUSDBaselineAgent)

    def test_candidate_runtime_updates_ema_off_session_and_shared_state_while_position_open(self):
        params = normalize_parameters(
            small_configuration(
                fast_ema=2,
                slow_ema=4,
                min_ema_separation_usd=0.1,
                confirmation_buffer_usd=0,
                confirmation_bars=1,
                stop_loss_usd_per_oz=0.5,
                take_profit_usd_per_oz=0.75,
                max_trades_per_utc_day=2,
            )
        )
        warmup_start = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
        sample_start = warmup_start + timedelta(minutes=40)
        warmup = [
            fixture_candle(warmup_start + timedelta(minutes=i), 2_500 + i * 0.2)
            for i in range(40)
        ]
        sample = [
            fixture_candle(sample_start + timedelta(minutes=i), 2_508 + i * 0.2)
            for i in range(80)
        ]
        agent = XAUUSDResearchAgent(params)
        observations = []
        for raw_bar in warmup + sample:
            stamp = datetime.fromisoformat(raw_bar["time"].replace("Z", "+00:00"))
            # A broker-held trade does not stop the shadow strategy from
            # processing each real completed candle and advancing indicators.
            bar = {
                "observed_at": (stamp + timedelta(minutes=1)).isoformat(),
                "close": (raw_bar["bid_close"] + raw_bar["ask_close"]) / 2,
                "high": (raw_bar["bid_high"] + raw_bar["ask_high"]) / 2,
                "low": (raw_bar["bid_low"] + raw_bar["ask_low"]) / 2,
            }
            observations.append((raw_bar, bar))
            agent.analyze_completed_bar(bar)

        result = _simulate(sample, warmup, params)
        replay = result["final_strategy_state"]
        self.assertAlmostEqual(replay["ema_fast"], agent.ema_fast)
        self.assertAlmostEqual(replay["ema_slow"], agent.ema_slow)
        self.assertEqual(replay["last_utc_day"], agent._last_utc_day.isoformat())
        self.assertEqual(replay["daily_entry_count"], agent._daily_entry_count)
        self.assertEqual(replay["previous_confirmation"], agent._previous_confirmation)
        self.assertEqual(replay["confirmation_streak"], agent._confirmation_streak)
        self.assertGreater(replay["ema_fast"], (warmup[0]["bid_close"] + warmup[0]["ask_close"]) / 2)
        self.assertGreater(result["signals_suppressed_by_open_position"], 0)
        self.assertGreater(result["overall"]["closed_trades"], 0)

        # Explicit off-session-only updates advance the same production reducer.
        off_session_state = initial_strategy_state()
        closes = [2_500.0, 2_510.0, 2_520.0]
        for minute, close in enumerate(closes):
            bar = {
                "observed_at": (warmup_start + timedelta(minutes=minute)).isoformat(),
                "close": close,
                "high": close + 1,
                "low": close - 1,
            }
            advance_completed_bar(off_session_state, bar, params)
        self.assertEqual(off_session_state["daily_entry_count"], 0)
        self.assertNotEqual(off_session_state["ema_fast"], closes[0])
        self.assertIsNotNone(off_session_state["last_observed_at"])

    def test_strategy_rule_shared_by_runtime_and_optimizer_is_directional_and_bounded(self):
        params = normalize_parameters(small_configuration(min_ema_separation_usd=1))
        self.assertEqual(raw_trend_signal(103, 101, 99, params), Signal.BUY.value)
        self.assertEqual(raw_trend_signal(98, 99, 101, params), Signal.SELL.value)
        self.assertIsNone(raw_trend_signal(101.0, 101, 99, params))


class TestTrainingOnlyOptimizer(unittest.TestCase):
    def test_five_minute_aggregation_preserves_real_side_ohlc_and_drops_gaps(self):
        start = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)
        minutes = [
            fixture_candle(start + timedelta(minutes=index), 2_500 + index)
            for index in range(10)
        ]
        five_minute, dropped = _aggregate_minutes(minutes, 5)
        self.assertEqual(len(five_minute), 2)
        self.assertEqual(five_minute[0]["complete_interval_m1_rows"], 5)
        self.assertEqual(five_minute[0]["bid_open"], minutes[0]["bid_open"])
        self.assertEqual(five_minute[0]["bid_high"], minutes[4]["bid_high"])
        self.assertEqual(five_minute[0]["ask_low"], minutes[0]["ask_low"])
        self.assertEqual(five_minute[0]["ask_close"], minutes[4]["ask_close"])
        self.assertEqual(dropped, 0)
        missing = minutes[:4] + minutes[5:]
        gapped, gap_count = _aggregate_minutes(missing, 5)
        self.assertEqual(len(gapped), 1)
        self.assertEqual(gapped[0]["time"], "2026-09-01T16:05:00Z")
        self.assertGreater(gap_count, 0)

    def test_holdout_sample_accessed_only_after_a_training_selection(self):
        class WatchedCandle(dict):
            index = 0
            first_holdout_index = 0

            def __getitem__(self, key):
                if self.index >= self.first_holdout_index and key.startswith(("bid_", "ask_")):
                    raise AssertionError("Training candidate selection read a holdout price")
                return super().__getitem__(key)

        start = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
        warmup_start = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)
        warmup = [
            fixture_candle(warmup_start + timedelta(minutes=index), 2_500.0)
            for index in range(40)
        ]
        bars = []
        for index in range(2_000):
            row = WatchedCandle(fixture_candle(start + timedelta(minutes=index)))
            row.index = index
            bars.append(row)
        expected_split = _raw_split_before_entry_session(
            bars, max(1, int(len(bars) * 0.70))
        )
        self.assertGreater(expected_split, 1_400)
        for row in bars:
            row.first_holdout_index = expected_split

        # A flat, out-of-session path cannot meet the validation rules. Therefore
        # the optimizer returns without even constructing a holdout price bar.
        report, candidate_rows = run_optimization(
            bars,
            warmup,
            source_sha256="a" * 64,
            baseline_report={"status": "unchanged_original_baseline", "strategy_changed": False},
            candidates=[small_configuration()],
        )
        self.assertEqual(len(candidate_rows), 1)
        self.assertEqual(report["candidate_count"], 1)
        self.assertFalse(report["selection_looked_at_holdout"])
        self.assertEqual(report["holdout_evaluation_count"], 0)
        self.assertEqual(report["out_of_sample"]["closed_trades"], None)
        self.assertIsNone(report["candidate_parameters"])
        self.assertFalse(report["recommended_for_paper"])

    def test_timestamp_cut_does_not_load_or_inspect_any_prices(self):
        class TimestampOnly:
            def __init__(self, stamp):
                self.values = {"time": stamp}

            def __getitem__(self, key):
                if key != "time":
                    raise AssertionError("A holdout price was inspected while locating its cut")
                return self.values[key]

        start = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
        rows = [
            TimestampOnly(
                (start + timedelta(minutes=index)).isoformat().replace("+00:00", "Z")
            )
            for index in range(600)
        ]
        self.assertEqual(_raw_split_before_entry_session(rows, 420), 420)

    def test_wilson_interval_discloses_small_sample_uncertainty(self):
        report = _metrics(
            [
                {"pnl_usd": 75.0},
                {"pnl_usd": -100.0},
                {"pnl_usd": 20.0},
            ]
        )
        interval = report["win_rate_95pct_wilson"]
        self.assertEqual(report["win_rate_pct"], 66.67)
        self.assertLess(interval["low_pct"], 66.67)
        self.assertGreater(interval["high_pct"], 66.67)
        self.assertGreater(interval["high_pct"] - interval["low_pct"], 70.0)

    def test_holdout_validation_requires_independent_positive_expectancy_and_sample(self):
        passing = {
            "closed_trades": 24,
            "wins": 15,
            "losses": 9,
            "net_pnl_usd": 500,
            "expectancy_usd_per_closed_trade": 20,
            "profit_factor": 1.2,
            "max_closed_trade_drawdown_usd": 1_500,
        }
        is_passing, reasons = _holdout_passes(passing)
        self.assertTrue(is_passing)
        self.assertEqual(reasons, [])
        weak = {**passing, "net_pnl_usd": -1}
        is_passing, reasons = _holdout_passes(weak)
        self.assertFalse(is_passing)
        self.assertIn("holdout net modeled P&L is not positive", reasons)


if __name__ == "__main__":
    unittest.main()