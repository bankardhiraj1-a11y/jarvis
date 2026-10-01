"""Small preregistered RSI/Bollinger XAUUSD study on saved bid/ask history."""

from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from agents.base import Signal
from agents.xauusd import LOT_SIZE, UNITS_PER_LOT, entry_holding_deadline
from agents.xauusd_highwin import (
    HIGHWIN_RESEARCH_STATUS,
    advance_highwin_bar,
    highwin_entry_policy_allows,
    highwin_holding_exit_reason,
    initial_highwin_state,
    normalize_highwin_parameters,
    register_highwin_entry,
)
from backtest.xauusd_evidence import (
    DEFAULT_EVIDENCE_DIR,
    TRAIN_FRACTION,
    XAUHistoryError,
    _exit_bar,
    _read_verified_saved_history,
    _timestamp,
    _within_entry_session,
)
from backtest.xauusd_optimization import (
    MIN_ENTRY_SESSION_UTC,
    _aggregate_minutes,
    _metrics,
    _prepare,
    _raw_split_before_entry_session,
    _split_before_entry_session,
)


STUDY_NAME = "XAUUSD selective Wilder-RSI/Bollinger closed-bar re-entry"
MAX_CANDIDATES = 36
MIN_DEVELOPMENT_TRADES = 30
MIN_VALIDATION_TRADES = 20
MIN_HOLDOUT_TRADES = 30
MIN_PROFIT_FACTOR = 1.10
MIN_HOLDOUT_PROFIT_FACTOR = 1.05
MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD = 3_000.0
MAX_SPREAD_TO_TARGET_RATIO = 0.25
RISK_PROFILES = (
    # target USD/oz, stop USD/oz. Stops are capped at $3/oz ($300 at 100 units).
    (3.75, 1.50),
    (4.00, 2.00),
    (4.50, 2.50),
    (5.00, 3.00),
)


def predeclared_candidates() -> list[dict[str, Any]]:
    """Exactly 32 preregistered settings; all features are causal and bounded."""
    result = []
    for timeframe in (1, 5):
        for rsi_period in (7, 14):
            for reentry in (20, 30):
                for target, stop in RISK_PROFILES:
                    result.append(
                        normalize_highwin_parameters(
                            {
                                "bar_interval_minutes": timeframe,
                                "rsi_period": rsi_period,
                                "rsi_reentry_threshold": reentry,
                                "bollinger_period": 20,
                                "bollinger_stddev": 2.0,
                                "regime_fast_ema": 20,
                                "regime_slow_ema": 50,
                                "max_range_ema_separation_usd": 2.0,
                                "stop_loss_usd_per_oz": stop,
                                "take_profit_usd_per_oz": target,
                                "max_hold_minutes": 25,
                                "allow_overnight": False,
                                "max_trades_per_utc_day": 3,
                                "position_quantity_units": 100,
                            }
                        )
                    )
    if not result or len(result) > MAX_CANDIDATES:
        raise AssertionError("Predeclared high-win study exceeds its 36-configuration cap")
    return result


def _bar_for_reducer(item: dict[str, Any]) -> dict[str, Any]:
    source = item["source"]
    return {
        "observed_at": item["observed_at"].isoformat(),
        "close": item["mid_close"],
        "high": (float(source["bid_high"]) + float(source["ask_high"])) / 2,
        "low": (float(source["bid_low"]) + float(source["ask_low"])) / 2,
    }


