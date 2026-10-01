"""Bounded, no-lookahead XAUUSD parameter selection on saved OANDA history."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from agents.xauusd import (
    LOT_SIZE,
    STRATEGY_PARAMETERS,
    UNITS_PER_LOT,
    advance_completed_bar,
    initial_strategy_state,
    normalize_parameters,
)
from agents.base import Signal
from backtest.xauusd_evidence import (
    DEFAULT_EVIDENCE_DIR,
    TRAIN_FRACTION,
    XAUHistoryError,
    _bar_observation_time,
    _exit_bar,
    _midpoint_close,
    _read_verified_saved_history,
    _timestamp,
    _within_entry_session,
)


ALGORITHM = "24 predeclared finite EMA trend/reversal/breakout configurations on genuine M1 or contiguous M5 bid/ask OHLC; UTC-daily candidate-signal cap 3; 2 completed-bar confirmations"
QUANTITY_UNITS = 100
LOT_SIZE = 1.0
TUNING_FRACTION_OF_TRAIN = 0.70
MIN_FIT_TRADES = 30
MIN_VALIDATION_TRADES = 20
MIN_HOLDOUT_TRADES = 20
MIN_VALIDATION_PROFIT_FACTOR = 1.10
MAX_VALIDATION_DRAWDOWN_USD = 2_500.0
MIN_HOLDOUT_PROFIT_FACTOR = 1.05
MAX_HOLDOUT_DRAWDOWN_USD = 2_500.0
MIN_ENTRY_SESSION_UTC = (16, 0)
MAX_CANDIDATES = 24


def candidate_grid() -> list[dict[str, Any]]:
    """Return 24 predeclared settings; no broad search or holdout tuning."""
    exits = (
        (0.50, 0.75),
        (0.75, 1.0),
        (1.0, 1.25),
        (1.5, 1.5),
    )
    model_configs = (
        ("ema_trend_continuation", 1, 12, 26, 5),
        ("ema_trend_continuation", 5, 4, 12, 5),
        ("ema_mean_reversion", 1, 12, 26, 5),
        ("ema_mean_reversion", 5, 4, 12, 5),
        ("ema_range_breakout", 1, 12, 26, 3),
        ("ema_range_breakout", 5, 4, 12, 3),
    )
    result = []
    for model, timeframe, fast, slow, lookback in model_configs:
        for target, stop in exits:
            result.append(
                normalize_parameters(
                    {
                        "signal_model": model,
                        "bar_interval_minutes": timeframe,
                        "fast_ema": fast,
                        "slow_ema": slow,
                        "min_ema_separation_usd": 1.0,
                        "confirmation_buffer_usd": 0.15,
                        "breakout_lookback": lookback,
                        "confirmation_bars": 2,
                        "stop_loss_usd_per_oz": stop,
                        "take_profit_usd_per_oz": target,
                        "max_trades_per_utc_day": 3,
                        "entry_cooldown_seconds": 30,
                        "position_quantity_units": QUANTITY_UNITS,
                    }
                )
            )
    if len(result) > MAX_CANDIDATES:
        raise AssertionError("Bounded candidate search exceeded its declared limit")
    return result


def _prepare(
    bars: Sequence[dict[str, Any]], *, timeframe_minutes: int = 1
) -> list[dict[str, Any]]:
    prepared = []
    previous = None
    for bar in bars:
        stamp = _timestamp(bar["time"])
        if previous is not None and stamp <= previous:
            raise XAUHistoryError("Optimizer requires strictly chronological, unique source candles")
        previous = stamp
        prepared.append(
            {
                "source": bar,
                "open_time": stamp,
                "observed_at": stamp + timedelta(minutes=timeframe_minutes),
                "mid_close": _midpoint_close(bar),
                "minute_index": int(stamp.timestamp() // (60 * timeframe_minutes)),
                "utc_day": (stamp + timedelta(minutes=timeframe_minutes)).date(),
            }
        )
    return prepared


def _aggregate_minutes(
    bars: Sequence[dict[str, Any]], interval_minutes: int
) -> tuple[list[dict[str, Any]], int]:
    """Aggregate only exact contiguous genuine provider bars into 1/5-minute OHLC."""
    if interval_minutes == 1:
        return list(bars), 0
    if interval_minutes != 5:
        raise ValueError("Only genuine OANDA M1 and contiguous M5 studies are supported")
    output: list[dict[str, Any]] = []
    group: list[dict[str, Any]] = []
    group_start: datetime | None = None
    last_open: datetime | None = None
    dropped_partial = 0
    for bar in bars:
        stamp = _timestamp(bar["time"])
        floored = stamp.replace(minute=(stamp.minute // interval_minutes) * interval_minutes, second=0, microsecond=0)
        if floored != group_start:
            if group:
                dropped_partial += 1
            group = []
            group_start = floored
            last_open = None
        if stamp != floored + timedelta(minutes=len(group)):
            if group:
                dropped_partial += 1
            group = []
            group_start = floored
            last_open = None
        if not group and stamp != floored:
            dropped_partial += 1
            last_open = stamp
            continue
        group.append(bar)
        last_open = stamp
        if len(group) < interval_minutes:
            continue
        if stamp != floored + timedelta(minutes=interval_minutes - 1):
            dropped_partial += 1
            group = []
            continue

        combined = dict(group[0])
        combined["time"] = _utc_z(floored)
        for side in ("bid", "ask"):
            for field in ("open", "high", "low", "close"):
                key = f"{side}_{field}"
                if field == "open":
                    combined[key] = group[0][key]
                elif field == "close":
                    combined[key] = group[-1][key]
                elif field == "high":
                    combined[key] = max(float(row[key]) for row in group)
                else:
                    combined[key] = min(float(row[key]) for row in group)
        combined["complete_interval_m1_rows"] = len(group)
        output.append(combined)
        group = []
    if group:
        dropped_partial += 1
    return output, dropped_partial


def _utc_z(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _split_before_entry_session(bars: Sequence[dict[str, Any]], desired_index: int) -> int:
    """Choose the next UTC pre-entry observation so the new daily cap starts flat."""
    for index in range(max(1, desired_index), len(bars) - 1):
        observed = bars[index]["observed_at"]
        if (observed.hour, observed.minute) < MIN_ENTRY_SESSION_UTC:
            return index
    return min(max(1, desired_index), len(bars) - 1)


def _raw_split_before_entry_session(
    bars: Sequence[dict[str, Any]], desired_index: int
) -> int:
    """Locate a split using timestamps alone, before any holdout price is read."""
    for index in range(max(1, desired_index), len(bars) - 1):
        observed = _timestamp(bars[index]["time"]) + timedelta(minutes=1)
        if (observed.hour, observed.minute) < MIN_ENTRY_SESSION_UTC:
            return index
    return min(max(1, desired_index), len(bars) - 1)


def _entry_session(observed_at: datetime) -> bool:
    encoded = observed_at.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return _within_entry_session(encoded)


def _metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [float(item["pnl_usd"]) for item in trades]
    wins = sum(value > 0 for value in pnl)
    losses = sum(value < 0 for value in pnl)
    breakevens = len(pnl) - wins - losses
    positive = sum(value for value in pnl if value > 0)
    negative = -sum(value for value in pnl if value < 0)
    equity = peak = max_drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    rate = wins / len(pnl) if pnl else None
    return {
        "closed_trades": len(pnl),
        "wins": wins,
        "losses": losses,
        "breakeven": breakevens,
        "win_rate_pct": round(100 * rate, 2) if rate is not None else None,
        "win_rate_95pct_wilson": _wilson_interval(wins, len(pnl)),
        "net_pnl_usd": round(sum(pnl), 2) if pnl else None,
        "expectancy_usd_per_closed_trade": round(sum(pnl) / len(pnl), 2) if pnl else None,
        "profit_factor": round(positive / negative, 4) if negative else None,
        "gross_profit_usd": round(positive, 2) if pnl else None,
        "gross_loss_usd": round(negative, 2) if pnl else None,
        "max_closed_trade_drawdown_usd": round(max_drawdown, 2) if pnl else None,
        "unclosed_or_boundary_positions_counted_as_results": False,
    }


def _wilson_interval(wins: int, total: int, z: float = 1.95996398454) -> dict[str, float] | None:
    if total <= 0:
        return None
    n = float(total)
    p = wins / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denominator
    return {"low_pct": round(100 * max(0.0, center - spread), 2), "high_pct": round(100 * min(1.0, center + spread), 2)}


def _simulate(
    bars: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    parameters: dict[str, Any],
    *,
    boundaries: Sequence[int] = (),
) -> dict[str, Any]:
    """One causal price-path replay, marking—not closing—positions at cut lines."""
    config = normalize_parameters(parameters)
    timeframe = config["bar_interval_minutes"]
    source_prepared = _prepare(bars)
    source_cuts = [source_prepared[index]["open_time"] for index in boundaries]
    study_bars, dropped_study = _aggregate_minutes(bars, timeframe)
    prepared = _prepare(study_bars, timeframe_minutes=timeframe)
    study_warmup, dropped_warmup = _aggregate_minutes(warmup, timeframe)
    prepared_warmup = _prepare(study_warmup, timeframe_minutes=timeframe)
    if len(prepared_warmup) < 26:
        raise XAUHistoryError("Optimizer requires 26 genuine pre-sample strategy bars for EMA warmup")
    state = initial_strategy_state()
    warmup_signals = 0
    for warmup_bar in prepared_warmup:
        source_bar = warmup_bar["source"]
        warmup_signal = advance_completed_bar(
            state,
            {
                "observed_at": warmup_bar["observed_at"].isoformat(),
                "close": warmup_bar["mid_close"],
                "high": (float(source_bar["bid_high"]) + float(source_bar["ask_high"])) / 2,
                "low": (float(source_bar["bid_low"]) + float(source_bar["ask_low"])) / 2,
            },
            config,
        )
        warmup_signals += warmup_signal is not None

    cuts = []
    for boundary_time in source_cuts:
        resolved = next(
            (
                index
                for index, item in enumerate(prepared)
                if item["open_time"] >= boundary_time
            ),
            None,
        )
        if resolved is not None and resolved > 0 and resolved < len(prepared):
            cuts.append(resolved)
    cuts = sorted(set(cuts))
    partition = 0
    next_cut_index = 0
    active: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    counts = [0 for _ in range(len(cuts) + 1)]
    signal_counts = [0 for _ in range(len(cuts) + 1)]
    unfilled = 0
    suppressed_by_open = 0

    for index, prepared_bar in enumerate(prepared):
        if next_cut_index < len(cuts) and index == cuts[next_cut_index]:
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
            state["previous_confirmation"] = None
            state["confirmation_streak"] = 0
            partition += 1
            next_cut_index += 1

        source_bar = prepared_bar["source"]
        if pending is not None:
            intent = pending
            pending = None
            entry_time = prepared_bar["open_time"]
            if (
                intent["target_partition"] != partition
                or not _entry_session(entry_time)
                or intent["utc_day"] != entry_time.date()
            ):
                unfilled += 1
            else:
                is_long = intent["signal"] == Signal.BUY.value
                entry_price = float(source_bar["ask_open"] if is_long else source_bar["bid_open"])
                direction = 1 if is_long else -1
                stop_gap = config["stop_loss_usd_per_oz"]
                target_gap = config["take_profit_usd_per_oz"]
                active = {
                    "signal": intent["signal"],
                    "side": direction,
                    "signal_observed_at": intent["signal_observed_at"],
                    "signal_candle_open_time": intent["signal_candle_open_time"],
                    "entry_time": source_bar["time"],
                    "entry_price": round(entry_price, 8),
                    "stop_price": round(entry_price - direction * stop_gap, 8),
                    "target_price": round(entry_price + direction * target_gap, 8),
                    "stop_usd_per_oz": stop_gap,
                    "target_usd_per_oz": target_gap,
                    "position_quantity_units": QUANTITY_UNITS,
                    "lot_size": LOT_SIZE,
                    "currency": "USD",
                    "fold": partition,
                    "execution_model": f"next genuine OANDA M{timeframe} candle open; BUY at ask / SELL at bid",
                }
                immediate = _exit_bar(
                    {
                        "signal": active["signal"],
                        "entry_price": active["entry_price"],
                        "stop_price": active["stop_price"],
                        "target_price": active["target_price"],
                    },
                    source_bar,
                )
                if immediate is not None:
                    exit_price = float(immediate["price"])
                    pnl = (exit_price - entry_price) * QUANTITY_UNITS * direction
                    trades.append(
                        {
                            **active,
                            "exit_bar_open_time": source_bar["time"],
                            "exit_time_basis": "OANDA candle-open timestamp for entry candle containing exit; intrabar trigger time is unknown",
                            "exit_price": round(exit_price, 8),
                            "exit_reason": immediate["reason"],
                            "pnl_usd": round(pnl, 8),
                            "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                            "status": "CLOSED",
                        }
                    )
                    counts[partition] += 1
                    active = None
        elif active is not None:
            exit_event = _exit_bar(active, source_bar)
            if exit_event is not None:
                pnl = (float(exit_event["price"]) - active["entry_price"]) * QUANTITY_UNITS * active["side"]
                trade = {
                    **active,
                    "exit_bar_open_time": source_bar["time"],
                    "exit_time_basis": "OANDA strategy-candle-open timestamp; intrabar trigger time within its OHLC range is unknown",
                    "exit_price": round(float(exit_event["price"]), 8),
                    "exit_reason": exit_event["reason"],
                    "pnl_usd": round(pnl, 8),
                    "outcome": "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven",
                    "status": "CLOSED",
                }
                trades.append(trade)
                counts[active["fold"]] += 1
                active = None

        observation = prepared_bar["observed_at"]
        source_bar = prepared_bar["source"]
        candidate_signal = advance_completed_bar(
            state,
            {
                "observed_at": observation.isoformat(),
                "close": prepared_bar["mid_close"],
                "high": (float(source_bar["bid_high"]) + float(source_bar["ask_high"])) / 2,
                "low": (float(source_bar["bid_low"]) + float(source_bar["ask_low"])) / 2,
            },
            config,
        )
        signal = candidate_signal
        if signal is None:
            continue
        signal_counts[partition] += 1
        # The shared reducer emits and counts state transitions even if an
        # already-open broker position makes the feeder suppress the entry.
        if active is not None:
            suppressed_by_open += 1
            continue
        next_index = index + 1
        if (
            next_index >= len(prepared)
            or (next_cut_index < len(cuts) and next_index == cuts[next_cut_index])
            or (prepared[next_index]["minute_index"] != prepared_bar["minute_index"] + 1)
            or not _entry_session(prepared[next_index]["open_time"])
        ):
            unfilled += 1
            continue
        pending = {
            "signal": signal,
            "signal_observed_at": observation.isoformat(),
            "signal_candle_open_time": source_bar["time"],
            "target_partition": partition,
            "utc_day": observation.date(),
        }

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

    fold_metrics = []
    for fold in range(len(cuts) + 1):
        fold_metrics.append(
            _metrics([trade for trade in trades if trade["fold"] == fold])
        )
    return {
        "overall": _metrics(trades),
        "folds": fold_metrics,
        "trades": trades,
        "unresolved_positions": unresolved,
        "unfilled_or_boundary_signals": unfilled,
        "confirmed_signals": sum(signal_counts),
        "signals_suppressed_by_open_position": suppressed_by_open,
        "closed_trade_counts_by_fold": counts,
        "complete_bars": len(prepared),
        "requested_interval_minutes": timeframe,
        "discarded_partial_interval_bars": dropped_study,
        "discarded_partial_warmup_bars": dropped_warmup,
        "ema_warmup_bars": len(prepared_warmup),
        "warmup_signals": warmup_signals,
        "cut_indices": cuts,
        "final_strategy_state": {
            "ema_fast": state["ema_fast"],
            "ema_slow": state["ema_slow"],
            "last_utc_day": (
                state["last_utc_day"].isoformat()
                if state["last_utc_day"] is not None
                else None
            ),
            "daily_entry_count": state["daily_entry_count"],
            "last_signal_time": state["last_signal_time"],
            "previous_confirmation": state["previous_confirmation"],
            "confirmation_streak": state["confirmation_streak"],
            "recent_completed_bars": list(state["recent_completed_bars"]),
            "last_observed_at": (
                state["last_observed_at"].isoformat()
                if state["last_observed_at"] is not None
                else None
            ),
        },
    }


def _validation_passes(fit: dict[str, Any], validation: dict[str, Any]) -> bool:
    validation_pf = validation["profit_factor"]
    validation_pf_passes = (
        validation["wins"] > 0 and validation["losses"] == 0
        if validation_pf is None
        else validation_pf >= MIN_VALIDATION_PROFIT_FACTOR
    )
    return (
        fit["closed_trades"] >= MIN_FIT_TRADES
        and fit["net_pnl_usd"] is not None
        and fit["net_pnl_usd"] > 0
        and fit["max_closed_trade_drawdown_usd"] is not None
        and fit["max_closed_trade_drawdown_usd"] <= MAX_VALIDATION_DRAWDOWN_USD
        and (fit["profit_factor"] is None or fit["profit_factor"] >= 1.0)
        and validation["closed_trades"] >= MIN_VALIDATION_TRADES
        and validation["net_pnl_usd"] is not None
        and validation["net_pnl_usd"] > 0
        and validation_pf_passes
        and validation["max_closed_trade_drawdown_usd"] is not None
        and validation["max_closed_trade_drawdown_usd"] <= MAX_VALIDATION_DRAWDOWN_USD
    )


def _candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    metrics = item["validation"]
    pf = metrics["profit_factor"]
    dd = metrics["max_closed_trade_drawdown_usd"]
    if pf is None:
        pf = math.inf if metrics["wins"] > 0 and metrics["losses"] == 0 else -1
    return (
        metrics["win_rate_pct"] if metrics["win_rate_pct"] is not None else -1,
        pf if pf is not None else -1,
        metrics["expectancy_usd_per_closed_trade"] or -math.inf,
        -(dd if dd is not None else math.inf),
        metrics["closed_trades"],
    )


def _candidate_report_row(item: dict[str, Any]) -> dict[str, Any]:
    fit, validation = item["fit"], item["validation"]
    return {
        **item["parameters"],
        "development_closed_trades": fit["closed_trades"],
        "development_wins": fit["wins"],
        "development_losses": fit["losses"],
        "development_win_rate_pct": fit["win_rate_pct"],
        "development_net_pnl_usd": fit["net_pnl_usd"],
        "development_expectancy_usd": fit["expectancy_usd_per_closed_trade"],
        "development_profit_factor": fit["profit_factor"],
        "development_max_drawdown_usd": fit["max_closed_trade_drawdown_usd"],
        "validation_closed_trades": validation["closed_trades"],
        "validation_wins": validation["wins"],
        "validation_losses": validation["losses"],
        "validation_win_rate_pct": validation["win_rate_pct"],
        "validation_wilson_95_low_pct": (
            validation["win_rate_95pct_wilson"]["low_pct"]
            if validation["win_rate_95pct_wilson"]
            else None
        ),
        "validation_wilson_95_high_pct": (
            validation["win_rate_95pct_wilson"]["high_pct"]
            if validation["win_rate_95pct_wilson"]
            else None
        ),
        "validation_net_pnl_usd": validation["net_pnl_usd"],
        "validation_expectancy_usd": validation["expectancy_usd_per_closed_trade"],
        "validation_profit_factor": validation["profit_factor"],
        "validation_max_drawdown_usd": validation["max_closed_trade_drawdown_usd"],
        "met_training_and_validation_rules": _validation_passes(fit, validation),
    }


def _candidate_diagnostic(item: dict[str, Any]) -> dict[str, Any]:
    """Summarize a rejected training candidate; never include holdout metrics."""
    fit, validation = item["fit"], item["validation"]
    failures = []
    if fit["closed_trades"] < MIN_FIT_TRADES:
        failures.append(f"development sample is below {MIN_FIT_TRADES} closed trades")
    if fit["net_pnl_usd"] is None or fit["net_pnl_usd"] <= 0:
        failures.append("development net P&L is not positive")
    if validation["closed_trades"] < MIN_VALIDATION_TRADES:
        failures.append(f"inner validation is below {MIN_VALIDATION_TRADES} closed trades")
    if validation["net_pnl_usd"] is None or validation["net_pnl_usd"] <= 0:
        failures.append("inner validation net P&L is not positive")
    validation_pf = validation["profit_factor"]
    if (
        validation_pf is None
        and not (validation["wins"] > 0 and validation["losses"] == 0)
    ) or (
        validation_pf is not None
        and validation_pf < MIN_VALIDATION_PROFIT_FACTOR
    ):
        failures.append(
            f"inner validation profit factor is below {MIN_VALIDATION_PROFIT_FACTOR}"
        )
    if (
        validation["max_closed_trade_drawdown_usd"] is None
        or validation["max_closed_trade_drawdown_usd"] > MAX_VALIDATION_DRAWDOWN_USD
    ):
        failures.append("inner validation closed-trade drawdown exceeds the search limit")
    return {
        "parameters": item["parameters"],
        "development_fit": fit,
        "inner_validation": validation,
        "reasons_rejected": failures,
        "not_evaluated_on_holdout": True,
    }


def _tuning_result(
    sample: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    candidates: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Read only the declared 70% development partition while selecting."""
    if len(sample) < 500 or len(warmup) < 40:
        raise XAUHistoryError("Insufficient provider-history bars for bounded XAUUSD optimization")
    if not candidates or len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"Candidate count must be between 1 and {MAX_CANDIDATES}")
    # The final 30% is not even converted into price-bearing bar objects until
    # a training-selected candidate exists and its one permitted evaluation
    # starts. Only row counts and timestamp metadata determine the outer cut.
    outer_cut = _raw_split_before_entry_session(
        sample, max(1, int(len(sample) * TRAIN_FRACTION))
    )
    development_only = sample[:outer_cut]
    development_prepared = _prepare(development_only)
    if len(development_only) < 500:
        raise XAUHistoryError("The pre-holdout training partition is too small for research")
    validation_cut = _split_before_entry_session(
        development_prepared,
        max(1, int(len(development_prepared) * TUNING_FRACTION_OF_TRAIN)),
    )
    if validation_cut >= len(development_only) - 1:
        raise XAUHistoryError("Training-only fit/validation split has insufficient data")

    validation_candidates = []
    for raw_config in candidates:
        config = normalize_parameters(raw_config)
        research = _simulate(
            development_only,
            warmup,
            config,
            boundaries=(validation_cut,),
        )
        fit, validation = research["folds"]
        item = {
            "parameters": config,
            "fit": fit,
            "validation": validation,
            "selection_rule_passed": _validation_passes(fit, validation),
        }
        validation_candidates.append(item)

    eligible = [item for item in validation_candidates if item["selection_rule_passed"]]
    selected = max(eligible, key=_candidate_sort_key) if eligible else None
    return {
        "outer_cut": outer_cut,
        "tuning_cut": validation_cut,
        "candidate_count": len(validation_candidates),
        "eligible_count": len(eligible),
        "selected": selected,
        "training_candidates": validation_candidates,
        "candidate_rows": [_candidate_report_row(item) for item in validation_candidates],
        "selection_basis": (
            "The best training-only validation win rate among configurations that first meet "
            "the minimum samples, positive development/validation expectancy, profit-factor, "
            "and drawdown constraints. Ties prefer profit factor, expectancy, then smaller drawdown."
        ),
    }


