"""Preregistered XAUUSD trading-session comparison on saved OANDA bid/ask bars."""

from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from agents.base import Signal
from agents.xauusd import (
    DEFAULT_ENTRY_WINDOW,
    advance_completed_bar,
    entry_holding_deadline,
    entry_holding_exit_reason,
    entry_holding_policy_allows,
    initial_strategy_state,
    entry_window_day_coverage_minutes,
    entry_window_intervals_utc,
    entry_window_session_day,
    normalize_parameters,
    within_entry_window,
)
from agents.xauusd_highwin import (
    HIGHWIN_STRATEGY_DEFAULTS,
    advance_highwin_bar,
    highwin_entry_policy_allows,
    initial_highwin_state,
    normalize_highwin_parameters,
    register_highwin_entry,
)
from backtest.xauusd_evidence import (
    DEFAULT_EVIDENCE_DIR,
    XAUHistoryError,
    _exit_bar,
    _read_verified_saved_history,
    _timestamp,
)
from backtest.xauusd_optimization import (
    LOT_SIZE,
    QUANTITY_UNITS,
    _aggregate_minutes,
    _metrics,
    _prepare,
)


STUDY_NAME = "XAUUSD fixed-strategy trading-session comparison"
MAX_HOLD_MINUTES = 25
DAILY_ACCEPTED_ENTRY_LIMIT = 3
MIN_FIT_TRADES = 30
MIN_VALIDATION_TRADES = 20
MIN_PROFIT_FACTOR = 1.10
MAX_DRAWDOWN_USD = 3_000.0
MAX_DEVELOPMENT_P95_SPREAD_TO_TARGET_PCT = 25.0


def _session(
    name: str,
    day_timezone: str,
    clauses: list[dict[str, str]],
    *,
    mode: str = "any",
) -> dict[str, Any]:
    return {
        "name": name,
        "mode": mode,
        "day_timezone": day_timezone,
        "clauses": clauses,
    }


SESSION_WINDOWS: tuple[dict[str, Any], ...] = (
    _session(
        "Asia_Tokyo_09_18",
        "Asia/Tokyo",
        [{"timezone": "Asia/Tokyo", "start": "09:00", "end": "18:00"}],
    ),
    _session(
        "Europe_London_08_17",
        "Europe/London",
        [{"timezone": "Europe/London", "start": "08:00", "end": "17:00"}],
    ),
    _session(
        "US_New_York_08_17",
        "America/New_York",
        [{"timezone": "America/New_York", "start": "08:00", "end": "17:00"}],
    ),
    _session(
        "EU_US_Overlap",
        "Europe/London",
        [
            {"timezone": "Europe/London", "start": "08:00", "end": "17:00"},
            {"timezone": "America/New_York", "start": "08:00", "end": "17:00"},
        ],
        mode="all",
    ),
    _session(
        "EU_US_Union",
        "America/New_York",
        [
            {"timezone": "Europe/London", "start": "08:00", "end": "17:00"},
            {"timezone": "America/New_York", "start": "08:00", "end": "17:00"},
        ],
        mode="any",
    ),
    DEFAULT_ENTRY_WINDOW,
)


def fixed_strategies() -> list[dict[str, Any]]:
    """Exactly two fixed rulesets; no parameter tuning by session."""
    ema = normalize_parameters(
        {
            "signal_model": "ema_trend_continuation",
            "bar_interval_minutes": 1,
            "fast_ema": 12,
            "slow_ema": 26,
            "min_ema_separation_usd": 1.0,
            "confirmation_buffer_usd": 0.5,
            "confirmation_bars": 2,
            "stop_loss_usd_per_oz": 1.5,
            "take_profit_usd_per_oz": 5.0,
            "max_hold_minutes": MAX_HOLD_MINUTES,
            "allow_overnight": False,
            "max_trades_per_utc_day": DAILY_ACCEPTED_ENTRY_LIMIT,
            "count_signals_toward_daily_entry_cap": False,
            "emit_signals_after_daily_entry_cap": True,
            "position_quantity_units": QUANTITY_UNITS,
        }
    )
    highwin = normalize_highwin_parameters(
        {
            **HIGHWIN_STRATEGY_DEFAULTS,
            "bar_interval_minutes": 1,
            "rsi_period": 7,
            "rsi_reentry_threshold": 20,
            "bollinger_period": 20,
            "bollinger_stddev": 2.0,
            "regime_fast_ema": 20,
            "regime_slow_ema": 50,
            "max_range_ema_separation_usd": 2.0,
            "stop_loss_usd_per_oz": 1.5,
            "take_profit_usd_per_oz": 3.75,
            "max_hold_minutes": MAX_HOLD_MINUTES,
            "allow_overnight": False,
            "max_trades_per_utc_day": DAILY_ACCEPTED_ENTRY_LIMIT,
            "position_quantity_units": QUANTITY_UNITS,
        }
    )
    return [
        {
            "strategy_key": "EMA12_26_SHARED",
            "strategy_name": "Shared causal EMA-12/26 continuation",
            "parameters": ema,
            "maximum_stop_usd_per_oz": 1.5,
            "take_profit_usd_per_oz": 5.0,
        },
        {
            "strategy_key": "RSI_BB_EXISTING_BEST_COVERAGE_FIXED",
            "strategy_name": "Existing training-only best-coverage RSI/Bollinger rule",
            "parameters": highwin,
            "maximum_stop_usd_per_oz": 1.5,
            "take_profit_usd_per_oz": 3.75,
        },
    ]


def preregistered_candidates() -> list[dict[str, Any]]:
    strategies = fixed_strategies()
    return [
        {
            "candidate_id": f"{strategy['strategy_key']}__{window['name']}",
            "strategy_key": strategy["strategy_key"],
            "strategy_name": strategy["strategy_name"],
            "window": window,
            "parameters": (
                normalize_highwin_parameters(
                    {**strategy["parameters"], "entry_window": window}
                )
                if strategy["strategy_key"].startswith("RSI_")
                else normalize_parameters(
                    {**strategy["parameters"], "entry_window": window}
                )
            ),
            "maximum_stop_usd_per_oz": strategy["maximum_stop_usd_per_oz"],
            "take_profit_usd_per_oz": strategy["take_profit_usd_per_oz"],
        }
        for strategy in strategies
        for window in SESSION_WINDOWS
    ]


def _within_window(timestamp: datetime, window: dict[str, Any]) -> bool:
    return within_entry_window(timestamp, {"entry_window": window})


def _session_day(timestamp: datetime, window: dict[str, Any]) -> date:
    return entry_window_session_day(timestamp, window)


