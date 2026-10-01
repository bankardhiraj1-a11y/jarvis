"""Pure holding-time and entry-eligibility policy helpers.

These decisions never execute or price an exit. Callers must obtain a fresh,
real provider quote before recording any fill; a due decision remains pending
when that quote is unavailable.
"""

from datetime import datetime, time, timedelta, timezone
import math
from typing import Any, Optional
from zoneinfo import ZoneInfo


_UTC = timezone.utc
_IST = ZoneInfo("Asia/Kolkata")
_NEW_YORK = ZoneInfo("America/New_York")
_INTRADAY_AGENTS = {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}
_GOLD_AGENT = "XAUUSD"
_STOCK_AGENT = "STOCKS"
_INTRADAY_CUTOFF = time(15, 20)
_GOLD_SESSION_CLOSE_UTC = time(23, 0)
_GOLD_NEW_YORK_ROLLOVER = time(17, 0)
_GOLD_ROLLOVER_WINDDOWN = timedelta(minutes=1)
_GOLD_DEFAULT_MAX_HOLD_MINUTES = 20


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _agent_name(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value)).strip().upper()


def _as_utc(value: Any) -> Optional[datetime]:
    """Normalize datetimes; database-naive timestamps are explicitly UTC."""
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


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def _decision(
    due: bool,
    reason: str,
    status: str,
    deadline: Optional[datetime],
    policy: str,
) -> dict:
    return {
        "due": bool(due),
        "reason": reason,
        "status": status,
        "deadline": _iso(deadline),
        "policy": policy,
    }


def _is_true(value: Any) -> bool:
    if value is True:
        return True
    return isinstance(value, str) and value.strip().lower() in {
        "true",
        "yes",
        "verified",
        "understood",
        "accounted_for",
    }


def _has_explicit_overnight_authorization(intent: Any) -> bool:
    if not _is_true(_field(intent, "allow_overnight")):
        return False

    reason = _field(intent, "reason")
    if not isinstance(reason, str) or not reason.strip():
        return False

    cost_awareness = any(
        _is_true(_field(intent, name))
        for name in (
            "cost_aware",
            "cost_awareness",
            "overnight_cost_aware",
            "cost_awareness_confirmed",
        )
    )
    financing_verified = any(
        _is_true(_field(intent, name))
        for name in (
            "financing_verified",
            "account_financing_verified",
            "financing_cost_verified",
        )
    )
    return cost_awareness and financing_verified


def _positive_max_hold_minutes(intent: Any) -> Optional[float]:
    value = _field(intent, "max_hold_minutes")
    if isinstance(value, bool):
        return None
    try:
        minutes = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(minutes) or minutes <= 0:
        return None
    return minutes


def next_gold_rollover_deadline(now: datetime) -> datetime:
    """Return the next 17:00 America/New_York rollover as an aware UTC time.

    Naive datetimes follow the policy module's database convention and are
    treated as UTC. At exactly 17:00 New York time, this returns tomorrow's
    rollover. Invalid input raises ``ValueError`` rather than guessing.
    """
    now_utc = _as_utc(now)
    if now_utc is None:
        raise ValueError("now must be a valid datetime")

    now_ny = now_utc.astimezone(_NEW_YORK)
    rollover_date = now_ny.date()
    if now_ny.timetz().replace(tzinfo=None) >= _GOLD_NEW_YORK_ROLLOVER:
        rollover_date += timedelta(days=1)
    local_rollover = datetime.combine(
        rollover_date, _GOLD_NEW_YORK_ROLLOVER, tzinfo=_NEW_YORK
    )
    return local_rollover.astimezone(_UTC)


def _gold_default_deadline(
    created_utc: datetime, max_hold_minutes: float
) -> tuple[datetime, str]:
    """Bound a non-carry XAUUSD position by time, UTC session, and rollover."""
    utc_session_end = datetime.combine(
        created_utc.date(), _GOLD_SESSION_CLOSE_UTC, tzinfo=_UTC
    )
    rollover_winddown = (
        next_gold_rollover_deadline(created_utc) - _GOLD_ROLLOVER_WINDDOWN
    )
    candidates = (
        (
            rollover_winddown,
            "NY_ROLLOVER",
        ),
        (
            created_utc + timedelta(minutes=max_hold_minutes),
            "MAX_HOLD",
        ),
        (
            utc_session_end,
            "UTC_SESSION",
        ),
    )
    return min(candidates, key=lambda candidate: candidate[0])


