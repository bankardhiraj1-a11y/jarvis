"""Durable, paper-only manual XAUUSD SELL limit orders.

Orders are never sent to a broker. A pending order becomes two ordinary paper
Trade rows only after a fresh, executable OANDA bid reaches its limit.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import math
import uuid
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import AgentName, PaperLimitOrder, Trade, TradeType
from trading.holding_policy import next_gold_rollover_deadline
from trading.live_paper import quote_has_timestamp, quote_is_fresh


_UTC = timezone.utc
_MAX_QUANTITY_OUNCES = 15.0
_MAX_PLANNED_RISK_USD = 150.0
_MAX_QUOTE_AGE_SECONDS = 15.0
_IST = ZoneInfo("Asia/Kolkata")


class PaperOrderError(ValueError):
    """A domain validation or state error suitable for an HTTP 400 response."""


OrderError = PaperOrderError


def _as_utc(value: Any, field: str = "time") -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise OrderError(f"{field} must be a valid datetime") from None
    if not isinstance(value, datetime):
        raise OrderError(f"{field} must be a valid datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_UTC)
    try:
        return value.astimezone(_UTC)
    except (OverflowError, ValueError):
        raise OrderError(f"{field} must be a valid datetime") from None


def _db_time(value: datetime) -> datetime:
    """Store aware UTC values in the existing naive-UTC DateTime convention."""
    return _as_utc(value).replace(tzinfo=None)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise OrderError(f"{label} must be a finite positive number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise OrderError(f"{label} must be a finite positive number") from None
    if not math.isfinite(result) or result <= 0:
        raise OrderError(f"{label} must be a finite positive number")
    return result


def _safe_entry_expiry(now_utc: datetime) -> datetime:
    utc_cutoff = datetime.combine(now_utc.date(), time(22, 35), tzinfo=_UTC)
    ny_cutoff = next_gold_rollover_deadline(now_utc) - timedelta(minutes=26)
    if now_utc >= utc_cutoff:
        raise OrderError("New XAUUSD orders are disabled at or after the 22:35 UTC cutoff")
    if now_utc >= ny_cutoff:
        raise OrderError("New XAUUSD orders are disabled within 26 minutes of NY rollover")
    return min(utc_cutoff, ny_cutoff)


def _validated_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OrderError("Order payload must be an object")
    if str(payload.get("symbol") or "").strip().upper() != "XAUUSD":
        raise OrderError("Manual paper limit orders are restricted to XAUUSD")
    if str(payload.get("side") or "").strip().upper() != "SELL":
        raise OrderError("Only manual XAUUSD SELL orders are supported")
    if payload.get("manual_order") is not True:
        raise OrderError("manual_order must be explicitly confirmed as true")
    if payload.get("session_override") is not True:
        raise OrderError("session_override must be explicitly confirmed as true")

    limit_price = _number(payload.get("limit_price"), "limit_price")
    stop_loss = _number(payload.get("stop_loss"), "stop_loss")
    take_profit = _number(payload.get("take_profit"), "take_profit")
    take_profit_2 = _number(payload.get("take_profit_2"), "take_profit_2")
    quantity = _number(payload.get("quantity_troy_ounces", 15), "quantity_troy_ounces")

    if stop_loss <= limit_price:
        raise OrderError("A SELL order stop_loss must be above its limit_price")
    if not limit_price > take_profit > take_profit_2 > 0:
        raise OrderError("SELL targets must be positive and ordered below the limit")
    if quantity > _MAX_QUANTITY_OUNCES:
        raise OrderError("Manual paper orders are capped at 15 troy ounces")
    planned_risk = (stop_loss - limit_price) * quantity
    if not math.isfinite(planned_risk) or planned_risk > _MAX_PLANNED_RISK_USD:
        raise OrderError("Planned stop risk must not exceed USD 150")

    client_order_id = payload.get("client_order_id")
    if client_order_id is None or not str(client_order_id).strip():
        client_order_id = str(uuid.uuid4())
    client_order_id = str(client_order_id).strip()
    if len(client_order_id) > 80:
        raise OrderError("client_order_id must be at most 80 characters")

    return {
        "client_order_id": client_order_id,
        "origin": "paper_manual",
        "symbol": "XAUUSD",
        "side": "SELL",
        "manual_order": True,
        "session_override": True,
        "limit_price": limit_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "take_profit_2": take_profit_2,
        "quantity_troy_ounces": quantity,
    }


def _matches_request(order: PaperLimitOrder, values: dict[str, Any]) -> bool:
    fields = (
        "client_order_id",
        "origin",
        "symbol",
        "side",
        "manual_order",
        "session_override",
        "limit_price",
        "stop_loss",
        "take_profit",
        "take_profit_2",
        "quantity_troy_ounces",
    )
    return all(getattr(order, field) == values[field] for field in fields)


def create_order(db, payload, now=None) -> PaperLimitOrder:
    """Create or return the idempotent durable pending manual order."""
    values = _validated_payload(payload)
    existing = (
        db.query(PaperLimitOrder)
        .filter(PaperLimitOrder.client_order_id == values["client_order_id"])
        .one_or_none()
    )
    if existing is not None:
        if not _matches_request(existing, values):
            raise OrderError("client_order_id already exists for a different order")
        return existing

    now_utc = _as_utc(now or datetime.now(_UTC), "now")
    expires_at = _safe_entry_expiry(now_utc)
    order = PaperLimitOrder(
        **values,
        status="PENDING",
        created_at=_db_time(now_utc),
        expires_at=_db_time(expires_at),
        last_reason="Waiting for a fresh, tradeable OANDA bid at or above the SELL limit",
    )
    db.add(order)
    try:
        db.flush()
        db.commit()
        return order
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(PaperLimitOrder)
            .filter(PaperLimitOrder.client_order_id == values["client_order_id"])
            .one_or_none()
        )
        if existing is not None and _matches_request(existing, values):
            return existing
        raise OrderError("Could not create order because its client_order_id is already used") from None
    except Exception as exc:
        db.rollback()
        raise OrderError("Could not persist paper limit order") from exc


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def serialize_order(order: PaperLimitOrder, db=None) -> dict[str, Any]:
    """Serialize the parent order and its two independently tracked trade legs."""
    state = str(order.status or "PENDING").upper()
    quantity_per_leg = float(order.quantity_troy_ounces) / 2.0
    basis_price = float(order.fill_price if order.fill_price is not None else order.limit_price)
    legs = []
    for label, target, trade_id in (
        ("TP1", order.take_profit, order.first_trade_id),
        ("TP2", order.take_profit_2, order.second_trade_id),
    ):
        trade = db.get(Trade, trade_id) if db is not None and trade_id is not None else None
        legs.append({
            "label": label,
            "trade_id": trade_id,
            "status": getattr(trade, "status", None),
            "quantity_troy_ounces": quantity_per_leg,
            "take_profit": float(target),
        })

    return {
        "id": order.id,
        "client_order_id": order.client_order_id,
        "origin": order.origin,
        "symbol": order.symbol,
        "side": order.side,
        "manual_order": bool(order.manual_order),
        "session_override": bool(order.session_override),
        "status": state,
        "pending": state == "PENDING",
        "filled": state == "FILLED",
        "limit_price": float(order.limit_price),
        "stop_loss": float(order.stop_loss),
        "take_profit": float(order.take_profit),
        "take_profit_2": float(order.take_profit_2),
        "quantity_troy_ounces": float(order.quantity_troy_ounces),
        "planned_risk_usd": round(
            (float(order.stop_loss) - float(order.limit_price))
            * float(order.quantity_troy_ounces),
            2,
        ),
        "fill_price": float(order.fill_price) if order.fill_price is not None else None,
        "filled_at": _iso(order.filled_at),
        "first_trade_id": order.first_trade_id,
        "second_trade_id": order.second_trade_id,
        "created_at": _iso(order.created_at),
        "expires_at": _iso(order.expires_at),
        "expires_at_ist": (
            _as_utc(order.expires_at).astimezone(_IST).isoformat()
            if order.expires_at is not None else None
        ),
        "expiry_deadline_label": "Safe entry cutoff (earliest of UTC session and NY rollover buffers)",
        "last_reason": order.last_reason,
        "legs": legs,
        "gross_potential_targets": [
            {
                "label": "TP1",
                "target_price": float(order.take_profit),
                "quantity_troy_ounces": quantity_per_leg,
                "basis_price": basis_price,
                "gross_usd": round(
                    (basis_price - float(order.take_profit)) * quantity_per_leg, 2
                ),
            },
            {
                "label": "TP2",
                "target_price": float(order.take_profit_2),
                "quantity_troy_ounces": quantity_per_leg,
                "basis_price": basis_price,
                "gross_usd": round(
                    (basis_price - float(order.take_profit_2)) * quantity_per_leg, 2
                ),
            },
        ],
        "potential_disclaimer": (
            "Gross target amounts are price-distance estimates only, not guarantees; "
            "fees, financing, slippage, and realized outcomes are not included."
        ),
    }


def list_orders(db) -> list[dict[str, Any]]:
    orders = (
        db.query(PaperLimitOrder)
        .order_by(PaperLimitOrder.created_at.desc(), PaperLimitOrder.id.desc())
        .all()
    )
    return [serialize_order(order, db) for order in orders]


def cancel_order(db, order_id) -> PaperLimitOrder:
    try:
        order = db.get(PaperLimitOrder, int(order_id))
    except (TypeError, ValueError, OverflowError):
        order = None
    if order is None:
        raise OrderError("Paper limit order was not found")
    status = str(order.status or "").upper()
    if status == "FILLED":
        raise OrderError("A filled paper limit order cannot be cancelled")
    if status == "CANCELLED":
        return order
    if status != "PENDING":
        raise OrderError(f"Only pending orders can be cancelled (current status: {status})")
    order.status = "CANCELLED"
    order.last_reason = "Cancelled manually before fill"
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise OrderError("Could not cancel paper limit order") from exc
    return order


def _quote_event_time(quote: Any, now_utc: datetime) -> tuple[Optional[datetime], Optional[str]]:
    if not isinstance(quote, dict):
        return None, "No OANDA quote is available"
    if str(quote.get("source") or "").strip().upper() != "OANDA":
        return None, "Quote provenance is not OANDA"
    if str(quote.get("environment") or "").strip().lower() not in {"practice", "live"}:
        return None, "OANDA quote environment must be practice or live"
    if quote.get("tradeable") is not True:
        return None, "OANDA instrument is not explicitly tradeable"
    if not quote_has_timestamp(quote):
        return None, "Quote has no provider timestamp"

    timestamp_value = quote.get("provider_timestamp") or quote.get("timestamp")
    try:
        event_time = _as_utc(timestamp_value, "provider timestamp")
    except OrderError:
        return None, "Quote provider timestamp is invalid"
    if event_time > now_utc:
        return None, "Quote provider timestamp is in the future"
    event_quote = dict(quote)
    event_quote["timestamp"] = event_time.isoformat()
    if (
        not quote_is_fresh(quote, _MAX_QUOTE_AGE_SECONDS, now=now_utc)
        or not quote_is_fresh(event_quote, _MAX_QUOTE_AGE_SECONDS, now=now_utc)
    ):
        return None, "OANDA quote is stale or not a fresh provider event"

    bid = _number_or_none(quote.get("bid"))
    ask = _number_or_none(quote.get("ask"))
    if bid is None or ask is None:
        return None, "Quote bid and ask must be finite positive prices"
    if ask < bid:
        return None, "Quote is crossed (ask is below bid)"
    return event_time, None


def _number_or_none(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _reject_pending(order: PaperLimitOrder, reason: str, skipped: list[dict[str, Any]]) -> None:
    order.last_reason = reason
    skipped.append({"order_id": order.id, "reason": reason})


def process_pending_orders(
    db,
    quote,
    now=None,
    accepted_entries_today=0,
) -> dict[str, Any]:
    """Expire due orders or atomically fill eligible orders from a real OANDA quote."""
    now_utc = _as_utc(now or datetime.now(_UTC), "now")
    if (
        isinstance(accepted_entries_today, bool)
        or not isinstance(accepted_entries_today, int)
        or accepted_entries_today < 0
    ):
        raise OrderError("accepted_entries_today must be a non-negative integer")

    pending = (
        db.query(PaperLimitOrder)
        .filter(PaperLimitOrder.status == "PENDING")
        .order_by(PaperLimitOrder.id.asc())
        .all()
    )
    summary: dict[str, Any] = {
        "filled_order_ids": [],
        "filled_trade_ids": [],
        "expired_order_ids": [],
        "skipped": [],
    }
    changed = False
    try:
        for order in pending:
            if now_utc >= _as_utc(order.expires_at):
                order.status = "EXPIRED"
                order.last_reason = "Expired at the safe-entry cutoff; pending orders do not carry overnight"
                summary["expired_order_ids"].append(order.id)
                changed = True

        still_pending = [order for order in pending if order.status == "PENDING"]
        if still_pending:
            event_time, quote_error = _quote_event_time(quote, now_utc)
            if quote_error:
                for order in still_pending:
                    _reject_pending(order, quote_error, summary["skipped"])
                    changed = True
            else:
                bid = float(quote["bid"])
                ask = float(quote["ask"])
                for order in still_pending:
                    if event_time < _as_utc(order.created_at):
                        _reject_pending(
                            order,
                            "Quote provider event predates order creation",
                            summary["skipped"],
                        )
                        changed = True
                        continue
                    if bid < float(order.limit_price):
                        order.last_reason = (
                            f"Fresh OANDA bid {bid:g} has not reached SELL limit "
                            f"{float(order.limit_price):g}"
                        )
                        summary["skipped"].append({
                            "order_id": order.id,
                            "reason": order.last_reason,
                        })
                        changed = True
                        continue
                    if ask >= float(order.stop_loss):
                        _reject_pending(
                            order,
                            "Current ask is at or above the SELL stop; unsafe entry gap",
                            summary["skipped"],
                        )
                        changed = True
                        continue
                    if accepted_entries_today > 1:
                        _reject_pending(
                            order,
                            "Two new legs would exceed the three-entry daily cap",
                            summary["skipped"],
                        )
                        changed = True
                        continue

                    open_trade = (
                        db.query(Trade)
                        .filter(
                            Trade.symbol == "XAUUSD",
                            Trade.status.in_(("OPEN", "ACTIVE")),
                        )
                        .first()
                    )
                    if open_trade is not None:
                        _reject_pending(
                            order,
                            "An OPEN XAUUSD trade already exists",
                            summary["skipped"],
                        )
                        changed = True
                        continue

                    fill_price = bid
                    quantity_per_leg = float(order.quantity_troy_ounces) / 2.0
                    entry_time = _db_time(event_time)
                    entry_timestamp = event_time.isoformat().replace("+00:00", "Z")
                    first_trade = Trade(
                        agent=AgentName.XAUUSD,
                        symbol="XAUUSD",
                        trade_type=TradeType.SELL,
                        quantity=quantity_per_leg,
                        entry_price=fill_price,
                        stop_loss=order.stop_loss,
                        take_profit=order.take_profit,
                        pnl=0.0,
                        status="OPEN",
                        created_at=entry_time,
                        data_source="OANDA",
                        entry_data_timestamp=entry_timestamp,
                    )
                    second_trade = Trade(
                        agent=AgentName.XAUUSD,
                        symbol="XAUUSD",
                        trade_type=TradeType.SELL,
                        quantity=quantity_per_leg,
                        entry_price=fill_price,
                        stop_loss=order.stop_loss,
                        take_profit=order.take_profit_2,
                        pnl=0.0,
                        status="OPEN",
                        created_at=entry_time,
                        data_source="OANDA",
                        entry_data_timestamp=entry_timestamp,
                    )
                    db.add_all((first_trade, second_trade))
                    db.flush()
                    order.first_trade_id = first_trade.id
                    order.second_trade_id = second_trade.id
                    order.fill_price = fill_price
                    order.filled_at = entry_time
                    order.status = "FILLED"
                    order.last_reason = (
                        "Filled at the actual fresh OANDA bid; no price was inferred "
                        "from the requested limit"
                    )
                    summary["filled_order_ids"].append(order.id)
                    summary["filled_trade_ids"].extend(
                        (first_trade.id, second_trade.id)
                    )
                    changed = True

        if changed:
            db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc, OrderError):
            raise
        raise OrderError("Could not process paper limit orders atomically") from exc
    return summary


def manual_order_for_trade(db, trade_id) -> Optional[PaperLimitOrder]:
    """Return the durable manual parent owning either Trade leg, if any."""
    try:
        key = int(trade_id)
    except (TypeError, ValueError, OverflowError):
        return None
    return (
        db.query(PaperLimitOrder)
        .filter(
            or_(
                PaperLimitOrder.first_trade_id == key,
                PaperLimitOrder.second_trade_id == key,
            )
        )
        .one_or_none()
    )


def manual_holding_intent(order: PaperLimitOrder) -> dict[str, Any]:
    """Explicit strategy-managed intent for a manual Gold session override."""
    return {
        "manual_order": True,
        "session_override": True,
        "holding_mode": "SL_TP_ROLLOVER",
        "max_hold_minutes": None,
        "allow_overnight": False,
        "reason": (
            "User-selected manual XAUUSD paper order; bypass only the normal "
            "London signal-session entry gate. Stops and targets manage the "
            "position without an elapsed-time exit; close by the UTC session "
            "cutoff or New York rollover wind-down."
        ),
        "order_id": getattr(order, "id", None),
        "origin": "paper_manual",
    }