def _can_enter(entry_time: datetime, window: dict[str, Any]) -> bool:
    return entry_holding_policy_allows(
        entry_time,
        MAX_HOLD_MINUTES,
        window,
        rollover_buffer_minutes=1,
    )


def _holding_exit_reason(
    entry_time: datetime,
    observed_at: datetime,
    parameters: dict[str, Any],
    window: dict[str, Any],
) -> str | None:
    return entry_holding_exit_reason(
        entry_time,
        observed_at,
        parameters["max_hold_minutes"],
        window,
        rollover_buffer_minutes=1,
    )


def _source_mid_bar(prepared: dict[str, Any]) -> dict[str, Any]:
    row = prepared["source"]
    return {
        "observed_at": prepared["observed_at"].isoformat(),
        "close": prepared["mid_close"],
        "high": (float(row["bid_high"]) + float(row["ask_high"])) / 2,
        "low": (float(row["bid_low"]) + float(row["ask_low"])) / 2,
    }


def _midnight_cut(bars: Sequence[dict[str, Any]], desired_index: int) -> int:
    """Find a split by timestamps only, at the next UTC calendar date."""
    if not bars:
        return 0
    index = min(max(0, desired_index), len(bars) - 1)
    starting_day = _timestamp(bars[index]["time"]).date()
    for candidate in range(index + 1, len(bars)):
        if _timestamp(bars[candidate]["time"]).date() > starting_day:
            return candidate
    return min(max(1, desired_index), len(bars) - 1)


def _spread_p95(
    development_bars: Sequence[dict[str, Any]],
    window: dict[str, Any],
) -> dict[str, Any]:
    values = []
    for row in development_bars:
        opened = _timestamp(row["time"])
        observed = opened + timedelta(minutes=1)
        if _within_window(observed, window):
            spread = float(row["ask_close"]) - float(row["bid_close"])
            if math.isfinite(spread) and spread >= 0:
                values.append(spread)
    if not values:
        return {
            "observations": 0,
            "median_usd_per_oz": None,
            "p95_usd_per_oz": None,
        }
    values.sort()
    return {
        "observations": len(values),
        "median_usd_per_oz": round(statistics.median(values), 8),
        "p95_usd_per_oz": round(values[math.ceil(0.95 * len(values)) - 1], 8),
    }


def _session_trade_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = _metrics(trades)
    metrics["gross_quote_side_pnl_before_unverified_costs_usd"] = metrics["net_pnl_usd"]
    metrics["pnl_basis"] = (
        "gross quote-side USD P&L; historical executable bid/ask includes observed spread, "
        "but unverified commission and financing are not included"
    )
    return metrics


