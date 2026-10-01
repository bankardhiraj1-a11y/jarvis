"""Pure helpers for live-provider paper trades and their provenance."""

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import inspect, text


_OPTION_CONTRACT = re.compile(
    r"^(?P<strike>\d+(?:\.\d+)?)\s+(?P<kind>CE|PE)\s+(?P<expiry>\d{4}-\d{2}-\d{2})$"
)
LIVE_DATA_SOURCES = frozenset({"DHAN", "OANDA"})


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _positive_price(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def quote_is_fresh(
    quote: Any,
    max_age_seconds: float = 15.0,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Fail closed unless a quote has an explicit recent age or timestamp."""
    if not isinstance(quote, dict) or quote.get("stale") is True:
        return False
    if quote.get("status") not in (None, "ok", "success", "live"):
        return False
    if _positive_price(quote.get("close", quote.get("last_price"))) is None:
        return False

    age = quote.get("age_seconds")
    if age is not None:
        try:
            parsed_age = float(age)
        except (TypeError, ValueError, OverflowError):
            return False
        return math.isfinite(parsed_age) and 0 <= parsed_age <= max_age_seconds

    timestamp = quote.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp.strip():
        return False
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    age_seconds = (current_time - parsed_timestamp.astimezone(timezone.utc)).total_seconds()
    return 0 <= age_seconds <= max_age_seconds


def quote_has_timestamp(quote: Any) -> bool:
    """Whether a quote carries a parseable provider timestamp for provenance."""
    return isinstance(quote, dict) and _parse_timestamp(quote.get("timestamp")) is not None


def option_entry_and_exit_prices(quote: Any) -> Optional[tuple]:
    """Return conservative long-option (ask entry, bid exit) prices."""
    if (
        not isinstance(quote, dict)
        or not quote_is_fresh(quote)
        or not quote_has_timestamp(quote)
    ):
        return None
    bid = _positive_price(quote.get("bid", quote.get("top_bid_price")))
    ask = _positive_price(quote.get("ask", quote.get("top_ask_price")))
    last = _positive_price(quote.get("last_price", quote.get("close")))
    if bid is None or ask is None or last is None or bid > ask:
        return None
    return ask, bid


def provider_side_price(quote: Any, transaction_side: str) -> Optional[float]:
    """Return the executable ask for BUY or bid for SELL from a fresh quote."""
    if (
        not isinstance(quote, dict)
        or not quote_is_fresh(quote)
        or not quote_has_timestamp(quote)
    ):
        return None
    side = str(transaction_side or "").strip().upper()
    if side == "BUY":
        return _positive_price(quote.get("ask"))
    if side == "SELL":
        return _positive_price(quote.get("bid"))
    return None


def build_long_option_paper_entry(
    signal: str,
    quote: Any,
    quantity: float,
    stop_points: float,
    target_points: float,
) -> Optional[Dict[str, Any]]:
    """Prepare a long CE/PE paper entry using only a fresh, real option quote."""
    direction = str(signal).strip().upper()
    if direction not in {"BUY", "SELL"} or not isinstance(quote, dict):
        return None
    expected_type = "CE" if direction == "BUY" else "PE"
    option_type = str(quote.get("option_type") or "").strip().upper()
    if option_type != expected_type:
        return None
    prices = option_entry_and_exit_prices(quote)
    if prices is None:
        return None
    entry_price, _ = prices
    try:
        quantity = float(quantity)
        stop_points = float(stop_points)
        target_points = float(target_points)
    except (TypeError, ValueError, OverflowError):
        return None
    if (
        not math.isfinite(quantity)
        or quantity <= 0
        or not math.isfinite(stop_points)
        or stop_points <= 0
        or not math.isfinite(target_points)
        or target_points <= 0
    ):
        return None
    try:
        contract = encode_option_contract(
            quote.get("strike"), option_type, quote.get("expiry")
        )
    except (TypeError, ValueError):
        return None
    return {
        "trade_type": "BUY",
        "signal": direction,
        "option_type": option_type,
        "option_strike": contract,
        "option_price": entry_price,
        "entry_price": entry_price,
        "stop_loss": max(0.05, entry_price - stop_points),
        "take_profit": entry_price + target_points,
        "quantity": quantity,
        "data_source": "DHAN",
        "entry_data_timestamp": quote.get("timestamp"),
    }


def encode_option_contract(strike: Any, option_type: str, expiry: str) -> str:
    """Persist the actual option identity in the existing option_strike field."""
    price = _positive_price(strike)
    kind = str(option_type).strip().upper()
    if price is None or kind not in {"CE", "PE"}:
        raise ValueError("Option contract requires a positive strike and CE/PE type")
    parsed_expiry = datetime.strptime(str(expiry), "%Y-%m-%d").date()
    normalized_strike = str(int(price)) if price.is_integer() else f"{price:g}"
    value = f"{normalized_strike} {kind} {parsed_expiry.isoformat()}"
    if len(value) > 20:
        raise ValueError("Option contract does not fit the existing option_strike field")
    return value


def parse_option_contract(value: Any) -> Optional[Dict[str, Any]]:
    """Parse the compact contract identity; legacy/non-option rows return None."""
    if not isinstance(value, str):
        return None
    match = _OPTION_CONTRACT.fullmatch(value.strip())
    if not match:
        return None
    try:
        expiry = datetime.strptime(match.group("expiry"), "%Y-%m-%d").date()
        strike = float(match.group("strike"))
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(strike) or strike <= 0:
        return None
    return {
        "strike": strike,
        "option_type": match.group("kind"),
        "expiry": expiry.isoformat(),
    }


def is_verified_closed_trade(trade: Any) -> bool:
    """Require auditable live-provider timestamps and finite closed-trade values."""
    source = str(getattr(trade, "data_source", "") or "").upper()
    entry_timestamp = _parse_timestamp(getattr(trade, "entry_data_timestamp", None))
    exit_timestamp = _parse_timestamp(getattr(trade, "exit_data_timestamp", None))
    closed_at = _parse_timestamp(getattr(trade, "closed_at", None))
    try:
        pnl = float(getattr(trade, "pnl", None))
        quantity = float(getattr(trade, "quantity", None))
    except (TypeError, ValueError, OverflowError):
        return False
    return bool(
        str(getattr(trade, "status", "")).upper() == "CLOSED"
        and source in LIVE_DATA_SOURCES
        and entry_timestamp is not None
        and exit_timestamp is not None
        and closed_at is not None
        and exit_timestamp >= entry_timestamp
        and closed_at >= exit_timestamp
        and math.isfinite(pnl)
        and math.isfinite(quantity)
        and quantity > 0
        and _positive_price(getattr(trade, "entry_price", None)) is not None
        and _positive_price(getattr(trade, "exit_price", None)) is not None
    )


def verified_closed_trade_metrics(trades: Iterable[Any]) -> Dict[str, Any]:
    """Count only closed paper trades with explicit live-provider provenance."""
    eligible = [trade for trade in trades if is_verified_closed_trade(trade)]

    wins = sum(1 for trade in eligible if float(trade.pnl) > 0)
    losses = sum(1 for trade in eligible if float(trade.pnl) < 0)
    total_pnl = sum(float(trade.pnl) for trade in eligible)
    count = len(eligible)
    return {
        "total_trades": count,
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate": round((wins / count) * 100, 2) if count else 0.0,
        "total_pnl": round(total_pnl, 2),
        "metrics_basis": "closed live-provider-price paper trades only",
    }


def ensure_trade_provenance_columns(db_engine: Any) -> None:
    """Add nullable provenance columns to an existing trades table safely."""
    inspector = inspect(db_engine)
    if "trades" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("trades")}
    additions = {
        "data_source": "VARCHAR(16)",
        "entry_data_timestamp": "VARCHAR(40)",
        "exit_data_timestamp": "VARCHAR(40)",
    }
    missing = [(name, sql_type) for name, sql_type in additions.items() if name not in existing]
    if not missing:
        return
    with db_engine.begin() as connection:
        for name, sql_type in missing:
            connection.execute(
                text(f"ALTER TABLE trades ADD COLUMN {name} {sql_type}")
            )
