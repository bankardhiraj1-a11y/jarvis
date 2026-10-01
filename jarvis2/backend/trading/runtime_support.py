"""Small, deterministic helpers for exchange sessions and paper-review evidence."""

from __future__ import annotations

from datetime import date, datetime
import math
from datetime import timezone
from pathlib import Path
import re
from typing import Any, Iterable
from zoneinfo import ZoneInfo


_IST = ZoneInfo("Asia/Kolkata")
_VERIFIED_CALENDAR = {
    # Official exchange-calendar fact supplied for the 2026-10-02 release.
    # Coverage is deliberately short: later dates fail closed until a newer
    # official calendar file is supplied.
    "verified_through": "2026-10-05",
    "holidays": {"2026-10-02": "Gandhi Jayanti"},
    "source": "Official BSE/NSE holiday-calendar verification, as of 2026-10-01",
}


def exchange_session_status(
    now: datetime, calendar: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Fail closed for Indian sessions beyond the verified calendar horizon."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=_IST)
    local = now.astimezone(_IST)
    session_date = local.date()
    if session_date.weekday() >= 5:
        return {
            "open": False,
            "status": "WEEKEND",
            "date": session_date.isoformat(),
            "reason": "Indian exchanges are closed on weekends",
        }

    source = calendar if isinstance(calendar, dict) else _VERIFIED_CALENDAR
    try:
        verified_through = date.fromisoformat(str(source["verified_through"]))
    except (KeyError, TypeError, ValueError):
        return {
            "open": False,
            "status": "CALENDAR_UNKNOWN",
            "date": session_date.isoformat(),
            "reason": "No valid verified Indian exchange calendar is available",
        }
    if session_date > verified_through:
        return {
            "open": False,
            "status": "CALENDAR_UNKNOWN",
            "date": session_date.isoformat(),
            "reason": "Exchange holiday status is not verified for this future date",
        }

    holidays = source.get("holidays", {})
    holiday = holidays.get(session_date.isoformat()) if isinstance(holidays, dict) else None
    if holiday:
        return {
            "open": False,
            "status": "EXCHANGE_HOLIDAY",
            "date": session_date.isoformat(),
            "reason": str(holiday),
        }
    return {
        "open": True,
        "status": "WEEKDAY",
        "date": session_date.isoformat(),
        "source": source.get("source"),
    }


def load_indian_exchange_calendar(workspace_root: Path | None = None) -> dict[str, Any]:
    """Prefer the parent-provided official 2026 exchange calendar source asset."""
    root = workspace_root or Path(__file__).resolve().parents[3]
    candidates = (
        root / "research" / "sources" / "indian-trading-holidays-2026.md",
        root / "jarvis2" / "research" / "sources" / "indian-trading-holidays-2026.md",
    )
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        holidays = {}
        exchange_calendar = content.split("## Settlement holidays", 1)[0]
        in_holiday_table = False
        for line in exchange_calendar.splitlines():
            if "| Date | Day | Holiday | Exchanges |" in line:
                in_holiday_table = True
                continue
            if not in_holiday_table or not line.lstrip().startswith("|"):
                continue
            if set(line.replace("|", "").replace("-", "").strip()) == set():
                continue
            exchange_row = line.lower()
            if "nse" not in exchange_row or "bse" not in exchange_row:
                continue
            match = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3})\s+2026\b", line)
            if not match:
                continue
            try:
                holiday_date = datetime.strptime(
                    f"{match.group(1)} {match.group(2)} 2026", "%d %b %Y"
                ).date()
            except ValueError:
                continue
            if holiday_date.weekday() < 5:
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                label = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cells[2] if len(cells) > 2 else "")
                holidays[holiday_date.isoformat()] = label or "Exchange holiday"
        if "2026-10-02" in holidays and holidays:
            return {
                "verified_through": "2026-12-31",
                "holidays": holidays,
                "source": "Zerodha NSE/BSE 2026 holiday calendar source asset",
            }
    return dict(_VERIFIED_CALENDAR)