def _simulate_session(
    bars: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    boundaries: Sequence[int] = (),
) -> dict[str, Any]:
    """Causal shared-reducer replay with local-session dates and accepted-entry cap."""
    parameters = candidate["parameters"]
    window = candidate["window"]
    interval_minutes = parameters["bar_interval_minutes"]
    highwin = candidate["strategy_key"].startswith("RSI_")
    prepared_source = _prepare(bars)
    boundary_times = [
        prepared_source[index]["open_time"]
        for index in boundaries
        if 0 <= index < len(prepared_source)
    ]
    study_bars, partial_bars = _aggregate_minutes(bars, interval_minutes)
    prepared = _prepare(study_bars, timeframe_minutes=interval_minutes)
    warm_bars, partial_warm = _aggregate_minutes(warmup, interval_minutes)
    prepared_warm = _prepare(warm_bars, timeframe_minutes=interval_minutes)
    minimum_warm = (
        max(
            parameters["rsi_period"] + 1,
            parameters["bollinger_period"],
            parameters["regime_slow_ema"],
        )
        if highwin
        else parameters["slow_ema"]
    )
    if len(prepared_warm) < minimum_warm:
        raise XAUHistoryError(
            f"Session replay requires {minimum_warm} pre-sample M{interval_minutes} warmup bars"
        )

    state = initial_highwin_state() if highwin else initial_strategy_state()
    reducer = advance_highwin_bar if highwin else advance_completed_bar
    for item in prepared_warm:
        reducer(state, _source_mid_bar(item), parameters)

    cuts = []
    for boundary_time in boundary_times:
        index = next(
            (i for i, item in enumerate(prepared) if item["open_time"] >= boundary_time),
            None,
        )
        if index is not None and 0 < index < len(prepared):
            cuts.append(index)
    cuts = sorted(set(cuts))
    partition = cut_cursor = 0
    active: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    daily_activity: dict[tuple[int, date], dict[str, int]] = {}
    entries_by_day: dict[date, int] = {}
    fold_signals = [0 for _ in range(len(cuts) + 1)]
    fold_closed = [0 for _ in range(len(cuts) + 1)]
    suppressed_open = suppressed_daily_cap = unfilled = 0
    time_exits = 0

    def activity(day: date, fold: int) -> dict[str, int]:
        return daily_activity.setdefault(
            (fold, day),
            {"complete_window_bars": 0, "raw_setups": 0, "calls": 0, "entries": 0, "closed": 0},
        )

    for index, item in enumerate(prepared):
        if cut_cursor < len(cuts) and index == cuts[cut_cursor]:
            if active is not None:
                unresolved.append(
                    {
                        "fold": partition,
                        "entry_time": active["entry_time"],
                        "status": "OPEN_AT_RESEARCH_BOUNDARY_UNREALIZED",
                        "mark_time": prepared[index - 1]["observed_at"].isoformat(),
                    }
                )
                active = None
            if pending is not None:
                unfilled += 1
                pending = None
            partition += 1
            cut_cursor += 1

        row = item["source"]
        observation = item["observed_at"]
        day = _session_day(observation, window)
        if _within_window(observation, window):
            activity(day, partition)["complete_window_bars"] += 1

        if pending is not None:
            intent, pending = pending, None
            entry_time = item["open_time"]
            entry_day = _session_day(entry_time, window)
            can_enter = (
                intent["fold"] == partition
                and intent["session_day"] == entry_day
                and _within_window(entry_time, window)
                and _can_enter(entry_time, window)
                and entries_by_day.get(entry_day, 0) < DAILY_ACCEPTED_ENTRY_LIMIT
            )
            if can_enter:
                can_enter = (
                    register_highwin_entry(state, entry_time, parameters)
                    if highwin
                    else True
                )
            if not can_enter:
                unfilled += 1
            else:
                entries_by_day[entry_day] = entries_by_day.get(entry_day, 0) + 1
                if not highwin:
                    state["daily_entry_count"] += 1
                activity(entry_day, partition)["entries"] += 1
                direction = 1 if intent["signal"] == Signal.BUY.value else -1
                side = "ask" if direction > 0 else "bid"
                entry_price = float(row[f"{side}_open"])
                stop = float(parameters["stop_loss_usd_per_oz"])
                target = float(parameters["take_profit_usd_per_oz"])
                active = {
                    "candidate_id": candidate["candidate_id"],
                    "strategy_key": candidate["strategy_key"],
                    "session_name": window["name"],
                    "session_day": entry_day.isoformat(),
                    "signal": intent["signal"],
                    "side": direction,
                    "signal_observed_at": intent["signal_observed_at"],
                    "entry_time": row["time"],
                    "entry_time_basis": "next complete genuine OANDA strategy candle open",
                    "entry_price": round(entry_price, 8),
                    "stop_price": round(entry_price - direction * stop, 8),
                    "target_price": round(entry_price + direction * target, 8),
                    "stop_loss_usd_per_oz": stop,
                    "take_profit_usd_per_oz": target,
                    "max_hold_minutes": MAX_HOLD_MINUTES,
                    "allow_overnight": False,
                    "quantity_units": QUANTITY_UNITS,
                    "lot_size_ounces": 100,
                    "fold": partition,
                    "entry_index": index,
                }
                immediate = _exit_bar(active, row)
                if immediate is not None:
                    pnl = (float(immediate["price"]) - entry_price) * QUANTITY_UNITS * direction
                    trades.append(
                        {
                            **active,
                            "exit_observed_at": observation.isoformat(),
                            "exit_price": round(float(immediate["price"]), 8),
                            "exit_reason": immediate["reason"],
                            "exit_time_basis": "actual executable-side candle OHLC; intrabar trigger time unknown",
                            "pnl_usd": round(pnl, 8),
                            "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                            "status": "CLOSED",
                            "holding_complete_strategy_bars": 1,
                        }
                    )
                    fold_closed[partition] += 1
                    activity(entry_day, partition)["closed"] += 1
                    active = None
        elif active is not None:
            exit_event = _exit_bar(active, row)
            parsed_entry = _timestamp(active["entry_time"])
            reason = _holding_exit_reason(
                parsed_entry,
                observation,
                parameters,
                window,
            )
            if exit_event is None and reason is not None:
                cross_session_day = _session_day(
                    observation, window
                ) != date.fromisoformat(active["session_day"])
                exit_side = "bid" if active["side"] > 0 else "ask"
                risk_deadline = entry_holding_deadline(
                    parsed_entry,
                    window,
                    rollover_buffer_minutes=1,
                )
                max_hold_deadline = parsed_entry + timedelta(
                    minutes=parameters["max_hold_minutes"]
                )
                nominal_deadline = (
                    risk_deadline[0]
                    if risk_deadline is not None
                    and risk_deadline[0] < max_hold_deadline
                    else max_hold_deadline
                )
                late_quote_gap = observation > nominal_deadline
                exit_event = {
                    "price": float(
                        row[
                            f"{exit_side}_{'open' if cross_session_day or late_quote_gap else 'close'}"
                        ]
                    ),
                    "reason": (
                        "no_carry_exit_after_deadline_quote_gap"
                        if late_quote_gap or cross_session_day
                        else reason
                    ),
                }
            if exit_event is not None:
                is_time_exit = exit_event["reason"] in {
                    "maximum_holding_period_exit",
                    "session_close_forced_exit",
                    "ny17_rollover_buffer_forced_exit",
                    "no_overnight_forced_exit",
                    "no_carry_exit_after_deadline_quote_gap",
                }
                time_exits += is_time_exit
                pnl = (
                    (float(exit_event["price"]) - active["entry_price"])
                    * QUANTITY_UNITS
                    * active["side"]
                )
                trades.append(
                    {
                        **active,
                        "exit_observed_at": observation.isoformat(),
                        "exit_price": round(float(exit_event["price"]), 8),
                        "exit_reason": exit_event["reason"],
                        "exit_time_basis": (
                            "first completed strategy-bar exit-side close at/after 25-minute/session deadline"
                            if exit_event["reason"]
                            in {
                                "maximum_holding_period_exit",
                                "session_close_forced_exit",
                                "ny17_rollover_buffer_forced_exit",
                                "no_carry_exit_after_deadline_quote_gap",
                            }
                            else "first available exit-side open after an unexpected no-carry deadline/data gap"
                            if exit_event["reason"]
                            in {"no_overnight_forced_exit", "no_carry_exit_after_deadline_quote_gap"}
                            else "actual executable-side candle OHLC; intrabar trigger time unknown"
                        ),
                        "pnl_usd": round(pnl, 8),
                        "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                        "status": "CLOSED",
                        "holding_complete_strategy_bars": index - active["entry_index"] + 1,
                    }
                )
                fold_closed[active["fold"]] += 1
                activity(day, partition)["closed"] += 1
                active = None

        signal = reducer(state, _source_mid_bar(item), parameters)
        if signal is None:
            continue
        fold_signals[partition] += 1
        activity(day, partition)["raw_setups"] += 1
        if active is not None:
            suppressed_open += 1
            continue
        if entries_by_day.get(day, 0) >= DAILY_ACCEPTED_ENTRY_LIMIT:
            suppressed_daily_cap += 1
            continue
        following = index + 1
        if (
            following >= len(prepared)
            or (cut_cursor < len(cuts) and following == cuts[cut_cursor])
            or prepared[following]["minute_index"] != item["minute_index"] + 1
            or _session_day(prepared[following]["open_time"], window) != day
            or not _within_window(prepared[following]["open_time"], window)
            or not _can_enter(prepared[following]["open_time"], window)
        ):
            unfilled += 1
            continue
        pending = {
            "signal": signal,
            "signal_observed_at": observation.isoformat(),
            "session_day": day,
            "fold": partition,
        }
        activity(day, partition)["calls"] += 1

    if active is not None:
        unresolved.append(
            {
                "fold": partition,
                "entry_time": active["entry_time"],
                "status": "OPEN_AT_SAMPLE_END_UNREALIZED",
            }
        )
    if pending is not None:
        unfilled += 1

    folds = []
    coverage_folds = []
    for fold in range(len(cuts) + 1):
        fold_trades = [trade for trade in trades if trade["fold"] == fold]
        folds.append(_session_trade_metrics(fold_trades))
        fold_days = sorted(day for fold_key, day in daily_activity if fold_key == fold)
        if fold_days:
            first_day, last_day = fold_days[0], fold_days[-1]
            weekday_count = sum(
                (first_day + timedelta(days=offset)).weekday() < 5
                for offset in range((last_day - first_day).days + 1)
            )
        else:
            first_day = last_day = None
            weekday_count = 0
        expected_bars_by_day = {
            day: entry_window_day_coverage_minutes(day, window) // interval_minutes
            for day in fold_days
        }
        eligible_days = [
            day
            for day in fold_days
            if expected_bars_by_day[day] > 0
            and daily_activity[(fold, day)]["complete_window_bars"]
            >= math.ceil(0.60 * expected_bars_by_day[day])
        ]
        calls = [daily_activity[(fold, day)]["calls"] for day in eligible_days]
        entries = [daily_activity[(fold, day)]["entries"] for day in eligible_days]
        closed = [daily_activity[(fold, day)]["closed"] for day in eligible_days]
        raw = [daily_activity[(fold, day)]["raw_setups"] for day in eligible_days]

        def daily_stats(values: list[int]) -> dict[str, Any]:
            return {
                "mean": round(statistics.mean(values), 4) if values else None,
                "median": statistics.median(values) if values else None,
                "histogram_0_1_2_3": {
                    str(count): sum(value == count for value in values)
                    for count in (0, 1, 2, 3)
                },
                "zero_days": sum(value == 0 for value in values),
            }

        coverage_folds.append(
            {
                "session_day_timezone": window["day_timezone"],
                "eligible_market_days": len(eligible_days),
                "session_days_with_any_bars": len(fold_days),
                "weekday_session_days_in_period": weekday_count,
                "eligible_market_day_coverage_pct_of_weekdays": (
                    round(100 * len(eligible_days) / weekday_count, 2)
                    if weekday_count
                    else None
                ),
                "partial_or_undercovered_session_days": len(fold_days) - len(eligible_days),
                "expected_complete_strategy_bars_per_session_day": (
                    round(statistics.mean(expected_bars_by_day.values()), 2)
                    if expected_bars_by_day
                    else None
                ),
                "eligible_session_day_range": (
                    {"first": first_day.isoformat(), "last": last_day.isoformat()}
                    if first_day is not None
                    else None
                ),
                "actionable_review_calls_per_eligible_day": daily_stats(calls),
                "raw_setups_per_eligible_day": daily_stats(raw),
                "accepted_entries_per_eligible_day": daily_stats(entries),
                "closed_trades_per_eligible_day": daily_stats(closed),
                "daily_accepted_entry_limit": DAILY_ACCEPTED_ENTRY_LIMIT,
            }
        )

    return {
        "overall": _session_trade_metrics(trades),
        "folds": folds,
        "coverage_by_fold": coverage_folds,
        "trades": trades,
        "unresolved_positions": unresolved,
        "unfilled_or_boundary_signals": unfilled,
        "raw_signals_suppressed_while_position_open": suppressed_open,
        "raw_signals_suppressed_after_three_accepted_entries": suppressed_daily_cap,
        "signals_by_fold": fold_signals,
        "closed_trade_counts_by_fold": fold_closed,
        "time_based_exits": time_exits,
        "strategy_bar_count": len(prepared),
        "requested_interval_minutes": interval_minutes,
        "discarded_partial_interval_bars": partial_bars,
        "discarded_partial_warmup_bars": partial_warm,
        "warmup_strategy_bars": len(prepared_warm),
    }