def _holdout_passes(holdout: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    if holdout["closed_trades"] < MIN_HOLDOUT_TRADES:
        reasons.append(f"holdout has fewer than {MIN_HOLDOUT_TRADES} closed trades")
    if holdout["net_pnl_usd"] is None or holdout["net_pnl_usd"] <= 0:
        reasons.append("holdout net modeled P&L is not positive")
    if holdout["expectancy_usd_per_closed_trade"] is None or holdout["expectancy_usd_per_closed_trade"] <= 0:
        reasons.append("holdout expectancy is not positive")
    holdout_pf_passes = (
        holdout["wins"] > 0 and holdout["losses"] == 0
        if holdout["profit_factor"] is None
        else holdout["profit_factor"] >= MIN_HOLDOUT_PROFIT_FACTOR
    )
    if not holdout_pf_passes:
        reasons.append(f"holdout profit factor is below {MIN_HOLDOUT_PROFIT_FACTOR}")
    if (
        holdout["max_closed_trade_drawdown_usd"] is None
        or holdout["max_closed_trade_drawdown_usd"] > MAX_HOLDOUT_DRAWDOWN_USD
    ):
        reasons.append(f"holdout closed-trade drawdown exceeds ${MAX_HOLDOUT_DRAWDOWN_USD:,.0f}")
    return not reasons, reasons


def run_optimization(
    sample: Sequence[dict[str, Any]],
    warmup: Sequence[dict[str, Any]],
    *,
    source_sha256: str,
    baseline_report: dict[str, Any],
    candidates: Sequence[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Select without reading the 30% final holdout; evaluate only the winner."""
    configurations = list(candidates if candidates is not None else candidate_grid())
    tuning = _tuning_result(sample, warmup, configurations)
    base: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "XAUUSD",
        "status": "no_training_candidate_met_minimum_rules",
        "research_status": "RESEARCH_NOT_VALIDATED",
        "runtime_import_status": "FROZEN_PRE_OPTIMIZATION_BASELINE_FALLBACK",
        "data_source": "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC",
        "source_file": baseline_report.get("raw_data_file"),
        "source_sha256": source_sha256,
        "sample_start_inclusive": baseline_report.get("sample_start_inclusive"),
        "sample_end_exclusive": baseline_report.get("sample_end_exclusive"),
        "sample_bars": len(sample),
        "warmup_bars": len(warmup),
        "development_fraction_of_sample": round(tuning["outer_cut"] / len(sample), 5),
        "inner_tuning_fraction_of_development": round(
            tuning["tuning_cut"] / tuning["outer_cut"], 5
        ),
        "candidate_count": tuning["candidate_count"],
        "training_eligible_candidate_count": tuning["eligible_count"],
        "quantity_units": QUANTITY_UNITS,
        "lot_size": LOT_SIZE,
        "units_per_lot": UNITS_PER_LOT,
        "currency": "USD",
        "algorithm": ALGORITHM,
        "timeframes_tested_minutes": [1, 5],
        "selection_basis": tuning["selection_basis"],
        "candidate_selection_rules": {
            "minimum_development_closed_trades": MIN_FIT_TRADES,
            "minimum_inner_validation_closed_trades": MIN_VALIDATION_TRADES,
            "development_and_validation_net_pnl_must_be_positive": True,
            "minimum_inner_validation_profit_factor": MIN_VALIDATION_PROFIT_FACTOR,
            "maximum_development_and_validation_drawdown_usd": MAX_VALIDATION_DRAWDOWN_USD,
            "rank": "highest eligible inner-validation win rate, then profit factor, expectancy, smaller drawdown",
        },
        "selection_looked_at_holdout": False,
        "holdout_evaluation_count": 0,
        "candidate_parameters": None,
        "train": {
            "closed_trades": None,
            "wins": None,
            "losses": None,
            "win_rate_pct": None,
            "net_pnl_usd": None,
        },
        "out_of_sample": {"closed_trades": None, "wins": None, "losses": None, "win_rate_pct": None, "net_pnl_usd": None},
        "overall": {"closed_trades": None, "wins": None, "losses": None, "win_rate_pct": None, "net_pnl_usd": None},
        "baseline_comparison": {
            "source_report_status": baseline_report.get("status"),
            "source_was_strategy_changed": baseline_report.get("strategy_changed"),
            "train": baseline_report.get("train"),
            "out_of_sample": baseline_report.get("out_of_sample"),
            "note": "Frozen pre-optimization baseline report on identical original OANDA CSV/SHA. Its process-lifetime three-signal cap is preserved for reproducibility.",
        },
        "execution_validated": False,
        "recommended_for_paper": False,
        "paper_entries_enabled": False,
        "live_orders_enabled": False,
        "fees_and_financing": "Historical spread is represented by actual bid/ask-side entry/exit prices. Commission, financing/swap, slippage beyond sampled side prices, margin and broker fills are not available and are not invented.",
        "limitations": [
            "A bounded search can select only among the published finite candidates; it cannot prove a global maximum or guarantee future win rate.",
            "The final chronological 30% is not read unless a single candidate passes training-only eligibility; no eligible candidate was found, so the holdout remains untouched.",
            "Closed-minute observations and next-minute bar opens are a price-bar research model, not a recorded historical order/fill or a true tick-by-tick live quote replay.",
            "No risk-free or profitable strategy is promised. Small samples and wide Wilson intervals remain uncertain.",
            "All price-derived trade profit/loss is expressed in USD for the fixed 100-unit (one 100 oz) research position.",
        ],
    }
    if tuning["selected"] is None:
        training_candidates = [
            _candidate_diagnostic(item)
            for item in sorted(
                tuning["training_candidates"],
                key=lambda item: (
                    item["validation"]["win_rate_pct"]
                    if item["validation"]["win_rate_pct"] is not None
                    else -1,
                    item["validation"]["expectancy_usd_per_closed_trade"]
                    if item["validation"]["expectancy_usd_per_closed_trade"] is not None
                    else -math.inf,
                ),
                reverse=True,
            )
        ]
        base["training_diagnostics"] = {
            "description": "Rejected in-sample fit and inner-validation candidates. This ranking is descriptive only, is not used to install a strategy, and contains no final holdout metrics.",
            "most_profitable_validation_candidate": _candidate_diagnostic(
                max(
                    tuning["training_candidates"],
                    key=lambda item: (
                        item["validation"]["net_pnl_usd"]
                        if item["validation"]["net_pnl_usd"] is not None
                        else -math.inf
                    ),
                )
            ),
            "highest_validation_win_rate_candidate": training_candidates[0],
            "positive_expectancy_validation_candidates": sum(
                1
                for item in tuning["training_candidates"]
                if item["validation"]["net_pnl_usd"] is not None
                and item["validation"]["net_pnl_usd"] > 0
            ),
            "diagnostic_top_candidates_listed": len(training_candidates),
            "search_candidates": tuning["candidate_count"],
        }
        base["reason"] = (
            "No candidate met the training-only minimum sample, positive-expectancy, "
            "profit-factor and drawdown requirements; the strategy was not replaced."
        )
        base["candidate_installation"] = "none_original_strategy_preserved"
        base["oos_validation_failures"] = [
            "No training-only candidate passed selection; the untouched final holdout was not evaluated."
        ]
        return base, tuning["candidate_rows"]

    chosen = tuning["selected"]["parameters"]
    base["candidate_parameters"] = dict(chosen)
    base["training_selected"] = {
        "fit": tuning["selected"]["fit"],
        "validation": tuning["selected"]["validation"],
    }

    # Evaluate the sole training-selected configuration on all sample data,
    # with the already-decided 70% boundary. No losing/superior candidate is
    # subsequently checked against any holdout prices.
    full = _simulate(sample, warmup, chosen, boundaries=(tuning["outer_cut"],))
    train, holdout = full["folds"]
    overall = full["overall"]
    holdout_passed, holdout_reasons = _holdout_passes(holdout)
    base.update(
        {
            "status": "candidate_evaluated_research_only",
            "holdout_evaluation_count": 1,
            "train": train,
            "out_of_sample": holdout,
            "overall": overall,
            "trades": full["trades"],
            "unresolved_positions": full["unresolved_positions"],
            "unfilled_or_boundary_signals": full["unfilled_or_boundary_signals"],
            "diagnostics": {
                "sample_complete_bars": full["complete_bars"],
                "warmup_session_closes": full["ema_warmup_session_bars"],
                "confirmed_signals": full["confirmed_signals"],
                "closed_trade_counts_by_fold": full["closed_trade_counts_by_fold"],
            },
            "oos_requirements_passed": holdout_passed,
            "oos_validation_failures": holdout_reasons,
            "execution_validated": False,
            # With no genuine live fills or non-spread costs, a price-bar pass
            # alone can never authorize paper entry.
            "recommended_for_paper": False,
            "candidate_installation": "research_only_default_agent_configuration",
            "paper_entries_enabled": False,
            "live_orders_enabled": False,
        }
    )
    return base, tuning["candidate_rows"]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def optimize_saved_xauusd(evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR) -> dict[str, Any]:
    """Verify and re-use the existing raw CSV; make no provider requests."""
    directory = Path(evidence_dir)
    baseline_path = directory / "xauusd_backtest.json"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise XAUHistoryError("The verified XAUUSD baseline report is unavailable") from exc
    if (
        baseline.get("data_source") != "OANDA_PRACTICE_HISTORICAL_COMPLETE_BID_ASK_OHLC"
        or baseline.get("provider") != "OANDA"
        or baseline.get("environment") != "practice"
        or baseline.get("instrument") != "XAU_USD"
        or baseline.get("strategy_changed") is not False
    ):
        raise XAUHistoryError("The source report is not the frozen, unchanged OANDA XAUUSD baseline")
    all_bars, verified_sha256 = _read_verified_saved_history(directory, baseline)
    sample_start = _timestamp(baseline["sample_start_inclusive"])
    sample_end = _timestamp(baseline["sample_end_exclusive"])
    sample, warmup = [], []
    for bar in all_bars:
        stamp = _timestamp(bar["time"])
        if sample_start <= stamp < sample_end:
            sample.append(bar)
        elif stamp < sample_start:
            warmup.append(bar)
    if len(sample) != baseline.get("complete_sample_candles"):
        raise XAUHistoryError("The frozen baseline sample length does not match the original OANDA report")
    result, candidate_rows = run_optimization(
        sample,
        warmup,
        source_sha256=verified_sha256,
        baseline_report=baseline,
    )
    result["provider_requests_made"] = 0
    result["raw_csv_modified"] = False
    _write_json(directory / "xauusd_optimization.json", result)

    csv_path = directory / "xauusd_optimizer_candidates.csv"
    if candidate_rows:
        tmp = csv_path.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(candidate_rows[0]))
            writer.writeheader()
            writer.writerows(candidate_rows)
        tmp.replace(csv_path)
        result["candidate_results_csv"] = csv_path.name
        _write_json(directory / "xauusd_optimization.json", result)
    return result


if __name__ == "__main__":
    report = optimize_saved_xauusd()
    compact = {
        key: report.get(key)
        for key in ("status", "candidate_count", "training_eligible_candidate_count", "candidate_parameters", "train", "out_of_sample", "oos_validation_failures", "recommended_for_paper", "source_sha256")
    }
    print(json.dumps(compact, indent=2, allow_nan=False))