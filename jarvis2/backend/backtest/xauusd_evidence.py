"""Replay the existing XAUUSD agent against genuine OANDA practice candles."""

from __future__ import annotations

import csv
import csv
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests
from dotenv import dotenv_values

from agents.base import Signal
from agents.xauusd_baseline import XAUUSDBaselineAgent as XAUUSDAgent


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "evidence"
INSTRUMENT = "XAU_USD"
GRANULARITY = "M1"
SAMPLE_DAYS = 90
EMA_WARMUP_DAYS = 7
MAX_PAGE_CANDLES = 5000
PAGE_DELAY_SECONDS = 0.15
MAX_PAGE_RETRIES = 3
TRAIN_FRACTION = 0.70
SESSION_START_UTC = (16, 0)
SESSION_END_UTC = (23, 0)
PRACTICE_HOST = "https://api-fxpractice.oanda.com/v3"
OHLC_FIELDS = (
    "bid_open",
    "bid_high",
    "bid_low",
    "bid_close",
    "ask_open",
    "ask_high",
    "ask_low",
    "ask_close",
)
CSV_FIELDS = ("time", "complete", *OHLC_FIELDS, "data_source", "environment", "instrument")
EXITABLE_STATUSES = frozenset(("CLOSED",))
MIN_HOLDOUT_TRADES_FOR_ADEQUACY = 30


class XAUHistoryError(Exception):
    """A sanitized historical-data failure; never includes headers or provider bodies."""


