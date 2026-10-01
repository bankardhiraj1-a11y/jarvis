"""Preview-only trading charge estimates; this module never places orders."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import Any, Iterable
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit


AS_OF = "2026-10-01"
INR = "INR"
USD = "USD"
_PAISE = Decimal("0.01")
_ZERODHA_CALCULATOR = {
    "name": "Zerodha brokerage calculator",
    "url": "https://zerodha.com/brokerage-calculator/#tab-equities",
    "as_of": AS_OF,
    "scope": "Broker-reference estimates; not an invoice or a claim that the user has a Zerodha account",
}
_ZERODHA_CHARGES = {
    "name": "Zerodha brokerage charges and taxes",
    "url": "https://zerodha.com/charges/",
    "as_of": AS_OF,
    "scope": "Published broker schedule and statutory charge descriptions",
}
_FINANCE_ACT_2026 = {
    "name": "Government of India, Finance Act 2026 (Finance Bill PDF)",
    "url": "https://www.indiabudget.gov.in/doc/Finance_Bill.pdf",
    "as_of": AS_OF,
    "scope": "Clause 143 amends option-sale and option-exercise STT effective 2026-04-01",
}
_SOURCES = [_ZERODHA_CALCULATOR, _ZERODHA_CHARGES, _FINANCE_ACT_2026]


class ChargeInputError(ValueError):
    """Invalid preview input. Routes can translate this into an HTTP 400."""


def _decimal(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ChargeInputError(f"{name} must be a finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ChargeInputError(f"{name} must be a finite number") from None
    if not number.is_finite():
        raise ChargeInputError(f"{name} must be a finite number")
    try:
        finite_as_float = math.isfinite(float(number))
    except (OverflowError, ValueError):
        finite_as_float = False
    if not finite_as_float:
        raise ChargeInputError(f"{name} must be within the supported finite range")
    if positive and number <= 0:
        raise ChargeInputError(f"{name} must be greater than zero")
    return number


def _money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    rounded = value.quantize(_PAISE, rounding=ROUND_HALF_UP)
    result = float(rounded)
    if not math.isfinite(result):
        raise ChargeInputError("Calculated amount exceeds the supported finite range")
    return 0.0 if result == 0 else result


def _stamp_money(value: Decimal | None) -> float | None:
    """Zerodha's reference calculator displays stamp duty rounded to whole rupees."""
    if value is None:
        return None
    rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    result = float(rounded)
    if not math.isfinite(result):
        raise ChargeInputError("Calculated amount exceeds the supported finite range")
    return 0.0 if result == 0 else result


def _stt_money(value: Decimal | None) -> float | None:
    """Match Zerodha's paise intermediate and nearest-whole-rupee STT display."""
    if value is None:
        return None
    paise_value = value.quantize(_PAISE, rounding=ROUND_HALF_UP)
    rounded = paise_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    result = float(rounded)
    if not math.isfinite(result):
        raise ChargeInputError("Calculated amount exceeds the supported finite range")
    return 0.0 if result == 0 else result


def _positive_order_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ChargeInputError(f"{name} must be an integer greater than zero")
    return value


