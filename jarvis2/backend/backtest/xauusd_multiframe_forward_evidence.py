"""Append-only, post-freeze evidence for the OANDA H4/M15/M3 paper hypothesis."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

_UTC = timezone.utc
_FRAMES = ("H4", "M15", "M3")
_QUOTE_FIELDS = ("source", "instrument", "environment", "bid", "ask", "tradeable")
_MIN_FILLS = 30
_MIN_DAYS = 10


def _stamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError("timestamp missing")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamps must have explicit UTC offsets")
    return parsed.astimezone(_UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(_UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class XauusdMultiframeForwardEvidence:
    """Freeze-bound, idempotent provider snapshots; no backfills or tuning."""

    def __init__(self, path: Path, freeze_path: Path, workspace_root: Path):
        self.path = Path(path)
        self.freeze_path = Path(freeze_path)
        self.workspace_root = Path(workspace_root)
        self.status = "not_initialized"
        self.error: str | None = None
        self.boundaries: dict[str, Any] = {}
        self.scope_hash = ""
        self._initialize()

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self) -> None:
        try:
            raw = self.freeze_path.read_bytes()
            self.boundaries = json.loads(raw)
            source_hashes = self.boundaries["frozen_sha256"]
            actual = {
                relative: hashlib.sha256(
                    (self.workspace_root / relative).read_bytes()
                ).hexdigest()
                for relative in source_hashes
            }
            if actual != source_hashes:
                raise ValueError("frozen strategy source hash changed")
            self.scope_hash = hashlib.sha256(raw).hexdigest()
            _stamp(self.boundaries["start_exclusive_utc"])
            _stamp(self.boundaries["decision_window_end_exclusive_utc"])
            with self._connect() as db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS freeze (
                        scope_hash TEXT PRIMARY KEY,
                        manifest_json TEXT NOT NULL,
                        initialized_at_utc TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS candles (
                        candle_key TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        frame TEXT NOT NULL,
                        bar_open_time TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        evaluation_role TEXT NOT NULL,
                        candle_json TEXT NOT NULL,
                        candle_sha256 TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS decisions (
                        decision_id TEXT PRIMARY KEY,
                        decision_at_utc TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        candidate_signal TEXT NOT NULL,
                        actionable_signal TEXT NOT NULL,
                        blockers_json TEXT NOT NULL,
                        directions_json TEXT NOT NULL,
                        snapshot_fetched_at_utc TEXT NOT NULL,
                        frame_counts_json TEXT NOT NULL,
                        input_candles_sha256 TEXT NOT NULL,
                        provider_quote_json TEXT NOT NULL,
                        decision_sha256 TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS decision_candles (
                        decision_id TEXT NOT NULL,
                        frame TEXT NOT NULL,
                        candle_key TEXT NOT NULL,
                        PRIMARY KEY(decision_id, frame, candle_key),
                        FOREIGN KEY(decision_id) REFERENCES decisions(decision_id),
                        FOREIGN KEY(candle_key) REFERENCES candles(candle_key)
                    );
                    CREATE TABLE IF NOT EXISTS decision_conflicts (
                        conflict_sha256 TEXT PRIMARY KEY,
                        decision_id TEXT NOT NULL,
                        recorded_at_utc TEXT NOT NULL,
                        observed_sha256 TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS fills (
                        trade_id INTEGER NOT NULL,
                        event_type TEXT NOT NULL,
                        event_at_utc TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        decision_id TEXT,
                        event_json TEXT NOT NULL,
                        event_sha256 TEXT NOT NULL,
                        PRIMARY KEY(trade_id, event_type)
                    );
                """)
                db.execute(
                    "CREATE TRIGGER IF NOT EXISTS freeze_no_update BEFORE UPDATE ON freeze "
                    "BEGIN SELECT RAISE(ABORT,'frozen evidence is immutable'); END"
                )
                for table in ("freeze", "candles", "decisions", "decision_candles", "decision_conflicts", "fills"):
                    db.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
                        "BEGIN SELECT RAISE(ABORT,'forward evidence is append-only'); END"
                    )
                    db.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
                        "BEGIN SELECT RAISE(ABORT,'forward evidence is append-only'); END"
                    )
                db.execute(
                    "INSERT OR IGNORE INTO freeze VALUES(?,?,?)",
                    (self.scope_hash, raw.decode(), datetime.now(_UTC).isoformat()),
                )
                stored = db.execute(
                    "SELECT scope_hash,manifest_json FROM freeze"
                ).fetchall()
                if stored != [(self.scope_hash, raw.decode())]:
                    raise ValueError("evidence store already belongs to a different frozen scope")
            self.status = "recording"
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            self.status = "boundary_or_storage_error"
            self.error = str(exc)

    def record_decision(
        self, decision: dict[str, Any], snapshot: dict[str, Any] | None, quote: dict[str, Any] | None
    ) -> bool:
        if self.status != "recording":
            raise ValueError("forward evidence recorder is not healthy")
        try:
            decision_at = _stamp(decision["decision_timestamp"])
            start = _stamp(self.boundaries["start_exclusive_utc"])
            end = _stamp(self.boundaries["decision_window_end_exclusive_utc"])
            if not (start < decision_at < end):
                return False
            if not isinstance(snapshot, dict) or snapshot.get("environment") != "practice":
                raise ValueError("eligible decision requires an OANDA practice candle snapshot")
            if not isinstance(quote, dict):
                raise ValueError("eligible decision requires its OANDA quote")
            quote_row = {field: quote.get(field) for field in _QUOTE_FIELDS}
            quote_row["timestamp"] = (
                quote.get("provider_timestamp") or quote.get("timestamp")
            )
            if (
                quote_row["source"] != "OANDA"
                or quote_row["instrument"] != "XAU_USD"
                or quote_row["environment"] != "practice"
                or quote_row["tradeable"] is not True
            ):
                raise ValueError("eligible decision requires a tradeable OANDA practice quote")
            quote_at = _stamp(quote_row["timestamp"])
            if abs((quote_at - decision_at).total_seconds()) > 210:
                raise ValueError("decision quote falls outside frozen freshness rules")
            if float(quote_row["bid"]) <= 0 or float(quote_row["ask"]) < float(quote_row["bid"]):
                raise ValueError("OANDA quote bid/ask is invalid")
            frames = snapshot.get("frames")
            if not isinstance(frames, dict) or set(frames) != set(_FRAMES):
                raise ValueError("decision does not contain all three timeframe snapshots")
            counts: dict[str, int] = {}
            refs: list[tuple[str, str]] = []
            candle_hashes = []
            with self._connect() as db:
                for frame in _FRAMES:
                    bars = frames[frame]
                    if not isinstance(bars, list) or not bars:
                        raise ValueError(f"{frame} evidence is missing")
                    counts[frame] = len(bars)
                    for original in bars:
                        bar = _json_safe(original)
                        opened = _stamp(bar["bar_open_time"])
                        observed = _stamp(bar["observed_at"])
                        if (
                            bar.get("provider") != "OANDA"
                            or bar.get("environment") != "practice"
                            or bar.get("complete") is not True
                            or observed > decision_at
                        ):
                            continue
                        key = f"OANDA:practice:{frame}:{_iso(opened)}"
                        bar_text = _canonical(bar).decode()
                        bar_hash = hashlib.sha256(bar_text.encode()).hexdigest()
                        role = "forward_evaluation" if observed > start else "pre_freeze_causal_warmup"
                        db.execute(
                            "INSERT OR IGNORE INTO candles VALUES(?,?,?,?,?,?,?,?,?)",
                            (key, "OANDA", "practice", frame, _iso(opened), _iso(observed),
                             role, bar_text, bar_hash),
                        )
                        existing = db.execute(
                            "SELECT candle_sha256 FROM candles WHERE candle_key=?", (key,)
                        ).fetchone()
                        if existing is None or existing[0] != bar_hash:
                            raise ValueError("provider candle changed for an immutable candle key")
                        refs.append((frame, key))
                        candle_hashes.append((frame, key, bar_hash))

                if not all(frame in {ref[0] for ref in refs} for frame in _FRAMES):
                    raise ValueError("decision has no complete, observable bars for every timeframe")
                latest_m3 = max(
                    _stamp(bar["observed_at"])
                    for bar in frames["M3"]
                    if _stamp(bar["observed_at"]) <= decision_at
                )
                if latest_m3 != decision_at:
                    raise ValueError("decision timestamp does not match its completed M3 bar")
                q_text = _canonical(_json_safe(quote_row)).decode()
                decision_row = {
                    "decision": _json_safe(decision),
                    "provider_quote": json.loads(q_text),
                    "snapshot_fetched_at": _json_safe(snapshot.get("fetched_at")),
                    "environment": "practice",
                    "frame_counts": counts,
                    "input_candles_sha256": _digest(sorted(candle_hashes)),
                }
                body = _canonical(decision_row).decode()
                row_hash = hashlib.sha256(body.encode()).hexdigest()
                cur = db.execute(
                    """INSERT OR IGNORE INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (str(decision["decision_id"]), _iso(decision_at), "OANDA", "XAU_USD",
                     "practice", str(decision.get("candidate_signal", "HOLD")),
                     str(decision.get("actionable_signal", "HOLD")),
                     _canonical(decision.get("blockers", [])).decode(),
                     _canonical({
                         key: decision.get(key)
                         for key in ("h4_direction", "m15_direction", "m3_direction")
                     }).decode(),
                     _iso(_stamp(snapshot["fetched_at"])), _canonical(counts).decode(),
                     decision_row["input_candles_sha256"], q_text, row_hash),
                )
                existing = db.execute(
                    "SELECT decision_sha256 FROM decisions WHERE decision_id=?",
                    (str(decision["decision_id"]),),
                ).fetchone()
                if existing is None or existing[0] != row_hash:
                    conflict = _digest([decision["decision_id"], row_hash])
                    db.execute(
                        "INSERT OR IGNORE INTO decision_conflicts VALUES(?,?,?,?)",
                        (conflict, str(decision["decision_id"]), datetime.now(_UTC).isoformat(), row_hash),
                    )
                    raise ValueError("decision ID was reused with different evidence; review required")
                if cur.rowcount:
                    db.executemany(
                        "INSERT INTO decision_candles VALUES(?,?,?)",
                        [(str(decision["decision_id"]), frame, key) for frame, key in refs],
                    )
            return bool(cur.rowcount)
        except (KeyError, TypeError, ValueError, OverflowError, sqlite3.Error) as exc:
            self.error = str(exc)
            raise

    def record_trade_event(self, trade: Any, event_type: str, decision_id: str | None) -> bool:
        if (
            self.status != "recording"
            or event_type not in {"accepted_entry", "closed_exit"}
            or not decision_id
        ):
            return False
        event_value = (
            getattr(trade, "entry_data_timestamp", None)
            if event_type == "accepted_entry"
            else getattr(trade, "exit_data_timestamp", None)
        )
        if not event_value:
            return False
        event_at = _stamp(event_value)
        if not (
            _stamp(self.boundaries["start_exclusive_utc"])
            < event_at
            < _stamp(self.boundaries["decision_window_end_exclusive_utc"])
        ):
            return False
        side = str(getattr(getattr(trade, "trade_type", None), "value", ""))
        raw = {
            "trade_id": int(trade.id),
            "strategy": self.boundaries["scope_id"],
            "paper_only": True,
            "actual_broker_execution": False,
            "status": (
                "ACCEPTED_PAPER_FILL"
                if event_type == "accepted_entry"
                else "CLOSED_PAPER_FILL"
            ),
            "side": side,
            "quantity_units": float(trade.quantity),
            "entry_price": float(trade.entry_price),
            "entry_data_timestamp": getattr(trade, "entry_data_timestamp", None),
            "data_source": getattr(trade, "data_source", None),
            "stop_loss": getattr(trade, "stop_loss", None),
            "take_profit": getattr(trade, "take_profit", None),
        }
        if event_type == "closed_exit":
            raw.update({
                "exit_price": getattr(trade, "exit_price", None),
                "exit_data_timestamp": event_value,
                "gross_executable_side_pnl_before_costs": (
                    (float(trade.entry_price) - float(trade.exit_price)) * float(trade.quantity)
                    if side == "SELL"
                    else (float(trade.exit_price) - float(trade.entry_price)) * float(trade.quantity)
                ) if trade.exit_price is not None and side in {"BUY", "SELL"} else None,
                "fees_funding_and_gap_costs": None,
            })
        text = _canonical(_json_safe(raw)).decode()
        with self._connect() as db:
            cur = db.execute(
                "INSERT OR IGNORE INTO fills VALUES(?,?,?,?,?,?,?,?)",
                (int(trade.id), event_type, _iso(event_at), "OANDA", "practice",
                 decision_id, text, hashlib.sha256(text.encode()).hexdigest()),
            )
            existing = db.execute(
                "SELECT event_sha256 FROM fills WHERE trade_id=? AND event_type=?",
                (int(trade.id), event_type),
            ).fetchone()
            if existing is None or existing[0] != hashlib.sha256(text.encode()).hexdigest():
                raise ValueError("automatic paper-fill evidence changed; review required")
            return bool(cur.rowcount)

    def decision_for_entry(self, entry_timestamp: Any, side: str) -> str | None:
        if self.status != "recording" or side not in {"BUY", "SELL"}:
            return None
        try:
            entry_at = _stamp(entry_timestamp)
            with sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=5) as db:
                candidates = db.execute(
                    """SELECT decision_id,decision_at_utc FROM decisions
                       WHERE actionable_signal=? ORDER BY decision_at_utc DESC LIMIT 100""",
                    (side,),
                ).fetchall()
            for decision_id, raw_at in candidates:
                age = (entry_at - _stamp(raw_at)).total_seconds()
                if 0 <= age <= 210:
                    return decision_id
        except (OSError, ValueError, sqlite3.Error):
            return None
        return None

    def report(self) -> dict[str, Any]:
        report = {
            "scope_id": self.boundaries.get("scope_id"),
            "scope_sha256": self.scope_hash or None,
            "collection_status": self.status,
            "error": self.error,
            "window_start_exclusive_utc": self.boundaries.get("start_exclusive_utc"),
            "window_end_exclusive_utc": self.boundaries.get("decision_window_end_exclusive_utc"),
            "provider": "OANDA",
            "instrument": "XAU_USD",
            "environment": "practice",
            "final_holdout_accessed": False,
            "retuning_on_window_prohibited": True,
            "actual_broker_orders": 0,
            "planned_risk_usd": 150,
            "costs_usd": None,
            "net_pnl_usd": None,
            "note": "Price-only gross P&L uses recorded executable-side prices. Unknown fees, funding and gap costs are not estimated.",
            "decisions": 0,
            "blocker_counts": {},
            "actionable_decisions": 0,
            "unique_candles_by_frame": {},
            "accepted_automatic_entries": 0,
            "unmatched_automatic_fills": 0,
            "closed_automatic_fills": 0,
            "gross_price_pnl_usd": None,
            "distinct_entry_dates_utc": 0,
            "evidence_threshold": {"closed_fills": _MIN_FILLS, "entry_dates_utc": _MIN_DAYS},
            "evaluation": "INSUFFICIENT_SAMPLE",
        }
        if self.status != "recording" or not self.path.exists():
            return report
        try:
            with sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=5) as db:
                report["decisions"] = db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
                report["actionable_decisions"] = db.execute(
                    "SELECT COUNT(*) FROM decisions WHERE actionable_signal IN ('BUY','SELL')"
                ).fetchone()[0]
                blocker_rows = db.execute("SELECT blockers_json FROM decisions").fetchall()
                blockers = Counter(
                    reason for (raw,) in blocker_rows for reason in json.loads(raw)
                )
                report["blocker_counts"] = dict(blockers.most_common())
                report["unique_candles_by_frame"] = dict(db.execute(
                    "SELECT frame,COUNT(*) FROM candles GROUP BY frame"
                ).fetchall())
                entries = db.execute(
                    """SELECT event_json FROM fills WHERE event_type='accepted_entry'
                       ORDER BY event_at_utc,trade_id"""
                ).fetchall()
                exits = db.execute(
                    """SELECT event_json FROM fills WHERE event_type='closed_exit'
                       ORDER BY event_at_utc,trade_id"""
                ).fetchall()
                report["accepted_automatic_entries"] = len(entries)
                report["unmatched_automatic_fills"] = sum(
                    1 for (raw,) in entries if not json.loads(raw).get("decision_id")
                )
                exit_data = [json.loads(raw) for (raw,) in exits]
                pnl = [
                    item["gross_executable_side_pnl_before_costs"]
                    for item in exit_data
                    if item.get("gross_executable_side_pnl_before_costs") is not None
                ]
                entry_dates = {
                    _stamp(json.loads(raw)["entry_data_timestamp"]).date().isoformat()
                    for (raw,) in entries
                }
                report["closed_automatic_fills"] = len(exit_data)
                report["distinct_entry_dates_utc"] = len(entry_dates)
                if len(pnl) == len(exit_data) and pnl:
                    report["gross_price_pnl_usd"] = round(sum(pnl), 2)
                if (
                    len(exit_data) >= _MIN_FILLS
                    and len(entry_dates) >= _MIN_DAYS
                    and len(pnl) == len(exit_data)
                ):
                    report["evaluation"] = "DESCRIPTIVE_SAMPLE_THRESHOLD_MET_NOT_VALIDATED"
                if datetime.now(_UTC) >= _stamp(self.boundaries["decision_window_end_exclusive_utc"]):
                    report["collection_status"] = "WINDOW_CLOSED"
            return report
        except (OSError, ValueError, sqlite3.Error) as exc:
            report["collection_status"] = "evidence_read_error"
            report["error"] = str(exc)
            return report