def _pf_passes(metrics: dict[str, Any]) -> bool:
    factor = metrics["profit_factor"]
    return (
        metrics["wins"] > 0 and metrics["losses"] == 0
        if factor is None
        else factor > MIN_PROFIT_FACTOR
    )


def _candidate_passes(
    fit: dict[str, Any],
    validation: dict[str, Any],
    spread_to_target_pct: float | None,
) -> bool:
    return (
        fit["closed_trades"] >= MIN_FIT_TRADES
        and validation["closed_trades"] >= MIN_VALIDATION_TRADES
        and fit["net_pnl_usd"] is not None
        and fit["net_pnl_usd"] > 0
        and validation["net_pnl_usd"] is not None
        and validation["net_pnl_usd"] > 0
        and _pf_passes(fit)
        and _pf_passes(validation)
        and fit["max_closed_trade_drawdown_usd"] is not None
        and fit["max_closed_trade_drawdown_usd"] <= MAX_DRAWDOWN_USD
        and validation["max_closed_trade_drawdown_usd"] is not None
        and validation["max_closed_trade_drawdown_usd"] <= MAX_DRAWDOWN_USD
        and spread_to_target_pct is not None
        and spread_to_target_pct <= MAX_DEVELOPMENT_P95_SPREAD_TO_TARGET_PCT
    )


def _candidate_reasons(
    fit: dict[str, Any],
    validation: dict[str, Any],
    spread_to_target_pct: float | None,
) -> list[str]:
    reasons = []
    if fit["closed_trades"] < MIN_FIT_TRADES:
        reasons.append(f"fit closed trades below {MIN_FIT_TRADES}")
    if validation["closed_trades"] < MIN_VALIDATION_TRADES:
        reasons.append(f"validation closed trades below {MIN_VALIDATION_TRADES}")
    if fit["net_pnl_usd"] is None or fit["net_pnl_usd"] <= 0:
        reasons.append("fit quote-side P&L is not positive")
    if validation["net_pnl_usd"] is None or validation["net_pnl_usd"] <= 0:
        reasons.append("validation quote-side P&L is not positive")
    if not _pf_passes(fit):
        reasons.append("fit profit factor is not above 1.10")
    if not _pf_passes(validation):
        reasons.append("validation profit factor is not above 1.10")
    if (
        fit["max_closed_trade_drawdown_usd"] is None
        or fit["max_closed_trade_drawdown_usd"] > MAX_DRAWDOWN_USD
        or validation["max_closed_trade_drawdown_usd"] is None
        or validation["max_closed_trade_drawdown_usd"] > MAX_DRAWDOWN_USD
    ):
        reasons.append("fit or validation drawdown exceeds USD 3,000")
    if (
        spread_to_target_pct is None
        or spread_to_target_pct > MAX_DEVELOPMENT_P95_SPREAD_TO_TARGET_PCT
    ):
        reasons.append("development p95 spread exceeds 25% of target or is unavailable")
    return reasons


def _rollover_timestamp_for_date(session_day: date) -> datetime:
    local_rollover = datetime.combine(
        session_day,
        time(17, 0),
        tzinfo=ZoneInfo("America/New_York"),
    )
    return local_rollover.astimezone(timezone.utc)


