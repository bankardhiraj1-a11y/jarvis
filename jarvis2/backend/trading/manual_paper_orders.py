"""Durable paper-only manual orders filled from fresh provider-side prices."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import math
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from models import ManualPaperOrder, Trade
from trading.holding_policy import next_gold_rollover_deadline
from trading.manual_gold_holding import manual_gold_holding_decision


_UTC = timezone.utc
_IST = ZoneInfo("Asia/Kolkata")
_MAX_AGE_SECONDS = 15.0
_GOLD_MAX_OUNCES = 15.0
_GOLD_MAX_RISK = 150.0
_GOLD_ENTRY_BUFFER_MINUTES = 25
_INDIA_MAX_RISK = 1000.0
_STOCKS = frozenset({"RELIANCE", "TCS", "INFY", "HDFCBANK", "BAJAJ-AUTO"})
_OPTION_UNDERLYINGS = frozenset({"SENSEX", "NIFTY", "BANKNIFTY"})
_INDIA_CUTOFF = time(15, 20)


class ManualOrderError(ValueError):
    """A safe domain or state error suitable for an HTTP 400 response."""


ManualPaperOrderError = ManualOrderError
OrderError = ManualOrderError


def _as_utc(value: Any, label: str = "time") -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise OrderError(f"{label} must be a valid datetime") from None
    if not isinstance(value, datetime):
        raise OrderError(f"{label} must be a valid datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_UTC)
    try:
        return value.astimezone(_UTC)
    except (OverflowError, ValueError):
        raise OrderError(f"{label} must be a valid datetime") from None


def _db_time(value: datetime) -> datetime:
    return _as_utc(value).replace(tzinfo=None)


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise OrderError(f"{label} must be a finite positive number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise OrderError(f"{label} must be a finite positive number") from None
    if not math.isfinite(result) or result <= 0:
        raise OrderError(f"{label} must be a finite positive number")
    return result


def _positive_or_none(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OrderError(f"{label} must be a positive integer")
    return value


def _gold_hard_closing_deadline(now_utc: datetime) -> datetime:
    utc_cutoff = datetime.combine(now_utc.date(), time(23, 0), tzinfo=_UTC)
    rollover_cutoff = next_gold_rollover_deadline(now_utc) - timedelta(minutes=1)
    return min(utc_cutoff, rollover_cutoff)


def _safe_gold_deadline(
    now_utc: datetime, entry_buffer_minutes: int = _GOLD_ENTRY_BUFFER_MINUTES
) -> datetime:
    """Latest safe entry time, reserving a conservative 25-minute buffer."""
    return _gold_hard_closing_deadline(now_utc) - timedelta(
        minutes=entry_buffer_minutes
    )


def _india_cutoff(day: date) -> datetime:
    return datetime.combine(day, _INDIA_CUTOFF, tzinfo=_IST).astimezone(_UTC)


def _validate_targets(side: str, entry: float, stop: float, target: float,
                      target_2: Optional[float]) -> None:
    if side == "BUY":
        valid = stop < entry < target
        second_valid = target_2 is None or target_2 > target
    else:
        valid = stop > entry > target
        second_valid = target_2 is None or target_2 < target
    if not valid or not second_valid:
        raise OrderError(
            "Stop loss and targets must be on the correct side of the entry; "
            "target 2 must be further from entry than target 1"
        )


def _validated_payload(payload: Any, now_utc: datetime) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OrderError("Order payload must be an object")
    market = str(payload.get("market") or "").strip().upper()
    symbol = str(payload.get("symbol") or "").strip().upper()
    side = str(payload.get("side") or "").strip().upper()
    order_type = str(payload.get("order_type") or "").strip().upper()
    if market not in {"GOLD", "STOCKS", "OPTIONS"}:
        raise OrderError("market must be GOLD, STOCKS, or OPTIONS")
    if side not in {"BUY", "SELL"}:
        raise OrderError("side must be BUY or SELL")
    if order_type not in {"MARKET", "LIMIT", "STOP"}:
        raise OrderError("order_type must be MARKET, LIMIT, or STOP")
    if payload.get("mode") not in (None, "PAPER"):
        raise OrderError("Manual orders are paper-only")
    if payload.get("manual_context") not in (None, True):
        raise OrderError("A manual order context is required")
    if market == "GOLD" and symbol != "XAUUSD":
        raise OrderError("GOLD orders are restricted to XAUUSD")
    if market == "STOCKS" and symbol not in _STOCKS:
        raise OrderError("STOCKS symbol is not in the supported current watchlist")
    if market == "OPTIONS":
        if symbol not in _OPTION_UNDERLYINGS:
            raise OrderError("OPTIONS underlying is not supported")
        if side != "BUY":
            raise OrderError("Only long BUY option orders are supported; naked option SELL is disabled")

    limit_price = (
        _positive(payload.get("limit_price"), "limit_price")
        if order_type != "MARKET" else None
    )
    stop_loss = _positive(payload.get("stop_loss"), "stop_loss")
    take_profit = _positive(payload.get("take_profit"), "take_profit")
    take_profit_2 = (
        _positive(payload.get("take_profit_2"), "take_profit_2")
        if payload.get("take_profit_2") is not None else None
    )
    quantity_raw = payload.get("quantity")
    if market == "GOLD":
        if quantity_raw is None:
            quantity_raw = payload.get("quantity_troy_ounces", 15)
        quantity = _positive(quantity_raw, "quantity (troy ounces)")
        if quantity > _GOLD_MAX_OUNCES:
            raise OrderError("XAUUSD manual paper orders are capped at 15 troy ounces")
        quantity_oz = quantity
        quantity_lots = None
        option_type = strike = expiry = None
    elif market == "STOCKS":
        quantity = _positive(quantity_raw, "quantity")
        if not quantity.is_integer():
            raise OrderError("STOCKS quantity must be a whole number of shares")
        quantity_oz = None
        quantity_lots = None
        option_type = strike = expiry = None
    else:
        quantity_lots = _integer(payload.get("quantity_lots"), "quantity_lots")
        quantity = float(quantity_lots)
        quantity_oz = None
        option_type = str(payload.get("option_type") or "").strip().upper()
        if option_type not in {"CE", "PE"}:
            raise OrderError("option_type must be CE or PE")
        strike = _positive(payload.get("strike"), "strike")
        expiry_value = payload.get("expiry")
        try:
            expiry_date = date.fromisoformat(str(expiry_value))
        except (TypeError, ValueError):
            raise OrderError("expiry must be a real ISO date") from None
        if expiry_date.isoformat() != str(expiry_value) or expiry_date < now_utc.astimezone(_IST).date():
            raise OrderError("expiry must be a current or future ISO date")
        expiry = expiry_date.isoformat()

    max_hold = payload.get("max_hold_minutes")
    if market == "GOLD":
        if max_hold is not None and (
            isinstance(max_hold, bool)
            or not isinstance(max_hold, int)
            or max_hold != _GOLD_ENTRY_BUFFER_MINUTES
        ):
            raise OrderError(
                "Gold max_hold_minutes must be null; legacy 25-minute payloads are accepted"
            )
        # Keep 25 in the non-null legacy field for compatibility. The separate
        # entry buffer is enforced below; this stored value is never an exit timer.
        max_hold = _GOLD_ENTRY_BUFFER_MINUTES
    else:
        if max_hold is None:
            max_hold = 20
        if (
            isinstance(max_hold, bool)
            or not isinstance(max_hold, int)
            or not 1 <= max_hold <= 25
        ):
            raise OrderError("max_hold_minutes must be an integer from 1 through 25")

    if take_profit_2 is not None:
        if market == "STOCKS" and int(quantity) < 2:
            raise OrderError("Two stock targets require at least two whole shares")
        if market == "OPTIONS" and quantity_lots < 2:
            raise OrderError("Two option targets require at least two whole lots")

    if limit_price is not None:
        _validate_targets(side, limit_price, stop_loss, take_profit, take_profit_2)
        risk = abs(limit_price - stop_loss) * quantity
        risk_cap = _GOLD_MAX_RISK if market == "GOLD" else _INDIA_MAX_RISK
        if risk > risk_cap:
            currency = "USD" if market == "GOLD" else "INR"
            raise OrderError(f"Planned stop risk must not exceed {currency} {risk_cap:g}")
    if market == "GOLD":
        deadline = _safe_gold_deadline(now_utc, _GOLD_ENTRY_BUFFER_MINUTES)
        if now_utc >= deadline:
            raise OrderError("New XAUUSD orders are disabled at the safe-entry cutoff")
        expires_at = deadline
    elif market == "OPTIONS":
        expires_at = min(
            now_utc + timedelta(days=7),
            _india_cutoff(date.fromisoformat(expiry)),
        )
    else:
        expires_at = now_utc + timedelta(days=7)

    return {
        "client_order_id": _client_order_key(payload),
        "market": market,
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "limit_price": limit_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "take_profit_2": take_profit_2,
        "quantity": quantity,
        "quantity_troy_ounces": quantity_oz,
        "quantity_lots": quantity_lots,
        "option_lot_size": None,
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry,
        "max_hold_minutes": max_hold,
        "manual_order": True,
        "session_override": True,
        "allow_overnight": False,
        "expires_at": _db_time(expires_at),
    }


def _leg_specs(order: ManualPaperOrder) -> list[tuple[str, float, float]]:
    if order.take_profit_2 is None:
        return [("TP1", float(order.quantity), float(order.take_profit))]
    if order.market == "GOLD":
        first_quantity = float(order.quantity) / 2.0
        second_quantity = float(order.quantity) - first_quantity
    else:
        total = int(order.quantity_lots or order.quantity)
        first_quantity = float(total // 2)
        second_quantity = float(total - int(first_quantity))
    return [
        ("TP1", first_quantity, float(order.take_profit)),
        ("TP2", second_quantity, float(order.take_profit_2)),
    ]


def serialize_manual_order(order: ManualPaperOrder, db=None) -> dict[str, Any]:
    """Return the durable parent and child-leg state using JSON-safe values."""
    state = str(order.status or "PENDING").upper()
    legs = []
    specs = _leg_specs(order)
    for index, (label, sized_quantity, target) in enumerate(specs):
        trade_id = order.first_trade_id if index == 0 else order.second_trade_id
        trade = db.get(Trade, trade_id) if db is not None and trade_id is not None else None
        item = {
            "label": label,
            "trade_id": trade_id,
            "status": getattr(trade, "status", None),
            "quantity": (
                float(trade.quantity) if trade is not None
                else sized_quantity * int(order.option_lot_size or 1)
                if order.market == "OPTIONS" and order.option_lot_size
                else sized_quantity if order.market != "OPTIONS" else None
            ),
            "quantity_lots": sized_quantity if order.market == "OPTIONS" else None,
            "take_profit": target,
        }
        legs.append(item)
    return {
        "id": f"manual-{order.id}",
        "client_order_id": order.client_order_id,
        "status": state,
        "symbol": order.symbol,
        "side": order.side,
        "market": order.market,
        "order_type": order.order_type,
        "limit_price": float(order.limit_price) if order.limit_price is not None else None,
        "stop_loss": float(order.stop_loss),
        "take_profit": float(order.take_profit),
        "take_profit_2": (
            float(order.take_profit_2) if order.take_profit_2 is not None else None
        ),
        "quantity": float(order.quantity),
        "quantity_troy_ounces": (
            float(order.quantity_troy_ounces)
            if order.quantity_troy_ounces is not None else None
        ),
        "quantity_lots": order.quantity_lots,
        "option_type": order.option_type,
        "strike": float(order.strike) if order.strike is not None else None,
        "expiry": order.expiry,
        "first_trade_id": order.first_trade_id,
        "second_trade_id": order.second_trade_id,
        "created_at": _iso(order.created_at),
        "expires_at": _iso(order.expires_at),
        "filled_at": _iso(order.filled_at),
        "fill_price": float(order.fill_price) if order.fill_price is not None else None,
        "last_reason": order.last_reason,
        "mode": "PAPER",
        "manual_order": bool(order.manual_order),
        "session_override": bool(order.session_override),
        "allow_overnight": bool(order.allow_overnight),
        **(
            {"holding_mode": "SL_TP_ROLLOVER"}
            if order.market == "GOLD" else {}
        ),
        "max_hold_minutes": (
            None if order.market == "GOLD" else int(order.max_hold_minutes)
        ),
        "option_lot_size": order.option_lot_size,
        "legs": legs,
    }


def list_manual_orders(db) -> list[dict[str, Any]]:
    orders = (
        db.query(ManualPaperOrder)
        .order_by(ManualPaperOrder.created_at.desc(), ManualPaperOrder.id.desc())
        .all()
    )
    return [serialize_manual_order(order, db) for order in orders]


def _order_key(order_id: Any) -> Optional[int]:
    value = str(order_id or "").strip()
    if value.startswith("manual-"):
        value = value[len("manual-"):]
    try:
        key = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return key if key > 0 else None


def cancel_manual_order(db, order_id) -> ManualPaperOrder:
    key = _order_key(order_id)
    order = db.get(ManualPaperOrder, key) if key is not None else None
    if order is None:
        raise OrderError("Manual paper order was not found")
    state = str(order.status or "").upper()
    if state == "FILLED":
        raise OrderError("A filled manual paper order cannot be cancelled")
    if state == "CANCELLED":
        return order
    if state != "PENDING":
        raise OrderError(f"Only pending orders can be cancelled (current status: {state})")
    order.status = "CANCELLED"
    order.last_reason = "Cancelled manually before fill"
    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise OrderError("Order changed concurrently; reload before cancelling") from None
    except SQLAlchemyError:
        db.rollback()
        raise OrderError("Could not cancel manual paper order") from None
    return order


def manual_order_for_trade(db, trade_id) -> Optional[ManualPaperOrder]:
    try:
        key = int(trade_id)
    except (TypeError, ValueError, OverflowError):
        return None
    return db.query(ManualPaperOrder).filter(
        or_(
            ManualPaperOrder.first_trade_id == key,
            ManualPaperOrder.second_trade_id == key,
        )
    ).one_or_none()


def manual_holding_intent(order: ManualPaperOrder) -> dict[str, Any]:
    """Policy metadata for the caller's market-specific manual holding rules."""
    is_gold = order.market == "GOLD"
    return {
        "manual_order": True,
        "session_override": True,
        "allow_overnight": False,
        **({"holding_mode": "SL_TP_ROLLOVER"} if is_gold else {}),
        "max_hold_minutes": None if is_gold else int(order.max_hold_minutes),
        "reason": (
            "User-selected manual XAUUSD paper order; stop/target-managed holding "
            "has no elapsed-time exit and is closed only by the UTC-session or "
            "New York rollover safety cutoff."
            if is_gold else
            "User-selected manual paper order; no overnight holding is allowed."
        ),
        "order_id": getattr(order, "id", None),
        "market": order.market,
        "symbol": order.symbol,
    }


