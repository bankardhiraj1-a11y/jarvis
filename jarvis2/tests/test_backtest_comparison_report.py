"""Synthetic report-contract fixtures only; never trading evidence."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from backtest.comparison_report import build_comparison, load_agent_evaluation, render_html


def make_reports(directory):
    agents = {
        name: {"status": "signal_only", "total_trades": 0, "win_rate": None, "total_pnl": None}
        for name in ("STOCKS", "OPTIONS", "SENSEX", "SENSEX_OPTIONS_SCALPING", "GIFT_NIFTY")
    }
    (directory / "latest_backtests.json").write_text(json.dumps({
        "data_source": "DHAN_HISTORICAL", "agents": agents, "retrieval": {},
    }))
    (directory / "xauusd_backtest.json").write_text(json.dumps({
        "data_source": "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC",
        "environment": "practice", "status": "insufficient_holdout_sample",
        "overall": {"closed_trades": 3, "wins": 1, "losses": 2, "win_rate_pct": 33.33, "net_pnl_usd": 200},
        "out_of_sample": {"closed_trades": 0, "win_rate_pct": None, "net_pnl_usd": None},
    }))


def test_gold_metrics_are_normalized_without_becoming_live_performance(tmp_path):
    make_reports(tmp_path)
    result = load_agent_evaluation(tmp_path, "XAUUSD")
    assert result["total_trades"] == 3
    assert result["win_rate"] == 33.33
    assert result["currency"] == "USD"
    assert result["environment"] == "practice"
    assert result["counted_toward_live_target"] is False


def test_all_agents_keep_null_metrics_and_strategy_findings(tmp_path):
    make_reports(tmp_path)
    result = build_comparison(tmp_path)
    assert len(result["agents"]) == 6
    assert result["agents"]["OPTIONS"]["win_rate"] is None
    assert result["paper_entries_enabled"] is False
    assert result["execution_validated"] is False
    page = render_html(result)
    assert "Not established" in page
    assert "counter is never reset" in page
    assert "<script" not in page
    assert "not trades" in page or "not live returns" in page