def _potential_rollover_exposures(
    simulation: dict[str, Any],
) -> dict[str, int]:
    """Conservative bar-time overlap count; no unverified financing is priced."""
    closed = unresolved = 0
    for trade in simulation["trades"]:
        entry = _timestamp(trade["entry_time"])
        observed_exit = _timestamp(trade["exit_observed_at"])
        local_start = entry.astimezone(ZoneInfo("America/New_York")).date()
        local_end = observed_exit.astimezone(ZoneInfo("America/New_York")).date()
        cursor = local_start
        while cursor <= local_end:
            rollover = _rollover_timestamp_for_date(cursor)
            if entry <= rollover <= observed_exit:
                closed += 1
                break
            cursor += timedelta(days=1)
    for item in simulation["unresolved_positions"]:
        if not item.get("mark_time"):
            continue
        entry = _timestamp(item["entry_time"])
        mark = _timestamp(item["mark_time"])
        if entry.astimezone(ZoneInfo("America/New_York")).date() <= (
            mark.astimezone(ZoneInfo("America/New_York")).date()
        ) and any(
            entry <= _rollover_timestamp_for_date(day) <= mark
            for day in (
                entry.astimezone(ZoneInfo("America/New_York")).date(),
                mark.astimezone(ZoneInfo("America/New_York")).date(),
            )
        ):
            unresolved += 1
    return {
        "closed_trade_intervals_potentially_overlapping_NY_17_rollover": closed,
        "unresolved_boundary_positions_marked_after_NY_17_rollover": unresolved,
        "financing_costs_estimated_or_charged": 0,
    }