def _intraday_decision(trade: Any, now_utc: datetime) -> dict:
    created_utc = _as_utc(_field(trade, "created_at"))
    if created_utc is None:
        return _decision(
            True,
            "Intraday position has no trustworthy creation timestamp; same-day closure cannot be verified.",
            "INTRADAY_EXIT_OVERDUE",
            None,
            "indian_intraday_1520_ist",
        )

    opened_date = created_utc.astimezone(_IST).date()
    now_ist = now_utc.astimezone(_IST)
    deadline = datetime.combine(opened_date, _INTRADAY_CUTOFF, tzinfo=_IST)

    if now_ist.date() != opened_date:
        return _decision(
            True,
            "Intraday position is still open outside its creation date in Asia/Kolkata; it must be exited using a fresh quote.",
            "INTRADAY_EXIT_OVERDUE",
            deadline,
            "indian_intraday_1520_ist",
        )
    if now_ist >= deadline:
        status = "INTRADAY_EXIT_DUE" if now_ist == deadline else "INTRADAY_EXIT_OVERDUE"
        return _decision(
            True,
            "Intraday position reached its 15:20 Asia/Kolkata wind-down deadline; exit only at a fresh provider quote.",
            status,
            deadline,
            "indian_intraday_1520_ist",
        )
    return _decision(
        False,
        "Intraday holding window remains open; 15:20 Asia/Kolkata is the mandatory wind-down deadline.",
        "HOLDING_POLICY_OK",
        deadline,
        "indian_intraday_1520_ist",
    )


def _gold_decision(trade: Any, now_utc: datetime, holding_intent: Any) -> dict:
    created_utc = _as_utc(_field(trade, "created_at"))
    if created_utc is None:
        return _decision(
            True,
            "XAUUSD position has no trustworthy creation timestamp; overnight duration cannot be verified.",
            "HOLDING_TIMESTAMP_MISSING",
            None,
            "xauusd_no_overnight_rollover_safe",
        )

    authorized_overnight = _has_explicit_overnight_authorization(holding_intent)
    max_hold_minutes = _positive_max_hold_minutes(holding_intent)
    if authorized_overnight and max_hold_minutes is not None:
        deadline = created_utc + timedelta(minutes=max_hold_minutes)
        policy = "xauusd_verified_overnight_max_hold"
        if now_utc >= deadline:
            return _decision(
                True,
                "XAUUSD reached the explicitly authorized maximum holding duration; exit only at a fresh provider quote.",
                "MAX_HOLD_DUE" if now_utc == deadline else "MAX_HOLD_OVERDUE",
                deadline,
                policy,
            )
        return _decision(
            False,
            "XAUUSD overnight holding is explicitly authorized with verified financing and remains within its maximum duration.",
            "HOLDING_POLICY_OK",
            deadline,
            policy,
        )

    if authorized_overnight:
        # Explicit verified financing permits crossing the NY rollover, but
        # without a positive strategy bound retain the previous same-UTC-day
        # ceiling rather than inventing an unlimited duration.
        deadline = datetime.combine(
            created_utc.date(), _GOLD_SESSION_CLOSE_UTC, tzinfo=_UTC
        )
        policy = "xauusd_verified_same_utc_session"
        if now_utc >= deadline:
            return _decision(
                True,
                "XAUUSD reached the conservative 23:00 UTC session close; no positive strategy maximum-hold duration was supplied.",
                "UTC_SESSION_EXIT_DUE"
                if now_utc == deadline
                else "UTC_SESSION_EXIT_OVERDUE",
                deadline,
                policy,
            )
        return _decision(
            False,
            "Verified overnight financing is authorized, but no positive strategy bound was supplied; close by 23:00 UTC.",
            "HOLDING_POLICY_OK",
            deadline,
            policy,
        )

    # Even a strategy-supplied duration is not permission to cross financing
    # rollover. Without one, use a shorter fail-closed duration than the normal
    # 25-minute strategy window so missing intent cannot silently extend risk.
    max_hold_minutes = max_hold_minutes or _GOLD_DEFAULT_MAX_HOLD_MINUTES
    deadline, limiting_factor = _gold_default_deadline(created_utc, max_hold_minutes)
    policy = "xauusd_no_overnight_rollover_safe"
    if now_utc >= deadline:
        reason_by_limit = {
            "NY_ROLLOVER": (
                "XAUUSD reached the one-minute quote-backed wind-down deadline before the next 17:00 America/New_York financing rollover; a due position must remain pending if no fresh quote is available."
            ),
            "MAX_HOLD": (
                "XAUUSD reached its maximum holding duration; exit only using a fresh provider quote."
            ),
            "UTC_SESSION": (
                "XAUUSD reached the 23:00 UTC session close; exit only using a fresh provider quote."
            ),
        }
        return _decision(
            True,
            reason_by_limit[limiting_factor],
            f"{limiting_factor}_EXIT_DUE"
            if now_utc == deadline
            else f"{limiting_factor}_EXIT_OVERDUE",
            deadline,
            policy,
        )
    reason = "XAUUSD has no verified explicit overnight authorization; its duration, 23:00 UTC session end, and next New York rollover wind-down are enforced."
    return _decision(False, reason, "HOLDING_POLICY_OK", deadline, policy)


