"""Deterministic software-fixture tests; none is a market-performance claim."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from backtest.xauusd_evidence import (
    INSTRUMENT,
    TRAIN_FRACTION,
    XAUHistoryError,
    _bar_observation_time,
    _csv_bytes,
    _exit_bar,
    _fetch_historical_candles,
    _format_utc_timestamp,
    _fold_metrics,
    _price_bar,
    _trade_pnl,
    _validate_nonoverlapping_warmup,
    _within_entry_session,
    _within_observed_bar_entry_session,
    evaluate_xauusd,
    validate_and_sort_candles,
)
from agents.base import Signal


def candle(timestamp, *, mid=2500.0, spread=0.2, minute_range=0.1):
    """Clearly synthetic fixture used only to test the adapter and controls."""
    bid = mid - spread / 2
    ask = mid + spread / 2
    return {
        "time": timestamp,
        "complete": True,
        "bid": {
            "o": str(bid),
            "h": str(bid + minute_range),
            "l": str(bid - minute_range),
            "c": str(bid),
        },
        "ask": {
            "o": str(ask),
            "h": str(ask + minute_range),
            "l": str(ask - minute_range),
            "c": str(ask),
        },
    }


class XAUHistoryAdapterTests(unittest.TestCase):
    def test_prices_are_genuine_side_specific_ohlc_not_fabricated_paths(self):
        row = _price_bar(candle("2026-09-28T17:04:00.000000000Z", mid=2501, spread=0.4))
        self.assertEqual(row["bid_open"], 2500.8)
        self.assertEqual(row["ask_open"], 2501.2)
        self.assertEqual(row["data_source"], "OANDA_PRACTICE_HISTORICAL")
        self.assertEqual(row["environment"], "practice")
        self.assertNotIn("volume", row)

    def test_incomplete_or_crossed_provider_bars_are_rejected(self):
        incomplete = candle("2026-09-28T17:04:00Z")
        incomplete["complete"] = False
        with self.assertRaises(XAUHistoryError):
            _price_bar(incomplete)
        crossed = candle("2026-09-28T17:04:00Z")
        crossed["ask"]["o"] = crossed["bid"]["o"]
        with self.assertRaises(XAUHistoryError):
            _price_bar(crossed)

    def test_chronology_is_sorted_but_duplicate_provider_prices_fail_closed(self):
        first = candle("2026-09-28T17:04:00Z")
        second = candle("2026-09-28T17:05:00Z", mid=2501)
        self.assertEqual(
            [row["time"] for row in validate_and_sort_candles([second, first])],
            [first["time"], second["time"]],
        )
        with self.assertRaisesRegex(XAUHistoryError, "duplicate"):
            validate_and_sort_candles([first, first])

    def test_completed_close_not_open_timestamp_controls_entry_session(self):
        # An OANDA 15:59 candle becomes observable at the allowed 16:00
        # boundary; a 22:59 candle only closes at 23:00 and cannot signal.
        self.assertTrue(_within_observed_bar_entry_session("2026-09-28T15:59:00Z"))
        self.assertTrue(_within_entry_session("2026-09-28T16:00:00Z"))
        self.assertFalse(_within_observed_bar_entry_session("2026-09-28T22:59:00Z"))
        self.assertEqual(
            _format_utc_timestamp(_bar_observation_time("2026-09-28T22:59:00Z")),
            "2026-09-28T23:00:00.000000Z",
        )

    def test_ema_warmup_rejects_candles_that_close_after_sample_open(self):
        sample = _price_bar(candle("2026-09-28T17:00:00Z"))
        exact_boundary = _price_bar(candle("2026-09-28T16:59:00Z", mid=2499))
        one_minute_future = _price_bar(candle("2026-09-28T17:00:00Z", mid=2499))
        two_minutes_future = _price_bar(candle("2026-09-28T17:01:00Z", mid=2499))
        _validate_nonoverlapping_warmup([sample], [exact_boundary])
        for invalid in (one_minute_future, two_minutes_future):
            with self.assertRaisesRegex(XAUHistoryError, "warm-up overlaps the sample"):
                _validate_nonoverlapping_warmup([sample], [invalid])

    def test_raw_evidence_contains_real_side_components_and_never_authorization(self):
        row = _price_bar(candle("2026-09-28T17:04:00Z"))
        data = _csv_bytes([row])
        self.assertIn(b"bid_open", data)
        self.assertIn(b"ask_close", data)
        self.assertIn(b"OANDA_PRACTICE_HISTORICAL", data)
        self.assertNotIn(b"Authorization", data)
        self.assertNotIn(b"account_id", data)

    def test_pagination_requires_actual_provider_bid_ask_and_skips_incomplete(self):
        class Response:
            status_code = 200

            def json(self):
                bars = [
                    candle("2026-09-28T17:04:00Z"),
                    candle("2026-09-28T17:05:00Z", mid=2501),
                ]
                bars[-1]["complete"] = False
                return {"instrument": INSTRUMENT, "granularity": "M1", "candles": bars}

        session = Mock()
        session.get.return_value = Response()
        rows = _fetch_historical_candles(
            "fixture-not-a-credential",
            start=datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 17, 6, tzinfo=timezone.utc),
            session=session,
            sleep=lambda _seconds: None,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["time"], "2026-09-28T17:04:00Z")
        self.assertEqual(session.get.call_args.kwargs["params"]["price"], "BA")
        self.assertEqual(session.get.call_args.kwargs["params"]["granularity"], "M1")
        self.assertNotIn("to", session.get.call_args.kwargs["params"])

    def test_provider_errors_do_not_escape_response_body_or_credentials(self):
        class Response:
            status_code = 401
            text = "fixture-sensitive-provider-response"

        session = Mock()
        session.get.return_value = Response()
        with self.assertRaises(XAUHistoryError) as raised:
            _fetch_historical_candles(
                "fixture-not-a-credential",
                start=datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 18, 0, tzinfo=timezone.utc),
                session=session,
                sleep=lambda _seconds: None,
            )
        self.assertNotIn("fixture-sensitive", str(raised.exception))
        self.assertNotIn("fixture-not-a-credential", str(raised.exception))


class XAUFillModelTests(unittest.TestCase):
    def row(self, time, mid, spread=0.2, minute_range=0.1):
        return _price_bar(candle(time, mid=mid, spread=spread, minute_range=minute_range))

    def test_long_entries_and_exits_use_real_trade_side_prices(self):
        buy = self.row("2026-09-28T17:04:00Z", mid=2500)
        self.assertAlmostEqual(buy["bid_open"], 2499.9)
        self.assertAlmostEqual(buy["ask_open"], 2500.1)
        position = {
            "signal": Signal.BUY.value, "entry_price": 2500.1,
            "quantity": 100, "stop": 2498.5, "target": 2505.1,
        }
        stop_bar = self.row("2026-09-28T17:05:00Z", mid=2498.8, minute_range=0.3)
        self.assertEqual(_exit_bar(position, stop_bar)["reason"], "stop_first_if_both_touched")
        self.assertAlmostEqual(_trade_pnl(position, 2498.5), -160)

    def test_short_side_uses_ask_for_stops_and_targets(self):
        position = {
            "signal": Signal.SELL.value, "entry_price": 2500.0,
            "quantity": 100, "stop": 2501.5, "target": 2495.0,
        }
        stop_bar = self.row("2026-09-28T17:05:00Z", mid=2501.3)
        self.assertEqual(_exit_bar(position, stop_bar)["reason"], "stop_first_if_both_touched")
        self.assertEqual(_trade_pnl(position, 2501.5), -150)

    def test_same_bar_conflict_is_resolved_conservatively_at_stop(self):
        position = {
            "signal": Signal.BUY.value, "entry_price": 2500.0,
            "quantity": 100, "stop": 2498.5, "target": 2505.0,
        }
        ambiguous = self.row("2026-09-28T17:05:00Z", mid=2501.75, minute_range=5)
        result = _exit_bar(position, ambiguous)
        self.assertEqual(result["reason"], "stop_first_if_both_touched")
        self.assertEqual(result["price"], 2498.5)

    def test_no_closed_sample_reports_success_ratio_or_fabricated_zero_returns(self):
        first_sample_open = datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc)
        bars = [
            self.row(
                (first_sample_open + timedelta(minutes=index))
                .isoformat().replace("+00:00", "Z"),
                2500,
            )
            for index in range(80)
        ]
        warmup = [
            self.row(
                (first_sample_open + timedelta(minutes=index - 40))
                .isoformat().replace("+00:00", "Z"),
                2500,
            )
            for index in range(40)
        ]
        report = evaluate_xauusd(bars, warmup_candles=warmup)
        self.assertEqual(report["status"], "insufficient_holdout_sample")
        self.assertIsNone(report["out_of_sample"]["win_rate_pct"])
        self.assertIsNone(report["out_of_sample"]["net_pnl_usd"])
        self.assertFalse(report["execution_validated"])
        self.assertEqual(report["training_fraction"], TRAIN_FRACTION)
        self.assertEqual(report["warmup_bars_before_sample"], 40)

    def test_replay_uses_the_real_agent_and_preserves_its_lifetime_three_signal_cap(self):
        first = datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc)
        warmup = [
            self.row(
                (first + timedelta(minutes=index - 40)).isoformat().replace("+00:00", "Z"),
                2500,
            )
            for index in range(40)
        ]
        trending = [
            self.row(
                (first + timedelta(minutes=index)).isoformat().replace("+00:00", "Z"),
                2500 if index < 20 else 2500 + (index - 20) * 1.5,
            )
            for index in range(140)
        ]
        result = evaluate_xauusd(trending, warmup_candles=warmup)
        # The price pattern is a synthetic software fixture, never empirical
        # OANDA evidence. It tests the genuine agent counter and fold boundaries.
        self.assertEqual(result["diagnostics"]["signals"], 3)
        self.assertEqual(result["agent_live_parameter_values"]["actual_agent_trade_count_at_sample_end"], 3)
        self.assertEqual(result["train"]["closed_trades"], 3)
        self.assertEqual(result["out_of_sample"]["closed_trades"], 0)
        self.assertIsNone(result["out_of_sample"]["win_rate_pct"])
        self.assertTrue(all(trade["fold"] == "train" for trade in result["trades"]))
        for trade in result["trades"]:
            signal_open = datetime.fromisoformat(
                trade["signal_candle_open_time"].replace("Z", "+00:00")
            )
            signal_close = signal_open + timedelta(minutes=1)
            self.assertEqual(
                trade["signal_time"],
                signal_close.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            )
            self.assertEqual(
                datetime.fromisoformat(trade["entry_time"].replace("Z", "+00:00")),
                signal_close,
            )
            self.assertEqual(trade["entry_bar_open_time"], trade["entry_time"])
            self.assertEqual(trade["exit_time"], trade["exit_bar_open_time"])
            self.assertIn("intrabar threshold-crossing time is unavailable", trade["exit_time_basis"])
        self.assertFalse(result["execution_validated"])

    def test_saved_report_refresh_rejects_modified_sha_without_network_or_mutation(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path

        from backtest.xauusd_evidence import refresh_saved_xauusd_backtest

        # Synthetic CSV fixture only: verifies integrity failure does not alter
        # either prior result or the mismatching provider-evidence bytes.
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory)
            source = evidence_dir / "synthetic-fixture.csv"
            source.write_bytes(b"synthetic fixture,not provider evidence\n")
            prior_report = {
                "provider": "OANDA",
                "environment": "practice",
                "instrument": INSTRUMENT,
                "granularity": "M1",
                "requested_price_components": ["bid", "ask"],
                "raw_data_file": source.name,
                "sha256": hashlib.sha256(b"different original file").hexdigest(),
            }
            report_path = evidence_dir / "xauusd_backtest.json"
            report_path.write_text(json.dumps(prior_report), encoding="utf-8")
            original_report = report_path.read_bytes()
            original_csv = source.read_bytes()
            with patch("backtest.xauusd_evidence._read_access_token", side_effect=AssertionError):
                with self.assertRaisesRegex(XAUHistoryError, "SHA-256 changed"):
                    refresh_saved_xauusd_backtest(evidence_dir=evidence_dir)
            self.assertEqual(report_path.read_bytes(), original_report)
            self.assertEqual(source.read_bytes(), original_csv)

    def test_closed_metrics_include_breakevens_in_denominator(self):
        results = _fold_metrics([
            {"pnl_usd": 10.0},
            {"pnl_usd": -4.0},
            {"pnl_usd": 0.0},
        ])
        self.assertEqual(results["closed_trades"], 3)
        self.assertEqual(results["wins"], 1)
        self.assertEqual(results["losses"], 1)
        self.assertEqual(results["breakeven"], 1)
        self.assertEqual(results["win_rate_pct"], 33.33)


if __name__ == "__main__":
    unittest.main()