def _trade_attribution(trades: Sequence[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "EU_ONLY": [],
        "EU_US_OVERLAP": [],
        "US_ONLY": [],
        "OUTSIDE_EU_US_WINDOWS": [],
    }
    london = ZoneInfo("Europe/London")
    new_york = ZoneInfo("America/New_York")
    for trade in trades:
        entry = _timestamp(trade["entry_time"])
        london_local = entry.astimezone(london)
        ny_local = entry.astimezone(new_york)
        in_eu = time(8, 0) <= london_local.timetz().replace(tzinfo=None) < time(17, 0)
        in_us = time(8, 0) <= ny_local.timetz().replace(tzinfo=None) < time(17, 0)
        key = (
            "EU_US_OVERLAP"
            if in_eu and in_us
            else "EU_ONLY"
            if in_eu
            else "US_ONLY"
            if in_us
            else "OUTSIDE_EU_US_WINDOWS"
        )
        buckets[key].append(trade)
    return {
        key: {
            "closed_trades": len(items),
            "wins": sum(item["pnl_usd"] > 0 for item in items),
            "losses": sum(item["pnl_usd"] < 0 for item in items),
            "quote_side_pnl_usd": round(sum(item["pnl_usd"] for item in items), 2),
            "expectancy_usd_per_trade": (
                round(sum(item["pnl_usd"] for item in items) / len(items), 2)
                if items
                else None
            ),
        }
        for key, items in buckets.items()
    }


def _schedule_for_date(window: dict[str, Any], day: date) -> list[dict[str, Any]]:
    ist = ZoneInfo("Asia/Kolkata")
    clauses = window["clauses"]
    raw_intervals = entry_window_intervals_utc(day, window)
    result = []
    for start_utc, end_utc in raw_intervals:
        result.append(
            {
                "start_utc": start_utc.isoformat(),
                "end_utc": end_utc.isoformat(),
                "start_ist": start_utc.astimezone(ist).isoformat(),
                "end_ist": end_utc.astimezone(ist).isoformat(),
                "start_ist_hhmm": start_utc.astimezone(ist).strftime("%H:%M"),
                "end_ist_hhmm": end_utc.astimezone(ist).strftime("%H:%M"),
            }
        )
    return result


def _session_schedule_metadata(
    windows: Sequence[dict[str, Any]],
    sample_start: datetime,
    sample_end_exclusive: datetime,
) -> list[dict[str, Any]]:
    output = []
    for window in windows:
        day_zone = ZoneInfo(window["day_timezone"])
        first_day = sample_start.astimezone(day_zone).date()
        last_day = (sample_end_exclusive - timedelta(minutes=1)).astimezone(day_zone).date()
        output.append(
            {
                "name": window["name"],
                "mode": window["mode"],
                "session_day_timezone": window["day_timezone"],
                "local_session_conventions_not_exchange_cash_open": True,
                "local_clauses": window["clauses"],
                "actual_utc_and_ist_interval_on_first_sample_local_date": {
                    "session_day": first_day.isoformat(),
                    "intervals": _schedule_for_date(window, first_day),
                },
                "actual_utc_and_ist_interval_on_last_sample_local_date": {
                    "session_day": last_day.isoformat(),
                    "intervals": _schedule_for_date(window, last_day),
                },
                "sample_session_day_range": {
                    "first": first_day.isoformat(),
                    "last": last_day.isoformat(),
                },
            }
        )
    return output


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _development_spread_and_candidate(
    candidate: dict[str, Any],
    simulation: dict[str, Any],
    spread: dict[str, Any],
) -> dict[str, Any]:
    fit, validation = simulation["folds"]
    fit_coverage, validation_coverage = simulation["coverage_by_fold"]
    target = candidate["take_profit_usd_per_oz"]
    p95 = spread["p95_usd_per_oz"]
    ratio = round(100 * p95 / target, 2) if p95 is not None else None
    time_exit_reasons = {
        reason: sum(
            trade["exit_reason"] == reason for trade in simulation["trades"]
        )
        for reason in (
            "maximum_holding_period_exit",
            "session_close_forced_exit",
            "ny17_rollover_buffer_forced_exit",
            "no_overnight_forced_exit",
            "no_carry_exit_after_deadline_quote_gap",
        )
    }
    return {
        "candidate_id": candidate["candidate_id"],
        "strategy_key": candidate["strategy_key"],
        "strategy_name": candidate["strategy_name"],
        "session": candidate["window"],
        "parameters": candidate["parameters"],
        "maximum_stop_usd_per_oz": candidate["maximum_stop_usd_per_oz"],
        "take_profit_usd_per_oz": target,
        "development_session_spread": {
            "fit": spread["fit"],
            "validation": spread["validation"],
            "combined_development": spread["combined_development"],
        },
        "development_p95_spread_to_target_pct": ratio,
        "fit": fit,
        "fit_coverage": fit_coverage,
        "validation": validation,
        "validation_coverage": validation_coverage,
        "development_time_based_exits": simulation["time_based_exits"],
        "development_time_exit_reason_counts": time_exit_reasons,
        "development_unresolved_positions_at_fold_or_sample_boundary": len(
            simulation["unresolved_positions"]
        ),
        "development_unfilled_or_boundary_signals": simulation["unfilled_or_boundary_signals"],
        "raw_signals_suppressed_while_open": simulation[
            "raw_signals_suppressed_while_position_open"
        ],
        "raw_signals_suppressed_at_daily_entry_cap": simulation[
            "raw_signals_suppressed_after_three_accepted_entries"
        ],
        "potential_rollover_exposure": _potential_rollover_exposures(simulation),
        "fit_disjoint_EU_US_entry_time_attribution": _trade_attribution(
            [trade for trade in simulation["trades"] if trade["fold"] == 0]
        ),
        "validation_disjoint_EU_US_entry_time_attribution": _trade_attribution(
            [trade for trade in simulation["trades"] if trade["fold"] == 1]
        ),
        "eligible_by_preregistered_fit_validation_rules": _candidate_passes(
            fit, validation, ratio
        ),
        "rejection_reasons": _candidate_reasons(fit, validation, ratio),
    }


def _csv_row(item: dict[str, Any]) -> dict[str, Any]:
    fit, val = item["fit"], item["validation"]
    fitcov, valcov = item["fit_coverage"], item["validation_coverage"]
    params = item["parameters"]

    def histogram(metrics: dict[str, Any], name: str) -> dict[str, int]:
        return metrics[name]["histogram_0_1_2_3"]

    return {
        "candidate_id": item["candidate_id"],
        "strategy_key": item["strategy_key"],
        "session_name": item["session"]["name"],
        "session_timezone": item["session"]["day_timezone"],
        "entry_window_mode": item["session"]["mode"],
        "local_clauses": json.dumps(item["session"]["clauses"], separators=(",", ":")),
        "bar_interval_minutes": params["bar_interval_minutes"],
        "fast_ema": params.get("fast_ema"),
        "slow_ema": params.get("slow_ema"),
        "rsi_period": params.get("rsi_period"),
        "rsi_reentry_threshold": params.get("rsi_reentry_threshold"),
        "stop_loss_usd_per_oz": params["stop_loss_usd_per_oz"],
        "take_profit_usd_per_oz": params["take_profit_usd_per_oz"],
        "max_hold_minutes": MAX_HOLD_MINUTES,
        "NY17_rollover_buffer_minutes": 1,
        "NY17_rollover_entry_cutoff": "full max hold must complete by 16:59 America/New_York",
        "allow_overnight": False,
        "fit_p95_spread_usd_per_oz": item["development_session_spread"]["fit"][
            "p95_usd_per_oz"
        ],
        "validation_p95_spread_usd_per_oz": item["development_session_spread"][
            "validation"
        ]["p95_usd_per_oz"],
        "development_p95_spread_usd_per_oz": item["development_session_spread"][
            "combined_development"
        ]["p95_usd_per_oz"],
        "development_p95_spread_to_target_pct": item[
            "development_p95_spread_to_target_pct"
        ],
        "fit_closed_trades": fit["closed_trades"],
        "fit_wins": fit["wins"],
        "fit_losses": fit["losses"],
        "fit_win_rate_pct": fit["win_rate_pct"],
        "fit_win_rate_wilson_95pct": json.dumps(fit["win_rate_95pct_wilson"]),
        "fit_quote_side_pnl_usd_before_unverified_costs": fit["net_pnl_usd"],
        "fit_expectancy_usd_per_trade": fit["expectancy_usd_per_closed_trade"],
        "fit_profit_factor": fit["profit_factor"],
        "fit_max_drawdown_usd": fit["max_closed_trade_drawdown_usd"],
        "fit_eligible_market_days": fitcov["eligible_market_days"],
        "fit_market_day_coverage_pct": fitcov[
            "eligible_market_day_coverage_pct_of_weekdays"
        ],
        "fit_mean_daily_actionable_calls": fitcov[
            "actionable_review_calls_per_eligible_day"
        ]["mean"],
        "fit_mean_daily_accepted_entries": fitcov[
            "accepted_entries_per_eligible_day"
        ]["mean"],
        "fit_mean_daily_closed_trades": fitcov[
            "closed_trades_per_eligible_day"
        ]["mean"],
        "fit_zero_call_days": fitcov["actionable_review_calls_per_eligible_day"]["zero_days"],
        "fit_daily_call_histogram": json.dumps(
            histogram(fitcov, "actionable_review_calls_per_eligible_day")
        ),
        "fit_daily_entry_histogram": json.dumps(
            histogram(fitcov, "accepted_entries_per_eligible_day")
        ),
        "fit_daily_close_histogram": json.dumps(
            histogram(fitcov, "closed_trades_per_eligible_day")
        ),
        "validation_closed_trades": val["closed_trades"],
        "validation_wins": val["wins"],
        "validation_losses": val["losses"],
        "validation_win_rate_pct": val["win_rate_pct"],
        "validation_win_rate_wilson_95pct": json.dumps(val["win_rate_95pct_wilson"]),
        "validation_quote_side_pnl_usd_before_unverified_costs": val["net_pnl_usd"],
        "validation_expectancy_usd_per_trade": val["expectancy_usd_per_closed_trade"],
        "validation_profit_factor": val["profit_factor"],
        "validation_max_drawdown_usd": val["max_closed_trade_drawdown_usd"],
        "validation_eligible_market_days": valcov["eligible_market_days"],
        "validation_market_day_coverage_pct": valcov[
            "eligible_market_day_coverage_pct_of_weekdays"
        ],
        "validation_mean_daily_actionable_calls": valcov[
            "actionable_review_calls_per_eligible_day"
        ]["mean"],
        "validation_mean_daily_accepted_entries": valcov[
            "accepted_entries_per_eligible_day"
        ]["mean"],
        "validation_mean_daily_closed_trades": valcov[
            "closed_trades_per_eligible_day"
        ]["mean"],
        "validation_zero_call_days": valcov[
            "actionable_review_calls_per_eligible_day"
        ]["zero_days"],
        "validation_daily_call_histogram": json.dumps(
            histogram(valcov, "actionable_review_calls_per_eligible_day")
        ),
        "validation_daily_entry_histogram": json.dumps(
            histogram(valcov, "accepted_entries_per_eligible_day")
        ),
        "validation_daily_close_histogram": json.dumps(
            histogram(valcov, "closed_trades_per_eligible_day")
        ),
        "fit_time_based_exits": item["development_time_based_exits"],
        "development_ny17_buffer_exits": item[
            "development_time_exit_reason_counts"
        ]["ny17_rollover_buffer_forced_exit"],
        "closed_trade_potential_NY17_rollover_exposures": item[
            "potential_rollover_exposure"
        ]["closed_trade_intervals_potentially_overlapping_NY_17_rollover"],
        "eligible_by_preregistered_rules": item["eligible_by_preregistered_fit_validation_rules"],
        "rejection_reasons": "; ".join(item["rejection_reasons"]),
    }


def _read_sample(evidence_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], str]:
    baseline_path = evidence_dir / "xauusd_backtest.json"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise XAUHistoryError("The frozen XAUUSD baseline report is unavailable") from exc
    if (
        baseline.get("data_source") != "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC"
        or baseline.get("provider") != "OANDA"
        or baseline.get("environment") != "practice"
        or baseline.get("instrument") != "XAU_USD"
        or baseline.get("strategy_changed") is not False
    ):
        raise XAUHistoryError("Saved source report is not the frozen unchanged OANDA XAU_USD baseline")
    all_bars, source_hash = _read_verified_saved_history(evidence_dir, baseline)
    start = _timestamp(baseline["sample_start_inclusive"])
    end = _timestamp(baseline["sample_end_exclusive"])
    sample = []
    warmup = []
    for bar in all_bars:
        stamp = _timestamp(bar["time"])
        if start <= stamp < end:
            sample.append(bar)
        elif stamp < start:
            warmup.append(bar)
    if len(sample) < 10_000 or len(warmup) < 1_000:
        raise XAUHistoryError("Saved OANDA sample or pre-sample indicator warmup is incomplete")
    return sample, warmup, baseline, source_hash