def _training_spread_p95(bars: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Compute spread diagnostics only on the development partition."""
    session_spreads = []
    for row in bars:
        opened = _timestamp(row["time"])
        observed = opened + timedelta(minutes=1)
        if (observed.hour, observed.minute) < MIN_ENTRY_SESSION_UTC or (
            observed.hour, observed.minute
        ) >= (23, 0):
            continue
        spread = float(row["ask_close"]) - float(row["bid_close"])
        if math.isfinite(spread) and spread >= 0:
            session_spreads.append(spread)
    if not session_spreads:
        raise XAUHistoryError("No development-session bid/ask spreads available for the cost filter")
    session_spreads.sort()
    p95 = session_spreads[math.ceil(0.95 * len(session_spreads)) - 1]
    return {
        "development_session_close_spread_observations": len(session_spreads),
        "median_spread_usd_per_oz": session_spreads[(len(session_spreads) - 1) // 2],
        "p95_spread_usd_per_oz": round(p95, 8),
        "maximum_spread_usd_per_oz": round(session_spreads[-1], 8),
    }


def _simulate_highwin(
    bars: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    parameters: dict[str, Any],
    *,
    boundaries: Sequence[int] = (),
) -> dict[str, Any]:
    """Replay the shared high-win reducer on complete M1 or contiguous M5 OHLC."""
    config = normalize_highwin_parameters(parameters)
    timeframe = config["bar_interval_minutes"]
    source_prepared = _prepare(bars)
    source_cuts = [source_prepared[index]["open_time"] for index in boundaries]
    study_bars, dropped_sample = _aggregate_minutes(bars, timeframe)
    prepared = _prepare(study_bars, timeframe_minutes=timeframe)
    study_warmup, dropped_warmup = _aggregate_minutes(warmup, timeframe)
    prepared_warmup = _prepare(study_warmup, timeframe_minutes=timeframe)
    warmup_required = max(
        config["rsi_period"] + 1,
        config["bollinger_period"],
        config["regime_slow_ema"],
    )
    if len(prepared_warmup) < warmup_required:
        raise XAUHistoryError(
            f"High-win replay requires {warmup_required} genuine pre-sample M{timeframe} bars"
        )

    state = initial_highwin_state()
    warmup_signals = 0
    for item in prepared_warmup:
        warmup_signals += advance_highwin_bar(
            state, _bar_for_reducer(item), config
        ) is not None

    cuts = []
    for boundary_time in source_cuts:
        resolved = next(
            (i for i, item in enumerate(prepared) if item["open_time"] >= boundary_time),
            None,
        )
        if resolved is not None and 0 < resolved < len(prepared):
            cuts.append(resolved)
    cuts = sorted(set(cuts))

    partition = next_cut = 0
    active: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    fold_counts = [0 for _ in range(len(cuts) + 1)]
    signals_by_fold = [0 for _ in range(len(cuts) + 1)]
    signals_suppressed_by_position = 0
    unfilled_or_boundary_signals = 0
    time_based_exits = 0
    day_activity: dict[tuple[int, Any], dict[str, int]] = {}

    def activity(day: Any, fold: int) -> dict[str, int]:
        return day_activity.setdefault(
            (fold, day),
            {
                "complete_entry_window_bars": 0,
                "setup_signals": 0,
                "review_calls": 0,
                "entries": 0,
                "closed": 0,
            },
        )

    for index, item in enumerate(prepared):
        if next_cut < len(cuts) and index == cuts[next_cut]:
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
                unfilled_or_boundary_signals += 1
                pending = None
            partition += 1
            next_cut += 1

        source = item["source"]
        observation = item["observed_at"]
        if _within_entry_session(observation.isoformat()):
            activity(observation.date(), partition)["complete_entry_window_bars"] += 1
        if pending is not None:
            intent = pending
            pending = None
            entry_open = item["open_time"]
            can_enter = not (
                intent["fold"] != partition
                or intent["utc_day"] != entry_open.date()
                or not _within_entry_session(entry_open.isoformat())
                or not highwin_entry_policy_allows(entry_open, config)
            )
            if can_enter:
                can_enter = register_highwin_entry(state, entry_open, config)
            if not can_enter:
                unfilled_or_boundary_signals += 1
            else:
                activity(entry_open.date(), partition)["entries"] += 1
                side = 1 if intent["signal"] == Signal.BUY.value else -1
                entry_price = float(source["ask_open"] if side > 0 else source["bid_open"])
                stop_gap = config["stop_loss_usd_per_oz"]
                target_gap = config["take_profit_usd_per_oz"]
                active = {
                    "signal": intent["signal"],
                    "side": side,
                    "signal_observed_at": intent["signal_observed_at"],
                    "signal_candle_open_time": intent["signal_candle_open_time"],
                    "entry_time": source["time"],
                    "entry_price": round(entry_price, 8),
                    "stop_price": round(entry_price - side * stop_gap, 8),
                    "target_price": round(entry_price + side * target_gap, 8),
                    "stop_usd_per_oz": stop_gap,
                    "target_usd_per_oz": target_gap,
                    "max_hold_minutes": config["max_hold_minutes"],
                    "allow_overnight": False,
                    "breakeven_win_rate_before_spread_pct": round(
                        100 * stop_gap / (stop_gap + target_gap), 2
                    ),
                    "position_quantity_units": UNITS_PER_LOT,
                    "lot_size": LOT_SIZE,
                    "currency": "USD",
                    "fold": partition,
                    "entry_index": index,
                    "execution_model": f"next genuine OANDA M{timeframe} candle open; BUY at ask / SELL at bid",
                }
                immediate = _exit_bar(active, source)
                if immediate is not None:
                    pnl = (float(immediate["price"]) - entry_price) * UNITS_PER_LOT * side
                    trades.append(
                        {
                            **active,
                            "exit_bar_open_time": source["time"],
                            "exit_time_basis": "Complete strategy candle open; intrabar ordering is unknown, and same-bar stop/target ambiguity resolves stop-first.",
                            "exit_price": round(float(immediate["price"]), 8),
                            "exit_reason": immediate["reason"],
                            "pnl_usd": round(pnl, 8),
                            "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                            "status": "CLOSED",
                            "holding_complete_strategy_bars": 1,
                        }
                    )
                    fold_counts[partition] += 1
                    activity(observation.date(), partition)["closed"] += 1
                    active = None
        elif active is not None:
            exit_event = _exit_bar(active, source)
            time_exit_reason = highwin_holding_exit_reason(
                active["entry_time"],
                observation,
                config,
            )
            if exit_event is None and time_exit_reason is not None:
                cross_date = observation.date() != _timestamp(active["entry_time"]).date()
                exit_side = "bid" if active["side"] > 0 else "ask"
                entry_time = _timestamp(active["entry_time"])
                risk_deadline = entry_holding_deadline(
                    entry_time,
                    config["entry_window"],
                    rollover_buffer_minutes=1,
                )
                max_hold_deadline = entry_time + timedelta(
                    minutes=config["max_hold_minutes"]
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
                        source[
                            f"{exit_side}_{'open' if cross_date or late_quote_gap else 'close'}"
                        ]
                    ),
                    "reason": (
                        "no_carry_exit_after_deadline_quote_gap"
                        if late_quote_gap or cross_date
                        else time_exit_reason
                    ),
                }
            if exit_event is not None:
                if exit_event["reason"] in (
                    "maximum_holding_period_exit",
                    "session_close_forced_exit",
                    "ny17_rollover_buffer_forced_exit",
                    "no_overnight_forced_exit",
                    "no_carry_exit_after_deadline_quote_gap",
                ):
                    time_based_exits += 1
                pnl = (
                    (float(exit_event["price"]) - active["entry_price"])
                    * UNITS_PER_LOT
                    * active["side"]
                )
                trades.append(
                    {
                        **active,
                        "exit_bar_open_time": source["time"],
                        "exit_time_basis": (
                            "Executable exit-side close of the first completed candle at/after the 25-minute or UTC session-close rule."
                            if exit_event["reason"] in (
                                "maximum_holding_period_exit",
                                "session_close_forced_exit",
                                "ny17_rollover_buffer_forced_exit",
                            )
                            else "First available executable exit-side open after an unobserved deadline or date boundary."
                            if exit_event["reason"]
                            in {
                                "no_overnight_forced_exit",
                                "no_carry_exit_after_deadline_quote_gap",
                            }
                            else "Complete strategy candle open; intrabar ordering is unknown, and same-bar stop/target ambiguity resolves stop-first."
                        ),
                        "exit_price": round(float(exit_event["price"]), 8),
                        "exit_reason": exit_event["reason"],
                        "pnl_usd": round(pnl, 8),
                        "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                        "status": "CLOSED",
                        "holding_complete_strategy_bars": index - active["entry_index"] + 1,
                    }
                )
                fold_counts[active["fold"]] += 1
                activity(observation.date(), partition)["closed"] += 1
                active = None

        # This exact pure reducer is also used by XAUUSDHighWinResearchAgent.
        signal = advance_highwin_bar(state, _bar_for_reducer(item), config)
        if signal is None:
            continue
        signals_by_fold[partition] += 1
        activity(observation.date(), partition)["setup_signals"] += 1
        if active is not None:
            signals_suppressed_by_position += 1
            continue
        following = index + 1
        if (
            following >= len(prepared)
            or (next_cut < len(cuts) and following == cuts[next_cut])
            or prepared[following]["minute_index"] != item["minute_index"] + 1
            or not _within_entry_session(prepared[following]["open_time"].isoformat())
            or not highwin_entry_policy_allows(prepared[following]["open_time"], config)
        ):
            unfilled_or_boundary_signals += 1
            continue
        pending = {
            "signal": signal,
            "signal_observed_at": item["observed_at"].isoformat(),
            "signal_candle_open_time": source["time"],
            "utc_day": item["observed_at"].date(),
            "fold": partition,
        }
        activity(observation.date(), partition)["review_calls"] += 1

    if active is not None:
        unresolved.append(
            {
                "fold": partition,
                "entry_time": active["entry_time"],
                "status": "OPEN_AT_SAMPLE_END_UNREALIZED",
            }
        )
    if pending is not None:
        unfilled_or_boundary_signals += 1
    def coverage_for(fold: int) -> dict[str, Any]:
        all_days = sorted(day for row_fold, day in day_activity if row_fold == fold)
        expected = int(420 / timeframe)
        minimum_bars = math.ceil(expected * 0.60)
        eligible_days = [
            day
            for day in all_days
            if day_activity[(fold, day)]["complete_entry_window_bars"] >= minimum_bars
        ]
        partial_days = len(all_days) - len(eligible_days)
        bar_counts = [
            day_activity[(fold, day)]["complete_entry_window_bars"]
            for day in all_days
        ]
        eligible_coverage_pct = [
            round(100 * day_activity[(fold, day)]["complete_entry_window_bars"] / expected, 2)
            for day in eligible_days
        ]
        calls = [day_activity[(fold, day)]["review_calls"] for day in eligible_days]
        setup_signals = [day_activity[(fold, day)]["setup_signals"] for day in eligible_days]
        entries = [day_activity[(fold, day)]["entries"] for day in eligible_days]
        closed = [day_activity[(fold, day)]["closed"] for day in eligible_days]

        def histogram(values: list[int]) -> dict[str, int]:
            return {
                "0": sum(value == 0 for value in values),
                "1": sum(value == 1 for value in values),
                "2": sum(value == 2 for value in values),
                "3": sum(value == 3 for value in values),
                "4_plus": sum(value >= 4 for value in values),
            }

        def daily_summary(values: list[int]) -> dict[str, Any]:
            return {
                "mean": round(statistics.mean(values), 4) if values else None,
                "median": statistics.median(values) if values else None,
                "histogram_0_1_2_3_4plus": histogram(values),
            }

        return {
            "eligible_active_trading_days": len(eligible_days),
            "active_trading_days_including_undercovered_partial_days": len(all_days),
            "partial_active_days_excluded_for_less_than_60pct_entry_window_coverage": partial_days,
            "expected_complete_bars_per_full_entry_window": expected,
            "entry_window_coverage_of_eligible_days_pct": {
                "mean": round(statistics.mean(eligible_coverage_pct), 2) if eligible_coverage_pct else None,
                "median": statistics.median(eligible_coverage_pct) if eligible_coverage_pct else None,
                "minimum": min(eligible_coverage_pct) if eligible_coverage_pct else None,
                "maximum": max(eligible_coverage_pct) if eligible_coverage_pct else None,
            },
            "complete_strategy_bars_per_active_day": {
                "mean": round(statistics.mean(bar_counts), 2) if bar_counts else None,
                "median": statistics.median(bar_counts) if bar_counts else None,
                "minimum": min(bar_counts) if bar_counts else None,
                "maximum": max(bar_counts) if bar_counts else None,
            },
            "minimum_complete_strategy_bars_for_eligible_day": minimum_bars,
            "zero_opportunity_days": sum(value == 0 for value in calls),
            "zero_proposed_review_call_days": sum(value == 0 for value in calls),
            "zero_raw_setup_signal_days": sum(value == 0 for value in setup_signals),
            "proposed_review_calls_per_eligible_active_day": daily_summary(calls),
            "raw_setup_signals_per_eligible_active_day": daily_summary(setup_signals),
            "actual_entries_per_eligible_active_day": daily_summary(entries),
            "closed_trades_per_eligible_active_day": daily_summary(closed),
            "daily_entry_cap": config["max_trades_per_utc_day"],
            "daily_coverage_target_calls": "2-3 actionable proposed/review calls per eligible active trading day; aspiration/selection objective, never forced",
        }

    return {
        "overall": _metrics(trades),
        "folds": [
            _metrics([trade for trade in trades if trade["fold"] == fold])
            for fold in range(len(cuts) + 1)
        ],
        "trades": trades,
        "unresolved_positions": unresolved,
        "unfilled_or_boundary_signals": unfilled_or_boundary_signals,
        "signals_suppressed_by_open_position": signals_suppressed_by_position,
        "confirmed_signals": sum(signals_by_fold),
        "signals_by_fold": signals_by_fold,
        "time_based_exits": time_based_exits,
        "coverage_by_fold": [coverage_for(fold) for fold in range(len(cuts) + 1)],
        "closed_trade_counts_by_fold": fold_counts,
        "complete_bars": len(prepared),
        "requested_interval_minutes": timeframe,
        "discarded_partial_interval_bars": dropped_sample,
        "discarded_partial_warmup_bars": dropped_warmup,
        "warmup_bars": len(prepared_warmup),
        "warmup_signals": warmup_signals,
        "final_state": {
            key: value
            for key, value in state.items()
            if key not in ("last_observed_at",)
        }
        | {
            "last_observed_at": (
                state["last_observed_at"].isoformat()
                if state["last_observed_at"]
                else None
            )
        },
    }


def _profit_factor_passes(metrics: dict[str, Any]) -> bool:
    factor = metrics["profit_factor"]
    return (
        metrics["wins"] > 0 and metrics["losses"] == 0
        if factor is None
        else factor >= MIN_PROFIT_FACTOR
    )


def _eligible(
    fit: dict[str, Any],
    validation: dict[str, Any],
    *,
    spread_to_target_ratio: float,
) -> bool:
    return (
        fit["closed_trades"] >= MIN_DEVELOPMENT_TRADES
        and validation["closed_trades"] >= MIN_VALIDATION_TRADES
        and fit["net_pnl_usd"] is not None
        and fit["net_pnl_usd"] > 0
        and validation["net_pnl_usd"] is not None
        and validation["net_pnl_usd"] > 0
        and _profit_factor_passes(fit)
        and _profit_factor_passes(validation)
        and fit["max_closed_trade_drawdown_usd"] is not None
        and fit["max_closed_trade_drawdown_usd"] <= MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD
        and validation["max_closed_trade_drawdown_usd"] is not None
        and validation["max_closed_trade_drawdown_usd"] <= MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD
        and spread_to_target_ratio <= MAX_SPREAD_TO_TARGET_RATIO
    )


def _candidate_item(
    candidate: dict[str, Any],
    fit: dict[str, Any],
    validation: dict[str, Any],
    fit_coverage: dict[str, Any],
    validation_coverage: dict[str, Any],
    spread_p95: float,
) -> dict[str, Any]:
    ratio = spread_p95 / candidate["take_profit_usd_per_oz"]
    return {
        "parameters": candidate,
        "fit": fit,
        "validation": validation,
        "fit_coverage": fit_coverage,
        "validation_coverage": validation_coverage,
        "development_p95_spread_usd_per_oz": spread_p95,
        "development_p95_spread_to_target_pct": round(100 * ratio, 2),
        "selection_rule_passed": _eligible(fit, validation, spread_to_target_ratio=ratio),
    }


def _candidate_row(item: dict[str, Any]) -> dict[str, Any]:
    fit, val, p = item["fit"], item["validation"], item["parameters"]
    replay = item["development_replay_diagnostics"]
    return {
        "market_identity": "Gold Spot / U.S. Dollar (XAUUSD); OANDA practice XAU_USD only",
        "provider": "OANDA",
        "environment": "practice",
        "quantity_units": 100,
        "units_per_lot": 100,
        "lot_size_ounces": 100,
        "currency": "USD",
        **p,
        "reward_risk_ratio": round(p["take_profit_usd_per_oz"] / p["stop_loss_usd_per_oz"], 4),
        "breakeven_win_rate_before_spread_pct": round(
            100 * p["stop_loss_usd_per_oz"] / (p["stop_loss_usd_per_oz"] + p["take_profit_usd_per_oz"]),
            2,
        ),
        "development_p95_spread_usd_per_oz": item["development_p95_spread_usd_per_oz"],
        "development_p95_spread_to_target_pct": item["development_p95_spread_to_target_pct"],
        "development_closed_trades": fit["closed_trades"],
        "development_wins": fit["wins"],
        "development_losses": fit["losses"],
        "development_win_rate_pct": fit["win_rate_pct"],
        "development_win_rate_wilson_95pct": fit["win_rate_95pct_wilson"],
        "development_net_pnl_usd": fit["net_pnl_usd"],
        "development_expectancy_usd_per_trade": fit["expectancy_usd_per_closed_trade"],
        "development_profit_factor": fit["profit_factor"],
        "development_max_drawdown_usd": fit["max_closed_trade_drawdown_usd"],
        "development_eligible_active_days": item["fit_coverage"]["eligible_active_trading_days"],
        "development_mean_daily_review_calls": item["fit_coverage"]["proposed_review_calls_per_eligible_active_day"]["mean"],
        "development_mean_daily_raw_setup_signals": item["fit_coverage"]["raw_setup_signals_per_eligible_active_day"]["mean"],
        "development_mean_daily_entries": item["fit_coverage"]["actual_entries_per_eligible_active_day"]["mean"],
        "development_zero_opportunity_days": item["fit_coverage"]["zero_opportunity_days"],
        "development_zero_proposed_review_call_days": item["fit_coverage"]["zero_proposed_review_call_days"],
        "development_daily_review_call_histogram": item["fit_coverage"]["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"],
        "validation_closed_trades": val["closed_trades"],
        "validation_wins": val["wins"],
        "validation_losses": val["losses"],
        "validation_win_rate_pct": val["win_rate_pct"],
        "validation_win_rate_wilson_95pct": val["win_rate_95pct_wilson"],
        "validation_net_pnl_usd": val["net_pnl_usd"],
        "validation_expectancy_usd_per_trade": val["expectancy_usd_per_closed_trade"],
        "validation_profit_factor": val["profit_factor"],
        "validation_max_drawdown_usd": val["max_closed_trade_drawdown_usd"],
        "validation_eligible_active_days": item["validation_coverage"]["eligible_active_trading_days"],
        "validation_mean_daily_review_calls": item["validation_coverage"]["proposed_review_calls_per_eligible_active_day"]["mean"],
        "validation_mean_daily_raw_setup_signals": item["validation_coverage"]["raw_setup_signals_per_eligible_active_day"]["mean"],
        "validation_mean_daily_entries": item["validation_coverage"]["actual_entries_per_eligible_active_day"]["mean"],
        "validation_zero_opportunity_days": item["validation_coverage"]["zero_opportunity_days"],
        "validation_zero_proposed_review_call_days": item["validation_coverage"]["zero_proposed_review_call_days"],
        "validation_daily_review_call_histogram": item["validation_coverage"]["proposed_review_calls_per_eligible_active_day"]["histogram_0_1_2_3_4plus"],
        "validation_daily_entry_histogram": item["validation_coverage"]["actual_entries_per_eligible_active_day"]["histogram_0_1_2_3_4plus"],
        "eligible_training_only": item["selection_rule_passed"],
        "development_unresolved_positions_at_fit_validation_boundaries": replay["unresolved_positions_at_boundaries"],
        "development_unfilled_or_boundary_signals": replay["unfilled_or_boundary_signals"],
        "development_signals_suppressed_while_position_open": replay["signals_suppressed_by_open_position"],
        "development_discarded_partial_sample_bars": replay["discarded_partial_interval_bars"],
        "development_discarded_partial_warmup_bars": replay["discarded_partial_warmup_bars"],
        "holdout_closed_trades": None,
        "holdout_wins": None,
        "holdout_losses": None,
        "holdout_win_rate_pct": None,
        "holdout_win_rate_wilson_95pct": None,
        "holdout_net_pnl_usd": None,
        "holdout_expectancy_usd_per_trade": None,
        "holdout_profit_factor": None,
        "holdout_max_drawdown_usd": None,
        "holdout_review_calls_mean_per_active_day": None,
        "holdout_raw_setup_signals_mean_per_active_day": None,
        "holdout_actual_entries_mean_per_active_day": None,
        "holdout_closed_trades_mean_per_active_day": None,
    }


def _candidate_rejection_reasons(item: dict[str, Any]) -> list[str]:
    reasons = []
    fit, val = item["fit"], item["validation"]
    if fit["closed_trades"] < MIN_DEVELOPMENT_TRADES:
        reasons.append("development trades below minimum")
    if val["closed_trades"] < MIN_VALIDATION_TRADES:
        reasons.append("inner-validation trades below minimum")
    if fit["net_pnl_usd"] is None or fit["net_pnl_usd"] <= 0:
        reasons.append("development net P&L is not positive")
    if val["net_pnl_usd"] is None or val["net_pnl_usd"] <= 0:
        reasons.append("validation net P&L is not positive")
    if not _profit_factor_passes(fit):
        reasons.append("development profit factor is below 1.10")
    if not _profit_factor_passes(val):
        reasons.append("validation profit factor is below 1.10")
    if item["development_p95_spread_to_target_pct"] > 100 * MAX_SPREAD_TO_TARGET_RATIO:
        reasons.append("development p95 spread exceeds 25% of target")
    if (
        fit["max_closed_trade_drawdown_usd"] is None
        or fit["max_closed_trade_drawdown_usd"] > MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD
        or val["max_closed_trade_drawdown_usd"] is None
        or val["max_closed_trade_drawdown_usd"] > MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD
    ):
        reasons.append("development or validation drawdown exceeds the USD 3,000 limit")
    return reasons


def _holdout_passes(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    if metrics["closed_trades"] < MIN_HOLDOUT_TRADES:
        reasons.append(f"holdout has fewer than {MIN_HOLDOUT_TRADES} closed trades")
    if metrics["net_pnl_usd"] is None or metrics["net_pnl_usd"] <= 0:
        reasons.append("holdout net P&L is not positive")
    if metrics["expectancy_usd_per_closed_trade"] is None or metrics["expectancy_usd_per_closed_trade"] <= 0:
        reasons.append("holdout expectancy is not positive")
    factor = metrics["profit_factor"]
    pf_passes = (
        metrics["wins"] > 0 and metrics["losses"] == 0
        if factor is None
        else factor >= MIN_HOLDOUT_PROFIT_FACTOR
    )
    if not pf_passes:
        reasons.append("holdout profit factor is below 1.05")
    if (
        metrics["max_closed_trade_drawdown_usd"] is None
        or metrics["max_closed_trade_drawdown_usd"] > MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD
    ):
        reasons.append("holdout drawdown exceeds the USD 3,000 limit")
    return not reasons, reasons


def run_highwin_optimization(
    sample: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    *,
    source_sha256: str,
    baseline_report: dict[str, Any],
    candidates: Sequence[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Search only development data; evaluate exactly one selected holdout once."""
    configurations = list(candidates if candidates is not None else predeclared_candidates())
    if not configurations or len(configurations) > MAX_CANDIDATES:
        raise ValueError(f"High-win configuration count must be between 1 and {MAX_CANDIDATES}")
    configurations = [normalize_highwin_parameters(item) for item in configurations]
    if len(sample) < 700 or len(warmup) < 100:
        raise XAUHistoryError("Insufficient complete OANDA history for the predeclared high-win study")

    outer_cut = _raw_split_before_entry_session(sample, max(1, int(len(sample) * TRAIN_FRACTION)))
    development = sample[:outer_cut]
    if len(development) < 500:
        raise XAUHistoryError("Pre-holdout development history is too small")
    development_prepared = _prepare(development)
    validation_cut = _split_before_entry_session(
        development_prepared,
        max(1, int(len(development_prepared) * 0.70)),
    )
    if validation_cut >= len(development) - 1:
        raise XAUHistoryError("Inner development/validation split has insufficient data")
    spread_stats = _training_spread_p95(development)
    p95_spread = spread_stats["p95_spread_usd_per_oz"]

    evaluated: list[dict[str, Any]] = []
    for config in configurations:
        simulation = _simulate_highwin(
            development,
            warmup,
            config,
            boundaries=(validation_cut,),
        )
        item = _candidate_item(
            config,
            simulation["folds"][0],
            simulation["folds"][1],
            simulation["coverage_by_fold"][0],
            simulation["coverage_by_fold"][1],
            p95_spread,
        )
        item["development_replay_diagnostics"] = {
            "unresolved_positions_at_boundaries": len(simulation["unresolved_positions"]),
            "unfilled_or_boundary_signals": simulation["unfilled_or_boundary_signals"],
            "signals_suppressed_by_open_position": simulation["signals_suppressed_by_open_position"],
            "discarded_partial_interval_bars": simulation["discarded_partial_interval_bars"],
            "discarded_partial_warmup_bars": simulation["discarded_partial_warmup_bars"],
            "time_based_exits": simulation["time_based_exits"],
        }
        item["reasons_rejected"] = _candidate_rejection_reasons(item)
        evaluated.append(item)

    eligible = [item for item in evaluated if item["selection_rule_passed"]]
    def coverage_score(item: dict[str, Any]) -> float:
        mean_calls = item["validation_coverage"]["proposed_review_calls_per_eligible_active_day"]["mean"]
        return max(0.0, 1.0 - abs((mean_calls or 0.0) - 2.5) / 2.5)

    selected = max(
        eligible,
        key=lambda item: (
            coverage_score(item),
            item["validation"]["win_rate_pct"]
            if item["validation"]["win_rate_pct"] is not None
            else -1,
            item["validation"]["profit_factor"]
            if item["validation"]["profit_factor"] is not None
            else math.inf,
            item["validation"]["expectancy_usd_per_closed_trade"]
            if item["validation"]["expectancy_usd_per_closed_trade"] is not None
            else -math.inf,
            -item["validation"]["max_closed_trade_drawdown_usd"],
        ),
    ) if eligible else None

    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "study": STUDY_NAME,
        "market_identity": "Gold Spot / U.S. Dollar (XAUUSD), OANDA practice instrument XAU_USD only",
        "research_status": HIGHWIN_RESEARCH_STATUS,
        "status": "NO_TRAINING_CANDIDATE_MET_MINIMUM_RULES",
        "data_source": "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC",
        "source_file": baseline_report.get("raw_data_file"),
        "source_sha256": source_sha256,
        "user_chart_snapshot_used_as_a_quote_or_price_input": False,
        "sample_start_inclusive": baseline_report.get("sample_start_inclusive"),
        "sample_end_exclusive": baseline_report.get("sample_end_exclusive"),
        "sample_bars": len(sample),
        "candidate_count": len(configurations),
        "development_bars": outer_cut,
        "inner_fit_bars": validation_cut,
        "inner_validation_bars": outer_cut - validation_cut,
        "warmup_bars": len(warmup),
        "predeclared_configuration_count": len(configurations),
        "predeclared_configurations": configurations,
        "training_eligible_candidate_count": len(eligible),
        "selection_rules": {
            "minimum_development_closed_trades": MIN_DEVELOPMENT_TRADES,
            "minimum_inner_validation_closed_trades": MIN_VALIDATION_TRADES,
            "development_and_validation_net_pnl_must_be_positive": True,
            "minimum_profit_factor_fit_and_validation": MIN_PROFIT_FACTOR,
            "maximum_fit_and_validation_closed_trade_drawdown_usd": MAX_DEVELOPMENT_OR_VALIDATION_DRAWDOWN_USD,
            "maximum_development_p95_spread_to_target_pct": 25.0,
            "coverage_rank": "Among candidates meeting positive expectancy, sample, PF, drawdown and spread rules: closest validation actionable proposed/review calls per eligible active day to 2.5, then higher validation win rate/PF/expectancy and lower drawdown. Actual accepted entries are separately capped at 3/day. 2/day is an objective, not a hard guarantee.",
            "final_holdout_rule": "Read/evaluate once only after one candidate passes all training rules; require at least 30 closed holdout trades, positive P&L/expectancy, PF >=1.05, and drawdown <=$3,000 for a positive research outcome.",
            "holdout_retraining_prohibited": True,
            "maximum_holding_minutes": 25,
            "overnight_holding_allowed": False,
        },
        "selection_looked_at_final_holdout": False,
        "holdout_evaluation_count": 0,
        "selected_parameters": None,
        "training_fit": None,
        "training_fit_daily_coverage": None,
        "development_70pct_train_aggregate": None,
        "development_70pct_train_aggregate_daily_coverage": None,
        "inner_validation": None,
        "inner_validation_daily_coverage": None,
        "out_of_sample": None,
        "out_of_sample_daily_coverage": None,
        "oos_validation_failures": None,
        "spread_filter": {
            **spread_stats,
            "maximum_p95_spread_to_target_pct": 25.0,
            "calculated_from": "development partition only; bid/ask close spread during UTC 16:00–23:00 entry session",
        },
        "risk_and_execution_rules": {
            "instrument": "Gold Spot / U.S. Dollar; XAUUSD; OANDA practice XAU_USD",
            "quantity_units": UNITS_PER_LOT,
            "lot_size": LOT_SIZE,
            "units_per_lot": 100,
            "lot_size_ounces": 100,
            "currency": "USD",
            "maximum_stop_usd_per_oz": 3.0,
            "maximum_stop_loss_usd_per_trade_at_100_units": 300.0,
            "pnl_fills": "next complete strategy candle open; BUY at ask, SELL at bid; exits on actual side-specific OHLC",
            "ambiguous_stop_and_target_same_bar": "stop-first",
            "stop_gap": "adverse gap exits use the next observed exit-side bar open, even beyond stop",
            "utc_entry_session": "16:00 inclusive to 23:00 exclusive",
            "indicator_updates": "Every complete M1/M5 candle, outside the entry session and while a position is open",
            "research_holding_intent": {
                "max_hold_minutes": 25,
                "allow_overnight": False,
                "exit_at": "First complete strategy-bar exit-side close at or after 25 minutes, or the 23:00 UTC session boundary, whichever occurs first; stop/target still take precedence when triggered.",
                "entry_cutoff": "Do not model an entry unless 25 minutes of session remain before 23:00 UTC.",
                "gap_fallback": "If an unexpected provider/data gap crosses the UTC date, close at the next observed exit-side open, label no_overnight_forced_exit, and disclose the missing path.",
                "fold_or_sample_boundary": "Positions still open at a research boundary are reported unresolved and excluded from closed-trade metrics.",
            },
            "spread_to_target_cap": "Development-session p95 quoted spread must be <=25% of target; P&L also directly uses bid/ask-side prices.",
            "breakeven_win_rate": "Per candidate, stop/(stop+target) before spread, gaps, slippage, commission, financing, and other unavailable costs.",
            "financing_and_commission": "No financing/swap or commission schedule was verified or modeled; gross quote-side P&L includes observed bid/ask spread. The 25-minute, no-overnight policy avoids intentionally carrying positions overnight.",
            "daily_coverage_objective": "Target 2-3 actionable proposed/review calls per adequately covered ACTIVE UTC trading day; measured and ranked, never forced. Actual entries and later closed trades are separate.",
            "opportunity_definition": "An actionable in-session BUY/SELL signal with a next complete in-session entry candle while the simulated strategy is flat; raw reducer setups while a position is held and boundary/unfilled setups are counted separately, not as actionable review calls.",
            "quote_source": "Only saved, verified OANDA practice XAU_USD bid/ask OHLC and provider candle timestamps. User chart/snapshot prices are reference only and are not used as quote, entry, exit, or price input.",
            "max_actual_entries_per_utc_day": 3,
            "daily_count_semantics": "Only successfully modeled next-bar entries count toward the daily 3-entry cap; actionable review calls, all raw setups, open-position-suppressed setups, unfilled signals, and closed trades are reported separately.",
            "eligible_active_day_definition": "At least 60% of expected complete candles in the 16:00–23:00 UTC entry window (252 M1 or 50 M5); weekends and under-covered partial days do not count.",
        },
        "runtime_research_interface": {
            "agent_class": "agents.xauusd_highwin.XAUUSDHighWinResearchAgent",
            "shared_indicator_reducer": "agents.xauusd_highwin.advance_highwin_bar",
            "accepted_entry_counter_hook": "XAUUSDHighWinResearchAgent.register_research_entry(entry_time)",
            "entry_policy_hook": "XAUUSDHighWinResearchAgent.research_entry_policy_allows(entry_time)",
            "holding_exit_hook": "XAUUSDHighWinResearchAgent.should_force_research_time_exit(observed_at) then close at actual current OANDA bid/ask",
            "position_clear_hook": "XAUUSDHighWinResearchAgent.mark_research_position_closed() after any modeled/accepted exit",
            "main_or_paper_live_gates_modified": False,
            "hook_semantics": "Parent may call only after an entry is accepted/filled; counts actual entries, not candidate calls. No paper integration is enabled by this study.",
        },
        "paper_entries_enabled": False,
        "live_orders_enabled": False,
        "execution_validated": False,
        "recommended_for_paper": False,
        "baseline_comparison": {
            "source_status": baseline_report.get("status"),
            "source_strategy_changed": baseline_report.get("strategy_changed"),
            "training": baseline_report.get("train"),
            "out_of_sample": baseline_report.get("out_of_sample"),
            "note": "The frozen 3-trade baseline is context only; it is not a 90% strategy claim.",
        },
        "limitations": [
            "90% is an aspirational training/research target, not a guarantee or an accepted threshold.",
            "This is a bounded 32-setting study, not a global search. Its small chronological samples have substantial uncertainty.",
            "M1/M5 OHLC cannot reveal intrabar ordering; stop-first treatment is conservative but is not tick-level order/fill validation.",
            "Historical spread is represented by actual bid/ask prices and a development-only p95/target filter. Commission, swap, slippage beyond sampled OHLC, and broker execution are unavailable.",
            "No strategy has been enabled; a positive holdout alone would not validate live execution or open the independent paper/live gate.",
            "Coverage is reported only on eligible active trading days. Minimum 2/day is not a filter that can force a review call or trade; realized frequency may remain below target.",
        ],
    }

    rows = []
    for item in evaluated:
        row = _candidate_row(item)
        row["rejection_reasons"] = "; ".join(item["reasons_rejected"])
        rows.append(row)

    if selected is None:
        diagnostics = sorted(
            evaluated,
            key=lambda item: (
                item["validation"]["win_rate_pct"]
                if item["validation"]["win_rate_pct"] is not None
                else -1,
                item["validation"]["closed_trades"],
            ),
            reverse=True,
        )
        most_profitable = max(
            evaluated,
            key=lambda item: (
                item["validation"]["net_pnl_usd"]
                if item["validation"]["net_pnl_usd"] is not None
                else -math.inf
            ),
        )
        best = diagnostics[0]
        report["training_diagnostics"] = {
            "description": "Rejected development-fit/inner-validation results only; no losing setting was evaluated on the final holdout.",
            "highest_validation_win_rate_candidate": {
                "parameters": best["parameters"],
                "development_fit": best["fit"],
                "inner_validation": best["validation"],
                "development_daily_coverage": best["fit_coverage"],
                "inner_validation_daily_coverage": best["validation_coverage"],
                "reasons_rejected": best["reasons_rejected"],
                "replay_diagnostics": best["development_replay_diagnostics"],
            },
            "best_validation_net_pnl_candidate": {
                "parameters": most_profitable["parameters"],
                "development_fit": most_profitable["fit"],
                "inner_validation": most_profitable["validation"],
                "development_daily_coverage": most_profitable["fit_coverage"],
                "inner_validation_daily_coverage": most_profitable["validation_coverage"],
                "reasons_rejected": most_profitable["reasons_rejected"],
                "replay_diagnostics": most_profitable["development_replay_diagnostics"],
            },
            "best_coverage_candidate": {
                "parameters": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["parameters"],
                "development_daily_coverage": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["fit_coverage"],
                "inner_validation_daily_coverage": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["validation_coverage"],
                "development_fit": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["fit"],
                "inner_validation": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["validation"],
                "win_rate_pct": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["validation"]["win_rate_pct"],
                "reasons_rejected": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["reasons_rejected"],
                "replay_diagnostics": max(
                    evaluated,
                    key=lambda item: (
                        coverage_score(item),
                        item["validation"]["closed_trades"],
                    ),
                )["development_replay_diagnostics"],
                "not_selected_unless_profitability_rules_pass": True,
            },
            "highest_validation_win_rate_candidate_by_win_rate": {
                "parameters": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["parameters"],
                "development_fit": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["fit"],
                "inner_validation": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["validation"],
                "development_daily_coverage": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["fit_coverage"],
                "inner_validation_daily_coverage": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["validation_coverage"],
                "not_selected_unless_profitability_rules_pass": True,
                "replay_diagnostics": max(
                    evaluated,
                    key=lambda item: (
                        item["validation"]["win_rate_pct"]
                        if item["validation"]["win_rate_pct"] is not None
                        else -1,
                        item["validation"]["closed_trades"],
                    ),
                )["development_replay_diagnostics"],
            },
            "daily_call_coverage_target": "2-3 actionable proposed/review calls per eligible active day; not guaranteed or forced",
            "positive_expectancy_inner_validation_candidates": sum(
                item["validation"]["net_pnl_usd"] is not None
                and item["validation"]["net_pnl_usd"] > 0
                for item in evaluated
            ),
        }
        report["reason"] = (
            "No predeclared candidate passed minimum sample size, positive development and validation P&L, "
            "profit-factor, drawdown, and spread-cost rules; the final holdout was left untouched."
        )
        return report, rows

    report["selected_parameters"] = selected["parameters"]
    report["training_fit"] = selected["fit"]
    report["training_fit_daily_coverage"] = selected["fit_coverage"]
    report["inner_validation"] = selected["validation"]
    report["inner_validation_daily_coverage"] = selected["validation_coverage"]
    report["selection_looked_at_final_holdout"] = False

    # This is the sole code path that reads final-holdout prices, after one
    # configuration has passed all predeclared development/validation rules.
    full = _simulate_highwin(
        sample,
        warmup,
        selected["parameters"],
        boundaries=(outer_cut,),
    )
    train, holdout = full["folds"]
    holdout_passed, failures = _holdout_passes(holdout)
    report["holdout_evaluation_count"] = 1
    report["selection_looked_at_final_holdout"] = True
    report["out_of_sample"] = holdout
    report["out_of_sample_daily_coverage"] = full["coverage_by_fold"][1]
    report["oos_validation_failures"] = failures
    report["selected_candidate_trade_log"] = full["trades"]
    report["selected_candidate_unresolved_positions"] = full["unresolved_positions"]
    report["selected_candidate_unfilled_or_boundary_signals"] = full["unfilled_or_boundary_signals"]
    report["selected_candidate_signals_suppressed_by_open_position"] = full[
        "signals_suppressed_by_open_position"
    ]
    report["development_70pct_train_aggregate"] = train
    report["development_70pct_train_aggregate_daily_coverage"] = full["coverage_by_fold"][0]
    report["status"] = (
        "OOS_POSITIVE_BUT_NOT_PAPER_READY"
        if holdout_passed
        else "SELECTED_CANDIDATE_FAILED_FINAL_HOLDOUT"
    )
    report["research_status"] = report["status"]
    report["recommended_for_paper"] = False
    selected_row = next(
        row for row in rows if row["rsi_period"] == selected["parameters"]["rsi_period"]
        and row["rsi_reentry_threshold"] == selected["parameters"]["rsi_reentry_threshold"]
        and row["bar_interval_minutes"] == selected["parameters"]["bar_interval_minutes"]
        and row["stop_loss_usd_per_oz"] == selected["parameters"]["stop_loss_usd_per_oz"]
        and row["take_profit_usd_per_oz"] == selected["parameters"]["take_profit_usd_per_oz"]
    )
    selected_row.update(
        {
            "holdout_closed_trades": holdout["closed_trades"],
            "holdout_wins": holdout["wins"],
            "holdout_losses": holdout["losses"],
            "holdout_win_rate_pct": holdout["win_rate_pct"],
            "holdout_win_rate_wilson_95pct": holdout["win_rate_95pct_wilson"],
            "holdout_net_pnl_usd": holdout["net_pnl_usd"],
            "holdout_expectancy_usd_per_trade": holdout["expectancy_usd_per_closed_trade"],
            "holdout_profit_factor": holdout["profit_factor"],
            "holdout_max_drawdown_usd": holdout["max_closed_trade_drawdown_usd"],
            "holdout_review_calls_mean_per_active_day": full["coverage_by_fold"][1]["proposed_review_calls_per_eligible_active_day"]["mean"],
            "holdout_raw_setup_signals_mean_per_active_day": full["coverage_by_fold"][1]["raw_setup_signals_per_eligible_active_day"]["mean"],
            "holdout_actual_entries_mean_per_active_day": full["coverage_by_fold"][1]["actual_entries_per_eligible_active_day"]["mean"],
            "holdout_closed_trades_mean_per_active_day": full["coverage_by_fold"][1]["closed_trades_per_eligible_active_day"]["mean"],
        }
    )
    return report, rows


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def optimize_saved_highwin(evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR) -> dict[str, Any]:
    """Predeclare configurations, then verify/replay saved data without provider requests."""
    directory = Path(evidence_dir)
    configurations = predeclared_candidates()
    report_path = directory / "xauusd_highwin.json"
    _write_json(
        report_path,
        {
            "schema_version": 1,
            "study": STUDY_NAME,
            "market_identity": "Gold Spot / U.S. Dollar (XAUUSD), OANDA practice XAU_USD only",
            "status": "PREDECLARED_CONFIGURATIONS_NOT_YET_EVALUATED",
            "user_chart_snapshot_used_as_a_quote_or_price_input": False,
            "candidate_count": len(configurations),
            "predeclared_configurations": configurations,
            "quantity_units": 100,
            "lot_size_ounces": 100,
            "selection_rules": {
                "minimum_fit_trades": MIN_DEVELOPMENT_TRADES,
                "minimum_inner_validation_trades": MIN_VALIDATION_TRADES,
                "fit_and_validation_net_pnl_positive": True,
                "profit_factor_minimum": MIN_PROFIT_FACTOR,
                "stop_loss_usd_per_oz_maximum": 3.0,
                "max_hold_minutes": 25,
                "allow_overnight": False,
                "entry_cutoff": "At least 25 minutes must remain before the 23:00 UTC session close.",
                "development_p95_spread_to_target_pct_maximum": 25.0,
                "actual_entries_per_utc_day_maximum": 3,
                "coverage_objective_per_eligible_active_day": "2-3 actionable proposed/review calls; actual entries separately capped at 3/day; ranking objective, not hard trade mandate",
                "eligible_active_day_definition": "At least 60% of the expected complete M1/M5 bars in UTC 16:00–23:00",
                "holdout": "chronological final 30%; untouched unless exactly one candidate meets all fit/validation rules",
            },
            "paper_entries_enabled": False,
            "live_orders_enabled": False,
        },
    )

    baseline_path = directory / "xauusd_backtest.json"
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
        raise XAUHistoryError("The source report is not the frozen unchanged OANDA baseline")
    all_bars, source_sha256 = _read_verified_saved_history(directory, baseline)
    sample_start = _timestamp(baseline["sample_start_inclusive"])
    sample_end = _timestamp(baseline["sample_end_exclusive"])
    sample, warmup = [], []
    for row in all_bars:
        stamp = _timestamp(row["time"])
        if sample_start <= stamp < sample_end:
            sample.append(row)
        elif stamp < sample_start:
            warmup.append(row)
    if len(sample) != baseline.get("complete_sample_candles"):
        raise XAUHistoryError("Saved source rows do not match the frozen baseline report")
    report, rows = run_highwin_optimization(
        sample,
        warmup,
        source_sha256=source_sha256,
        baseline_report=baseline,
        candidates=configurations,
    )
    report["provider_requests_made"] = 0
    report["raw_csv_modified"] = False
    report["candidate_results_csv"] = "xauusd_highwin_candidates.csv"
    _write_json(report_path, report)

    csv_path = directory / "xauusd_highwin_candidates.csv"
    temporary = csv_path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(csv_path)
    return report


if __name__ == "__main__":
    result = optimize_saved_highwin()
    print(
        json.dumps(
            {
                key: result.get(key)
                for key in (
                    "status",
                    "research_status",
                    "predeclared_configuration_count",
                    "training_eligible_candidate_count",
                    "selected_parameters",
                    "training_diagnostics",
                    "out_of_sample",
                    "oos_validation_failures",
                    "selection_looked_at_final_holdout",
                    "source_sha256",
                )
            },
            indent=2,
            allow_nan=False,
        )
    )