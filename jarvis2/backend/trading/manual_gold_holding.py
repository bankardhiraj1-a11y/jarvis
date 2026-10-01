"""Holding-time decisions for manual XAUUSD positions."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from trading.holding_policy import next_gold_rollover_deadline


_UTC = timezone.utc
_GOLD_SESSION_CUTOFF = time(23, 0)
_ROLLOVER_BUFFER = timedelta(minutes=1)
_POLICY = "manual_gold_sl_tp_rollover"


def _as_utc(value: Any) -> Optional[datetime]:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_UTC)
    try:
        return value.astimezone(_UTC)
    except (OverflowError, ValueError):
        return None


def _result(
    due: bool,
    status: str,
    reason: str,
    deadline: Optional[datetime],
) -> dict[str, Any]:
    return {
        "due": due,
        "status": status,
        "reason": reason,
        "deadline": deadline.isoformat() if deadline is not None else None,
        "policy": _POLICY,
    }


def manual_gold_holding_decision(entry_time: Any, now: Any) -> dict[str, Any]:
    """Enforce only the UTC-session and next-NY-rollover safety exits.

    The entry timestamp must be the actual provider-event time. Manual Gold
    positions have no elapsed-time holding cap; open positions remain managed
    by their stop/target strategy until the earlier mandatory safety cutoff.
    """
    opened = _as_utc(entry_time)
    now_utc = _as_utc(now)
    if now_utc is None:
        return _result(
            True,
            "POLICY_TIME_INVALID",
            "Current time is missing or invalid; manual XAUUSD holding safety cannot be established.",
            None,
        )
    if opened is None:
        return _result(
            True,
            "HOLDING_TIMESTAMP_MISSING",
            "Manual XAUUSD position has no trustworthy provider entry timestamp; close using a fresh provider quote.",
            None,
        )

    session_cutoff = datetime.combine(
        opened.date(), _GOLD_SESSION_CUTOFF, tzinfo=_UTC
    )
    rollover_cutoff = (
        next_gold_rollover_deadline(opened) - _ROLLOVER_BUFFER
    )
    deadline = min(session_cutoff, rollover_cutoff)
    limiting_factor = (
        "UTC_SESSION" if session_cutoff <= rollover_cutoff else "NY_ROLLOVER"
    )
    if now_utc >= deadline:
        status = (
            f"{limiting_factor}_EXIT_DUE"
            if now_utc == deadline
            else f"{limiting_factor}_EXIT_OVERDUE"
        )
        reason = (
            "Manual XAUUSD reached the 23:00 UTC session cutoff; exit only using a fresh provider quote."
            if limiting_factor == "UTC_SESSION"
            else (
                "Manual XAUUSD reached the one-minute wind-down before the next "
                "17:00 America/New_York rollover; exit only using a fresh provider quote."
            )
        )
        return _result(True, status, reason, deadline)

    reason = (
        "Manual XAUUSD remains managed by its stop/target strategy without an "
        "elapsed-time exit; close by the earlier 23:00 UTC or New York rollover "
        "safety cutoff."
    )
    return _result(False, "HOLDING_POLICY_OK", reason, deadline)