def run_saved_session_study(
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
) -> dict[str, Any]:
    """Write the preregistration first, then inspect only development/validation for selection."""
    directory = Path(evidence_dir)
    windows = list(SESSION_WINDOWS)
    candidates = preregistered_candidates()
    prereg_path = directory / "xauusd_session_study_preregistered.json"
    report_path = directory / "xauusd_session_study.json"
    candidates_path = directory / "xauusd_session_study_candidates.csv"
    prereg = {
        "schema_version": 1,
        "study": STUDY_NAME,
        "status": "PREDECLARED_CONFIGURATIONS_NOT_YET_EVALUATED",
        "market_identity": "Gold Spot / U.S. Dollar (XAUUSD), OANDA practice XAU_USD only",
        "provider_requests_allowed": False,
        "raw_history_edits_allowed": False,
        "user_snapshot_used_as_price_input": False,
        "candidate_count": len(candidates),
        "candidate_rule": "Exactly two fixed existing strategy rulesets across six preregistered session schedules; no per-session parameter search.",
        "candidate_configurations": candidates,
        "windows": windows,
        "execution_and_cost_rules": {
            "next_complete_genuine_M1_open": "BUY at ask / SELL at bid",
            "exits": "Actual executable-side OANDA bid/ask OHLC; stop-first if intrabar stop/target order is ambiguous; adverse stop-gap fill at next observed exit-side open.",
            "quantity": "100 OANDA units / 100 oz",
            "max_stop_usd_per_oz": 3.0,
            "fixed_max_hold_minutes": MAX_HOLD_MINUTES,
            "allow_overnight": False,
            "NY17_no_carry_rule": "Use America/New_York IANA timezone; require full 25-minute hold plus 1-minute quote-exit buffer to finish by 16:59 NY time. Force using actual exit-side quote at that cutoff. Do not enter if the window fails this or its session close.",
            "end_of_session": "Require the full 25-minute max hold to finish before the session window closes; force at the actual exit-side close on its first complete bar at/after the limit.",
            "max_accepted_entries_per_session_day_global": DAILY_ACCEPTED_ENTRY_LIMIT,
            "holdout": "Chronological final 30%; zero inspection/evaluation unless one candidate passes every fit and validation rule.",
        },
        "selection_rules": {
            "fit_min_closed_trades": MIN_FIT_TRADES,
            "validation_min_closed_trades": MIN_VALIDATION_TRADES,
            "fit_and_validation_quote_side_pnl_must_be_positive": True,
            "profit_factor_must_exceed": MIN_PROFIT_FACTOR,
            "fit_and_validation_max_drawdown_usd": MAX_DRAWDOWN_USD,
            "development_session_p95_spread_to_target_pct_maximum": MAX_DEVELOPMENT_P95_SPREAD_TO_TARGET_PCT,
            "ranking": "Among qualifying combinations only, highest validation simulated quote-side P&L; do not optimize on holdout.",
            "daily_review_calls": "2-3 actionable calls per eligible active session day is an aspiration and metric, never forced.",
        },
        "selection_bias_context": "An additional fixed 12 combinations following the prior 24- and 32-candidate studies (56 earlier configurations) are a bounded, multiple-comparison research screen, not independent proof or a preregistered confirmatory holdout.",
    }
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(prereg_path, prereg)

    sample, warmup, baseline, source_hash = _read_sample(directory)
    outer_cut = _midnight_cut(sample, int(0.70 * len(sample)))
    if outer_cut <= 1 or outer_cut >= len(sample) - 1:
        raise XAUHistoryError("Session study cannot form a chronological pre-holdout development split")
    development = sample[:outer_cut]
    inner_cut = _midnight_cut(development, int(0.70 * len(development)))
    if inner_cut <= 1 or inner_cut >= len(development) - 1:
        raise XAUHistoryError("Session study cannot form a fit/validation split")
    evaluated: list[dict[str, Any]] = []
    for candidate in candidates:
        simulation = _simulate_session(
            development,
            warmup,
            candidate,
            boundaries=(inner_cut,),
        )
        spread = {
            "fit": _spread_p95(development[:inner_cut], candidate["window"]),
            "validation": _spread_p95(development[inner_cut:], candidate["window"]),
            "combined_development": _spread_p95(development, candidate["window"]),
        }
        spread["p95_usd_per_oz"] = spread["combined_development"]["p95_usd_per_oz"]
        evaluated.append(
            _development_spread_and_candidate(candidate, simulation, spread)
        )

    eligible = [
        item
        for item in evaluated
        if item["eligible_by_preregistered_fit_validation_rules"]
    ]
    eligible.sort(
        key=lambda item: (
            item["validation"]["net_pnl_usd"],
            item["validation"]["expectancy_usd_per_closed_trade"],
            item["validation"]["profit_factor"]
            if item["validation"]["profit_factor"] is not None
            else math.inf,
            -item["validation"]["max_closed_trade_drawdown_usd"],
        ),
        reverse=True,
    )
    validation_diagnostic = max(
        evaluated,
        key=lambda item: (
            item["validation"]["net_pnl_usd"]
            if item["validation"]["net_pnl_usd"] is not None
            else -math.inf,
            item["validation"]["expectancy_usd_per_closed_trade"]
            if item["validation"]["expectancy_usd_per_closed_trade"] is not None
            else -math.inf,
        ),
    )
    per_session = []
    for window in windows:
        session_rows = [item for item in evaluated if item["session"]["name"] == window["name"]]
        best_diagnostic = max(
            session_rows,
            key=lambda item: (
                item["validation"]["net_pnl_usd"]
                if item["validation"]["net_pnl_usd"] is not None
                else -math.inf
            ),
        )
        per_session.append(
            {
                "session_name": window["name"],
                "best_validation_pnl_candidate_diagnostic": best_diagnostic["candidate_id"],
                "best_validation_pnl_usd": best_diagnostic["validation"]["net_pnl_usd"],
                "candidate_eligible": best_diagnostic[
                    "eligible_by_preregistered_fit_validation_rules"
                ],
                "not_a_winner_unless_all_preregistered_rules_pass": True,
            }
        )
    session_start = _timestamp(baseline["sample_start_inclusive"])
    session_end = _timestamp(baseline["sample_end_exclusive"])
    report = {
        "schema_version": 1,
        "study": STUDY_NAME,
        "status": (
            "TRAINING_CANDIDATE_FOUND_HOLDOUT_UNEVALUATED"
            if eligible
            else "NO_FIT_AND_VALIDATION_ELIGIBLE_CANDIDATE"
        ),
        "market_identity": "Gold Spot / U.S. Dollar (XAUUSD), OANDA practice instrument XAU_USD only",
        "data_source": "verified saved complete OANDA practice XAU_USD bid/ask M1 history",
        "source_file": baseline.get("raw_data_file"),
        "source_sha256": source_hash,
        "provider_requests_made": 0,
        "raw_source_modified": False,
        "user_snapshot_or_latest_quote_used_as_price_input": False,
        "sample_start_inclusive": baseline["sample_start_inclusive"],
        "sample_end_exclusive": baseline["sample_end_exclusive"],
        "sample_bars": len(sample),
        "warmup_bars_before_sample": len(warmup),
        "development_bars_only_before_final_holdout": outer_cut,
        "fit_bars": inner_cut,
        "inner_validation_bars": outer_cut - inner_cut,
        "predeclaration_file": prereg_path.name,
        "candidate_count": len(evaluated),
        "training_eligible_candidate_count": len(eligible),
        "final_holdout_evaluation_count": 0,
        "final_holdout_inspected_for_selection": False,
        "final_holdout_rule": "Untouched, unevaluated because no candidate passed fit and inner-validation requirements.",
        "strategy_and_execution_rules": prereg["execution_and_cost_rules"],
        "selection_rules": prereg["selection_rules"],
        "session_schedules_actual_IANA_Dst_sample_dates_UTC_and_IST": _session_schedule_metadata(
            windows, session_start, session_end
        ),
        "multiple_comparison_and_selection_bias": prereg["selection_bias_context"],
        "financing_and_commission_limitation": (
            "P&L is gross quote-side USD P&L before unverified commission, spread is embedded by bid/ask fills, "
            "and verified OANDA financing/swap terms were unavailable (the existing OANDA instruments lookup returned 404). "
            "No fees or financing have been fabricated or subtracted."
        ),
        "NY17_no_carry_policy": {
            "timezone": "America/New_York via IANA ZoneInfo (DST-aware)",
            "rollover_at_local_time": "17:00",
            "quote_exit_buffer_minutes": 1,
            "max_hold_minutes": MAX_HOLD_MINUTES,
            "entry_requires_full_hold_before": "the earlier of the local session close and 16:59 America/New_York",
            "exits_use": "actual observed executable-side quote; unexpected data gaps that delay exit are reported as residual exposure, never charged a fabricated fee",
        },
        "potential_NY_17_rollover_definition": (
            "Count any observed entry-to-exit interval reaching or crossing 17:00 America/New_York; exact intrabar exit time is unknown from M1 OHLC. "
            "The common cutoff should prevent planned exposure. Nonzero counts indicate an unexpected data/quote gap or OHLC-time uncertainty, not a financing charge."
        ),
        "eligible_candidates_ranked_by_validation_quote_side_pnl": [
            item["candidate_id"] for item in eligible
        ],
        "highest_validation_pnl_diagnostic_not_automatically_eligible": {
            "candidate_id": validation_diagnostic["candidate_id"],
            "session_name": validation_diagnostic["session"]["name"],
            "strategy_name": validation_diagnostic["strategy_name"],
            "validation_metrics": validation_diagnostic["validation"],
            "validation_coverage": validation_diagnostic["validation_coverage"],
            "fit_metrics": validation_diagnostic["fit"],
            "fit_coverage": validation_diagnostic["fit_coverage"],
            "eligible": validation_diagnostic[
                "eligible_by_preregistered_fit_validation_rules"
            ],
            "rejection_reasons": validation_diagnostic["rejection_reasons"],
        },
        "session_validation_pnl_diagnostics": sorted(
            per_session,
            key=lambda item: item["best_validation_pnl_usd"]
            if item["best_validation_pnl_usd"] is not None
            else -math.inf,
            reverse=True,
        ),
        "candidate_results": evaluated,
        "paper_configuration_switched": False,
        "paper_entries_enabled_by_this_study": False,
        "live_orders_enabled": False,
        "baseline_or_prior_study_evidence_modified": False,
    }

    # No holdout slice or prices are passed to a simulator unless a selected
    # candidate has already satisfied both development partitions.
    if len(eligible) == 1:
        chosen = eligible[0]
        chosen_spec = next(
            item for item in candidates if item["candidate_id"] == chosen["candidate_id"]
        )
        # Adequacy of the untouched final segment is established from
        # timestamps only before a one-time price replay.
        holdout = sample[outer_cut:]
        holdout_simulation = _simulate_session(holdout, warmup, chosen_spec)
        holdout_metrics = holdout_simulation["overall"]
        holdout_ok = (
            holdout_metrics["closed_trades"] >= 30
            and holdout_metrics["net_pnl_usd"] is not None
            and holdout_metrics["net_pnl_usd"] > 0
            and (holdout_metrics["profit_factor"] is None or holdout_metrics["profit_factor"] >= 1.05)
            and holdout_metrics["max_closed_trade_drawdown_usd"] is not None
            and holdout_metrics["max_closed_trade_drawdown_usd"] <= MAX_DRAWDOWN_USD
        )
        report["final_holdout_evaluation_count"] = 1
        report["final_holdout_inspected_for_selection"] = True
        report["final_holdout_rule"] = "One-time evaluation after exactly one eligible fit/validation candidate."
        report["selected_training_candidate"] = chosen["candidate_id"]
        report["final_holdout_metrics"] = holdout_metrics
        report["final_holdout_coverage"] = holdout_simulation["coverage_by_fold"][0]
        report["final_holdout_potential_rollover_exposure"] = _potential_rollover_exposures(
            holdout_simulation
        )
        report["status"] = (
            "HOLDOUT_PASS_RESEARCH_ONLY" if holdout_ok else "HOLDOUT_FAILED_RESEARCH_ONLY"
        )

    rows = [_csv_row(item) for item in evaluated]
    with candidates_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    _write_json(report_path, report)
    return report


def main() -> None:
    report = run_saved_session_study()
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()