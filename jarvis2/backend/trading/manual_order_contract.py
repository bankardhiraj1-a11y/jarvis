"""Request identity, idempotent persistence, and response contract helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from models import ManualPaperOrder
from trading.manual_paper_orders import (
    OrderError,
    _UTC,
    _as_utc,
    _db_time,
    _validated_payload,
)


_MANUAL_REQUEST_FIELDS = (
    "client_order_id",
    "market",
    "symbol",
    "side",
    "order_type",
    "limit_price",
    "stop_loss",
    "take_profit",
    "take_profit_2",
    "quantity",
    "quantity_troy_ounces",
    "quantity_lots",
    "option_type",
    "strike",
    "expiry",
    "max_hold_minutes",
)


def _client_order_key(payload: dict[str, Any]) -> str:
    import uuid

    value = payload.get("client_order_id")
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str):
        raise OrderError("client_order_id must be a string")
    value = value.strip()
    if not value or len(value) > 80:
        raise OrderError("client_order_id must contain 1 to 80 characters")
    return value


def _matches_manual_request(
    order: ManualPaperOrder, values: dict[str, Any]
) -> bool:
    return all(
        getattr(order, field) == values[field]
        for field in _MANUAL_REQUEST_FIELDS
    )


def _matching_client_order(db, client_order_id: str, request: dict[str, Any]):
    winner = db.query(ManualPaperOrder).filter(
        ManualPaperOrder.client_order_id == client_order_id
    ).one_or_none()
    if winner is None:
        return None
    try:
        values = _validated_payload(
            request, _as_utc(winner.created_at, "existing created_at")
        )
    except OrderError:
        return None
    return winner if _matches_manual_request(winner, values) else None


def create_manual_order(db, payload, now=None) -> ManualPaperOrder:
    """Persist/replay an idempotent manual paper order by client key."""
    if not isinstance(payload, dict):
        raise OrderError("Order payload must be an object")
    request = dict(payload)
    client_order_id = _client_order_key(request)
    request["client_order_id"] = client_order_id
    now_utc = _as_utc(now or datetime.now(_UTC), "now")
    existing = db.query(ManualPaperOrder).filter(
        ManualPaperOrder.client_order_id == client_order_id
    ).one_or_none()
    if existing is not None:
        try:
            replay_values = _validated_payload(
                request, _as_utc(existing.created_at, "existing created_at")
            )
        except OrderError:
            raise OrderError(
                "client_order_id already exists for a different manual order"
            ) from None
        if _matches_manual_request(existing, replay_values):
            return existing
        raise OrderError("client_order_id already exists for a different manual order")

    values = _validated_payload(request, now_utc)
    order = ManualPaperOrder(
        **values,
        status="PENDING",
        created_at=_db_time(now_utc),
        last_reason="Waiting for a fresh, executable provider quote",
    )
    db.add(order)
    try:
        db.commit()
        return order
    except IntegrityError:
        db.rollback()
        winner = _matching_client_order(db, client_order_id, request)
        if winner is not None:
            return winner
        raise OrderError(
            "client_order_id already exists for a different manual order"
        ) from None
    except Exception:
        db.rollback()
        winner = _matching_client_order(db, client_order_id, request)
        if winner is not None:
            return winner
        raise OrderError("Could not persist manual paper order") from None