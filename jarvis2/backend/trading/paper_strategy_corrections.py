"""Audited, counterfactual corrections for legacy manual Gold PAPER exits.

This service never contacts a broker or creates a new trade. It only replays
provider observations supplied by its caller against the two existing legs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Optional

from models import PaperLimitOrder, PaperTradeCorrection, Trade, TradeType


_UTC = timezone.utc
_MAX_CURRENT_QUOTE_AGE_SECONDS = 15.0
_REPLAY_NOTE = (
    "Sampled provider observations; unobserved intratick movements unknown. "
    "Historical samples may lack tradeability flags and are price evidence, not verified executions. "
    "This is a strategy-corrected PAPER simulation, not uninterrupted forward results."
)
_AUDIT_LABEL = "Strategy-corrected PAPER; prior timed close retained"


class PaperTradeCorrectionError(ValueError):
    """Evidence or state is insufficient to correct a legacy PAPER exit."""


def _as_utc(value: Any, label: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            raise PaperTradeCorrectionError(f"{label} must be a valid timestamp") from None
    if not isinstance(value, datetime):
        raise PaperTradeCorrectionError(f"{label} must be a valid timestamp")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=_UTC)
    try:
        return value.astimezone(_UTC)
    except (OverflowError, ValueError):
        raise PaperTradeCorrectionError(f"{label} must be a valid timestamp") from None


def _db_time(value: datetime) -> datetime:
    return value.astimezone(_UTC).replace(tzinfo=None)


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return _as_utc(value, "timestamp").isoformat().replace("+00:00", "Z")


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise PaperTradeCorrectionError(f"{label} must be a finite positive price")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise PaperTradeCorrectionError(f"{label} must be a finite positive price") from None
    if not math.isfinite(number) or number <= 0:
        raise PaperTradeCorrectionError(f"{label} must be a finite positive price")
    return number


def _quote_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (tuple, list)):
        if len(value) == 2 and isinstance(value[1], dict):
            quote = dict(value[1])
            quote.setdefault("provider_timestamp", value[0])
            return quote
        if len(value) == 6:
            timestamp, bid, ask, source, environment, tradeable = value
            return {
                "provider_timestamp": timestamp,
                "bid": bid,
                "ask": ask,
                "source": source,
                "environment": environment,
                "tradeable": tradeable,
            }
    raise PaperTradeCorrectionError(
        "Each replay observation must be a quote object or a supported quote tuple"
    )


def _validated_quote(value: Any, *, now_utc: Optional[datetime] = None) -> dict[str, Any]:
    quote = _quote_mapping(value)
    if str(quote.get("source") or "").strip().upper() != "OANDA":
        raise PaperTradeCorrectionError("Replay quote provenance must be OANDA")
    environment = str(quote.get("environment") or "").strip().lower()
    if environment not in {"practice", "live"}:
        raise PaperTradeCorrectionError("OANDA quote environment must be practice or live")
    if quote.get("tradeable") is False or (
        now_utc is not None and quote.get("tradeable") is not True
    ):
        raise PaperTradeCorrectionError("OANDA quote must be explicitly tradeable")
    if quote.get("stale") is True or quote.get("timestamp_basis") == "receipt":
        raise PaperTradeCorrectionError("Quote is stale or has receipt-time provenance")
    if quote.get("status") not in (None, "ok", "success", "live"):
        raise PaperTradeCorrectionError("OANDA quote status is not successful")
    if quote.get("age_seconds") is not None:
        try:
            age = float(quote["age_seconds"])
        except (TypeError, ValueError, OverflowError):
            raise PaperTradeCorrectionError("Quote age_seconds is invalid") from None
        if not math.isfinite(age) or age < 0 or age > _MAX_CURRENT_QUOTE_AGE_SECONDS:
            raise PaperTradeCorrectionError("Quote was not fresh when recorded")

    timestamp = quote.get("provider_timestamp") or quote.get("timestamp")
    event_time = _as_utc(timestamp, "OANDA provider timestamp")
    bid = _positive(quote.get("bid"), "OANDA bid")
    ask = _positive(quote.get("ask"), "OANDA ask")
    if ask < bid:
        raise PaperTradeCorrectionError("OANDA quote is crossed (ask is below bid)")
    if now_utc is not None:
        age = (now_utc - event_time).total_seconds()
        if age < 0:
            raise PaperTradeCorrectionError("Current OANDA quote timestamp is in the future")
        if age > _MAX_CURRENT_QUOTE_AGE_SECONDS:
            raise PaperTradeCorrectionError("Current OANDA quote is stale")
    return {
        "quote": quote,
        "event_time": event_time,
        "bid": bid,
        "ask": ask,
        "environment": environment,
    }


def _eligible_original_close(trade: Trade) -> tuple[datetime, datetime]:
    if str(trade.status or "").upper() != "CLOSED":
        raise PaperTradeCorrectionError(f"Trade {trade.id} is not an original CLOSED leg")
    if (
        str(trade.symbol or "").upper() != "XAUUSD"
        or str(getattr(trade.agent, "value", trade.agent)).upper() != "XAUUSD"
        or str(trade.data_source or "").upper() != "OANDA"
    ):
        raise PaperTradeCorrectionError(f"Trade {trade.id} is not an OANDA XAUUSD PAPER leg")
    if str(getattr(trade.trade_type, "value", trade.trade_type)).upper() != "SELL":
        raise PaperTradeCorrectionError(f"Trade {trade.id} is not a SELL leg")
    if not trade.entry_data_timestamp or not trade.exit_data_timestamp:
        raise PaperTradeCorrectionError(
            f"Trade {trade.id} lacks real OANDA entry/exit timestamps"
        )

    entry_event = _as_utc(trade.entry_data_timestamp, "Original entry provider timestamp")
    exit_event = _as_utc(trade.exit_data_timestamp, "Original exit provider timestamp")
    if trade.created_at is None or trade.closed_at is None:
        raise PaperTradeCorrectionError(f"Trade {trade.id} lacks its original entry/close time")
    entry_time = _as_utc(trade.created_at, "Original entry time")
    closed_at = _as_utc(trade.closed_at, "Original closed_at")
    exit_price = _positive(trade.exit_price, "Original exit price")
    stop = _positive(trade.stop_loss, "Original stop loss")
    target = _positive(trade.take_profit, "Original take profit")

    if entry_event < entry_time - timedelta(seconds=15) or entry_event > entry_time + timedelta(seconds=15):
        raise PaperTradeCorrectionError(f"Trade {trade.id} entry time is not backed by its provider event")
    if exit_event < entry_event or exit_event > closed_at:
        raise PaperTradeCorrectionError(f"Trade {trade.id} original exit timestamp is inconsistent")
    if closed_at - entry_time < timedelta(minutes=25):
        raise PaperTradeCorrectionError(
            f"Trade {trade.id} does not show the legacy 25-minute time-exit pattern"
        )
    if not target < exit_price < stop:
        raise PaperTradeCorrectionError(
            f"Trade {trade.id} original close was not strictly between its SELL stop and target"
        )
    return entry_event, exit_event


def _entry_snapshot(trade: Trade) -> dict[str, Any]:
    return {
        "agent": str(getattr(trade.agent, "value", trade.agent)),
        "symbol": trade.symbol,
        "trade_type": str(getattr(trade.trade_type, "value", trade.trade_type)),
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "created_at": _iso(trade.created_at),
        "data_source": trade.data_source,
        "entry_data_timestamp": trade.entry_data_timestamp,
        "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit,
    }


def _audit_summary(audits: list[PaperTradeCorrection]) -> dict[str, Any]:
    ordered = sorted(audits, key=lambda audit: audit.trade_id)
    resumed = [audit.trade_id for audit in ordered if audit.corrected_status == "OPEN"]
    replay_closed = [audit.trade_id for audit in ordered if audit.corrected_status == "CLOSED"]
    return {
        "label": _AUDIT_LABEL,
        "correction_type": "strategy-corrected PAPER simulation",
        "corrected_trade_ids": [audit.trade_id for audit in ordered],
        "resumed_trade_ids": resumed,
        "replay_closed_trade_ids": replay_closed,
        "reason": {audit.trade_id: audit.correction_reason for audit in ordered},
        "audit_ids": [audit.id for audit in ordered],
        "replay_sample_count": {
            audit.trade_id: audit.replay_sample_count for audit in ordered
        },
        "replay_data_note": _REPLAY_NOTE,
        "uninterrupted_forward_results": False,
    }


def correct_time_exit(
    db,
    order_id,
    request_id,
    observations,
    current_quote,
    now=None,
) -> dict[str, Any]:
    """Correct a qualifying legacy timed close using only supplied OANDA evidence.

    Each original leg remains the same trade with unchanged entry fields. The
    former close is copied to an immutable audit row before its state is revised.
    """
    try:
        key = int(order_id)
    except (TypeError, ValueError, OverflowError):
        raise PaperTradeCorrectionError("Paper limit order id must be an integer") from None
    request = str(request_id or "").strip()
    if not request or len(request) > 80:
        raise PaperTradeCorrectionError("request_id must contain 1 to 80 characters")
    now_utc = _as_utc(now or datetime.now(_UTC), "now")

    try:
        order = (
            db.query(PaperLimitOrder)
            .filter(PaperLimitOrder.id == key)
            .with_for_update()
            .one_or_none()
        )
        if order is None:
            raise PaperTradeCorrectionError("Legacy paper limit order was not found")
        if (
            str(order.status or "").upper() != "FILLED"
            or str(order.origin or "").lower() != "paper_manual"
            or str(order.symbol or "").upper() != "XAUUSD"
            or str(order.side or "").upper() != "SELL"
            or order.manual_order is not True
        ):
            raise PaperTradeCorrectionError(
                "Only a filled legacy manual XAUUSD SELL PAPER order can be corrected"
            )

        trade_ids = [order.first_trade_id, order.second_trade_id]
        if any(trade_id is None for trade_id in trade_ids) or len(set(trade_ids)) != 2:
            raise PaperTradeCorrectionError("Filled order does not have two distinct trade legs")
        trades = (
            db.query(Trade)
            .filter(Trade.id.in_(trade_ids))
            .order_by(Trade.id.asc())
            .with_for_update()
            .all()
        )
        if len(trades) != 2:
            raise PaperTradeCorrectionError("Both original paper trade legs must exist")
        by_id = {trade.id: trade for trade in trades}

        existing_request = (
            db.query(PaperTradeCorrection)
            .filter(PaperTradeCorrection.request_id == request)
            .order_by(PaperTradeCorrection.trade_id.asc())
            .all()
        )
        if existing_request:
            if (
                any(audit.order_id != order.id for audit in existing_request)
                or {audit.trade_id for audit in existing_request} != set(trade_ids)
            ):
                raise PaperTradeCorrectionError(
                    "request_id was already used for a different correction"
                )
            db.rollback()
            return _audit_summary(existing_request)

        prior_audit = (
            db.query(PaperTradeCorrection)
            .filter(PaperTradeCorrection.trade_id.in_(trade_ids))
            .first()
        )
        if prior_audit is not None:
            raise PaperTradeCorrectionError(
                "An original leg already has a strategy-correction audit"
            )
        other_open = (
            db.query(Trade)
            .filter(
                Trade.symbol == "XAUUSD",
                Trade.status.in_(("OPEN", "ACTIVE")),
                Trade.id.notin_(trade_ids),
            )
            .with_for_update()
            .first()
        )
        if other_open is not None:
            raise PaperTradeCorrectionError(
                "Another OPEN XAUUSD trade exists outside this order's two legs"
            )

        current = _validated_quote(current_quote, now_utc=now_utc)
        try:
            supplied_observations = list(observations)
        except TypeError:
            raise PaperTradeCorrectionError(
                "Recorded OANDA observations must be a non-empty iterable"
            ) from None
        if not supplied_observations:
            raise PaperTradeCorrectionError(
                "No historical OANDA observations were supplied after the original close"
            )
        replay_quotes = [_validated_quote(item) for item in supplied_observations]
        for quote in replay_quotes:
            if quote["environment"] != current["environment"]:
                raise PaperTradeCorrectionError(
                    "Historical observations and current quote must use the same OANDA environment"
                )

        revision_at = _db_time(now_utc)
        audits: list[PaperTradeCorrection] = []
        for trade_id in trade_ids:
            trade = by_id[trade_id]
            _, original_exit_event = _eligible_original_close(trade)
            expected_target = (
                order.take_profit if trade_id == order.first_trade_id else order.take_profit_2
            )
            if (
                float(trade.entry_price) != float(order.fill_price)
                or float(trade.quantity) != float(order.quantity_troy_ounces) / 2.0
                or float(trade.stop_loss) != float(order.stop_loss)
                or float(trade.take_profit) != float(expected_target)
                or order.filled_at is None
                or abs(
                    (_as_utc(trade.created_at, "Original entry time")
                     - _as_utc(order.filled_at, "Original order fill time")).total_seconds()
                ) > 15
            ):
                raise PaperTradeCorrectionError(
                    f"Trade {trade.id} no longer matches its original parent fill and plan"
                )
            original_status = str(trade.status)
            original_exit_price = trade.exit_price
            original_closed_at = trade.closed_at
            original_exit_data_timestamp = trade.exit_data_timestamp
            original_pnl = trade.pnl
            original_entry_fields = _entry_snapshot(trade)
            samples = [
                quote
                for quote in replay_quotes
                if original_exit_event < quote["event_time"] <= current["event_time"]
            ]
            if not samples:
                raise PaperTradeCorrectionError(
                    f"No historical OANDA observations after trade {trade.id}'s original close"
                )
            samples.sort(key=lambda quote: quote["event_time"])
            # Current fresh quote is deliberately last, including when its event
            # timestamp ties a supplied sample.
            samples.append(current)

            trigger = None
            for sample in samples:
                ask = sample["ask"]
                if ask >= float(trade.stop_loss):
                    trigger = (sample, "stop_loss")
                    break
                if ask <= float(trade.take_profit):
                    trigger = (sample, "take_profit")
                    break

            if trigger is None:
                corrected_status = "OPEN"
                corrected_exit_price = None
                corrected_closed_at = None
                corrected_exit_timestamp = None
                reason = (
                    "Resumed PAPER leg after sampled observations showed no stop or "
                    "target trigger; prior timed close retained in audit"
                )
                trade.status = "OPEN"
                trade.exit_price = None
                trade.closed_at = None
                trade.exit_data_timestamp = None
                trade.pnl = None
            else:
                sample, trigger_kind = trigger
                corrected_status = "CLOSED"
                corrected_exit_price = sample["ask"]
                corrected_closed_at = _db_time(sample["event_time"])
                corrected_exit_timestamp = _iso(sample["event_time"])
                trigger_label = "stop loss" if trigger_kind == "stop_loss" else "take profit"
                reason = (
                    f"Counterfactual strategy-corrected PAPER close: first sampled "
                    f"OANDA ask triggered {trigger_label}; prior timed close retained"
                )
                trade.status = "CLOSED"
                trade.exit_price = corrected_exit_price
                trade.closed_at = corrected_closed_at
                trade.exit_data_timestamp = corrected_exit_timestamp
                # No fee/cost calculator is invoked or implied by this replay.
                trade.pnl = None

            audit = PaperTradeCorrection(
                request_id=request,
                order_id=order.id,
                trade_id=trade.id,
                original_status=original_status,
                original_exit_price=original_exit_price,
                original_closed_at=original_closed_at,
                original_exit_data_timestamp=original_exit_data_timestamp,
                original_pnl=original_pnl,
                original_entry_fields=original_entry_fields,
                revision_at=revision_at,
                replay_sample_count=len(samples),
                replay_data_note=_REPLAY_NOTE,
                corrected_status=corrected_status,
                corrected_exit_price=corrected_exit_price,
                corrected_closed_at=corrected_closed_at,
                corrected_exit_data_timestamp=corrected_exit_timestamp,
                correction_reason=reason,
            )
            audits.append(audit)
            db.add(audit)

        db.flush()
        db.commit()
        return _audit_summary(audits)
    except PaperTradeCorrectionError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise PaperTradeCorrectionError(
            "Could not apply the paper strategy correction atomically"
        ) from exc


def correction_for_trade(db, trade_id) -> Optional[dict[str, Any]]:
    """Serialize the retained original close and strategy-correction audit."""
    try:
        key = int(trade_id)
    except (TypeError, ValueError, OverflowError):
        return None
    audit = (
        db.query(PaperTradeCorrection)
        .filter(PaperTradeCorrection.trade_id == key)
        .order_by(PaperTradeCorrection.revision_at.desc(), PaperTradeCorrection.id.desc())
        .first()
    )
    if audit is None:
        return None
    return {
        "label": _AUDIT_LABEL,
        "replay_type": "sampled_provider_observation_counterfactual",
        "original_close": {
            "status": audit.original_status,
            "exit_price": audit.original_exit_price,
            "closed_at": _iso(audit.original_closed_at),
            "exit_data_timestamp": audit.original_exit_data_timestamp,
            "pnl": audit.original_pnl,
        },
        "original_entry_fields": audit.original_entry_fields,
        "corrected_at": _iso(audit.revision_at),
        "corrected_status": audit.corrected_status,
        "corrected_exit_price": audit.corrected_exit_price,
        "corrected_closed_at": _iso(audit.corrected_closed_at),
        "corrected_exit_data_timestamp": audit.corrected_exit_data_timestamp,
        "request_id": audit.request_id,
        "order_id": audit.order_id,
        "audit_id": audit.id,
        "replay_sample_count": audit.replay_sample_count,
        "replay_data_note": audit.replay_data_note,
        "reason": audit.correction_reason,
        "uninterrupted_forward_results": False,
    }