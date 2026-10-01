"""Keep genuine live observations separate from trades and performance metrics."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from trading.live_paper import quote_has_timestamp, quote_is_fresh


class LiveObservationRecorder:
    """Append whitelisted provider snapshots for future chronological replay."""

    FIELDS = (
        "symbol", "close", "last_price", "bid", "ask", "volume",
        "timestamp", "received_at", "observed_at", "received_at_timestamp",
        "timestamp_kind", "security_id", "exchange_segment",
        "strike", "expiry", "option_type",
        "source", "currency", "instrument", "environment",
    )

    def __init__(self, path, *, source="DHAN"):
        if source not in {"DHAN", "OANDA"}:
            raise ValueError("Observation source must be DHAN or OANDA")
        self.source = source
        self.path = Path(path)
        self.status = "not_started"
        self.last_saved_at = None
        self.last_error = None
        self.saved_this_run = 0

    def record(self, quotes):
        rows = []
        sampled_at = datetime.now(timezone.utc).isoformat()
        for quote in quotes:
            if (
                not quote_is_fresh(quote)
                or not quote_has_timestamp(quote)
                or not quote.get("symbol")
                or quote.get("source") != self.source
                or (self.source == "OANDA" and quote.get("symbol") != "XAUUSD")
            ):
                continue
            snapshot = {
                field: quote[field]
                for field in self.FIELDS
                if field in quote and isinstance(quote[field], (str, int, float))
            }
            rows.append((
                sampled_at, quote["symbol"], quote["timestamp"],
                json.dumps(snapshot, allow_nan=False),
            ))
        if not rows:
            self.status = "waiting_for_fresh_data"
            return 0
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path, timeout=5) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS observations (
                        id INTEGER PRIMARY KEY,
                        sampled_at TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        exchange_trade_timestamp TEXT NOT NULL,
                        snapshot_json TEXT NOT NULL
                    )
                """)
                db.executemany(
                    "INSERT INTO observations "
                    "(sampled_at, symbol, exchange_trade_timestamp, snapshot_json) "
                    "VALUES (?, ?, ?, ?)", rows,
                )
            self.status = "recording"
            self.last_saved_at = sampled_at
            self.saved_this_run += len(rows)
            self.last_error = None
            return len(rows)
        except (OSError, sqlite3.Error):
            self.status = "storage_error"
            self.last_error = "Live observation storage failed; no trading result was recorded"
            return 0

    def get_status(self):
        return {
            "status": self.status,
            "observations_saved_this_run": self.saved_this_run,
            "last_saved_at": self.last_saved_at,
            "last_error": self.last_error,
            "data_source": self.source,
            "purpose": "genuine live snapshots for chronological forward/replay evaluation",
            "paper_trades_created": False,
            "price_basis": (
                "observed depth filtered by recent exchange trade time; not depth update time"
                if self.source == "DHAN"
                else "OANDA bid/ask and provider quote time; practice/live environment retained"
            ),
        }