def wilson_interval(wins: int, trials: int, z: float = 1.959963984540054) -> dict[str, float] | None:
    """95% Wilson interval for a binomial win rate; no interval for zero trials."""
    if (
        isinstance(wins, bool)
        or isinstance(trials, bool)
        or not isinstance(wins, int)
        or not isinstance(trials, int)
        or trials <= 0
        or wins < 0
        or wins > trials
        or not math.isfinite(z)
        or z <= 0
    ):
        return None
    p = wins / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * trials)) / trials) / denominator
    return {
        "low_pct": round(max(0.0, center - margin) * 100, 2),
        "high_pct": round(min(1.0, center + margin) * 100, 2),
    }


def daily_trade_review(
    trades: Iterable[Any],
    *,
    review_date: date,
    calls: int | None,
    quote_currency: str = "INR",
    session_timezone: str = "Asia/Kolkata",
) -> dict[str, Any]:
    """Summarize only closed trades with authentic provider-price provenance."""
    closed = []
    review_zone = ZoneInfo(session_timezone)
    for trade in trades:
        if (
            str(getattr(trade, "status", "")).upper() != "CLOSED"
            or str(getattr(trade, "data_source", "")).upper() not in {"DHAN", "OANDA"}
            or not getattr(trade, "entry_data_timestamp", None)
            or not getattr(trade, "exit_data_timestamp", None)
        ):
            continue
        try:
            entry_event = datetime.fromisoformat(
                str(trade.entry_data_timestamp).strip().replace("Z", "+00:00")
            )
            exit_event = datetime.fromisoformat(
                str(trade.exit_data_timestamp).strip().replace("Z", "+00:00")
            )
            closed_event = getattr(trade, "closed_at", None)
            if not isinstance(closed_event, datetime):
                continue
            entry_event = (
                entry_event.replace(tzinfo=timezone.utc)
                if entry_event.tzinfo is None else entry_event
            ).astimezone(timezone.utc)
            exit_event = (
                exit_event.replace(tzinfo=timezone.utc)
                if exit_event.tzinfo is None else exit_event
            ).astimezone(timezone.utc)
            closed_event = (
                closed_event.replace(tzinfo=timezone.utc)
                if closed_event.tzinfo is None else closed_event
            ).astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        if not entry_event <= exit_event <= closed_event:
            continue
        try:
            entry_price = float(getattr(trade, "entry_price"))
            exit_price = float(getattr(trade, "exit_price"))
            quantity = float(getattr(trade, "quantity"))
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            not all(math.isfinite(value) for value in (entry_price, exit_price, quantity))
            or min(entry_price, exit_price, quantity) <= 0
        ):
            continue
        closed_at = getattr(trade, "closed_at", None)
        if isinstance(closed_at, datetime):
            closed_date = (
                closed_at.replace(tzinfo=timezone.utc)
                if closed_at.tzinfo is None
                else closed_at
            ).astimezone(review_zone).date()
            if closed_date != review_date:
                continue
        else:
            continue
        closed.append(trade)

    classified_values = []
    for trade in closed:
        try:
            pnl = float(trade.pnl)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(pnl):
            classified_values.append(pnl)
    wins = sum(value > 0 for value in classified_values)
    losses = sum(value < 0 for value in classified_values)
    breakeven = sum(value == 0 for value in classified_values)
    classified = wins + losses + breakeven
    interval = wilson_interval(wins, classified)
    return {
        "date": review_date.isoformat(),
        "status": "INSUFFICIENT_SAMPLE" if classified < 30 else "RESEARCH_ONLY",
        "research_status": "UNVALIDATED",
        "closed_verified_paper_trades": len(closed),
        "classified_trades": classified,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "unclassified_cost_or_provenance": len(closed) - classified,
        "win_rate_pct": round(wins / classified * 100, 2) if classified else None,
        "win_rate_95pct_wilson": interval,
        "currency": quote_currency,
        "gross_price_pnl": round(
            sum(
                (
                    (float(trade.exit_price) - float(trade.entry_price))
                    * float(trade.quantity)
                    * (1 if getattr(trade.trade_type, "value", trade.trade_type) == "BUY" else -1)
                )
                for trade in closed
            ),
            2,
        ),
        "note": (
            "A sample below 30 is insufficient; no closed-trade sample, including three trades, "
            "is a validation or 90% win-rate claim."
        ),
        "daily_calls": calls,
        "daily_entries": None,
        "daily_exits": None,
    }