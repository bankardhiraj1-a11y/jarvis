"""Provider-quote processing helpers for manual paper orders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from models import AgentName, ManualPaperOrder, Trade, TradeType
from trading.charges import ChargeInputError, calculate_charges
from trading.live_paper import (
    build_long_option_paper_entry,
    encode_option_contract,
    parse_option_contract,
    provider_side_price,
)
from trading.manual_paper_orders import (
    _GOLD_ENTRY_BUFFER_MINUTES,
    _GOLD_MAX_RISK,
    _INDIA_CUTOFF,
    _INDIA_MAX_RISK,
    _IST,
    _MAX_AGE_SECONDS,
    _UTC,
    ManualOrderError,
    OrderError,
    _as_utc,
    _db_time,
    _gold_hard_closing_deadline,
    _india_cutoff,
    _leg_specs,
    _positive,
    _positive_or_none,
    _validate_targets,
    _save_order,
    serialize_manual_order,
)


def _quote_event_time(quote: Any, now_utc: datetime) -> tuple[Optional[datetime], Optional[str]]:
    if not isinstance(quote, dict):
        return None, "No provider quote is available"
    if quote.get("stale") is True or quote.get("timestamp_basis") == "receipt":
        return None, "Quote is stale or lacks provider-event provenance"
    if quote.get("status") not in (None, "ok", "success", "live"):
        return None, "Provider quote status is not executable"
    raw_time = quote.get("provider_timestamp") or quote.get("timestamp")
    try:
        event_time = _as_utc(raw_time, "provider timestamp")
    except OrderError:
        return None, "Quote has no valid provider timestamp"
    age = (now_utc - event_time).total_seconds()
    if age < 0 or age > _MAX_AGE_SECONDS:
        return None, "Quote is stale or timestamped in the future"
    bid = _positive_or_none(quote.get("bid", quote.get("top_bid_price")))
    ask = _positive_or_none(quote.get("ask", quote.get("top_ask_price")))
    if bid is None or ask is None or ask < bid:
        return None, "Quote must contain a valid, uncrossed provider bid and ask"
    return event_time, None


def _quote_error_for_order(order: ManualPaperOrder, quote: dict[str, Any]) -> Optional[str]:
    source = str(quote.get("source") or "").strip().upper()
    symbol = str(quote.get("symbol") or "").strip().upper()
    if order.market == "GOLD":
        if source != "OANDA":
            return "XAUUSD fill requires an OANDA quote"
        if quote.get("instrument") != "XAU_USD":
            return "OANDA quote is not the XAU_USD instrument"
        if str(quote.get("environment") or "").lower() not in {"practice", "live"}:
            return "OANDA environment is not verified"
        if quote.get("tradeable") is not True:
            return "XAUUSD instrument is not explicitly tradeable"
    else:
        if source != "DHAN":
            return "Indian-market fills require a Dhan provider quote"
        if quote.get("market_session_open") is False:
            return "Indian market session is closed"
        if quote.get("entry_blocked_reason") not in (None, ""):
            return "Indian-market entry is blocked by the current provider or session policy"
        if symbol != order.symbol:
            return "Dhan quote does not match the requested underlying"
    return None


def _option_lot_and_contract(
    order: ManualPaperOrder, quote: dict[str, Any]
) -> tuple[Optional[int], Optional[str]]:
    contract = quote.get("contract")
    if not isinstance(contract, (dict, str)):
        return None, "Option quote has no verified contract metadata"
    lot_size = quote.get("lot_size")
    if isinstance(lot_size, bool) or not isinstance(lot_size, int) or lot_size <= 0:
        return None, "Option quote has no verified positive integer lot_size"
    details = contract if isinstance(contract, dict) else {}
    identity = details.get("security_id", details.get("id", quote.get("security_id")))
    try:
        identity = int(identity)
    except (TypeError, ValueError, OverflowError):
        identity = 0
    if identity <= 0:
        return None, "Option contract metadata has no real provider security ID"
    quote_identity = quote.get("security_id")
    if quote_identity is not None:
        try:
            if int(quote_identity) != identity:
                return None, "Option quote security ID does not match verified contract metadata"
        except (TypeError, ValueError, OverflowError):
            return None, "Option quote security ID is invalid"
    symbol = str(
        details.get("underlying_symbol")
        or details.get("underlying")
        or details.get("symbol")
        or quote.get("symbol")
        or ""
    ).strip().upper()
    if symbol != order.symbol:
        return None, "Option contract metadata does not match the requested underlying"
    contract_identity = parse_option_contract(contract) if isinstance(contract, str) else None
    values = {
        "strike": details.get("strike", quote.get("strike")),
        "option_type": details.get("option_type", quote.get("option_type")),
        "expiry": details.get("expiry", quote.get("expiry")),
    }
    if contract_identity:
        values = {
            key: value if value is not None else contract_identity[key]
            for key, value in values.items()
        }
    try:
        encoded = encode_option_contract(
            values["strike"], str(values["option_type"] or "").upper(),
            str(values["expiry"]),
        )
    except (TypeError, ValueError):
        return None, "Option contract metadata is incomplete or invalid"
    parsed = parse_option_contract(encoded)
    if (
        parsed is None
        or parsed["strike"] != float(order.strike)
        or parsed["option_type"] != order.option_type
        or parsed["expiry"] != order.expiry
    ):
        return None, "Real option contract metadata differs from the requested contract"
    exchange = str(
        details.get("exchange")
        or details.get("exchange_segment")
        or details.get("segment")
        or quote.get("exchange")
        or quote.get("exchange_segment")
        or quote.get("segment")
        or ""
    ).upper()
    expected = "BSE" if order.symbol == "SENSEX" else "NSE"
    if exchange and not (
        exchange == expected or exchange.startswith(expected + "_")
    ):
        return None, "Option contract is listed on an unexpected exchange"
    if not exchange:
        return None, "Option contract metadata has no exchange identity"
    return lot_size, None


def _triggered(order: ManualPaperOrder, bid: float, ask: float) -> bool:
    if order.order_type == "MARKET":
        return True
    limit = float(order.limit_price)
    if order.order_type == "LIMIT":
        return ask <= limit if order.side == "BUY" else bid >= limit
    return ask >= limit if order.side == "BUY" else bid <= limit


def _charge_estimate(
    order: ManualPaperOrder, entry: float, exit_price: float, quantity: float,
    event_time: datetime,
) -> Optional[float]:
    if order.market == "GOLD":
        return None
    request = {
        "market": "INDIA",
        "product": "index_options" if order.market == "OPTIONS" else "equity_intraday",
        "exchange": "BSE" if order.market == "OPTIONS" and order.symbol == "SENSEX" else "NSE",
        "symbol": order.symbol,
        "side": order.side,
        "quantity": quantity,
        "entry_price": entry,
        "exit_price": exit_price,
        "entry_orders": 1,
        "exit_orders": 1,
        "entry_time": event_time.isoformat(),
        "exit_time": (event_time + timedelta(minutes=1)).isoformat(),
    }
    try:
        result = calculate_charges(request)
    except (ChargeInputError, TypeError, ValueError):
        return None
    if not result.get("complete") or result.get("total_additional_charges") is None:
        return None
    return float(result["total_additional_charges"])


def _make_trades(
    order: ManualPaperOrder,
    quote: dict[str, Any],
    event_time: datetime,
    fill_price: float,
    lot_size: Optional[int],
) -> tuple[list[Trade], Optional[str]]:
    bid = _positive_or_none(quote.get("bid", quote.get("top_bid_price")))
    ask = _positive_or_none(quote.get("ask", quote.get("top_ask_price")))
    if bid is None or ask is None:
        return [], "Provider bid/ask is unavailable"
    _validate_targets(
        order.side, fill_price, float(order.stop_loss),
        float(order.take_profit),
        float(order.take_profit_2) if order.take_profit_2 is not None else None,
    )
    exit_side = "SELL" if order.side == "BUY" else "BUY"
    current_exit = bid if exit_side == "SELL" else ask
    if order.side == "BUY" and current_exit <= float(order.stop_loss):
        return [], "Current executable bid is already at or below the requested stop"
    if order.side == "SELL" and current_exit >= float(order.stop_loss):
        return [], "Current executable ask is already at or above the requested stop"

    specs = _leg_specs(order)
    total_units = (
        float(order.quantity_troy_ounces)
        if order.market == "GOLD"
        else float(order.quantity) * int(lot_size or 1)
        if order.market == "OPTIONS"
        else float(order.quantity)
    )
    if order.market == "GOLD":
        cap, currency = _GOLD_MAX_RISK, "USD"
    else:
        cap, currency = _INDIA_MAX_RISK, "INR"
    actual_risk = abs(fill_price - float(order.stop_loss)) * total_units
    if not math.isfinite(actual_risk):
        return [], "Actual-fill stop risk is not finite"
    if order.market == "GOLD" and actual_risk > cap:
        return [], f"Actual-fill planned risk exceeds {currency} {cap:g}"

    agent = (
        AgentName.XAUUSD if order.market == "GOLD"
        else AgentName.STOCKS if order.market == "STOCKS"
        else AgentName.SENSEX_OPTIONS_SCALPING if order.symbol == "SENSEX"
        else AgentName.OPTIONS
    )
    stamp = event_time.isoformat().replace("+00:00", "Z")
    trades: list[Trade] = []
    indian_stop_fees = 0.0
    indian_round_trip_fees = 0.0
    for _, leg_size, target in specs:
        quantity = leg_size * int(lot_size or 1) if order.market == "OPTIONS" else leg_size
        fee = _charge_estimate(order, fill_price, target, quantity, event_time)
        if order.market != "GOLD":
            stop_fee = _charge_estimate(
                order, fill_price, float(order.stop_loss), quantity, event_time
            )
            gross_target = (
                (target - fill_price) * quantity
                if order.side == "BUY" else (fill_price - target) * quantity
            )
            if fee is None or stop_fee is None:
                return [], "Verified complete Indian-market charges are unavailable"
            if gross_target <= fee:
                return [], "Target is not economically positive after estimated charges"
            indian_round_trip_fees += fee
            indian_stop_fees += stop_fee

        option_contract = None
        if order.market == "OPTIONS":
            option_contract = encode_option_contract(
                order.strike, order.option_type, order.expiry
            )
            helper_quote = dict(quote)
            helper_quote.update({
                "option_type": order.option_type,
                "strike": order.strike,
                "expiry": order.expiry,
                "bid": bid,
                "ask": ask,
                "last_price": quote.get("last_price", quote.get("close", ask)),
                "timestamp": event_time.isoformat(),
                "timestamp_basis": "exchange",
            })
            signal = "BUY" if order.option_type == "CE" else "SELL"
            prepared = build_long_option_paper_entry(
                signal,
                helper_quote,
                quantity,
                fill_price - float(order.stop_loss),
                target - fill_price,
            )
            if (
                prepared is None
                or abs(float(prepared["entry_price"]) - fill_price) > 1e-9
                or abs(float(prepared["stop_loss"]) - float(order.stop_loss)) > 1e-9
                or abs(float(prepared["take_profit"]) - target) > 1e-9
            ):
                return [], "Long option paper-entry validation rejected the actual quote"
            data_source = "DHAN"
            option_price = fill_price
        else:
            data_source = "OANDA" if order.market == "GOLD" else "DHAN"
            option_price = None
        trades.append(Trade(
            agent=agent,
            symbol=order.symbol,
            trade_type=TradeType(order.side),
            quantity=quantity,
            entry_price=fill_price,
            stop_loss=float(order.stop_loss),
            take_profit=target,
            pnl=0.0,
            status="OPEN",
            created_at=_db_time(event_time),
            option_strike=option_contract,
            option_price=option_price,
            data_source=data_source,
            entry_data_timestamp=stamp,
        ))
    if order.market != "GOLD" and actual_risk + indian_stop_fees > cap:
        return [], (
            f"Actual-fill stop risk including complete estimated stop charges "
            f"exceeds {currency} {cap:g}"
        )
    available_capital = quote.get("_available_capital")
    if available_capital is not None:
        capital = _positive_or_none(available_capital)
        required = fill_price * total_units + indian_round_trip_fees
        if capital is None or required > capital:
            return [], (
                "Order not filled because available capital is below notional "
                "plus the complete estimated round-trip charge buffer"
            )
    return trades, None


def process_manual_orders(
    db,
    resolve_quote,
    now=None,
    gold_entries_today=0,
    available_capital=None,
) -> dict[str, Any]:
    """Expire or atomically fill pending parents using their actual provider quote."""
    now_utc = _as_utc(now or datetime.now(_UTC), "now")
    if (
        isinstance(gold_entries_today, bool)
        or not isinstance(gold_entries_today, int)
        or gold_entries_today < 0
    ):
        raise OrderError("gold_entries_today must be a non-negative integer")
    capital_provider = available_capital
    if available_capital is not None and not callable(available_capital):
        capital = _positive(available_capital, "available_capital")
        capital_provider = lambda _order: capital
    pending_ids = [
        order_id for (order_id,) in db.query(ManualPaperOrder.id)
        .filter(ManualPaperOrder.status == "PENDING")
        .order_by(ManualPaperOrder.id.asc()).all()
    ]
    summary: dict[str, Any] = {
        "filled_order_ids": [],
        "filled_trade_ids": [],
        "filled_orders": [],
        "expired_order_ids": [],
        "skipped": [],
        "exceptions": [],
    }
    accepted_gold_entries = gold_entries_today

    def skipped(order: ManualPaperOrder, reason: str) -> None:
        order.last_reason = reason[:500]
        summary["skipped"].append({"order_id": order.id, "reason": reason})
        if not _save_order(db, order):
            summary["exceptions"].append({
                "order_id": order.id,
                "reason": "Could not persist order state because it changed concurrently",
            })

    for order_id in pending_ids:
        order = db.get(ManualPaperOrder, order_id)
        if order is None or str(order.status).upper() != "PENDING":
            continue
        if now_utc >= _as_utc(order.expires_at):
            order.status = "EXPIRED"
            order.last_reason = "Expired; manual paper orders never carry overnight"
            if _save_order(db, order):
                summary["expired_order_ids"].append(order.id)
            else:
                summary["exceptions"].append({
                    "order_id": order.id,
                    "reason": "Could not expire order because it changed concurrently",
                })
            continue
        if (
            order.market in {"STOCKS", "OPTIONS"}
            and now_utc.astimezone(_IST).time().replace(tzinfo=None) >= _INDIA_CUTOFF
        ):
            skipped(order, "Indian-market entries are disabled at or after 15:20 IST")
            continue
        try:
            quote = resolve_quote(order)
        except Exception:
            skipped(order, "Provider quote resolution failed")
            summary["exceptions"].append({
                "order_id": order.id, "reason": "Provider quote resolution failed",
            })
            continue
        if not isinstance(quote, dict):
            skipped(order, "No provider quote is available")
            continue
        if order.market != "GOLD" and capital_provider is not None:
            try:
                quote_capital = _positive(
                    capital_provider(order), "available_capital"
                )
            except Exception:
                skipped(order, "Available capital is invalid or unavailable")
                continue
            quote = dict(quote)
            quote["_available_capital"] = quote_capital
        quote = dict(quote)
        if "bid" not in quote:
            quote["bid"] = quote.get("top_bid_price")
        if "ask" not in quote:
            quote["ask"] = quote.get("top_ask_price")
        event_time, quote_error = _quote_event_time(quote, now_utc)
        if quote_error:
            skipped(order, quote_error)
            continue
        quote["timestamp"] = event_time.isoformat()
        source_error = _quote_error_for_order(order, quote)
        if source_error:
            skipped(order, source_error)
            continue
        if event_time < _as_utc(order.created_at):
            skipped(order, "Quote provider event predates order creation")
            continue
        if order.market in {"STOCKS", "OPTIONS"}:
            cutoff = _india_cutoff(event_time.astimezone(_IST).date())
            if event_time.astimezone(_IST).time().replace(tzinfo=None) >= _INDIA_CUTOFF:
                skipped(order, "Indian-market quote is at or after the 15:20 IST entry cutoff")
                continue
            if event_time + timedelta(minutes=order.max_hold_minutes) > cutoff:
                skipped(order, "Full maximum hold does not fit before the 15:20 IST cutoff")
                continue

        lot_size = None
        if order.market == "OPTIONS":
            lot_size, contract_error = _option_lot_and_contract(order, quote)
            if contract_error:
                skipped(order, contract_error)
                continue
        bid = _positive_or_none(quote.get("bid", quote.get("top_bid_price")))
        ask = _positive_or_none(quote.get("ask", quote.get("top_ask_price")))
        if bid is None or ask is None:
            skipped(order, "Provider quote is missing executable bid/ask")
            continue
        if not _triggered(order, bid, ask):
            skipped(order, f"Fresh provider quote has not triggered the {order.order_type} order")
            continue
        if order.market == "GOLD":
            required_entries = 2 if order.take_profit_2 is not None else 1
            if accepted_gold_entries + required_entries > 3:
                skipped(order, "Filling all gold target legs would exceed the three-entry daily cap")
                continue

        open_trade = db.query(Trade).filter(
            Trade.symbol == order.symbol,
            Trade.status.in_(("OPEN", "ACTIVE")),
        ).first()
        if open_trade is not None:
            skipped(order, f"An OPEN {order.symbol} position already exists")
            continue
        fill_price = provider_side_price(quote, order.side)
        if fill_price is None:
            skipped(order, "No fresh executable provider-side fill price is available")
            continue
        try:
            trades, fill_error = _make_trades(
                order, quote, event_time, fill_price, lot_size
            )
        except (TypeError, ValueError, OverflowError):
            trades, fill_error = [], "Provider contract could not be validated for paper entry"
        if fill_error:
            skipped(order, fill_error)
            continue
        if (
            order.market == "GOLD"
            and event_time + timedelta(minutes=_GOLD_ENTRY_BUFFER_MINUTES)
            > _gold_hard_closing_deadline(event_time)
        ):
            skipped(
                order,
                "Conservative 25-minute entry buffer does not fit before the XAUUSD safe cutoff",
            )
            continue

        order.option_lot_size = lot_size
        order.fill_price = fill_price
        order.filled_at = _db_time(event_time)
        order.status = "FILLED"
        order.last_reason = "Filled at the actual fresh provider-side price"
        db.add_all(trades)
        if trades:
            order.first_trade_id = None
            order.second_trade_id = None
            try:
                db.flush()
                order.first_trade_id = trades[0].id
                order.second_trade_id = trades[1].id if len(trades) > 1 else None
                db.commit()
            except StaleDataError:
                db.rollback()
                summary["exceptions"].append({
                    "order_id": order.id,
                    "reason": "Order changed concurrently; all fill legs were rolled back",
                })
                continue
            except Exception:
                db.rollback()
                summary["exceptions"].append({
                    "order_id": order.id,
                    "reason": "Could not commit provider fill; all fill legs were rolled back",
                })
                continue
        summary["filled_order_ids"].append(order.id)
        summary["filled_orders"].append(serialize_manual_order(order, db))
        summary["filled_trade_ids"].extend(trade.id for trade in trades)
        if order.market == "GOLD":
            accepted_gold_entries += len(trades)
    return summary