def _read_access_token() -> str:
    token = os.environ.get("OANDA_ACCESS_TOKEN") or os.environ.get("ONDA_ACCESS_TOKEN")
    if token:
        return token.strip()
    for location in (Path(".env"), Path(__file__).resolve().parents[1] / ".env"):
        if location.is_file():
            values = dotenv_values(location)
            token = values.get("OANDA_ACCESS_TOKEN") or values.get("ONDA_ACCESS_TOKEN")
            if token:
                return str(token).strip()
    return ""


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise XAUHistoryError("Provider candle is missing its ISO 8601 UTC timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise XAUHistoryError("Provider candle timestamp is invalid") from exc
    if result.tzinfo is None:
        raise XAUHistoryError("Provider candle has no timezone")
    return result.astimezone(timezone.utc)


def _bar_observation_time(bar_open_timestamp: str) -> datetime:
    """OANDA candle timestamps name the open; OHLC is known one minute later."""
    return _timestamp(bar_open_timestamp) + timedelta(minutes=1)


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _price_bar(candle: Any) -> dict[str, Any]:
    if not isinstance(candle, dict) or candle.get("complete") is not True:
        raise XAUHistoryError("Incomplete or invalid OANDA candle cannot enter a backtest")
    if all(field in candle for field in OHLC_FIELDS):
        candle = {
            "time": candle.get("time"),
            "complete": candle.get("complete"),
            "bid": {
                "o": candle["bid_open"],
                "h": candle["bid_high"],
                "l": candle["bid_low"],
                "c": candle["bid_close"],
            },
            "ask": {
                "o": candle["ask_open"],
                "h": candle["ask_high"],
                "l": candle["ask_low"],
                "c": candle["ask_close"],
            },
        }
    prices: dict[str, float] = {}
    for side in ("bid", "ask"):
        quote = candle.get(side)
        if not isinstance(quote, dict):
            raise XAUHistoryError("OANDA did not return both bid and ask OHLC prices")
        for letter in ("o", "h", "l", "c"):
            try:
                number = float(quote[letter])
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise XAUHistoryError("OANDA returned invalid bid/ask candle values") from exc
            if not math.isfinite(number) or number <= 0:
                raise XAUHistoryError("OANDA returned non-positive or non-finite OHLC data")
            prices[f"{side}_{dict(o='open', h='high', l='low', c='close')[letter]}"] = number

    for letter in ("open", "high", "low", "close"):
        bid = prices[f"bid_{letter}"]
        ask = prices[f"ask_{letter}"]
        if bid > ask:
            raise XAUHistoryError("OANDA historical bid exceeds ask")
    if (
        prices["bid_low"] > min(prices["bid_open"], prices["bid_close"])
        or prices["bid_high"] < max(prices["bid_open"], prices["bid_close"])
        or prices["ask_low"] > min(prices["ask_open"], prices["ask_close"])
        or prices["ask_high"] < max(prices["ask_open"], prices["ask_close"])
    ):
        raise XAUHistoryError("OANDA returned malformed bid/ask OHLC ranges")
    timestamp = candle.get("time")
    _timestamp(timestamp)
    return {
        "time": timestamp,
        **prices,
        "complete": True,
        "data_source": "OANDA_PRACTICE_HISTORICAL",
        "environment": "practice",
        "instrument": INSTRUMENT,
    }


def validate_and_sort_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fail closed on duplicate or out-of-order prices; never interpolate gaps."""
    normalized = sorted((_price_bar(row) for row in rows), key=lambda row: _timestamp(row["time"]))
    previous: datetime | None = None
    for row in normalized:
        current = _timestamp(row["time"])
        if previous is not None and current <= previous:
            raise XAUHistoryError("OANDA history contains duplicate or non-chronological candles")
        previous = current
    return normalized


def _fetch_historical_candles(
    token: str,
    *,
    start: datetime,
    end: datetime,
    session: Any = requests,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Fetch only complete, unsmoothed, genuine bid/ask M1 bars."""
    request_start = start.astimezone(timezone.utc)
    stop_at = end.astimezone(timezone.utc)
    if request_start >= stop_at:
        raise XAUHistoryError("Requested XAUUSD historical date range is empty")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_final: datetime | None = None
    while request_start < stop_at:
        params = {
            "from": request_start.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "granularity": GRANULARITY,
            "price": "BA",
            "smooth": "false",
            "includeFirst": "true",
            "count": MAX_PAGE_CANDLES,
        }
        for attempt in range(MAX_PAGE_RETRIES + 1):
            try:
                response = session.get(
                    f"{PRACTICE_HOST}/instruments/{INSTRUMENT}/candles",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
            except requests.RequestException as exc:
                if attempt == MAX_PAGE_RETRIES:
                    raise XAUHistoryError("OANDA candle history request failed; inspect provider connectivity") from exc
                sleep(2**attempt)
                continue
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt == MAX_PAGE_RETRIES:
                    raise XAUHistoryError(f"OANDA candle history is temporarily unavailable (HTTP {response.status_code})")
                sleep(min(16, 2**attempt))
                continue
            if response.status_code != 200:
                raise XAUHistoryError(
                    f"OANDA practice candle history rejected access (HTTP {response.status_code}); no results reported"
                )
            try:
                payload = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as exc:
                raise XAUHistoryError("OANDA historical-candle response is not valid JSON") from exc
            if (
                not isinstance(payload, dict)
                or payload.get("instrument") != INSTRUMENT
                or payload.get("granularity") != GRANULARITY
                or not isinstance(payload.get("candles"), list)
            ):
                raise XAUHistoryError("OANDA response failed historical-instrument provenance checks")
            page = payload["candles"]
            if not page:
                return rows
            parsed = [_price_bar(candle) for candle in page if isinstance(candle, dict) and candle.get("complete") is True]
            for row in parsed:
                timestamp = _timestamp(row["time"])
                if not request_start <= timestamp < stop_at or row["time"] in seen:
                    continue
                if previous_final is not None and timestamp <= previous_final:
                    raise XAUHistoryError("OANDA pagination is not strictly chronological")
                rows.append(row)
                seen.add(row["time"])
                previous_final = timestamp

            final_timestamp = _timestamp(page[-1].get("time")) if isinstance(page[-1], dict) else None
            if final_timestamp is None or final_timestamp < request_start:
                raise XAUHistoryError("OANDA candle pagination did not advance; refusing incomplete history")
            if final_timestamp + timedelta(minutes=1) >= stop_at:
                return rows
            if len(page) < MAX_PAGE_CANDLES:
                # A short page is not evidence that the requested end date
                # has been reached. Do not silently treat provider history
                # gaps or truncation as a complete sample.
                raise XAUHistoryError("OANDA historical candles ended before the requested sample boundary")
            request_start = final_timestamp + timedelta(minutes=1)
            sleep(PAGE_DELAY_SECONDS)
            break
        else:
            raise XAUHistoryError("OANDA candle history exhausted its safe retry limit")
    return rows


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _store_history(evidence_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = evidence_dir / "xauusd_1m_ba_last90d.csv"
    contents = _csv_bytes(rows)
    tmp_path = path.with_suffix(".csv.tmp")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(contents)
    tmp_path.replace(path)
    return {
        "raw_data_file": path.name,
        "sha256": hashlib.sha256(contents).hexdigest(),
        "complete_bid_ask_candles_saved": len(rows),
        "storage_contains_token_or_account_identifiers": False,
    }


def _within_entry_session(timestamp: str) -> bool:
    """Return whether this already-observable event is inside the UTC entry window."""
    utc_time = _timestamp(timestamp).time()
    local_time = (utc_time.hour, utc_time.minute)
    return SESSION_START_UTC <= local_time < SESSION_END_UTC


def _within_observed_bar_entry_session(bar_open_timestamp: str) -> bool:
    """Check the existing gate when the completed candle is actually observable."""
    return _within_entry_session(_format_utc_timestamp(_bar_observation_time(bar_open_timestamp)))


def _validate_nonoverlapping_warmup(
    sample: list[dict[str, Any]], warmup: list[dict[str, Any]]
) -> None:
    """Require each EMA warm-up candle to be complete before the first sample open."""
    if not sample or not warmup:
        return
    sample_start = _timestamp(sample[0]["time"])
    for bar in warmup:
        if _bar_observation_time(bar["time"]) > sample_start:
            raise XAUHistoryError(
                "EMA warm-up overlaps the sample: a warm-up candle closes after the first sample candle opens"
            )


def _midpoint_close(row: dict[str, Any]) -> float:
    return (row["bid_close"] + row["ask_close"]) / 2


def _exit_bar(position: dict[str, Any], bar: dict[str, Any]) -> dict[str, Any] | None:
    """Use actual exit-side OHLC; resolve same-minute SL/TP collisions against the trade."""
    stop = position.get("stop", position.get("stop_price"))
    target = position.get("target", position.get("target_price"))
    if position["signal"] == Signal.BUY.value:
        opening = bar["bid_open"]
        high = bar["bid_high"]
        low = bar["bid_low"]
        if opening <= stop:
            return {"price": opening, "reason": "gap_through_stop"}
        if opening >= target:
            return {"price": target, "reason": "gap_through_target"}
        if low <= stop:
            return {"price": stop, "reason": "stop_first_if_both_touched"}
        if high >= target:
            return {"price": target, "reason": "take_profit"}
    else:
        opening = bar["ask_open"]
        high = bar["ask_high"]
        low = bar["ask_low"]
        if opening >= stop:
            return {"price": opening, "reason": "gap_through_stop"}
        if opening <= target:
            return {"price": target, "reason": "gap_through_target"}
        if high >= stop:
            return {"price": stop, "reason": "stop_first_if_both_touched"}
        if low <= target:
            return {"price": target, "reason": "take_profit"}
    return None


def _trade_pnl(position: dict[str, Any], exit_price: float) -> float:
    side = 1 if position["signal"] == Signal.BUY.value else -1
    return (exit_price - position["entry_price"]) * position["quantity"] * side


def _fold_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(trade["pnl_usd"]) for trade in trades]
    winners = sum(value > 0 for value in pnls)
    losers = sum(value < 0 for value in pnls)
    breakeven = sum(value == 0 for value in pnls)
    peak = 0.0
    equity = 0.0
    max_drawdown = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "closed_trades": len(pnls),
        "wins": winners,
        "losses": losers,
        "breakeven": breakeven,
        "win_rate_pct": round(winners * 100 / len(pnls), 2) if pnls else None,
        "net_pnl_usd": round(sum(pnls), 2) if pnls else None,
        "max_closed_trade_drawdown_usd": round(max_drawdown, 2) if pnls else None,
        "unclassified_results_as_zero": False,
    }


def evaluate_xauusd(
    candles: list[dict[str, Any]],
    *,
    warmup_candles: list[dict[str, Any]] | None = None,
    quantity: float = 100.0,
) -> dict[str, Any]:
    """Replay the unmodified XAUUSDAgent over provider-verified full M1 candles.

    Entry indicators use the live agent's midpoint close; simulated entries
    happen at the next completed minute's executable side. The single agent
    and its actual lifetime entry counter persist across the chronological split.
    A training position cannot consume or exit on a holdout bar.
    """
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("XAUUSD research quantity must be positive and finite")
    bars = validate_and_sort_candles(candles)
    warmup = validate_and_sort_candles(warmup_candles or [])
    _validate_nonoverlapping_warmup(bars, warmup)
    if len(bars) < 30:
        return {
            "status": "insufficient_history",
            "reason": "Fewer than 30 complete provider bid/ask M1 bars; no return estimate",
            "execution_validated": False,
            "strategy_changed": False,
            "trades": [],
            "overall": _fold_metrics([]),
            "train": _fold_metrics([]),
            "out_of_sample": _fold_metrics([]),
        }
    warmup_closes = [
        _midpoint_close(bar) for bar in warmup
        if _within_entry_session(_format_utc_timestamp(_bar_observation_time(bar["time"])))
    ]
    if len(warmup_closes) < 26:
        return {
            "status": "insufficient_ema_warmup",
            "reason": "Fewer than 26 complete pre-sample OANDA session bars for a meaningful EMA-26 warmup; no success ratio reported",
            "execution_validated": False,
            "strategy_changed": False,
            "trades": [],
            "overall": _fold_metrics([]),
            "train": _fold_metrics([]),
            "out_of_sample": _fold_metrics([]),
            "warmup_session_bars": len(warmup_closes),
        }
    cut = max(1, int(len(bars) * TRAIN_FRACTION))
    # Entry signals must themselves be observable in the fold. Any trade that
    # is still open at the cut is closed out of the sample, never at a
    # holdout-side price.
    agent = XAUUSDAgent()
    alpha_12 = 2 / 13
    alpha_26 = 2 / 27
    agent.ema_12 = warmup_closes[0]
    agent.ema_26 = warmup_closes[0]
    for close in warmup_closes[1:]:
        agent.ema_12 = close * alpha_12 + agent.ema_12 * (1 - alpha_12)
        agent.ema_26 = close * alpha_26 + agent.ema_26 * (1 - alpha_26)
    agent_clock = [0.0]
    trades: list[dict[str, Any]] = []
    open_positions: dict[str, list[dict[str, Any]]] = {"train": [], "out_of_sample": []}
    discarded_pending: list[dict[str, Any]] = []
    counts = {
        "processed_complete_candles": len(bars),
        "session_candles": 0,
        "signals": 0,
        "signals_outside_entry_session": 0,
        "open_positions_at_sample_boundaries": 0,
        "skipped_overlapping_signals": 0,
        "unfilled_boundary_signals": 0,
    }
    active: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None

    from unittest.mock import patch

    with patch("agents.xauusd_baseline.time.time", side_effect=lambda: agent_clock[0]):
        for index, bar in enumerate(bars):
            observation_time = _bar_observation_time(bar["time"])
            fold = "train" if index < cut else "out_of_sample"

            if index == cut:
                if active is not None:
                    active["status"] = "OPEN_AT_TRAIN_HOLDOUT_BOUNDARY_UNREALIZED_ONLY"
                    active["mark_time"] = _format_utc_timestamp(
                        _bar_observation_time(bars[index - 1]["time"])
                    )
                    active["mark_price"] = round(
                        bars[index - 1]["bid_close"]
                        if active["signal"] == Signal.BUY.value
                        else bars[index - 1]["ask_close"],
                        8,
                    )
                    open_positions["train"].append(active)
                    counts["open_positions_at_sample_boundaries"] += 1
                    active = None
                if pending is not None:
                    discarded_pending.append({
                        "signal_time": pending["signal_time"],
                        "signal_candle_open_time": pending["signal_candle_open_time"],
                        "status": "UNFILLED_TRAIN_SIGNAL_AT_HOLDOUT_BOUNDARY",
                        "counted_as_trade": False,
                    })
                    counts["unfilled_boundary_signals"] += 1
                    pending = None

            # The application observes complete OHLC at bar close, while its
            # paper-feeder still monitors already-open positions outside its
            # new-entry session.
            agent_clock[0] = observation_time.timestamp()

            if active is not None:
                exit_event = _exit_bar(active, bar)
                if exit_event is not None:
                    pnl = _trade_pnl(active, float(exit_event["price"]))
                    trades.append({
                        **active,
                        "exit_time": bar["time"],
                        "exit_bar_open_time": bar["time"],
                        "exit_time_basis": (
                            "provider_candle_open_timestamp; exact intrabar threshold-crossing "
                            "time is unavailable from OHLC"
                        ),
                        "exit_price": round(float(exit_event["price"]), 8),
                        "exit_reason": exit_event["reason"],
                        "pnl_usd": round(pnl, 8),
                        "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                        "status": "CLOSED",
                    })
                    active = None
                # Like the live feeder, observing or closing an already-open
                # position uses this minute; analyze resumes on the next one.
                continue

            if pending is not None:
                entry_signal = pending
                pending = None
                signal = entry_signal["signal"]
                entry_price = bar["ask_open"] if signal == Signal.BUY.value else bar["bid_open"]
                direction = 1 if signal == Signal.BUY.value else -1
                distance_to_stop = float(agent.stop_loss_pips)
                target = entry_price + direction * float(agent.target_pips)
                stop = entry_price - direction * distance_to_stop
                # Opens outside configured UTC entry hours cannot be filled by
                # the application; do not backfill to a later, better price.
                if not _within_entry_session(bar["time"]):
                    discarded_pending.append({
                        "signal_time": entry_signal["signal_time"],
                        "signal_candle_open_time": entry_signal["signal_candle_open_time"],
                        "status": "NEXT_BAR_ENTRY_OUTSIDE_CONFIGURED_SESSION",
                        "counted_as_trade": False,
                    })
                    continue
                active = {
                    "signal_time": entry_signal["signal_time"],
                    "signal_candle_open_time": entry_signal["signal_candle_open_time"],
                    "entry_time": bar["time"],
                    "entry_bar_open_time": bar["time"],
                    "entry_time_basis": "modeled_fill_at_next_provider_M1_candle_open; not a recorded broker fill",
                    "signal": signal,
                    "entry_price": round(entry_price, 8),
                    "stop_price": round(stop, 8),
                    "target_price": round(target, 8),
                    "quantity": quantity,
                    "quantity_basis": "configured backend paper-trade quantity, units (100)",
                    "currency": "USD",
                    "fold": fold,
                    "execution_model": "next_complete_M1_open_OANDA_bid_ask",
                }
                # Conservatively allow a subsequent intraminute stop/target on
                # the entry bar itself, with the stop winning any ambiguity.
                exit_event = _exit_bar(active, bar)
                if exit_event is not None:
                    pnl = _trade_pnl(active, float(exit_event["price"]))
                    trades.append({
                        **active,
                        "exit_time": bar["time"],
                        "exit_bar_open_time": bar["time"],
                        "exit_time_basis": (
                            "provider_candle_open_timestamp; exact intrabar threshold-crossing "
                            "time is unavailable from OHLC"
                        ),
                        "exit_price": round(float(exit_event["price"]), 8),
                        "exit_reason": exit_event["reason"],
                        "pnl_usd": round(pnl, 8),
                        "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                        "status": "CLOSED",
                    })
                    active = None
                # Do not call analyze twice during one provider candle.
                continue

            if not _within_entry_session(_format_utc_timestamp(observation_time)):
                continue

            counts["session_candles"] += 1
            decision = agent.analyze({"close": _midpoint_close(bar)})
            if decision is Signal.HOLD:
                continue
            if decision not in (Signal.BUY, Signal.SELL):
                continue
            counts["signals"] += 1
            signal = decision.value
            next_index = index + 1
            signal_time = _format_utc_timestamp(observation_time)
            if next_index >= len(bars) or next_index == cut:
                counts["unfilled_boundary_signals"] += 1
                discarded_pending.append({
                    "signal_time": signal_time,
                    "signal_candle_open_time": bar["time"],
                    "status": "SIGNAL_AT_SAMPLE_END_NO_TRADE",
                    "counted_as_trade": False,
                })
                continue
            if not _within_entry_session(bars[next_index]["time"]):
                counts["signals_outside_entry_session"] += 1
                continue
            if next_index < cut and bars[next_index]["time"] == bars[index]["time"]:
                counts["skipped_overlapping_signals"] += 1
                continue
            pending = {
                "signal": signal,
                "signal_time": signal_time,
                "signal_candle_open_time": bar["time"],
            }

    if active is not None:
        endpoint = bars[cut - 1] if active.get("fold") == "train" else bars[-1]
        position_status = (
            "OPEN_AT_TRAIN_HOLDOUT_BOUNDARY_UNREALIZED_ONLY"
            if active.get("fold") == "train"
            else "OPEN_AT_SAMPLE_END_UNREALIZED_ONLY"
        )
        active["status"] = position_status
        active["mark_time"] = _format_utc_timestamp(_bar_observation_time(endpoint["time"]))
        active["mark_price"] = round(
            endpoint["bid_close"] if active["signal"] == Signal.BUY.value else endpoint["ask_close"],
            8,
        )
        open_positions[active["fold"]].append(active)
        counts["open_positions_at_sample_boundaries"] += 1
    if pending is not None:
        counts["unfilled_boundary_signals"] += 1
        discarded_pending.append({
            "signal_time": pending["signal_time"],
            "signal_candle_open_time": pending["signal_candle_open_time"],
            "status": "SIGNAL_AT_SAMPLE_END_NO_TRADE",
            "counted_as_trade": False,
        })

    train = [trade for trade in trades if trade["fold"] == "train"]
    holdout = [trade for trade in trades if trade["fold"] == "out_of_sample"]
    metric = _fold_metrics(trades)
    out_sample_metric = _fold_metrics(holdout)
    adequate = out_sample_metric["closed_trades"] >= MIN_HOLDOUT_TRADES_FOR_ADEQUACY
    return {
        "status": "evaluated_bar_model" if adequate else "insufficient_holdout_sample",
        "performance_claim_status": (
            "research_estimate_only" if adequate else "no_statistically_reliable_success_ratio"
        ),
        "adequate_minimum_holdout_sample": adequate,
        "minimum_holdout_trades_for_adequacy": MIN_HOLDOUT_TRADES_FOR_ADEQUACY,
        "execution_validated": False,
        "strategy_changed": False,
        "counted_toward_paper_win_targets": False,
        "total_complete_bars": len(bars),
        "warmup_bars_before_sample": len(warmup),
        "warmup_session_bars_applied_to_ema": len(warmup_closes),
        "split_bar_index": cut,
        "training_fraction": TRAIN_FRACTION,
        "holdout_fraction": 1 - TRAIN_FRACTION,
        "overall": metric,
        "train": _fold_metrics(train),
        "out_of_sample": out_sample_metric,
        "trades": trades,
        "open_positions_by_fold": open_positions,
        "unfilled_signals": discarded_pending,
        "diagnostics": counts,
        "agent_live_parameter_values": {
            "ema_12_period": 12,
            "ema_26_period": 26,
            "min_ema_separation_usd_oz": agent.min_ema_separation,
            "close_confirmation_buffer_usd_oz": agent.confirmation_buffer,
            "stop_distance_usd_oz": agent.stop_loss_pips,
            "target_distance_usd_oz": agent.target_pips,
            "entry_cooldown_seconds": agent.entry_cooldown,
            "max_trades_per_agent_process": agent.max_trades_per_day,
            "actual_agent_trade_count_at_sample_end": agent.open_trade_count,
            "nominal_signal_confirmation_count": agent.signal_confirmation_count,
            "nominal_signal_confirmation_count_used_by_analyze": False,
        },
        "chronology": (
            "Signals are scored in the first 70% of available M1 bars. Open training positions "
            "and pending signals are marked/discarded at the 70% boundary; neither can exit or "
            "enter using a holdout bar. The original agent instance and its lifetime trade cap "
            "continue unchanged into the flat-position, chronologically later holdout."
        ),
    }


def run_live_xauusd_backtest(
    *,
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
    now: datetime | None = None,
    session: Any = requests,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fetch and score the last 90 days from authenticated OANDA practice candles."""
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    floor_now = generated_at.replace(second=0, microsecond=0)
    provider_retrieval_end = floor_now - timedelta(minutes=2)
    sample_start = floor_now - timedelta(days=SAMPLE_DAYS)
    fetch_start = sample_start - timedelta(days=EMA_WARMUP_DAYS)
    destination = Path(evidence_dir)
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": generated_at.isoformat(),
        "provider": "OANDA",
        "environment": "practice",
        "instrument": INSTRUMENT,
        "currency": "USD",
        "granularity": GRANULARITY,
        "source_endpoint": "/v3/instruments/XAU_USD/candles",
        "requested_price_components": ["bid", "ask"],
        "requested_smoothed_candles": False,
        "history_window_days": SAMPLE_DAYS,
        "warmup_history_days_requested": EMA_WARMUP_DAYS,
        "sample_start_inclusive": sample_start.isoformat(),
        "sample_end_exclusive": floor_now.isoformat(),
        "provider_retrieval_end_exclusive": provider_retrieval_end.isoformat(),
        "split": "chronological first 70% train, last 30% out of sample",
        "strategy_changed": False,
        "execution_validated": False,
        "counted_toward_paper_win_targets": False,
        "status": "blocked",
        "paper_entries_remain_blocked": True,
        "live_orders_enabled": False,
    }
    token = _read_access_token()
    if not token:
        report["reason"] = "OANDA practice-history token is not configured; no history was queried"
        _atomic_write_report(destination, report)
        return report

    try:
        rows = validate_and_sort_candles(
            _fetch_historical_candles(
                token,
                start=fetch_start,
                end=provider_retrieval_end,
                session=session,
                sleep=sleep,
            )
        )
        token = ""
        warmup_rows = [row for row in rows if _timestamp(row["time"]) < sample_start]
        sample_rows = [row for row in rows if sample_start <= _timestamp(row["time"]) < floor_now]
        if len(sample_rows) < 30:
            raise XAUHistoryError(
                "OANDA returned fewer than 30 complete, genuine in-window M1 candles; no success ratio reported"
            )
        if _timestamp(sample_rows[-1]["time"]) < floor_now - timedelta(hours=73):
            raise XAUHistoryError(
                "OANDA historical candles do not reach a recent enough complete market session; no current-window success ratio reported"
            )
        evidence = _store_history(destination, rows)
        report.update(evidence)
        report["first_provider_candle_utc"] = rows[0]["time"]
        report["last_provider_candle_utc"] = rows[-1]["time"]
        report["complete_sample_candles"] = len(sample_rows)
        report["complete_pre_sample_warmup_candles"] = len(warmup_rows)
        # Warm up only the strategy EMAs on earlier provider session closes;
        # keep all counted research signals inside the actual 90-day window.
        result = evaluate_xauusd(
            sample_rows, warmup_candles=warmup_rows, quantity=100.0
        )
        result["train_cut_provider_timestamp"] = sample_rows[result["split_bar_index"]]["time"]
        result["last_complete_sample_provider_timestamp"] = sample_rows[-1]["time"]
        result["entry_size_configuration"] = {
            "paper_quantity": 100,
            "units": "existing backend paper_trade quantity",
            "strategy_lot_size_attribute": getattr(XAUUSDAgent(), "lot_size", None),
            "strategy_lot_size_comment": "Existing XAUUSD agent describes 1.0 lot as 100 oz",
            "note": (
                "PnL uses 100 existing backend quantity units; broker-specific unit-to-ounce "
                "conversion is not assumed. The agent's lot_size attribute is not the quantity "
                "used by the existing main.py XAUUSD paper-entry branch."
            ),
        }
        result["strategy_execution_assumptions"] = {
            "signal_feed": "midpoint of genuine OANDA bid/ask M1 closes",
            "signal_timing": "OANDA bar time is the bar OPEN; signals, agent time.time(), and entry-window eligibility use bar OPEN plus one M1 interval, when the completed close is observable",
            "indicator_replay": "calls the unmodified XAUUSDAgent.analyze on complete one-minute closes only when the close-observation time is inside the existing 16:00–23:00 UTC entry window",
            "fills": "next complete M1 candle's actual provider OPEN time, using executable bid/ask open; BUY fills at ask, SELL fills at bid",
            "exits": "BUY closes at historical bid; SELL closes at historical ask; exit records retain the actual provider candle OPEN timestamp because the exact intrabar level-crossing time is unknown",
            "open_position_monitoring": "Existing positions continue to be checked on complete candles outside the new-entry window, as the live feeder monitors open trades before checking its entry-hours gate",
            "ambiguous_same_minute_stop_and_target": "stop first; no synthetic intrabar price path",
            "position_limit": "one simulated open position; original agent lifetime maximum of three accepted signals is preserved; its code does not reset this counter daily",
            "configured_entry_hours": "16:00 inclusive to 23:00 exclusive UTC, matching main._market_hours_open for XAUUSD",
            "signal_confirmation": "do not invent the configured two-signal confirmation; the existing analyze method does not implement it",
            "spread": "captured directly by entry and exit prices from genuine OANDA bid/ask OHLC",
            "fees_and_financing": "not modeled; no account fee, swap, home-currency or financing schedule was verified",
            "limitations": [
                "The live strategy consumes repeated five-second quotes; the provider history is one-minute OHLC. Signals become observable at each candle OPEN + 1 minute; exact tick-level signal timing and EMA paths cannot be reproduced. This is an explicitly labeled one-minute signal approximation, not exact tick parity.",
                "An exit's provider candle OPEN timestamp identifies the OHLC bar containing a modeled exit, not the instant its stop/target was crossed; OHLC cannot establish that intrabar time.",
                "Daily max_trades_per_day field is actually a process-lifetime counter in the unchanged analyze implementation. This replay preserves the real behavior, so up to three signals are counted for the process, not three resettable daily trades.",
                "OANDA practice pricing is genuine OANDA market history but does not establish live-account authorization or actual live fills.",
                "A next-minute OHLC bid/ask entry is a modeled executable-side bar fill, not a recorded historical OANDA fill or proof of realistic slippage.",
                "No statistical or execution validation is claimed. Win rate is calculated only from closed trades, with open/boundary trades excluded.",
            ],
            "execution_validated": False,
            "paper_entries_remain_blocked": True,
        }
        report.update(result)
        report["status"] = result["status"]
        report["data_source"] = "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC"
    except (XAUHistoryError, OSError, requests.RequestException, ValueError, KeyError, TypeError) as exc:
        # All thrown provider failures are sanitized to controlled error text;
        # do not write provider responses, URLs, headers, or account identity.
        token = ""
        report["status"] = "blocked"
        report["reason"] = str(exc)
        report["execution_validated"] = False
        report["counted_toward_paper_win_targets"] = False
        report["win_rate_pct"] = None
        report["total_pnl_usd"] = None
        _atomic_write_report(destination, report)
        return report
    _atomic_write_report(destination, report)
    return report


def _atomic_write_report(destination: Path, report: dict[str, Any]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "xauusd_backtest.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_verified_saved_history(
    evidence_dir: Path, report: dict[str, Any]
) -> tuple[list[dict[str, Any]], str]:
    """Reload only the existing immutable OANDA CSV whose reported SHA matches."""
    filename = report.get("raw_data_file")
    expected_sha256 = report.get("sha256")
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
    ):
        raise XAUHistoryError("Saved XAUUSD evidence has no trustworthy raw-file identity")
    path = evidence_dir / filename
    try:
        contents = path.read_bytes()
    except OSError as exc:
        raise XAUHistoryError("Previously verified OANDA XAUUSD raw history is unavailable") from exc
    actual_sha256 = hashlib.sha256(contents).hexdigest()
    if actual_sha256 != expected_sha256:
        raise XAUHistoryError("Saved OANDA raw candle SHA-256 changed; refusing to refresh the report")

    try:
        reader = csv.DictReader(contents.decode("utf-8").splitlines())
        if reader.fieldnames is None or not set(CSV_FIELDS).issubset(reader.fieldnames):
            raise XAUHistoryError("Saved OANDA raw candle CSV columns do not match provider provenance")
        rows = []
        for raw in reader:
            if (
                raw.get("data_source") != "OANDA_PRACTICE_HISTORICAL"
                or raw.get("environment") != "practice"
                or raw.get("instrument") != INSTRUMENT
                or raw.get("complete") != "True"
            ):
                raise XAUHistoryError("Saved candle is not a verified complete OANDA practice bar")
            bar = dict(raw)
            bar["complete"] = True
            for field in OHLC_FIELDS:
                bar[field] = float(raw[field])
            rows.append(bar)
    except (UnicodeDecodeError, csv.Error, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, XAUHistoryError):
            raise
        raise XAUHistoryError("Saved verified OANDA historical CSV cannot be parsed") from exc
    normalized = validate_and_sort_candles(rows)
    if not normalized:
        raise XAUHistoryError("Saved OANDA raw historical CSV contains no complete candle data")
    if (
        normalized[0]["time"] != report.get("first_provider_candle_utc")
        or normalized[-1]["time"] != report.get("last_provider_candle_utc")
        or len(normalized) != report.get("complete_bid_ask_candles_saved")
    ):
        raise XAUHistoryError("Saved OANDA raw history does not match the original report provenance")
    return normalized, actual_sha256


def refresh_saved_xauusd_backtest(
    *, evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR
) -> dict[str, Any]:
    """Correct and rewrite results exclusively from the hash-verified saved raw CSV.

    This offline correction helper does not read tokens, construct an HTTP
    session, make provider requests, or modify the raw CSV.
    """
    destination = Path(evidence_dir)
    report_path = destination / "xauusd_backtest.json"
    try:
        original_bytes = report_path.read_bytes()
        report = json.loads(original_bytes)
        if (
            not isinstance(report, dict)
            or report.get("provider") != "OANDA"
            or report.get("environment") != "practice"
            or report.get("instrument") != INSTRUMENT
            or report.get("granularity") != GRANULARITY
            or report.get("requested_price_components") != ["bid", "ask"]
        ):
            raise XAUHistoryError("Existing XAUUSD report does not describe genuine OANDA practice bid/ask history")
        rows, verified_sha256 = _read_verified_saved_history(destination, report)
        sample_start = _timestamp(report["sample_start_inclusive"])
        sample_end = _timestamp(report["sample_end_exclusive"])
        retrieval_end = _timestamp(report["provider_retrieval_end_exclusive"])
        if (
            sample_end - sample_start != timedelta(days=SAMPLE_DAYS)
            or not sample_start < retrieval_end < sample_end
            or retrieval_end > _timestamp(rows[-1]["time"]) + timedelta(minutes=1)
        ):
            raise XAUHistoryError("Original OANDA 90-day sample boundaries do not match saved raw history")
        warmup_rows = [bar for bar in rows if _timestamp(bar["time"]) < sample_start]
        sample_rows = [
            bar for bar in rows
            if sample_start <= _timestamp(bar["time"]) < sample_end
        ]
        if (
            len(sample_rows) != report.get("complete_sample_candles")
            or len(warmup_rows) != report.get("complete_pre_sample_warmup_candles")
        ):
            raise XAUHistoryError("Original OANDA sample and warm-up bar counts do not match saved raw history")
        # Defense in depth: the warm-up must finish no later than the first
        # in-window provider bar's OPEN, not merely precede its OPEN timestamp.
        _validate_nonoverlapping_warmup(sample_rows, warmup_rows)
        result = evaluate_xauusd(sample_rows, warmup_candles=warmup_rows, quantity=100.0)
        result["train_cut_provider_timestamp"] = sample_rows[result["split_bar_index"]]["time"]
        result["last_complete_sample_provider_timestamp"] = sample_rows[-1]["time"]
        result["entry_size_configuration"] = {
            "paper_quantity": 100,
            "units": "existing backend paper_trade quantity",
            "strategy_lot_size_attribute": getattr(XAUUSDAgent(), "lot_size", None),
            "strategy_lot_size_comment": "Existing XAUUSD agent describes 1.0 lot as 100 oz",
            "note": (
                "PnL uses 100 existing backend quantity units; broker-specific unit-to-ounce "
                "conversion is not assumed. The agent's lot_size attribute is not the quantity "
                "used by the existing main.py XAUUSD paper-entry branch."
            ),
        }
        result["strategy_execution_assumptions"] = {
            "signal_feed": "midpoint of genuine OANDA bid/ask M1 closes",
            "signal_timing": "OANDA bar time is the bar OPEN; signals, agent time.time(), and entry-window eligibility use bar OPEN plus one M1 interval, when the completed close is observable",
            "indicator_replay": "calls the unmodified XAUUSDAgent.analyze on complete one-minute closes only when the close-observation time is inside the existing 16:00–23:00 UTC entry window",
            "fills": "next complete M1 candle's actual provider OPEN time, using executable bid/ask open; BUY fills at ask, SELL fills at bid",
            "exits": "BUY closes at historical bid; SELL closes at historical ask; exit records retain the actual provider candle OPEN timestamp because the exact intrabar level-crossing time is unknown",
            "open_position_monitoring": "Existing positions continue to be checked on complete candles outside the new-entry window, as the live feeder monitors open trades before checking its entry-hours gate",
            "ambiguous_same_minute_stop_and_target": "stop first; no synthetic intrabar price path",
            "position_limit": "one simulated open position; original agent lifetime maximum of three accepted signals is preserved; its code does not reset this counter daily",
            "configured_entry_hours": "16:00 inclusive to 23:00 exclusive UTC, checked against close-observation time for entries, matching main._market_hours_open for XAUUSD",
            "signal_confirmation": "do not invent the configured two-signal confirmation; the existing analyze method does not implement it",
            "spread": "captured directly by entry and exit prices from genuine OANDA bid/ask OHLC",
            "fees_and_financing": "not modeled; no account fee, swap, home-currency or financing schedule was verified",
            "limitations": [
                "The live strategy consumes repeated five-second quotes; the provider history is one-minute OHLC. Signals become observable at each candle OPEN + 1 minute; exact tick-level signal timing and EMA paths cannot be reproduced. This is an explicitly labeled one-minute signal approximation, not exact tick parity.",
                "An exit's provider candle OPEN timestamp identifies the OHLC bar containing a modeled exit, not the instant its stop/target was crossed; OHLC cannot establish that intrabar time.",
                "Daily max_trades_per_day field is actually a process-lifetime counter in the unchanged analyze implementation. This replay preserves the real behavior, so up to three signals are counted for the process, not three resettable daily trades.",
                "OANDA practice pricing is genuine OANDA market history but does not establish live-account authorization or actual live fills.",
                "A next-minute OHLC bid/ask entry is a modeled executable-side bar fill, not a recorded historical OANDA fill or proof of realistic slippage.",
                "No statistical or execution validation is claimed. Win rate is calculated only from closed trades, with open/boundary trades excluded.",
            ],
            "execution_validated": False,
            "paper_entries_remain_blocked": True,
        }
        report.update(result)
        report["status"] = result["status"]
        report["data_source"] = "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC"
        report["raw_data_file"] = Path(report["raw_data_file"]).name
        report["sha256"] = verified_sha256
        report["offline_report_refresh"] = {
            "raw_csv_hash_verified": True,
            "provider_requests_made": 0,
            "raw_csv_modified": False,
            "original_sample_start_preserved": sample_start.isoformat(),
            "original_sample_end_preserved": sample_end.isoformat(),
            "warmup_ended_at_or_before_first_sample_open": True,
        }
        _atomic_write_report(destination, report)
        return report
    except (XAUHistoryError, OSError, ValueError, KeyError, TypeError) as exc:
        # Fail closed: keep the original report and raw evidence intact if
        # provenance or the cached CSV cannot be verified.
        if isinstance(exc, XAUHistoryError):
            raise
        raise XAUHistoryError("Saved XAUUSD report or hash-verified OANDA evidence is malformed") from exc


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Backtest XAUUSD from OANDA practice history or replay hash-verified saved history offline."
    )
    parser.add_argument(
        "evidence_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_EVIDENCE_DIR,
        help="XAUUSD evidence directory",
    )
    parser.add_argument(
        "--replay-saved",
        action="store_true",
        help="Refresh the corrected report from the already saved SHA-256-verified candle CSV without networking",
    )
    args = parser.parse_args()
    report = (
        refresh_saved_xauusd_backtest(evidence_dir=args.evidence_dir)
        if args.replay_saved
        else run_live_xauusd_backtest(evidence_dir=args.evidence_dir)
    )
    summary: dict[str, Any] = {
        key: report.get(key) for key in (
            "provider",
            "environment",
            "instrument",
            "status",
            "complete_sample_candles",
            "complete_pre_sample_warmup_candles",
        )
    }
    result = report.get("out_of_sample", {})
    if result:
        summary["out_of_sample"] = {
            key: result.get(key)
            for key in ("closed_trades", "wins", "losses", "breakeven", "win_rate_pct", "net_pnl_usd")
        }
    if report.get("reason"):
        summary["reason"] = report["reason"]
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()