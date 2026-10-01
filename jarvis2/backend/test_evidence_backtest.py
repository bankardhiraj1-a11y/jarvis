import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))

from backtest.evidence_backtest import (  # noqa: E402
    _complete_rows,
    _modeled_equity_charges,
    _metrics,
    options_ohlc_signals,
    run_evidence_backtests,
    sensex_scalping_ohlc_signals,
    stock_bar_trades,
)
from data.dhan_history import DhanHistoryError  # noqa: E402
from agents.options import OptionsAgent  # noqa: E402
from agents.sensex_options_scalping import SensexOptionsScalpingAgent  # noqa: E402


def _candle(day, open_, high, low, close, volume=100):
    return {
        "timestamp": datetime(day.year, day.month, day.day, 10, tzinfo=timezone.utc).isoformat(),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def test_metrics_count_only_gains_and_losses_and_preserve_ties_in_denominator():
    metrics = _metrics([{"pnl": 20}, {"pnl": -10}, {"pnl": 0}])
    assert metrics["total_trades"] == 3
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate"] == 33.33
    assert metrics["total_pnl"] == 10


def test_empty_metric_sample_has_no_misleading_win_rate():
    assert _metrics([])["win_rate"] is None


def test_drawdown_uses_chronological_exit_order():
    metrics = _metrics(
        [
            {"exit_date": "2026-01-02", "symbol": "TCS", "pnl": 5000},
            {"exit_date": "2026-01-01", "symbol": "INFY", "pnl": -10000},
        ]
    )
    assert metrics["max_drawdown_pct"] == 10.0


def test_stock_model_warms_up_and_uses_daily_bars_in_order():
    start = date(2025, 1, 1)
    bars = []
    # Establish an authentic-shaped trend history and then a genuine-form
    # breakout candidate. These values exercise software only, never evidence.
    for index in range(280):
        price = 100 + index * 5
        bars.append(_candle(start + timedelta(days=index), price, price + 2, price - 2, price + 1))
    for index in range(80):
        price = 1495 - index * 5
        bars.append(_candle(start + timedelta(days=180 + index), price, price + 2, price - 5, price - 3))
    signal_day = start + timedelta(days=360)
    bars.append(_candle(signal_day, 1210, 1220, 1205, 1215, volume=1000))
    bars.append(_candle(signal_day + timedelta(days=1), 1220, 1300, 1100, 1175))
    result = stock_bar_trades(bars)
    assert result["signal_count"] >= 1
    assert result["trades"]
    assert result["trades"][0]["quantity"] == 50
    assert result["trades"][0]["exit_reason"] == "stop_first_if_both_levels_touch"
    assert result["trades"][0]["modeled_costs"] > 0


def test_equity_charges_scale_variable_costs_not_flat_brokerage():
    one_share = _modeled_equity_charges(100, 105, 1)
    fifty_shares = _modeled_equity_charges(100, 105, 50)
    assert fifty_shares > one_share
    assert fifty_shares < one_share * 50


def test_same_symbol_signals_cannot_overlap(monkeypatch):
    import backtest.evidence_backtest as backtest

    bars = [
        _candle(date(2026, 1, 1) + timedelta(days=index), 100, 105, 95, 100)
        for index in range(6)
    ]
    monkeypatch.setattr(
        backtest,
        "stock_signals",
        lambda _: [
            {"signal_index": 0, "signal_date": "2026-01-01", "stop": 90, "target": 110},
            {"signal_index": 1, "signal_date": "2026-01-02", "stop": 90, "target": 110},
        ],
    )
    bars[2]["high"] = 111
    replay = stock_bar_trades(bars)
    assert len(replay["trades"]) == 1
    assert replay["skipped_overlapping_signals"][0]["signal_date"] == "2026-01-02"


def test_training_exit_does_not_inspect_holdout_bar(monkeypatch):
    import backtest.evidence_backtest as backtest

    bars = [
        _candle(date(2026, 1, 1) + timedelta(days=index), 100, 105, 95, 100)
        for index in range(5)
    ]
    bars[4]["high"] = 120  # Would hit target, but belongs to holdout.
    monkeypatch.setattr(
        backtest,
        "stock_signals",
        lambda _: [
            {"signal_index": 2, "signal_date": "2026-01-03", "stop": 90, "target": 110}
        ],
    )
    replay = stock_bar_trades(bars)
    assert replay["trades"] == []
    assert replay["open_positions_at_sample_end"][0]["status"] == "OPEN_AT_TRAIN_HOLDOUT_BOUNDARY"
    assert replay["open_positions_at_sample_end"][0]["sample_end_date"] == bars[3]["timestamp"][:10]


def _intraday_candle(timestamp, open_, high, low, close, volume=10):
    return {
        "timestamp": timestamp.isoformat(),
        "timestamp_epoch": int(timestamp.timestamp()),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def test_scalper_adapter_finds_directional_setup_from_real_ohlc():
    start = datetime(2026, 9, 1, 9, 15, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    candles = [
        _intraday_candle(start, 100, 105, 99, 103),
        _intraday_candle(start + timedelta(minutes=1), 103, 108, 102, 107),
    ]
    replay = sensex_scalping_ohlc_signals(
        SensexOptionsScalpingAgent(), {"SENSEX": candles}
    )
    assert replay["raw_setup_count"] == 1
    assert replay["signal_count"] == 1
    assert replay["signals"][0]["signal"] == "BUY"
    assert replay["signals"][0]["timestamp"] == (start + timedelta(minutes=2)).isoformat()


def test_options_adapter_uses_wick_range_from_completed_ohlc_and_no_future_bar():
    ist = timezone(timedelta(hours=5, minutes=30))
    fifteen = []
    for day_offset in range(3):
        day = date(2026, 9, 1) + timedelta(days=day_offset)
        for quarter in range(7):
            timestamp = datetime(day.year, day.month, day.day, 9, 15, tzinfo=ist) + timedelta(minutes=15 * quarter)
            fifteen.append(_intraday_candle(timestamp, 10000, 10050, 9950, 10000, volume=100))
    last_complete = fifteen[-1]["timestamp_epoch"] + 15 * 60
    next_partial = _intraday_candle(
        datetime.fromtimestamp(last_complete, timezone.utc).astimezone(ist),
        10000,
        10100,
        9900,
        10000,
        volume=100000,
    )
    available_minute = _intraday_candle(
        datetime.fromtimestamp(last_complete, timezone.utc).astimezone(ist),
        9951,
        9954,
        9948,
        9951,
        volume=25,
    )
    signal_only = options_ohlc_signals(
        OptionsAgent(),
        {"NIFTY": [available_minute]},
        {"NIFTY": fifteen + [next_partial]},
    )
    diagnostics = signal_only["per_symbol"]["NIFTY"]
    assert diagnostics["completed_15m_bars"] == 21
    assert diagnostics["candidate_signal_count"] == 1
    assert diagnostics["signals"][0]["tier"] == "TIER2"
    assert diagnostics["signals"][0]["signal"] == "BUY"
    assert diagnostics["signals"][0]["timestamp"] == _bar_end_for_test(available_minute).isoformat()


def test_current_session_bars_are_excluded():
    today = date(2026, 10, 1)
    yesterday = today - timedelta(days=1)
    rows = [
        _candle(yesterday, 100, 105, 99, 104),
        _candle(today, 104, 110, 103, 109),
    ]
    assert [row["timestamp"][:10] for row in _complete_rows(rows, today)] == [
        yesterday.isoformat()
    ]


def test_report_contract_fails_closed_without_real_provider_history():
    class UnavailableProvider:
        def fetch_daily(self, *args, **kwargs):
            raise DhanHistoryError("fixture is unavailable")

        def fetch_intraday(self, *args, **kwargs):
            raise DhanHistoryError("fixture is unavailable")

    with TemporaryDirectory() as directory:
        report = run_evidence_backtests(
            client=UnavailableProvider(),
            evidence_dir=directory,
            today=date(2026, 10, 1),
            request_sleep=lambda _: None,
        )
        assert set(report["agents"]) == {
            "STOCKS",
            "OPTIONS",
            "SENSEX_OPTIONS_SCALPING",
            "SENSEX",
            "GIFT_NIFTY",
        }
        assert report["agents"]["STOCKS"]["status"] == "unavailable"
        assert report["agents"]["GIFT_NIFTY"]["status"] == "unavailable"
        assert report["agents"]["STOCKS"]["execution_validated"] is False
        assert report["agents"]["STOCKS"]["strategy_changed"] is False
        assert report["retrieval"]["raw_data_files"] == []
        assert report["retrieval"]["requests_attempted"] == 11


def _bar_end_for_test(row):
    return datetime.fromisoformat(row["timestamp"]) + timedelta(minutes=1)
