import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backtest.xauusd_multiframe_forward_evidence import (
    XauusdMultiframeForwardEvidence,
)


ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "research/xauusd-multiframe-forward-freeze-2026-10-01.json"
UTC = timezone.utc


def evidence(tmp_path):
    return XauusdMultiframeForwardEvidence(
        tmp_path / "forward.sqlite", FREEZE, ROOT
    )


def fixture_decision():
    freeze = json.loads(FREEZE.read_text())
    start = datetime.fromisoformat(
        freeze["start_exclusive_utc"].replace("Z", "+00:00")
    )
    at = start + timedelta(minutes=3)
    text = lambda value: value.isoformat().replace("+00:00", "Z")
    frame_sizes = {"H4": timedelta(hours=4), "M15": timedelta(minutes=15), "M3": timedelta(minutes=3)}
    frames = {}
    for frame, size in frame_sizes.items():
        close_at = at if frame == "M3" else at - size
        frames[frame] = [{
            "bar_open_time": text(close_at - size),
            "observed_at": text(close_at),
            "open": 4000.0, "high": 4001.0, "low": 3999.0, "close": 4000.5,
            "bid_close": 4000.4, "ask_close": 4000.6,
            "complete": True, "provider": "OANDA",
            "environment": "practice", "bar_interval_minutes": int(size.total_seconds() / 60),
        }]
    quote_at = at + timedelta(seconds=1)
    decision_at = text(at)
    return (
        {
            "decision_id": f"xauusd-multiframe:{decision_at}",
            "decision_timestamp": decision_at,
            "candidate_signal": "HOLD",
            "actionable_signal": "HOLD",
            "blockers": ["no_complete_multiframe_setup"],
            "h4_direction": "UNKNOWN",
            "m15_direction": "UNKNOWN",
            "m3_direction": "UNKNOWN",
        },
        {
            "fetched_at": text(quote_at),
            "environment": "practice",
            "frames": frames,
        },
        {
            "source": "OANDA", "instrument": "XAU_USD",
            "environment": "practice", "tradeable": True,
            "provider_timestamp": text(quote_at),
            "bid": 4000.4, "ask": 4000.6,
        },
    )


def test_persists_hold_decisions_bars_and_provider_quote_immutably(tmp_path):
    recorder = evidence(tmp_path)
    assert recorder.status == "recording", recorder.error
    decision, snapshot, quote = fixture_decision()

    assert recorder.record_decision(decision, snapshot, quote)
    assert not recorder.record_decision(decision, snapshot, quote)

    report = recorder.report()
    assert report["decisions"] == 1
    assert report["actionable_decisions"] == 0
    assert report["blocker_counts"] == {"no_complete_multiframe_setup": 1}
    assert report["unique_candles_by_frame"] == {"H4": 1, "M15": 1, "M3": 1}
    assert report["evaluation"] == "INSUFFICIENT_SAMPLE"
    with sqlite3.connect(recorder.path) as db:
        stored = db.execute(
            "SELECT provider_quote_json FROM decisions"
        ).fetchone()[0]
        assert json.loads(stored)["bid"] == 4000.4
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM decisions")


def test_rejects_wrong_provider_environment_and_never_backfills(tmp_path):
    recorder = evidence(tmp_path)
    decision, snapshot, quote = fixture_decision()
    bad_quote = {**quote, "environment": "live"}
    with pytest.raises(ValueError, match="tradeable OANDA practice quote"):
        recorder.record_decision(decision, snapshot, bad_quote)
    assert recorder.report()["decisions"] == 0

    too_old = datetime.fromisoformat(
        json.loads(FREEZE.read_text())["start_exclusive_utc"].replace("Z", "+00:00")
    )
    decision["decision_timestamp"] = (too_old - timedelta(minutes=3)).isoformat()
    assert recorder.record_decision(decision, snapshot, quote) is False
    assert recorder.report()["decisions"] == 0