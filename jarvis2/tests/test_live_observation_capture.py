"""Synthetic software fixtures, never backtest or trading evidence."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from backtest.live_capture import LiveObservationRecorder


def test_only_fresh_whitelisted_dhan_quotes_are_recorded(tmp_path):
    recorder = LiveObservationRecorder(tmp_path / "observations.sqlite")
    quote = {
        "symbol": "NIFTY", "close": 100, "bid": 99, "ask": 101,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "DHAN", "unexpected_secret_field": "never persist",
    }
    stale = {**quote, "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()}
    assert recorder.record([quote, stale, {**quote, "source": "OANDA"}]) == 1
    with sqlite3.connect(recorder.path) as db:
        row = db.execute("SELECT snapshot_json FROM observations").fetchone()
        assert "unexpected_secret_field" not in json.loads(row[0])
        assert db.execute("SELECT name FROM sqlite_master WHERE name='trades'").fetchone() is None
    assert recorder.get_status()["paper_trades_created"] is False


def test_missing_market_data_does_not_create_an_observation_database(tmp_path):
    recorder = LiveObservationRecorder(tmp_path / "observations.sqlite")
    assert recorder.record([{}, None]) == 0
    assert not recorder.path.exists()
    assert recorder.get_status()["status"] == "waiting_for_fresh_data"