def manual_holding_decision(
    order: ManualPaperOrder, entry_time: Any, now: Any
) -> dict[str, Any]:
    """Apply strategy-managed Gold or bounded Indian manual holding rules."""
    if order.market == "GOLD":
        return manual_gold_holding_decision(entry_time, now)

    now_utc = _as_utc(now, "now")
    try:
        opened = _as_utc(entry_time, "entry_time")
    except OrderError:
        return {
            "due": True,
            "reason": "Manual Indian-market position has no trustworthy entry timestamp; close using a fresh provider quote.",
            "status": "INTRADAY_EXIT_OVERDUE",
            "deadline": None,
            "policy": "manual_indian_intraday_bounded",
        }
    entry_day = opened.astimezone(_IST).date()
    cutoff = _india_cutoff(entry_day)
    maximum = opened + timedelta(minutes=int(order.max_hold_minutes))
    deadline = min(cutoff, maximum)
    due = now_utc >= deadline
    exact_cutoff = now_utc == deadline
    return {
        "due": due,
        "reason": (
            "Manual Indian-market position reached its intraday/maximum-hold deadline; "
            "exit only using a fresh provider quote."
            if due else
            "Manual Indian-market position remains within its same-day bounded holding window."
        ),
        "status": (
            "INTRADAY_EXIT_DUE" if exact_cutoff and cutoff <= maximum
            else "MAX_HOLD_DUE" if exact_cutoff
            else "INTRADAY_EXIT_OVERDUE" if due and cutoff <= maximum
            else "MAX_HOLD_OVERDUE" if due
            else "HOLDING_POLICY_OK"
        ),
        "deadline": _iso(deadline),
        "policy": "manual_indian_intraday_bounded",
    }


def _save_order(db, order: ManualPaperOrder) -> bool:
    try:
        db.commit()
        return True
    except StaleDataError:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        return False


from trading.manual_order_contract import _client_order_key, create_manual_order
from trading.manual_paper_order_processing import process_manual_orders