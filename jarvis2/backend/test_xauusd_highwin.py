"""Synthetic software tests for the preregistered high-win research path."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from agents.base import Signal
from agents.xauusd_highwin import (
    XAUUSDHighWinResearchAgent,
    advance_highwin_bar,
    highwin_entry_policy_allows,
    highwin_holding_exit_reason,
    initial_highwin_state,
    normalize_highwin_parameters,
    register_highwin_entry,
)
from backtest.xauusd_evidence import _exit_bar
from backtest.xauusd_highwin import (
    _simulate_highwin,
    predeclared_candidates,
    run_highwin_optimization,
)
from backtest.xauusd_optimization import _raw_split_before_entry_session


def synthetic_ohlc(stamp: datetime, close: float) -> dict:
    """Deterministic software-only fixture; never used as market evidence."""
    return {
        "time": stamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "complete": True,
        "bid_open": close - 0.35,
        "bid_high": close - 0.1,
        "bid_low": close - 0.6,
        "bid_close": close - 0.35,
        "ask_open": close + 0.35,
        "ask_high": close + 0.6,
        "ask_low": close + 0.1,
        "ask_close": close + 0.35,
    }


def make_parameters(**overrides):
    config = {
        "bar_interval_minutes": 1,
        "rsi_period": 7,
        "rsi_reentry_threshold": 30,
        "bollinger_period": 20,
        "bollinger_stddev": 2.0,
        "regime_fast_ema": 20,
        "regime_slow_ema": 50,
        "max_range_ema_separation_usd": 2.0,
        "stop_loss_usd_per_oz": 2.0,
        "take_profit_usd_per_oz": 4.0,
        "max_trades_per_utc_day": 3,
        "position_quantity_units": 100,
    }
    config.update(overrides)
    return normalize_highwin_parameters(config)


class TestPredeclaredHighwinStudy(unittest.TestCase):
    def test_configuration_count_spread_cost_and_risk_bounds_are_fixed(self):
        configs = predeclared_candidates()
        self.assertEqual(len(configs), 32)
        self.assertLessEqual(len(configs), 36)
        self.assertEqual({item["bar_interval_minutes"] for item in configs}, {1, 5})
        self.assertTrue(all(item["position_quantity_units"] == 100 for item in configs))
        self.assertTrue(all(item["max_hold_minutes"] == 25 for item in configs))
        self.assertTrue(all(item["allow_overnight"] is False for item in configs))
        self.assertTrue(all(item["stop_loss_usd_per_oz"] <= 3 for item in configs))
        self.assertTrue(all(item["take_profit_usd_per_oz"] >= 3.75 for item in configs))
        break_even_rates = {
            round(
                100 * item["stop_loss_usd_per_oz"]
                / (item["stop_loss_usd_per_oz"] + item["take_profit_usd_per_oz"]),
                2,
            )
            for item in configs
        }
        self.assertTrue(all(28 <= rate <= 38 for rate in break_even_rates))

    def test_it_rejects_a_stop_above_three_dollars_per_ounce(self):
        with self.assertRaisesRegex(ValueError, "risk/data bounds"):
            make_parameters(stop_loss_usd_per_oz=3.01)

    def test_ambiguous_and_gap_through_stops_are_resolved_adversely(self):
        position = {
            "signal": Signal.BUY.value,
            "entry_price": 100.0,
            "stop_price": 98.0,
            "target_price": 104.0,
        }
        both_touched = {
            "bid_open": 100.0,
            "bid_high": 105.0,
            "bid_low": 97.0,
            "ask_open": 100.7,
            "ask_high": 105.7,
            "ask_low": 97.7,
        }
        self.assertEqual(_exit_bar(position, both_touched), {
            "price": 98.0,
            "reason": "stop_first_if_both_touched",
        })
        gapped = {**both_touched, "bid_open": 96.5}
        self.assertEqual(_exit_bar(position, gapped), {
            "price": 96.5,
            "reason": "gap_through_stop",
        })

    def test_highwin_runtime_and_historical_replay_share_complete_bar_state(self):
        parameters = make_parameters(
            rsi_period=3,
            rsi_reentry_threshold=30,
            bollinger_period=10,
            bollinger_stddev=1.0,
            max_range_ema_separation_usd=20.0,
        )
        warmup_start = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
        warmup = []
        for index in range(80):
            offset = (index % 12) - 6
            warmup.append(synthetic_ohlc(
                warmup_start + timedelta(minutes=index),
                2_500.0 + offset * 0.4,
            ))
        sample_start = warmup_start + timedelta(minutes=80)
        path = [2_500.0 + ((index * 7) % 19 - 9) * 0.3 for index in range(180)]
        sample = [
            synthetic_ohlc(sample_start + timedelta(minutes=index), price)
            for index, price in enumerate(path)
        ]

        agent = XAUUSDHighWinResearchAgent(parameters)
        runtime_signals = 0
        for source in warmup + sample:
            open_time = datetime.fromisoformat(source["time"].replace("Z", "+00:00"))
            bar = {
                "observed_at": (open_time + timedelta(minutes=1)).isoformat(),
                "close": (source["bid_close"] + source["ask_close"]) / 2,
                "high": (source["bid_high"] + source["ask_high"]) / 2,
                "low": (source["bid_low"] + source["ask_low"]) / 2,
            }
            runtime_signals += agent.analyze_completed_bar(bar) != Signal.HOLD

        replay = _simulate_highwin(sample, warmup, parameters)
        state = replay["final_state"]
        self.assertAlmostEqual(state["ema_regime_fast"], agent.highwin_state["ema_regime_fast"])
        self.assertAlmostEqual(state["ema_regime_slow"], agent.highwin_state["ema_regime_slow"])
        self.assertEqual(state["rsi"], agent.highwin_state["rsi"])
        self.assertEqual(state["closes"], agent.highwin_state["closes"])
        self.assertEqual(state["daily_entry_count"], agent.highwin_state["daily_entry_count"])
        self.assertEqual(
            replay["warmup_signals"] + replay["confirmed_signals"],
            runtime_signals,
        )
        self.assertEqual(agent.position_quantity_units, 100)
        self.assertEqual(agent.lot_size, 1.0)
        self.assertLessEqual(agent.stop_loss_usd_per_oz, 3.0)

    def test_gap_resets_technical_warmup_but_not_same_day_risk_count(self):
        parameters = make_parameters(rsi_period=3, bollinger_period=10)
        state = initial_highwin_state()
        start = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)
        for index in range(20):
            close = 2_500 + index * 0.1
            advance_highwin_bar(
                state,
                {
                    "observed_at": (start + timedelta(minutes=index)).isoformat(),
                    "close": close,
                    "high": close + 0.2,
                    "low": close - 0.2,
                },
                parameters,
            )
        state["daily_entry_count"] = 2
        after_gap = start + timedelta(minutes=35)
        advance_highwin_bar(
            state,
            {
                "observed_at": after_gap.isoformat(),
                "close": 2_500,
                "high": 2_501,
                "low": 2_499,
            },
            parameters,
        )
        self.assertEqual(state["daily_entry_count"], 2)
        self.assertEqual(state["closes"], [2_500])
        self.assertIsNone(state["rsi"])
        self.assertEqual(state["last_observed_at"], after_gap)

    def test_only_accepted_entries_count_toward_three_per_day(self):
        parameters = make_parameters(max_trades_per_utc_day=3)
        state = initial_highwin_state()
        entry_time = datetime(2026, 9, 1, 16, 1, tzinfo=timezone.utc)
        self.assertTrue(register_highwin_entry(state, entry_time, parameters))
        self.assertTrue(register_highwin_entry(state, entry_time, parameters))
        self.assertTrue(register_highwin_entry(state, entry_time, parameters))
        self.assertFalse(register_highwin_entry(state, entry_time, parameters))
        self.assertEqual(state["daily_entry_count"], 3)

        next_day = entry_time + timedelta(days=1)
        self.assertTrue(register_highwin_entry(state, next_day, parameters))
        self.assertEqual(state["daily_entry_count"], 1)

    def test_25_minute_intraday_policy_prevents_overnight_holds(self):
        parameters = make_parameters()
        entry = datetime(2026, 9, 1, 20, 34, tzinfo=timezone.utc)
        self.assertTrue(highwin_entry_policy_allows(entry, parameters))
        self.assertFalse(
            highwin_entry_policy_allows(entry + timedelta(minutes=1), parameters)
        )
        self.assertIsNone(
            highwin_holding_exit_reason(
                datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc),
                datetime(2026, 9, 1, 16, 24, tzinfo=timezone.utc),
                parameters,
            )
        )
        self.assertEqual(
            highwin_holding_exit_reason(
                datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc),
                datetime(2026, 9, 1, 16, 25, tzinfo=timezone.utc),
                parameters,
            ),
            "maximum_holding_period_exit",
        )
        self.assertEqual(
            highwin_holding_exit_reason(
                entry,
                datetime(2026, 9, 1, 20, 59, tzinfo=timezone.utc),
                parameters,
            ),
            "ny17_rollover_buffer_forced_exit",
        )
        self.assertEqual(
            highwin_holding_exit_reason(
                entry,
                datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
                parameters,
            ),
            "no_overnight_forced_exit",
        )

        agent = XAUUSDHighWinResearchAgent(parameters)
        self.assertTrue(agent.research_entry_policy_allows(entry))
        self.assertTrue(agent.register_research_entry(entry))
        self.assertFalse(agent.register_research_entry(entry + timedelta(minutes=1)))
        self.assertFalse(
            agent.should_force_research_time_exit(entry + timedelta(minutes=24))
        )
        self.assertTrue(
            agent.should_force_research_time_exit(entry + timedelta(minutes=25))
        )
        agent.mark_research_position_closed()
        self.assertFalse(
            agent.should_force_research_time_exit(entry + timedelta(minutes=26))
        )

    def test_candidate_search_never_reads_holdout_prices_without_training_selection(self):
        class WatchedCandle(dict):
            first_holdout_index = 0
            index = 0

            def __getitem__(self, key):
                if self.index >= self.first_holdout_index and key.startswith(("bid_", "ask_")):
                    raise AssertionError("High-win selection read an untouched holdout price")
                return super().__getitem__(key)

        start = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
        warmup_start = datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc)
        warmup = [
            synthetic_ohlc(warmup_start + timedelta(minutes=index), 2_500.0)
            for index in range(120)
        ]
        bars = []
        for index in range(1_500):
            row = WatchedCandle(synthetic_ohlc(start + timedelta(minutes=index), 2_500.0))
            row.index = index
            bars.append(row)
        split = _raw_split_before_entry_session(bars, int(len(bars) * 0.70))
        for row in bars:
            row.first_holdout_index = split

        report, rows = run_highwin_optimization(
            bars,
            warmup,
            source_sha256="b" * 64,
            baseline_report={"status": "unchanged", "strategy_changed": False},
            candidates=[predeclared_candidates()[0]],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["holdout_evaluation_count"], 0)
        self.assertFalse(report["selection_looked_at_final_holdout"])
        self.assertIsNone(report["out_of_sample"])
        self.assertIsNone(report["selected_parameters"])
        self.assertFalse(report["paper_entries_enabled"])
        coverage = report["training_diagnostics"]["best_coverage_candidate"]["inner_validation_daily_coverage"]
        self.assertIn("proposed_review_calls_per_eligible_active_day", coverage)
        self.assertIn("actual_entries_per_eligible_active_day", coverage)
        self.assertIn("closed_trades_per_eligible_active_day", coverage)
        self.assertIn("entry_window_coverage_of_eligible_days_pct", coverage)
        self.assertEqual(
            coverage["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"]["0"]
            + coverage["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"]["1"]
            + coverage["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"]["2"]
            + coverage["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"]["3"]
            + coverage["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"]["4_plus"],
            coverage["eligible_active_trading_days"],
        )


if __name__ == "__main__":
    unittest.main()