def _timestamp(value: Any, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ChargeInputError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ChargeInputError(f"{name} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        raise ChargeInputError(f"{name} must include a timezone")
    return parsed


def _add_component(
    components: list[dict[str, Any]],
    *,
    code: str,
    label: str,
    amount: Decimal | None,
    currency: str,
    basis: str,
    additional: bool = True,
    status: str | None = None,
) -> None:
    components.append({
        "code": code,
        "label": label,
        "amount": _money(amount),
        "currency": currency,
        "status": status or ("known" if amount is not None else "unknown"),
        "basis": basis,
        "additional": additional,
    })


def _side_values(
    *,
    side: str,
    entry_price: Decimal,
    exit_price: Decimal | None,
    quantity: Decimal,
    entry_orders: int,
    exit_orders: int,
) -> list[dict[str, Any]]:
    entry_trade_side = side
    exit_trade_side = "SELL" if side == "BUY" else "BUY"
    return [
        {
            "name": "entry",
            "price": entry_price,
            "trade_side": entry_trade_side,
            "orders": entry_orders,
            "known": True,
        },
        {
            "name": "exit",
            "price": exit_price,
            "trade_side": exit_trade_side,
            "orders": exit_orders,
            "known": exit_price is not None,
        },
    ]


def _india_components(
    *,
    product: str,
    exchange: str,
    sides: list[dict[str, Any]],
    quantity: Decimal,
    symbol: str | None,
    dp_scrips: int | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    components: list[dict[str, Any]] = []
    notes: list[str] = []

    brokerage_rate = Decimal("0.0003")  # 0.03% per executed order, capped at ₹20/order.
    sebi_rate = Decimal("0.000001")  # ₹10 per crore.
    if product == "equity_intraday":
        stt_rate = Decimal("0.00025")
        exchange_rates = {"NSE": Decimal("0.0000307"), "BSE": None}
        stamp_rate = Decimal("0.00003")
    elif product == "equity_delivery":
        stt_rate = Decimal("0.001")
        exchange_rates = {"NSE": Decimal("0.0000307"), "BSE": None}
        stamp_rate = Decimal("0.00015")
    else:
        stt_rate = Decimal("0.0015")
        exchange_rates = {"NSE": Decimal("0.0003553"), "BSE": Decimal("0.000325")}
        stamp_rate = Decimal("0.00002") if exchange == "NSE" else Decimal("0.00003")

    base_by_side: dict[str, Decimal | None] = {}
    for transaction in sides:
        name = transaction["name"]
        price = transaction["price"]
        orders = transaction["orders"]
        trade_side = transaction["trade_side"]
        turnover = price * quantity if price is not None else None

        brokerage = (
            Decimal("20") * orders
            if turnover is not None and product == "index_options"
            else min(turnover * brokerage_rate, Decimal("20") * orders)
            if turnover is not None and product != "equity_delivery"
            else Decimal("0") if turnover is not None else None
        )
        _add_component(
            components,
            code=f"brokerage_{name}",
            label=f"Brokerage ({name})",
            amount=brokerage,
            currency=INR,
            basis=(
                f"₹20 × {orders} executed order(s)"
                if product == "index_options"
                else "Zero brokerage for regular resident equity delivery"
                if product == "equity_delivery"
                else f"Lower of 0.03% of {name} turnover or ₹20 × {orders} executed order(s)"
            ),
        )

        stt_applies = product == "equity_delivery" or trade_side == "SELL"
        stt = turnover * stt_rate if turnover is not None and stt_applies else (
            Decimal("0") if turnover is not None else None
        )
        stt_label = (
            "STT (delivery, buy and sell)"
            if product == "equity_delivery"
            else "STT (sell-side option premium)"
            if product == "index_options"
            else "STT (intraday sell side)"
        )
        _add_component(
            components,
            code=f"stt_{name}",
            label=stt_label,
            amount=stt,
            currency=INR,
            basis=(
                "0.10% on both delivery sides"
                if product == "equity_delivery"
                else "0.15% on sell-side option premium; buy/exercise intrinsic-value STT is not modeled"
                if product == "index_options"
                else "0.025% on the sell side"
            ),
        )
        components[-1]["amount"] = _stt_money(stt)
        components[-1]["basis"] += (
            "; displayed to nearest whole rupee by the Zerodha calculator; "
            "not a claim about statutory half-rupee rounding"
        )

        rate = exchange_rates[exchange]
        exchange_amount = turnover * rate if turnover is not None and rate is not None else (
            Decimal("0") if turnover is not None and rate is not None else None
        )
        _add_component(
            components,
            code=f"exchange_{name}",
            label=f"Exchange transaction charge ({name})",
            amount=exchange_amount,
            currency=INR,
            basis=(
                f"{exchange} rate on {name} turnover: "
                + (
                    "0.00307% (NSE)"
                    if product != "index_options" and exchange == "NSE"
                    else "0.00375% published baseline; security-group rate cannot be established without the scrip group"
                    if product != "index_options"
                    else "0.03553% of premium (NSE)"
                    if exchange == "NSE"
                    else "0.0325% of premium (BSE)"
                )
            ),
        )

        sebi = turnover * sebi_rate if turnover is not None else None
        _add_component(
            components,
            code=f"sebi_{name}",
            label=f"SEBI turnover charge ({name})",
            amount=sebi,
            currency=INR,
            basis="₹10 per crore of turnover",
        )

        if turnover is None:
            base_by_side[name] = None
        elif exchange_amount is None or brokerage is None or sebi is None:
            base_by_side[name] = None
        else:
            base_by_side[name] = brokerage + exchange_amount + sebi

    if product == "equity_delivery" and all(item["price"] is not None for item in sides):
        delivery_stt = _stt_money(
            sum((item["price"] * quantity * stt_rate for item in sides), Decimal("0"))
        )
        entry_stt = next(item for item in components if item["code"] == "stt_entry")
        exit_stt = next(item for item in components if item["code"] == "stt_exit")
        exit_stt["amount"] = _money(
            Decimal(str(delivery_stt)) - Decimal(str(entry_stt["amount"]))
        )
        exit_stt["basis"] += "; rupee remainder allocated to exit so sides match calculator total"

    # The calculator rounds exchange turnover charges on aggregate turnover.
    # Allocate any paise remainder to the exit line so its side detail still
    # sums to the published aggregate line (the options sample is 29.85, not
    # 14.21 + 15.63 = 29.84).
    applied_exchange_rate = exchange_rates[exchange]
    if applied_exchange_rate is not None and all(item["price"] is not None for item in sides):
        entry_turnover = sides[0]["price"] * quantity
        exit_turnover = sides[1]["price"] * quantity
        total_exchange = _money((entry_turnover + exit_turnover) * applied_exchange_rate)
        entry_component = next(item for item in components if item["code"] == "exchange_entry")
        exit_component = next(item for item in components if item["code"] == "exchange_exit")
        remainder = Decimal(str(total_exchange)) - Decimal(str(entry_component["amount"]))
        exit_component["amount"] = _money(remainder)
        exit_component["basis"] += "; paise remainder allocated so both sides sum to aggregate turnover charge"

    for transaction in sides:
        name = transaction["name"]
        base = base_by_side[name]
        _add_component(
            components,
            code=f"gst_{name}",
            label=f"GST ({name})",
            amount=base * Decimal("0.18") if base is not None else None,
            currency=INR,
            basis="18% of brokerage, exchange transaction charges and SEBI charges",
        )

    buy_transactions = [item for item in sides if item["trade_side"] == "BUY"]
    if len(buy_transactions) != 1:
        raise ChargeInputError("A preview must have exactly one buy side")
    buy = buy_transactions[0]
    buy_turnover = buy["price"] * quantity if buy["price"] is not None else None
    stamp_duty = buy_turnover * stamp_rate if buy_turnover is not None else None
    _add_component(
        components,
        code="stamp_duty",
        label="Stamp duty (buy side)",
        amount=stamp_duty,
        currency=INR,
        basis=(
            f"{'NSE' if exchange == 'NSE' else 'BSE'} buy-side stamp rate: "
            + (
                "0.003% (equity intraday)"
                if product == "equity_intraday"
                else "0.015% (equity delivery)"
                if product == "equity_delivery"
                else "0.002% (NSE options) or 0.003% (BSE options)"
            )
            + "; displayed rounded to nearest whole rupee"
        ),
    )
    components[-1]["amount"] = _stamp_money(stamp_duty)

    # The schedule is per scrip/ISIN, while the calculate request deliberately
    # has no demat identifier or holding/settlement context.
    has_sell = any(item["trade_side"] == "SELL" and item["price"] is not None for item in sides)
    if product == "equity_delivery" and (has_sell or any(item["trade_side"] == "SELL" for item in sides)):
        if dp_scrips is None:
            dp_amount = None
            dp_status = None
            dp_basis = (
                "Unknown by default: requires the delivered scrip/ISIN and settlement context. "
                "A published Zerodha standard schedule lists ₹15.34 per scrip sold."
            )
            notes.append(
                "Delivery sell-side DP fees are unknown because no explicit dp_scrips/DP-per-ISIN "
                "assumption was supplied."
            )
        else:
            dp_amount = Decimal("15.34") * dp_scrips
            dp_status = "assumption"
            dp_basis = (
                f"Assumed published Zerodha standard DP charge ₹15.34 × {dp_scrips} scrip(s)/ISIN(s); "
                "not an actual verified account invoice and settlement/ISIN context remains the caller's assumption"
            )
            notes.append(
                f"Delivery DP uses an explicit {dp_scrips}-scrip published-schedule assumption; "
                "it is not an actual account invoice."
            )
        _add_component(
            components,
            code="dp_delivery_sell",
            label="Depository participant charge (delivery sell)",
            amount=dp_amount,
            currency=INR,
            basis=dp_basis,
            status=dp_status,
        )

    if exchange == "BSE" and product != "index_options":
        notes.append(
            "BSE equity transaction charges vary by scrip group. The request has no BSE group, "
            "so the exchange charge and its GST are unknown rather than guessed from the "
            "published 0.00375% baseline."
        )
    if product == "index_options":
        notes.append(
            "This estimate covers premium-based option trades, not exercised/assigned contracts; "
            "0.15% STT on intrinsic value for options bought and exercised is not included."
        )
    if symbol and product == "equity_delivery":
        notes.append(
            "A symbol is included for trade context only; it is not used to infer DP charges "
            "or a BSE scrip-group rate."
        )
    return components, notes


def _safe_oanda_metadata(metadata: Any) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    if metadata.get("verified") is not True or metadata.get("instrument") != "XAU_USD":
        return None
    source = metadata.get("source")
    source_name = source.get("name") if isinstance(source, dict) else source
    if source_name not in {
        "OANDA account instrument metadata",
        "OANDA official schedule",
    }:
        return None
    source_url = source.get("url") if isinstance(source, dict) else None
    if source_url is not None:
        if not isinstance(source_url, str):
            return None
        parsed_url = urlsplit(source_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "www.oanda.com"
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            return None
    return metadata


def _metadata_source_name(metadata: dict[str, Any]) -> str:
    source = metadata.get("source")
    return source.get("name") if isinstance(source, dict) else str(source)


def _commission_schedule(metadata: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    if metadata.get("commission_status") not in (None, "verified"):
        return None
    commission = metadata.get("commission")
    commission = commission if isinstance(commission, dict) else {}
    rate_value = next(
        (
            metadata[key] for key in (
                "commission_usd_per_million_side",
                "commission_usd_per_million",
                "commission_rate_usd_per_million",
            ) if key in metadata
        ),
        next(
            (commission[key] for key in ("usd_per_million_side", "usd_per_million", "rate_usd_per_million")
             if key in commission),
            None,
        ),
    )
    minimum_value = next(
        (
            metadata[key] for key in (
                "minimum_commission_usd_per_order",
                "min_commission_usd_per_order",
                "minimum_commission_usd",
                "min_commission_usd",
            ) if key in metadata
        ),
        next(
            (commission[key] for key in (
                "minimum_usd_per_order", "min_usd_per_order", "minimum_usd", "min_usd"
            ) if key in commission),
            None,
        ),
    )
    if rate_value is None or minimum_value is None:
        return None
    rate = _decimal(rate_value, "gold_cost_metadata.commission rate")
    minimum = _decimal(minimum_value, "gold_cost_metadata.minimum commission")
    if rate < 0 or minimum < 0:
        raise ChargeInputError("Verified OANDA commission rate and minimum cannot be negative")
    return rate, minimum


_WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")


def _weekday_charges(value: Any) -> dict[int, int] | None:
    """Normalize a complete OANDA financingDaysOfWeek snapshot.

    Missing weekdays are not inferred as one day (or zero days): an incomplete
    schedule cannot substantiate financing.
    """
    weekday_ids = {
        alias: index
        for index, weekday in enumerate(_WEEKDAYS)
        for alias in (weekday, weekday[:3])
    }
    pairs: list[tuple[Any, Any]] = []
    if isinstance(value, dict):
        if all(type(key) is int and 0 <= key < 7 for key in value):
            if set(value) != set(range(7)):
                return None
            if any(
                isinstance(charged, bool)
                or not isinstance(charged, int)
                or not 0 <= charged <= 7
                for charged in value.values()
            ):
                return None
            return dict(value)
        pairs = list(value.items())
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                return None
            weekday = item.get("dayOfWeek", item.get("day_of_week"))
            if not isinstance(weekday, str):
                weekday = item.get("weekday")
            charged = item.get("days_charged", item.get("daysCharged"))
            pairs.append((weekday, charged))
    else:
        return None

    normalized: dict[int, int] = {}
    for weekday, charged in pairs:
        if not isinstance(weekday, str):
            return None
        index = weekday_ids.get(weekday.strip().upper())
        if index is None or index in normalized:
            return None
        if isinstance(charged, bool) or not isinstance(charged, int) or not 0 <= charged <= 7:
            return None
        normalized[index] = charged
    return normalized if set(normalized) == set(range(7)) else None


def _metadata_weekday_schedule(metadata: dict[str, Any]) -> dict[int, int] | None:
    values = [
        metadata[key] for key in (
            "weekday_charges",
            "weekday_schedule",
            "financing_days_of_week",
        )
        if key in metadata and metadata[key] is not None
    ]
    if not values:
        return None
    schedules = [_weekday_charges(value) for value in values]
    if any(schedule is None for schedule in schedules):
        return None
    return schedules[0] if all(schedule == schedules[0] for schedule in schedules) else None


def _rollover_count(
    entry: datetime,
    exit: datetime,
    weekday_charges: Any,
) -> tuple[int, int] | None:
    """Count actual 17:00 New York rollovers and schedule-provided charge days."""
    schedule = _weekday_charges(weekday_charges)
    if schedule is None:
        return None
    new_york = ZoneInfo("America/New_York")
    start = entry.astimezone(new_york)
    finish = exit.astimezone(new_york)
    day = start.date()
    if datetime.combine(day, time(17), new_york) <= start:
        day += timedelta(days=1)
    count = charged_days = 0
    while day <= finish.date():
        rollover = datetime.combine(day, time(17), new_york)
        if start < rollover <= finish:
            count += 1
            charged_days += schedule[day.weekday()]
        day += timedelta(days=1)
    return count, charged_days


def _commission_amount(
    turnover: Decimal,
    rate_per_million: Decimal,
    orders: int,
    minimum_per_order: Decimal,
) -> Decimal:
    """Apply the verified per-order minimum to rate-based commission."""
    proportional = turnover * rate_per_million / Decimal("1000000")
    minimum_total = minimum_per_order * orders
    return max(proportional, minimum_total)


def _gold_components(
    *,
    quantity_oz: Decimal,
    entry_price: Decimal,
    exit_price: Decimal | None,
    side: str,
    entry_orders: int,
    exit_orders: int,
    entry_time: datetime | None,
    exit_time: datetime | None,
    metadata: Any,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, str]]]:
    components: list[dict[str, Any]] = []
    notes = [
        "XAUUSD quantities are troy ounces: 100 units equal one 100-oz OANDA lot.",
        "XAUUSD prices supplied to this calculator are hypothetical preview inputs unless "
        "the caller independently confirms they came from a fresh cached OANDA quote.",
        "Bid/ask spread is already embedded in executable ask-entry/bid-exit P&L; the displayed "
        "spread amount is informational and is not deducted a second time.",
    ]
    safe_metadata = _safe_oanda_metadata(metadata)
    trusted_sources: list[dict[str, str]] = []

    if safe_metadata:
        trusted_sources.append({
            "name": _metadata_source_name(safe_metadata),
            # Never pass through an account-specific path, ID, token, or URL.
            "url": "https://www.oanda.com/",
        })
    else:
        notes.append(
            "OANDA commission and financing are unknown: no verified XAU_USD account/instrument "
            "metadata or applicable OANDA schedule was supplied. Generic OANDA documentation "
            "is not treated as an account-specific zero-cost quote."
        )

    commission_terms = _commission_schedule(safe_metadata) if safe_metadata else None

    entry_turnover = quantity_oz * entry_price
    exit_turnover = quantity_oz * exit_price if exit_price is not None else None
    rates = (("entry", entry_turnover, entry_orders), ("exit", exit_turnover, exit_orders))
    for name, turnover, orders in rates:
        if commission_terms is None:
            commission = None
            basis = (
                "Unknown: verified OANDA commission rate and explicit minimum-per-order "
                "metadata are both required"
            )
        elif turnover is None:
            commission = None
            basis = "Unknown: exit price is not supplied"
        else:
            commission_rate, commission_minimum = commission_terms
            commission = _commission_amount(
                turnover, commission_rate, orders, commission_minimum
            )
            basis = (
                f"Verified OANDA commission of USD {commission_rate} per USD 1,000,000 "
                f"of {name} notional, with USD {commission_minimum} minimum × {orders} "
                "executed order(s); individual order notionals are unavailable, so the "
                "minimum is applied to aggregate side notional"
            )
        _add_component(
            components,
            code=f"commission_{name}",
            label=f"OANDA commission ({name})",
            amount=commission,
            currency=USD,
            basis=basis,
            status="assumption" if commission_terms is not None and orders > 1 else None,
        )

    financing = None
    financing_basis = "Unknown: no verified OANDA financing/rollover schedule"
    if safe_metadata and entry_time and exit_time:
        day_basis = safe_metadata.get("financing_day_basis")
        long_rate = safe_metadata.get("long_financing_annual_pct")
        short_rate = safe_metadata.get("short_financing_annual_pct")
        weekday_charges = _metadata_weekday_schedule(safe_metadata)
        if (
            weekday_charges is not None and day_basis in (360, 365)
            and long_rate is not None and short_rate is not None
            and safe_metadata.get("financing_rate_status") in (None, "verified")
        ):
            rate_value = long_rate if side == "BUY" else short_rate
            annual_rate = _decimal(rate_value, f"gold_cost_metadata.{side.lower()}_financing_annual_pct")
            rollover_result = _rollover_count(
                entry_time, exit_time, weekday_charges
            )
            if exit_time < entry_time:
                raise ChargeInputError("exit_time must be after entry_time")
            if rollover_result is None:
                financing_basis = (
                    "Unknown: complete weekday_charges schedule is required for financing"
                )
                financing = None
            else:
                rollover_count, financed_days = rollover_result
                financing = (
                    entry_turnover * annual_rate / Decimal("100")
                    * Decimal(financed_days) / Decimal(day_basis)
                )
                financing_basis = (
                    f"Verified annual rate {annual_rate}% for {side.lower()} XAU_USD financing; "
                    f"{rollover_count} New York 17:00 rollover(s), {financed_days} financing "
                    f"day(s) from the complete weekday_charges schedule; {day_basis}-day basis"
                )
        else:
            financing_basis = (
                "Unknown: supplied metadata lacks verified long/short rates, day basis, "
                "or a complete weekday_charges schedule"
            )
    elif safe_metadata and (entry_time is None or exit_time is None):
        financing_basis = "Unknown: entry_time and exit_time are required to determine rollover financing"
    elif not safe_metadata:
        financing_basis = "Unknown: no verified OANDA financing/rollover schedule"
    _add_component(
        components,
        code="financing",
        label="OANDA financing / rollover",
        amount=financing,
        currency=USD,
        basis=financing_basis,
    )
    if financing is None:
        notes.append(financing_basis + ".")
    return components, notes, trusted_sources


def _valid_cached_gold_quote(quote: Any) -> dict[str, Any] | None:
    if not isinstance(quote, dict) or quote.get("source") != "OANDA":
        return None
    if quote.get("instrument") != "XAU_USD" or quote.get("stale") is True:
        return None
    timestamp = quote.get("provider_timestamp") or quote.get("timestamp")
    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    except (ValueError, TypeError):
        return None
    if not 0 <= age <= 30:
        return None
    try:
        bid = _decimal(quote.get("bid"), "gold_quote.bid", positive=True)
        ask = _decimal(quote.get("ask"), "gold_quote.ask", positive=True)
    except ChargeInputError:
        return None
    if bid > ask:
        return None
    return {
        "source": "OANDA",
        "instrument": "XAU_USD",
        "currency": USD,
        "bid": float(bid),
        "ask": float(ask),
        "timestamp": parsed.astimezone(timezone.utc).isoformat(),
        "age_seconds": round(age, 3),
        "status": "live",
    }


def _result(
    *,
    currency: str,
    components: list[dict[str, Any]],
    gross_pnl: Decimal | None,
    embedded_spread: Decimal | None,
    notes: list[str],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    unknown = any(component["amount"] is None for component in components if component["additional"])
    known_total = sum(
        (Decimal(str(component["amount"])) for component in components
         if component["additional"] and component["amount"] is not None),
        Decimal("0"),
    )
    rounded_known = _money(known_total)
    total_additional = None if unknown else rounded_known
    net_after_known = gross_pnl - Decimal(str(rounded_known)) if gross_pnl is not None else None
    net = (
        gross_pnl - Decimal(str(total_additional))
        if gross_pnl is not None and total_additional is not None
        else None
    )
    return {
        "currency": currency,
        "status": "partial_estimate" if unknown else "complete_estimate",
        "complete": not unknown,
        "components": components,
        "embedded_spread_cost": _money(embedded_spread),
        "known_additional_charges": rounded_known,
        "total_additional_charges": total_additional,
        "price_pnl_before_additional_fees": _money(gross_pnl),
        "net_pnl": _money(net),
        "net_pnl_after_known_charges": _money(net_after_known),
        "notes": list(dict.fromkeys(notes)),
        "sources": sources,
    }


def calculate_charges(
    requestdict: dict[str, Any],
    *,
    gold_quote: dict[str, Any] | None = None,
    gold_cost_metadata: dict[str, Any] | None = None,
    dp_scrips: int | None = None,
) -> dict[str, Any]:
    """Calculate a fee preview from finite positive prices and quantities.

    No networking is performed. For OANDA, callers may pass only an already-cached
    quote and verified, sanitized cost metadata; manual prices remain hypothetical.
    """
    if not isinstance(requestdict, dict):
        raise ChargeInputError("request must be an object")
    market = requestdict.get("market", "INDIA")
    if not isinstance(market, str) or market not in {"INDIA", "XAUUSD"}:
        raise ChargeInputError("market must be INDIA or XAUUSD")
    quantity = _decimal(requestdict.get("quantity"), "quantity", positive=True)
    entry_price = _decimal(requestdict.get("entry_price"), "entry_price", positive=True)
    exit_price = (
        _decimal(requestdict["exit_price"], "exit_price", positive=True)
        if requestdict.get("exit_price") is not None else None
    )
    side = requestdict.get("side", "BUY")
    if not isinstance(side, str) or side not in {"BUY", "SELL"}:
        raise ChargeInputError("side must be BUY or SELL")
    entry_orders = _positive_order_count(requestdict.get("entry_orders", 1), "entry_orders")
    exit_orders = _positive_order_count(requestdict.get("exit_orders", 1), "exit_orders")
    entry_time = _timestamp(requestdict.get("entry_time"), "entry_time")
    exit_time = _timestamp(requestdict.get("exit_time"), "exit_time")

    if exit_time and entry_time and exit_time <= entry_time:
        raise ChargeInputError("exit_time must be after entry_time")
    if exit_time and not entry_time:
        raise ChargeInputError("entry_time is required when exit_time is supplied")

    sides = _side_values(
        side=side,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        entry_orders=entry_orders,
        exit_orders=exit_orders,
    )
    pnl = None
    if exit_price is not None:
        pnl = (exit_price - entry_price) * quantity
        if side == "SELL":
            pnl = -pnl

    if market == "INDIA":
        product = requestdict.get("product", "equity_intraday")
        if not isinstance(product, str) or product not in {"equity_intraday", "equity_delivery", "index_options"}:
            raise ChargeInputError(
                "product must be equity_intraday, equity_delivery, or index_options"
            )
        exchange = requestdict.get("exchange", "NSE")
        if not isinstance(exchange, str) or exchange not in {"NSE", "BSE"}:
            raise ChargeInputError("exchange must be NSE or BSE")
        if product == "index_options" and exchange not in {"NSE", "BSE"}:
            raise ChargeInputError("index_options exchange must be NSE or BSE")
        payload_dp_scrips = requestdict.get("dp_scrips")
        if dp_scrips is not None and payload_dp_scrips is not None and dp_scrips != payload_dp_scrips:
            raise ChargeInputError("dp_scrips was specified inconsistently")
        dp_scrips = dp_scrips if dp_scrips is not None else payload_dp_scrips
        if dp_scrips is not None and (
            isinstance(dp_scrips, bool) or not isinstance(dp_scrips, int) or dp_scrips < 1
        ):
            raise ChargeInputError("dp_scrips must be a positive integer when supplied")
        if dp_scrips is not None and product != "equity_delivery":
            raise ChargeInputError("dp_scrips only applies to equity_delivery")
        components, notes = _india_components(
            product=product,
            exchange=exchange,
            sides=sides,
            quantity=quantity,
            symbol=requestdict.get("symbol"),
            dp_scrips=dp_scrips,
        )
        return _result(
            currency=INR,
            components=components,
            gross_pnl=pnl,
            embedded_spread=None,
            notes=notes + [
                "Prices are consumed as supplied and are never refreshed or represented as a live quote; manually supplied prices are hypothetical preview inputs.",
                "Zerodha-reference estimate for preview only; actual charges vary by broker, "
                "account status, contract note, security and applicable statutory rates."
            ],
            sources=list(_SOURCES),
        )

    exchange = requestdict.get("exchange", "OANDA")
    if dp_scrips is not None or requestdict.get("dp_scrips") is not None:
        raise ChargeInputError("dp_scrips only applies to Indian equity delivery previews")
    if exchange != "OANDA":
        raise ChargeInputError("XAUUSD previews must use exchange OANDA")
    components, notes, gold_sources = _gold_components(
        quantity_oz=quantity,
        entry_price=entry_price,
        exit_price=exit_price,
        side=side,
        entry_orders=entry_orders,
        exit_orders=exit_orders,
        entry_time=entry_time,
        exit_time=exit_time,
        metadata=gold_cost_metadata,
    )
    quote = _valid_cached_gold_quote(gold_quote)
    if quote is None:
        embedded_spread = None
        notes.append("No fresh cached OANDA XAU_USD quote was supplied; embedded spread is unavailable.")
    else:
        embedded_spread = (Decimal(str(quote["ask"])) - Decimal(str(quote["bid"]))) * quantity
        notes.append("Fresh cached OANDA bid/ask spread shown for reference; it is not an extra fee.")
        gold_sources.append({
            "name": "Cached OANDA XAU_USD quote",
            "url": "https://www.oanda.com/",
        })
    return _result(
        currency=USD,
        components=components,
        gross_pnl=pnl,
        embedded_spread=embedded_spread,
        notes=notes,
        sources=gold_sources,
    )


def get_charge_rules(
    *,
    gold_quote: dict[str, Any] | None = None,
    gold_cost_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the cached-rule reference and sanitized optional OANDA metadata."""
    quote = _valid_cached_gold_quote(gold_quote)
    safe_metadata = _safe_oanda_metadata(gold_cost_metadata)
    if safe_metadata:
        commission_terms = _commission_schedule(safe_metadata)
        schedule = _metadata_weekday_schedule(safe_metadata)
        metadata_summary = {
            "status": "verified",
            "instrument": "XAU_USD",
            "source": _metadata_source_name(safe_metadata),
            "as_of": safe_metadata.get("as_of"),
            "commission": "verified" if commission_terms is not None else "unknown",
            "commission_usd_per_million_side": (
                float(commission_terms[0]) if commission_terms is not None else None
            ),
            "minimum_commission_usd_per_order": (
                float(commission_terms[1]) if commission_terms is not None else None
            ),
            "financing": "verified" if (
                schedule is not None
                and safe_metadata.get("financing_day_basis") in (360, 365)
                and safe_metadata.get("long_financing_annual_pct") is not None
                and safe_metadata.get("short_financing_annual_pct") is not None
                and safe_metadata.get("financing_rate_status") in (None, "verified")
            ) else "unknown",
            "weekday_charges": (
                {_WEEKDAYS[index]: schedule[index] for index in range(7)}
                if schedule is not None else None
            ),
        }
    else:
        metadata_summary = {
            "status": "unknown",
            "instrument": "XAU_USD",
            "source": None,
            "as_of": None,
            "commission": "unknown",
            "financing": "unknown",
            "commission_usd_per_million_side": None,
            "minimum_commission_usd_per_order": None,
            "weekday_charges": None,
        }
    indian_rules = {
        "broker_reference": "Zerodha; estimate only, not an invoice",
        "brokerage": {
            "equity_intraday": "0.03% per executed order or ₹20, whichever is lower",
            "equity_delivery": "₹0 for regular resident equity delivery",
            "index_options": "₹20 per executed order",
        },
        "equity_intraday": {
            "stt": "0.025% on sell side",
            "transaction_charge": {"NSE": "0.00307%", "BSE": "0.00375% published baseline; group-dependent"},
            "stamp_duty": "0.003% on buy side",
        },
        "equity_delivery": {
            "stt": "0.10% on buy and sell sides",
            "transaction_charge": {"NSE": "0.00307%", "BSE": "0.00375% published baseline; group-dependent"},
            "stamp_duty": "0.015% on buy side",
            "dp_charge": "Unknown per calculation without scrip/ISIN and settlement context; published Zerodha schedule says ₹15.34 per scrip sold",
        },
        "index_options": {
            "stt": "0.15% of sell-side premium; 0.15% intrinsic value on options bought and exercised is outside this preview",
            "transaction_charge": {"NSE": "0.03553% of premium", "BSE": "0.0325% of premium"},
            "stamp_duty": {"NSE": "0.002% on buy side", "BSE": "0.003% on buy side"},
        },
        "common": {
            "gst": "18% of brokerage + exchange transaction charges + SEBI charges",
            "sebi": "₹10 per crore of turnover",
            "rounding": "Zerodha's calculator JavaScript applies Math.round to STT after a 2-decimal intermediate and to stamp duty; estimates follow its nearest-whole-rupee display convention, not a verified statutory half-rupee ruling. Other modeled lines use decimal round-half-up to paise.",
        },
        "limitations": [
            "BSE equity transaction charge depends on the scrip group; exact group is not an input, so BSE equity estimates are partial.",
            "Delivery DP fee depends on the delivered scrip/ISIN and settlement circumstances; it is never guessed.",
            "Delivery DP can be modeled only when the caller explicitly supplies dp_scrips; this uses the published Zerodha ₹15.34/scrip standard as an assumption, not a verified account invoice.",
            "Regular-resident account pricing is assumed. Account-class-specific brokerage is not modeled.",
            "OANDA financing requires a complete seven-day weekday_charges schedule; missing days are never inferred.",
        ],
    }
    notes = [
        "All calculations are previews, not quotes, contract notes, tax advice, or order instructions.",
        "Rates are a Zerodha-reference estimate captured 2026-10-01; actual charges depend on the broker, scrip, account and exchange.",
        "Only already-cached real OANDA quotes may be displayed; this call does not refresh market data or make an HTTP request.",
        "OANDA fees remain unknown unless verified XAU_USD account/instrument metadata or an applicable official schedule is provided.",
    ]
    return {
        "as_of": AS_OF,
        "sources": list(_SOURCES),
        "indian_rules": indian_rules,
        "gold": {
            "quote": quote,
            "cost_metadata": metadata_summary,
            "lot_size_troy_ounces": 100,
        },
        "notes": notes,
    }


def _field(trade: Any, name: str, default: Any = None) -> Any:
    if isinstance(trade, dict):
        return trade.get(name, default)
    return getattr(trade, name, default)


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value or "")).upper()


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        # Persisted Trade timestamps were written by datetime.utcnow(); their
        # naive representation is known UTC, unlike caller-supplied timestamps.
        parsed = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return parsed.astimezone(timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return value
        parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        return parsed.astimezone(timezone.utc).isoformat()
    return value.isoformat() if hasattr(value, "isoformat") else None


def _naive_db_timestamp(value: Any) -> bool:
    if isinstance(value, datetime):
        return value.tzinfo is None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).tzinfo is None
        except (ValueError, TypeError):
            return False
    return False


def charges_for_trade(
    trade: Any,
    *,
    gold_quote: dict[str, Any] | None = None,
    gold_cost_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only charge preview for a dict or persisted trade object."""
    agent = _enum_value(_field(trade, "agent"))
    symbol = str(_field(trade, "symbol", "") or "")
    is_gold = agent == "XAUUSD" or symbol.upper() == "XAUUSD"
    is_options = (
        agent in {"OPTIONS", "SENSEX_OPTIONS_SCALPING"}
        or _field(trade, "option_strike") is not None
    )
    product = "index_options" if is_options else "equity_delivery" if agent == "STOCKS" else "equity_intraday"
    exchange = "OANDA" if is_gold else "BSE" if agent == "SENSEX_OPTIONS_SCALPING" else "NSE"
    side = _enum_value(_field(trade, "trade_type", "BUY"))
    if side not in {"BUY", "SELL"}:
        side = "BUY"
    created_at_value = _field(trade, "created_at")
    closed_at_value = _field(trade, "closed_at")
    used_naive_utc_timestamp = is_gold and any(
        _naive_db_timestamp(value) for value in (created_at_value, closed_at_value)
    )
    created_at = _iso(created_at_value)
    closed_at = _iso(closed_at_value)
    exit_price = _field(trade, "exit_price")
    status = str(_field(trade, "status", "OPEN") or "OPEN")
    if exit_price is None and status.upper() == "CLOSED":
        # Closed trades in older persistence paths might lack exit_price. Do not
        # reinterpret a historical stored P&L or manufacture a fill price.
        exit_price = None
    request = {
        "market": "XAUUSD" if is_gold else "INDIA",
        "exchange": exchange,
        "product": product,
        "symbol": symbol,
        "quantity": _field(trade, "quantity"),
        "entry_price": _field(trade, "entry_price"),
        "exit_price": exit_price,
        "side": side,
        "entry_time": created_at if is_gold else None,
        "exit_time": closed_at if is_gold and exit_price is not None else None,
    }
    result = calculate_charges(
        request,
        gold_quote=gold_quote if is_gold else None,
        gold_cost_metadata=gold_cost_metadata if is_gold else None,
    )
    if used_naive_utc_timestamp:
        result["notes"].append(
            "A naive persisted trade timestamp was interpreted as UTC because the database "
            "stores Trade timestamps from datetime.utcnow(); manual preview timestamps must "
            "include a timezone."
        )
    return result


def get_charge_trades(
    trades: Iterable[Any],
    *,
    gold_quote: dict[str, Any] | None = None,
    gold_cost_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize available trades with estimates; routes supply their DB query."""
    result = []
    notes = [
        "Trades are read-only previews; existing stored trade P&L is not rewritten.",
        "NSE reference rates are used for Indian trades by default; SENSEX_OPTIONS_SCALPING is mapped to BSE index-option rates.",
    ]
    for trade in trades:
        agent = _enum_value(_field(trade, "agent"))
        symbol = str(_field(trade, "symbol", "") or "")
        trade_id = _field(trade, "id")
        result.append({
            "trade_id": trade_id,
            "agent": agent,
            "symbol": symbol,
            "status": str(_field(trade, "status", "UNKNOWN") or "UNKNOWN"),
            "currency": USD if agent == "XAUUSD" or symbol.upper() == "XAUUSD" else INR,
            "charges": charges_for_trade(
                trade,
                gold_quote=gold_quote,
                gold_cost_metadata=gold_cost_metadata,
            ),
        })
    return {"trades": result, "notes": notes}


def sized_stock_entry(
    *,
    available_capital: Any,
    risk_capital: Any,
    entry_price: Any,
    stop_price: Any,
    expected_exit_price: Any,
    exchange: str = "NSE",
    product: str = "equity_delivery",
    dp_scrips: int | None = None,
    expected_net_profit_min: Any = 0,
    entry_orders: int = 1,
    exit_orders: int = 1,
    side: str = "BUY",
) -> dict[str, Any]:
    """Fee-aware, cash/risk-capped stock sizing preview (never submits an order).

    The risk cap includes adverse price loss at the stop plus known round-trip
    charges. The capital cap reserves the full entry notional plus known fees.
    """
    capital = _decimal(available_capital, "available_capital", positive=True)
    risk_budget = _decimal(risk_capital, "risk_capital", positive=True)
    entry = _decimal(entry_price, "entry_price", positive=True)
    stop = _decimal(stop_price, "stop_price", positive=True)
    target = _decimal(expected_exit_price, "expected_exit_price", positive=True)
    min_net = _decimal(expected_net_profit_min, "expected_net_profit_min")
    if exchange not in {"NSE", "BSE"}:
        raise ChargeInputError("exchange must be NSE or BSE")
    if product not in {"equity_intraday", "equity_delivery"}:
        raise ChargeInputError("product must be equity_intraday or equity_delivery")
    if dp_scrips is not None and (
        isinstance(dp_scrips, bool) or not isinstance(dp_scrips, int) or dp_scrips < 1
    ):
        raise ChargeInputError("dp_scrips must be a positive integer when supplied")
    if dp_scrips is not None and product != "equity_delivery":
        raise ChargeInputError("dp_scrips only applies to equity_delivery")
    if side not in {"BUY", "SELL"}:
        raise ChargeInputError("side must be BUY or SELL")
    entries = _positive_order_count(entry_orders, "entry_orders")
    exits = _positive_order_count(exit_orders, "exit_orders")
    adverse_loss_per_share = entry - stop if side == "BUY" else stop - entry
    if adverse_loss_per_share <= 0:
        raise ChargeInputError("stop_price must be on the loss side of entry_price")
    if (side == "BUY" and target <= entry) or (side == "SELL" and target >= entry):
        raise ChargeInputError("expected_exit_price must be on the profit side of entry_price")

    max_shares_by_capital = int(capital // entry)
    max_shares_by_risk = int(risk_budget // adverse_loss_per_share)
    max_shares = min(max_shares_by_capital, max_shares_by_risk)
    chosen_quantity = 0
    chosen_risk = Decimal("0")
    chosen_capital = Decimal("0")
    low, high = 1, max_shares
    while low <= high:
        shares = (low + high) // 2
        quantity = Decimal(shares)
        risk_charge = calculate_charges({
            "market": "INDIA",
            "product": product,
            "exchange": exchange,
            "quantity": shares,
            "entry_price": float(entry),
            "exit_price": float(stop),
            "side": side,
            "entry_orders": entries,
            "exit_orders": exits,
            "dp_scrips": dp_scrips,
        })
        if not risk_charge["complete"]:
            break
        fee_at_stop = Decimal(str(risk_charge["total_additional_charges"]))
        total_risk = adverse_loss_per_share * quantity + fee_at_stop
        capital_with_fees = entry * quantity + fee_at_stop
        if total_risk <= risk_budget and capital_with_fees <= capital:
            chosen_quantity = shares
            chosen_risk = total_risk
            chosen_capital = capital_with_fees
            low = shares + 1
        else:
            high = shares - 1

    if chosen_quantity == 0:
        return {
            "quantity": 0,
            "accepted": False,
            "reason": (
                "No positive integer share quantity fits both caps with a complete fee estimate; "
                "BSE scrip-group or delivery DP costs can make sizing incomplete."
            ),
            "risk_capital": _money(risk_budget),
            "available_capital": _money(capital),
            "estimated_risk_including_known_charges": None,
            "estimated_capital_including_known_charges": None,
            "expected_net_profit": None,
            "charges": None,
            "product": product,
            "orders_placed": False,
        }

    chosen = calculate_charges({
        "market": "INDIA",
        "product": product,
        "exchange": exchange,
        "quantity": chosen_quantity,
        "entry_price": float(entry),
        "exit_price": float(target),
        "side": side,
        "entry_orders": entries,
        "exit_orders": exits,
        "dp_scrips": dp_scrips,
    })
    net = chosen["net_pnl"]
    accepted = net is not None and Decimal(str(net)) > min_net
    return {
        "quantity": chosen_quantity,
        "accepted": accepted,
        "reason": (
            "Expected net profit after modeled fees exceeds the configured gate."
            if accepted
            else "Expected net profit after modeled fees does not exceed the configured gate."
        ),
        "risk_capital": _money(risk_budget),
        "available_capital": _money(capital),
        "estimated_risk_including_known_charges": _money(chosen_risk),
        "estimated_capital_including_known_charges": _money(chosen_capital),
        "expected_net_profit": net,
        "charges": chosen,
        "product": product,
        "orders_placed": False,
    }