def holding_exit_decision(
    trade: Any, *, now: datetime, holding_intent: Any = None
) -> dict:
    """Return a pure time-policy decision for an existing trade.

    Naive ``created_at`` database values are interpreted as UTC. This helper
    does not inspect quotes, assign fills, or mutate ``trade``.
    """
    now_utc = _as_utc(now)
    if now_utc is None:
        return _decision(
            True,
            "Current time is missing or invalid; holding safety cannot be established.",
            "POLICY_TIME_INVALID",
            None,
            "fail_safe",
        )

    trade_status = _agent_name(_field(trade, "status", "OPEN"))
    if trade_status and trade_status not in {"OPEN", "ACTIVE"}:
        return _decision(
            False,
            "Trade is not open; no holding-time exit is due.",
            "NOT_OPEN",
            None,
            "no_open_position",
        )

    agent = _agent_name(_field(trade, "agent", _field(trade, "agent_name")))
    if agent in _INTRADAY_AGENTS:
        return _intraday_decision(trade, now_utc)
    if agent == _GOLD_AGENT:
        return _gold_decision(trade, now_utc, holding_intent)
    if agent == _STOCK_AGENT:
        return _decision(
            False,
            "Stocks follow strategy stop/target and holding rules; no arbitrary holding timeout is applied.",
            "STRATEGY_MANAGED",
            None,
            "stock_strategy_managed",
        )
    return _decision(
        False,
        "No time-based holding cutoff is defined for this agent.",
        "STRATEGY_MANAGED",
        None,
        "strategy_managed",
    )


def _entry_side(holding_intent: Any) -> str:
    for name in ("trade_type", "side", "direction", "action"):
        value = _field(holding_intent, name)
        if value is not None:
            return _agent_name(value)
    return ""


def entry_allowed_by_holding_policy(
    agent_name: Any, *, now: datetime, holding_intent: Any = None
) -> bool:
    """Return whether a new entry is compatible with the holding-time policy.

    For STOCKS, an explicitly identified SELL/SHORT entry is rejected because
    this policy does not establish support for carrying a cash-delivery short.
    """
    now_utc = _as_utc(now)
    if now_utc is None:
        return False

    agent = _agent_name(agent_name)
    if agent in _INTRADAY_AGENTS:
        return now_utc.astimezone(_IST).time().replace(tzinfo=None) < _INTRADAY_CUTOFF
    if agent == _STOCK_AGENT:
        return _entry_side(holding_intent) not in {
            "SELL",
            "SHORT",
            "SELL_SHORT",
            "SELLSHORT",
        }
    if agent == _GOLD_AGENT:
        if _has_explicit_overnight_authorization(holding_intent):
            if _positive_max_hold_minutes(holding_intent) is not None:
                return True
            # Authorization alone is not a duration bound. This case uses
            # the same-UTC-day 23:00 fallback in holding_exit_decision.
            verified_no_bound_session_end = datetime.combine(
                now_utc.date(), _GOLD_SESSION_CLOSE_UTC, tzinfo=_UTC
            )
            return now_utc < verified_no_bound_session_end
        max_hold_minutes = (
            _positive_max_hold_minutes(holding_intent)
            or _GOLD_DEFAULT_MAX_HOLD_MINUTES
        )
        proposed_end = now_utc + timedelta(minutes=max_hold_minutes)
        utc_session_end = datetime.combine(
            now_utc.date(), _GOLD_SESSION_CLOSE_UTC, tzinfo=_UTC
        )
        rollover_winddown = (
            next_gold_rollover_deadline(now_utc) - _GOLD_ROLLOVER_WINDDOWN
        )
        latest_safe_end = min(utc_session_end, rollover_winddown)
        return proposed_end <= latest_safe_end
    return True