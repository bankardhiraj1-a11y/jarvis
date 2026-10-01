"""Bounded, read-only Dhan history exports and honest strategy evaluation."""

import argparse
import csv
import json
import math
import time
from datetime import date, datetime, time as day_time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from data.dhan_history import DhanHistoryClient, DhanHistoryError


IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "evidence"
STOCKS = {
    "RELIANCE": ("2885", "NSE_EQ"),
    "TCS": ("11536", "NSE_EQ"),
    "INFY": ("1594", "NSE_EQ"),
    "HDFCBANK": ("1333", "NSE_EQ"),
    "BAJAJ-AUTO": ("16669", "NSE_EQ"),
}
INDEXES = {
    "NIFTY": ("13", "IDX_I"),
    "BANKNIFTY": ("25", "IDX_I"),
    "SENSEX": ("51", "IDX_I"),
}
DAILY_FROM = date(2025, 1, 1)
REQUEST_INTERVAL_SECONDS = 1.1


def _metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    ordered = sorted(trades, key=lambda trade: (trade.get("exit_date", ""), trade.get("symbol", "")))
    pnls = [float(trade["pnl"]) for trade in ordered]
    wins = sum(pnl > 0 for pnl in pnls)
    losses = sum(pnl < 0 for pnl in pnls)
    equity = peak = 100_000.0
    max_drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
    positive = sum(pnl for pnl in pnls if pnl > 0)
    negative = -sum(pnl for pnl in pnls if pnl < 0)
    return {
        "total_trades": len(pnls),
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate": round(wins * 100 / len(pnls), 2) if pnls else None,
        "total_pnl": round(sum(pnls), 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "profit_factor": round(positive / negative, 3) if negative else (
            None if positive == 0 else "undefined_no_losses"
        ),
    }


def _ema(candles: List[Dict[str, Any]], period: int) -> float:
    closes = [float(candle["close"]) for candle in candles[-period:]]
    if len(closes) < period:
        return 0.0
    multiplier = 2 / (period + 1)
    value = closes[0]
    for close in closes[1:]:
        value = close * multiplier + value * (1 - multiplier)
    return value


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    if len(candles) < period:
        return 0.0
    true_ranges = []
    for index, candle in enumerate(candles):
        high, low = float(candle["high"]), float(candle["low"])
        if index == 0:
            true_ranges.append(high - low)
        else:
            previous = float(candles[index - 1]["close"])
            true_ranges.append(max(high - low, abs(high - previous), abs(low - previous)))
    return sum(true_ranges[-period:]) / period


def stock_signals(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replay the configured VCP gate at completed daily closes.

    Required EMA-200/EMA-50, 20-day breakout, volume confirmation, ATR stop,
    previous completed-bar low and 2R target follow the existing agent rules.
    This is an explicitly disclosed daily-bar approximation, not a claim that
    the historical intraday tick trigger or real fills were reproduced.
    """
    signals = []
    volumes = []
    last_signal_day = None
    for index, candle in enumerate(candles):
        history = candles[:index]
        if len(history) < 200 or len(volumes) < 20:
            volumes.append(int(candle["volume"]))
            continue
        close = float(candle["close"])
        if _ema(history, 200) <= _ema(history, 50):
            volumes.append(int(candle["volume"]))
            continue
        high_20d = max(float(bar["high"]) for bar in history[-20:])
        avg_volume = sum(volumes[-20:]) / 20
        if close > high_20d and int(candle["volume"]) > avg_volume * 2:
            atr = _atr(history, 14)
            stop = max(close - 1.5 * atr, float(history[-1]["low"]))
            if (close - stop) / close > 0.03:
                stop = close * 0.97
            if stop > 0 and stop < close:
                signal_day = candle["timestamp"][:10]
                if signal_day != last_signal_day:
                    signals.append(
                        {
                            "signal_index": index,
                            "signal_date": signal_day,
                            "signal_close": close,
                            "stop": stop,
                            "target": close + 2 * (close - stop),
                        }
                    )
                    last_signal_day = signal_day
        volumes.append(int(candle["volume"]))
    return signals


def _modeled_equity_charges(entry: float, exit_price: float, quantity: float) -> float:
    """Paper estimate only: modeled fees are not a broker ledger."""
    turnover = (entry + exit_price) * quantity
    brokerage = 80.0
    gst = brokerage * 0.01427
    stt = exit_price * quantity * 0.00013
    exchange = turnover * 0.000031
    sebi = 1.68
    stamp = 12.0
    return brokerage + gst + stt + exchange + sebi + stamp


def stock_bar_trades(
    candles: List[Dict[str, Any]],
    *,
    symbol: str = "",
    quantity: float = 50.0,
    fee_model=_modeled_equity_charges,
) -> Dict[str, Any]:
    """One position per symbol at a time; unresolved end bars remain open."""
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("normalized research quantity must be positive")
    signals = stock_signals(candles)
    trades = []
    open_positions = []
    cross_boundary_positions = []
    skipped_overlapping_signals = []
    pending_by_index = {signal["signal_index"] + 1: signal for signal in signals}
    cut = int(len(candles) * 0.8)
    next_available_index = 0
    for entry_index in sorted(pending_by_index):
        if entry_index >= len(candles):
            open_positions.append(
                {
                    "symbol": symbol,
                    "signal_date": pending_by_index[entry_index]["signal_date"],
                    "status": "SIGNAL_AT_SAMPLE_END_NO_NEXT_SESSION_ENTRY",
                }
            )
            continue
        signal = pending_by_index[entry_index]
        if entry_index < next_available_index:
            skipped_overlapping_signals.append(
                {"symbol": symbol, "signal_date": signal["signal_date"], "reason": "existing same-symbol paper position still open"}
            )
            continue
        entry_bar = candles[entry_index]
        entry = float(entry_bar["open"])
        stop = signal["stop"]
        target = signal["target"]
        split = "train" if entry_index < cut else "out_of_sample"
        # A training position is never inspected against holdout bars. The
        # independent holdout starts flat, while retaining the full preceding
        # history only as indicator warmup.
        segment_end = cut if split == "train" else len(candles)
        exit_price = None
        exit_reason = None
        exit_date = None
        exit_index = None
        for bar_index in range(entry_index, segment_end):
            bar = candles[bar_index]
            opened, low, high = float(bar["open"]), float(bar["low"]), float(bar["high"])
            if opened <= stop:
                exit_price, exit_reason = opened, "gap_through_stop"
            elif opened >= target:
                exit_price, exit_reason = opened, "gap_through_target"
            elif low <= stop:
                exit_price, exit_reason = stop, "stop_first_if_both_levels_touch"
            elif high >= target:
                exit_price, exit_reason = target, "take_profit"
            if exit_price is not None:
                exit_date = bar["timestamp"][:10]
                exit_index = bar_index
                break
        if exit_price is None:
            boundary_index = max(entry_index, segment_end - 1)
            boundary_bar = candles[boundary_index]
            status = (
                "OPEN_AT_TRAIN_HOLDOUT_BOUNDARY"
                if split == "train"
                else "OPEN_AT_SAMPLE_END_UNREALIZED_ONLY"
            )
            open_positions.append(
                {
                    "symbol": symbol,
                    "signal_date": signal["signal_date"],
                    "entry_date": entry_bar["timestamp"][:10],
                    "sample_end_date": boundary_bar["timestamp"][:10],
                    "quantity": quantity,
                    "entry": round(entry, 4),
                    "stop": round(stop, 4),
                    "target": round(target, 4),
                    "mark_price": round(float(boundary_bar["close"]), 4),
                    "unrealized_gross_pnl": round((float(boundary_bar["close"]) - entry) * quantity, 4),
                    "status": status,
                }
            )
            # Independent split testing resets position state at its boundary;
            # no training exit is inferred from later holdout candles.
            if split == "train":
                next_available_index = cut
            continue
        raw_pnl = (exit_price - entry) * quantity
        charges = fee_model(entry, exit_price, quantity)
        trade = {
                "symbol": symbol,
                "signal_date": signal["signal_date"],
                "entry_date": entry_bar["timestamp"][:10],
                "exit_date": exit_date,
                "quantity": quantity,
                "entry": round(entry, 4),
                "exit": round(exit_price, 4),
                "exit_reason": exit_reason,
                "modeled_costs": round(charges, 4),
                "pnl": round(raw_pnl - charges, 4),
                "split": split,
            }
        trades.append(trade)
        next_available_index = (exit_index or entry_index) + 1
    return {
        "signal_count": len(signals),
        "trades": trades,
        "all": _metrics(trades),
        "train": _metrics([trade for trade in trades if trade["split"] == "train"]),
        "out_of_sample": _metrics(
            [trade for trade in trades if trade["split"] == "out_of_sample"]
        ),
        "train_cut_date": candles[cut]["timestamp"][:10] if len(candles) > cut else None,
        "open_positions_at_sample_end": open_positions,
        "cross_boundary_positions_excluded_from_both_splits": cross_boundary_positions,
        "skipped_overlapping_signals": skipped_overlapping_signals,
        "method": "Existing VCP EMA/volume/breakout and stop/target formulas approximated on complete daily bars; entries at next-session open; one same-symbol position at a time; same-bar stop first; 50 shares; one flat round-trip brokerage per trade plus turnover-based modeled statutory charges. Train and holdout are scored independently; the training replay stops at the split and never consults holdout candles for a training exit. Unclosed boundary positions are marked unrealized and excluded from realized win rate/P&L.",
        "limitations": [
            "Daily close bar approximation; the original live VCP trigger arrives on intraday ticks and cannot be reproduced from one daily bar.",
            "No bid/ask depth history; LTP/OHLC cannot validate executable fills.",
            "The daily model evaluates at most one signal per bar. Because genuine day-level events cannot replay original intraday ticks, it does not claim exact parity with the agent's tick-level signal timing; its two-hour cooldown and three-entry-per-day gates cannot be exercised by more than one daily signal.",
            "Per-symbol one-open-position rule is applied. Aggregate run includes five separate 50-share lanes, without capital reservation/portfolio allocation.",
            "Holdout is a flat-start simulation warmed with pre-holdout candles. Training positions still open at the split are separately disclosed and not closed using holdout prices.",
        ],
    }


def _bar_end(row: Dict[str, Any], duration_minutes: int) -> datetime:
    start = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    return start + timedelta(minutes=duration_minutes)


def sensex_scalping_ohlc_signals(
    agent: Any,
    candles_by_symbol: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Apply the unchanged scalping pattern to completed, actual OHLC bars."""
    signals = []
    raw_setups = 0
    processed = 0
    signals_per_day: Dict[tuple, List[datetime]] = {}
    for symbol in sorted(candles_by_symbol):
        candles = sorted(candles_by_symbol[symbol], key=lambda bar: bar["timestamp_epoch"])
        for index in range(1, len(candles)):
            previous, current = candles[index - 1], candles[index]
            processed += 1
            previous_green = float(previous["close"]) > float(previous["open"])
            current_green = float(current["close"]) > float(current["open"])
            previous_red = float(previous["close"]) < float(previous["open"])
            current_red = float(current["close"]) < float(current["open"])
            direction = None
            if previous_green and current_green and float(current["high"]) > float(previous["high"]):
                direction = "BUY"
            elif previous_red and current_red and float(current["low"]) < float(previous["low"]):
                direction = "SELL"
            if direction is None:
                continue

            raw_setups += 1
            available = _bar_end(current, 1)
            local = available.astimezone(IST)
            day_key = (symbol, local.date())
            daily = signals_per_day.setdefault(day_key, [])
            if len(daily) >= agent.max_trades_per_day:
                continue
            if daily and available - daily[-1] < agent.min_time_between_trades:
                continue
            tp = agent.calculate_dynamic_tp(float(current["close"]), [previous, current])
            signals.append(
                {
                    "symbol": symbol,
                    "timestamp": available.isoformat(),
                    "signal": direction,
                    "underlying_close": float(current["close"]),
                    "target_points": tp,
                    "signal_type": "underlying_breakout_candidate",
                }
            )
            daily.append(available)
    return {
        "signal_count": len(signals),
        "raw_setup_count": raw_setups,
        "signals": signals,
        "processed_completed_ohlc_pairs": processed,
        "adapter": "uses Dhan one-minute OHLC; compares previous/current full bars; signal timestamp is current bar start + 1 minute; no close-only candle reconstruction",
        "limitations": ["The 15-minute loss cooldown cannot be reconstructed without option-premium outcomes; only the 10-minute spacing and daily candidate cap are applied.", "Signals are underlying setups only and do not imply trades or option fills."],
        "reason": "Candidate signals on SENSEX underlying only. No historical option contract selection, premium fill, quantity interpretation, exit outcome, or option P&L.",
    }


def options_ohlc_signals(
    agent: Any,
    minute_rows_by_symbol: Dict[str, List[Dict[str, Any]]],
    fifteen_minute_rows_by_symbol: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Replay option-underlying rules using completed 15m OHLC + 1m closes."""
    all_signals = []
    diagnostics = {}
    for symbol in sorted(minute_rows_by_symbol):
        minutes = sorted(minute_rows_by_symbol[symbol], key=lambda row: row["timestamp_epoch"])
        fifteen = sorted(
            fifteen_minute_rows_by_symbol.get(symbol, []),
            key=lambda row: row["timestamp_epoch"],
        )
        completed = []
        next_bar = 0
        tiers = {"tier1_positions": [], "tier2_positions": [], "tier3_positions": []}
        signals = []
        minute_evaluations = 0

        for minute in minutes:
            available = _bar_end(minute, 1)
            while next_bar < len(fifteen) and _bar_end(fifteen[next_bar], 15) <= available:
                completed.append(dict(fifteen[next_bar]))
                next_bar += 1

            local = available.astimezone(IST)
            if local.hour > 15 or (local.hour == 15 and local.minute >= 15):
                for positions in tiers.values():
                    positions.clear()
                continue
            if not (9 <= local.hour < 16) or len(completed) < 21:
                continue
            minute_evaluations += 1
            if agent.daily_pnl <= -(agent.daily_loss_cap * 100):
                continue

            price = float(minute["close"])
            signal = None
            tier = None
            option_kind = None
            tp = agent.tp_points_conservative
            if len(tiers["tier1_positions"]) < agent.max_positions:
                ema5 = agent.calculate_ema(completed, 5)
                ema21 = agent.calculate_ema(completed, 21)
                rsi = agent.calculate_rsi(completed, 14)
                recent_volume = sum(float(bar["volume"]) for bar in completed[-3:]) / 3
                average_volume = sum(float(bar["volume"]) for bar in completed[-20:]) / 20
                confirmed = recent_volume > average_volume * 1.5
                if confirmed and price > ema5 and ema5 > ema21 and rsi > 50:
                    signal, tier, option_kind = "BUY", "TIER1", "CALL"
                    tp = agent.tp_points_aggressive if rsi > 70 else agent.tp_points_conservative
                elif confirmed and price < ema5 and ema5 < ema21 and rsi < 50:
                    signal, tier, option_kind = "SELL", "TIER1", "PUT"
                    tp = agent.tp_points_aggressive if rsi < 30 else agent.tp_points_conservative

            if signal is None and len(tiers["tier2_positions"]) < 2:
                atr = agent.calculate_atr(completed, 14)
                highest = max(float(bar["high"]) for bar in completed[-20:])
                lowest = min(float(bar["low"]) for bar in completed[-20:])
                if price > highest - atr * 0.5 and atr > 50:
                    signal, tier, option_kind = "SELL", "TIER2", "PUT"
                elif price < lowest + atr * 0.5 and atr > 50:
                    signal, tier, option_kind = "BUY", "TIER2", "CALL"

            if signal is not None:
                tiers[f"{tier.lower()}_positions"].append(
                    {"entry": price, "type": option_kind, "symbol": symbol}
                )
                detail = {
                    "symbol": symbol,
                    "timestamp": available.isoformat(),
                    "signal": signal,
                    "tier": tier,
                    "option_type_candidate": option_kind,
                    "underlying_price": price,
                    "target_points_from_strategy": tp,
                    "signal_type": "underlying_based_option_candidate",
                }
                signals.append(detail)

        diagnostics[symbol] = {
            "candidate_signal_count": len(signals),
            "processed_one_minute_bars": len(minutes),
            "strategy_evaluation_count": minute_evaluations,
            "completed_15m_bars": len(completed),
            "signals": signals,
                    "adapter": "uses full Dhan 15-minute OHLCV for indicator history and each fully elapsed Dhan one-minute candle close as available price; no incomplete bar or intrabar path is invented",
                    "limitations": ["Position slots are held until the agent's 15:15 hard exit because option-premium exits cannot be reconstructed; the live strategy may release slots earlier."],
        }
        all_signals.extend(signals)
    return {
        "signal_count": len(all_signals),
        "processed_bars": sum(item["processed_one_minute_bars"] for item in diagnostics.values()),
        "per_symbol": diagnostics,
        "reason": "Signal candidates use genuine underlying index OHLC only; option contracts, premiums, fills, and P&L are not available from this fixed-contract executable data set.",
    }


def _complete_rows(
    rows: List[Dict[str, Any]],
    today: date,
    *,
    intraday: bool = False,
) -> List[Dict[str, Any]]:
    """Exclude today's forming session and keep authentic regular-session bars."""
    completed = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        local = timestamp.astimezone(IST)
        if local.date() >= today or local.weekday() >= 5:
            continue
        if intraday and not day_time(9, 15) <= local.time().replace(tzinfo=None) <= day_time(15, 30):
            continue
        # Dhan OHLC timestamps encode the exchange-local bar time; retain the
        # epoch and render it with IST offset so session dates are not shifted
        # to the previous UTC calendar day (e.g. midnight IST == 18:30Z).
        normalized = dict(row)
        normalized["timestamp"] = local.isoformat()
        normalized["session_date"] = local.date().isoformat()
        completed.append(normalized)
    return completed


def _empty_metrics() -> Dict[str, Any]:
    return {
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": None,
        "total_pnl": None,
        "execution_validated": False,
        "strategy_changed": False,
    }


def _agent_entry(status: str, reason: str, **fields: Any) -> Dict[str, Any]:
    return {
        "status": status,
        **_empty_metrics(),
        "reason": reason,
        **fields,
    }


def _load_verified_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    if not rows or any(row.get("data_source") != "DHAN_HISTORICAL" for row in rows):
        raise ValueError(f"Historical evidence provenance failed validation: {path.name}")
    for row in rows:
        for field in ("timestamp_epoch", "open", "high", "low", "close", "volume"):
            row[field] = float(row[field])
        row["timestamp_epoch"] = int(row["timestamp_epoch"])
    return sorted(rows, key=lambda row: row["timestamp_epoch"])


def refresh_saved_backtest_report(evidence_dir: Any = DEFAULT_EVIDENCE_DIR) -> Dict[str, Any]:
    """Recompute evaluation locally from saved DHAN_HISTORICAL CSVs, with no API calls."""
    directory = Path(evidence_dir)
    report_path = directory / "latest_backtests.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("data_source") != "DHAN_HISTORICAL":
        raise ValueError("Saved backtest report is not provider-history evidence")

    per_symbol = {}
    for symbol in STOCKS:
        raw_path = directory / f"{symbol.lower()}_daily_2025_to_current.csv"
        bars = _load_verified_csv(raw_path)
        evaluation = stock_bar_trades(bars, symbol=symbol, quantity=50)
        per_symbol[symbol] = {
            "status": "completed_bar_model" if len(bars) >= 200 else "unavailable",
            "reason": "Genuine Dhan daily OHLCV; disclosed approximation of existing VCP rules; 50 shares with flat round-trip brokerage plus turnover-based modeled fees; realized exits only.",
            **_empty_metrics(),
            "total_trades": evaluation["all"]["total_trades"],
            "winning_trades": evaluation["all"]["winning_trades"],
            "losing_trades": evaluation["all"]["losing_trades"],
            "win_rate": evaluation["all"]["win_rate"],
            "total_pnl": evaluation["all"]["total_pnl"],
            "bar_count": len(bars),
            "warmup_required_bars": 200,
            "warmup_satisfied": len(bars) >= 200,
            "execution_validated": False,
            "trades": evaluation["trades"],
            "evaluation": evaluation,
            "raw_data_file": raw_path.name,
        }

    stock_trades = sorted(
        [
            {**trade, "symbol": symbol}
            for symbol, result in per_symbol.items()
            for trade in result["trades"]
        ],
        key=lambda trade: (trade["exit_date"], trade["symbol"]),
    )
    train = [trade for trade in stock_trades if trade["split"] == "train"]
    holdout = [trade for trade in stock_trades if trade["split"] == "out_of_sample"]
    all_open = [
        position
        for result in per_symbol.values()
        for position in result["evaluation"]["open_positions_at_sample_end"]
    ]
    report["agents"]["STOCKS"] = _agent_entry(
        "completed_bar_model" if all(result["warmup_satisfied"] for result in per_symbol.values()) else "unavailable",
        "Completed daily-bar model for the existing stock strategy rules, at 50 shares per symbol. Portfolio P&L is a chronological sum across five separate lanes; no global capital allocation was simulated. Training positions are never evaluated against holdout bars; the independent holdout starts flat.",
        **_metrics(stock_trades),
        execution_validated=False,
        bar_count=sum(item["bar_count"] for item in per_symbol.values()),
        warmup_required_bars=200,
        all_symbols_warmup_satisfied=all(item["warmup_satisfied"] for item in per_symbol.values()),
        train=_metrics(train),
        out_of_sample=_metrics(holdout),
        train_cut_dates={
            symbol: result["evaluation"]["train_cut_date"]
            for symbol, result in per_symbol.items()
        },
        trades=stock_trades,
        open_positions_at_boundaries=all_open,
        per_symbol=per_symbol,
        modeled_cost_basis="50 shares per trade; one ₹80 flat round-trip brokerage estimate plus per-trade turnover based fee estimates",
    )

    option_minutes = {
        symbol: _load_verified_csv(directory / f"{symbol.lower()}_1m_last30d.csv")
        for symbol in ("NIFTY", "BANKNIFTY")
    }
    option_fifteen = {
        symbol: _load_verified_csv(directory / f"{symbol.lower()}_15m_last30d.csv")
        for symbol in ("NIFTY", "BANKNIFTY")
    }
    from agents.options import OptionsAgent

    options = options_ohlc_signals(OptionsAgent(), option_minutes, option_fifteen)
    report["agents"]["OPTIONS"] = _agent_entry(
        "signal_only",
        options["reason"],
        total_trades=0,
        signal_count=options["signal_count"],
        signal_diagnostics=options,
        underlying_bars=options["processed_bars"],
    )

    sensex_minutes = _load_verified_csv(directory / "sensex_1m_last30d.csv")
    from agents.sensex_options_scalping import SensexOptionsScalpingAgent

    scalping = sensex_scalping_ohlc_signals(
        SensexOptionsScalpingAgent(), {"SENSEX": sensex_minutes}
    )
    report["agents"]["SENSEX_OPTIONS_SCALPING"] = _agent_entry(
        "signal_only",
        scalping["reason"],
        total_trades=0,
        signal_count=scalping["signal_count"],
        signal_diagnostics=scalping,
        bar_count=len(sensex_minutes),
    )
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["replay_adapter_details"] = {
        "STOCKS": "daily signal bar close; next-session daily open entry; 50 shares; no train exit looks into holdout; same-symbol single-position; OHLC stop-first; flat round-trip brokerage charged once",
        "OPTIONS": "Dhan 1-minute close available only after minute end; signal indicators use only completed Dhan 15-minute OHLCV whose end is no later than event availability",
        "SENSEX_OPTIONS_SCALPING": "Dhan 1-minute previous/current full OHLC breakout; availability timestamp is current minute bar end; limits/cooldown use signal times; no fabricated within-bar path",
        "all_signal_counts_are_not_trade_counts": True,
        "no_option_pnl_from_underlying_index_points": True,
        "no_provider_requests_made_while_replaying_saved_history": True,
        "prior_close_only_adapter_counts_are_superseded": True,
    }
    retrieval = report.setdefault("retrieval", {})
    retrieval["replayed_from_existing_raw_history"] = True
    retrieval["new_provider_requests_for_this_replay"] = 0
    report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report


def run_evidence_backtests(
    *,
    client: Optional[DhanHistoryClient] = None,
    evidence_dir: Any = DEFAULT_EVIDENCE_DIR,
    today: Optional[date] = None,
    request_sleep= time.sleep,
    sleeper_seconds: float = REQUEST_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    """Download authentic Dhan bars with a request cap and write durable evidence."""
    client = client or DhanHistoryClient()
    now = datetime.now(timezone.utc)
    india_today = today or now.astimezone(IST).date()
    to_date = india_today  # Dhan historical endpoints use an exclusive end date.
    start_intraday = to_date - timedelta(days=30)
    destination = Path(evidence_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "generated_at": now.isoformat(),
        "data_source": "DHAN_HISTORICAL",
        "agents": {},
        "retrieval": {
            "daily_from": DAILY_FROM.isoformat(),
            "to_date_exclusive": to_date.isoformat(),
            "intraday_from": start_intraday.isoformat(),
            "historical_requests_throttled_seconds": sleeper_seconds,
            "paper_entry_gate_remains_closed": True,
        },
    }
    daily_rows: Dict[str, List[Dict[str, Any]]] = {}
    intraday_rows: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    stock_reports: Dict[str, Dict[str, Any]] = {}
    request_count = 0
    errors: List[str] = []

    def pause_before_next():
        nonlocal request_count
        if request_count:
            request_sleep(sleeper_seconds)
        request_count += 1

    for symbol, (security_id, segment) in STOCKS.items():
        try:
            pause_before_next()
            rows = client.fetch_daily(security_id, segment, "EQUITY", DAILY_FROM, to_date)
            rows = _complete_rows(rows, india_today)
            if rows:
                csv_name = f"{symbol.lower()}_daily_2025_to_current.csv"
                client.export_csv(rows, destination / csv_name)
                daily_rows[symbol] = rows
            else:
                csv_name = None
                errors.append(f"{symbol}: no completed daily candles returned")
            evaluation = stock_bar_trades(
                rows, symbol=symbol, quantity=50
            ) if rows else None
            status = (
                "completed_bar_model"
                if evaluation and len(rows) >= 200
                else "unavailable"
            )
            stock_reports[symbol] = {
                "status": status,
                "reason": (
                    "Genuine Dhan daily bars; 50-share completed-bar model of the existing VCP rules; bar fills are a modeled price study, not historically executable fills."
                    if evaluation and len(rows) >= 200
                    else "Genuine candles are below the existing strategy's 200-daily-bar warmup requirement."
                    if evaluation
                    else "Dhan daily bars unavailable; no synthetic fallback."
                ),
                **_empty_metrics(),
                "total_trades": evaluation["all"]["total_trades"] if evaluation else None,
                "winning_trades": evaluation["all"]["winning_trades"] if evaluation else 0,
                "losing_trades": evaluation["all"]["losing_trades"] if evaluation else 0,
                "win_rate": evaluation["all"]["win_rate"] if evaluation else None,
                "total_pnl": evaluation["all"]["total_pnl"] if evaluation else None,
                "bar_count": len(rows),
                "warmup_required_bars": 200,
                "warmup_satisfied": len(rows) >= 200,
                "execution_validated": False,
                "trades": evaluation["trades"] if evaluation else [],
                "evaluation": evaluation,
                "raw_data_file": csv_name,
            }
        except (DhanHistoryError, ValueError, OSError):
            errors.append(f"{symbol}: Dhan data unavailable or failed validation")
            stock_reports[symbol] = {
                **_agent_entry(
                    "unavailable", "No valid authentic daily candles were available; no synthetic data used."
                ),
                "bar_count": 0,
                "warmup_required_bars": 200,
                "warmup_satisfied": False,
                "trades": [],
            }

    stock_trades = [
        trade
        for result in stock_reports.values()
        for trade in result.get("trades", [])
    ]
    stock_trades.sort(key=lambda trade: (trade["signal_date"], trade["entry_date"]))
    stock_models = [
        result["evaluation"]
        for result in stock_reports.values()
        if result.get("evaluation") is not None
    ]
    train_trades = [
        trade for trade in stock_trades if trade["split"] == "train"
    ]
    holdout_trades = [
        trade for trade in stock_trades if trade["split"] == "out_of_sample"
    ]
    if stock_models:
        all_stats = _metrics(stock_trades)
        all_stock_warmup = all(
            result.get("warmup_satisfied", False) for result in stock_reports.values()
        )
        report["agents"]["STOCKS"] = _agent_entry(
            "completed_bar_model" if all_stock_warmup else "unavailable",
            "Five equities evaluated at the strategy's 50-share base quantity. Aggregate P&L is a research sum, not a jointly capital-constrained portfolio; fee costs are modeled estimates.",
            **all_stats,
            execution_validated=False,
            bar_count=sum(result.get("bar_count", 0) for result in stock_reports.values()),
            warmup_required_bars=200,
            all_symbols_warmup_satisfied=all_stock_warmup,
            train=_metrics(train_trades),
            out_of_sample=_metrics(holdout_trades),
            train_cut_dates={
                symbol: result["evaluation"]["train_cut_date"]
                for symbol, result in stock_reports.items()
                if result.get("evaluation") is not None
            },
            trades=stock_trades,
            per_symbol=stock_reports,
            modeled_cost_basis="50 shares per security; estimates only",
        )
    else:
        report["agents"]["STOCKS"] = _agent_entry(
            "unavailable",
            "No authentic daily series could be validated for the configured stock universe.",
            total_trades=None,
            per_symbol=stock_reports,
        )

    for symbol, (security_id, segment) in INDEXES.items():
        intraday_rows[symbol] = {}
        for interval in ("1", "15"):
            try:
                pause_before_next()
                rows = client.fetch_intraday(
                    security_id,
                    segment,
                    "INDEX",
                    interval,
                    start_intraday,
                    to_date,
                )
                rows = _complete_rows(rows, india_today, intraday=True)
                if rows:
                    csv_name = f"{symbol.lower()}_{interval}m_last30d.csv"
                    client.export_csv(rows, destination / csv_name)
                    intraday_rows[symbol][interval] = rows
                else:
                    csv_name = None
                    errors.append(f"{symbol}/{interval}m: no completed intraday candles returned")
                if symbol == "SENSEX" and interval == "1":
                    report["agents"]["SENSEX_OPTIONS_SCALPING"] = _agent_entry(
                        "signal_only",
                        "One-minute SENSEX underlying signals only; historical option premium OHLC is not a fixed-contract, bid/ask executable series.",
                        total_trades=0,
                        signal_diagnostics=None,
                        bar_count=len(rows),
                        raw_data_file=csv_name,
                    )
            except (DhanHistoryError, ValueError, OSError):
                errors.append(f"{symbol}/{interval}m: Dhan data unavailable or failed validation")

    from agents.options import OptionsAgent

    options_signals = options_ohlc_signals(
        OptionsAgent(),
        {
            symbol: intraday_rows.get(symbol, {}).get("1", [])
            for symbol in ("NIFTY", "BANKNIFTY")
        },
        {
            symbol: intraday_rows.get(symbol, {}).get("15", [])
            for symbol in ("NIFTY", "BANKNIFTY")
        },
    )
    signal_total = options_signals["signal_count"]
    report["agents"]["OPTIONS"] = _agent_entry(
        "signal_only",
        options_signals["reason"],
        total_trades=0,
        signal_count=signal_total,
        signal_diagnostics=options_signals,
        underlying_bars=options_signals["processed_bars"],
        execution_validated=False,
    )

    sensex_15 = intraday_rows.get("SENSEX", {}).get("15", [])
    sensex_1 = intraday_rows.get("SENSEX", {}).get("1", [])
    if sensex_15:
        report["agents"]["SENSEX"] = _agent_entry(
            "unavailable",
            "The legacy spread/iron-condor strategy requires multiple exact option legs; no executable P&L can be modeled from index bars. Strategy uses wall-clock scheduling and is not replayed on shifted historical time.",
            total_trades=None,
            bar_count=len(sensex_15),
            raw_data_file="sensex_15m_last30d.csv",
        )
    else:
        report["agents"]["SENSEX"] = _agent_entry(
            "unavailable",
            "No completed SENSEX 15-minute candles; legacy multileg options P&L is unsupported.",
        )
    if sensex_1:
        from agents.sensex_options_scalping import SensexOptionsScalpingAgent

        scalping = sensex_scalping_ohlc_signals(
            SensexOptionsScalpingAgent(), {"SENSEX": sensex_1}
        )
        report["agents"]["SENSEX_OPTIONS_SCALPING"]["signal_diagnostics"] = scalping
        report["agents"]["SENSEX_OPTIONS_SCALPING"]["total_trades"] = 0
        report["agents"]["SENSEX_OPTIONS_SCALPING"]["signal_count"] = scalping["signal_count"]
    elif "SENSEX_OPTIONS_SCALPING" not in report["agents"]:
        report["agents"]["SENSEX_OPTIONS_SCALPING"] = _agent_entry(
            "unavailable",
            "No completed one-minute SENSEX history; no option execution P&L can be inferred.",
        )

    report["agents"]["GIFT_NIFTY"] = _agent_entry(
        "unavailable",
        "No verified GIFT NIFTY instrument mapping or account entitlement was established; no symbol/contract was inferred."
    )
    report["retrieval"].update(
        {
            "requests_attempted": request_count,
            "errors": errors,
            "raw_data_files": sorted(path.name for path in destination.glob("*.csv")),
            "raw_data_included": bool(list(destination.glob("*.csv"))),
        }
    )
    path = destination / "latest_backtests.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--fetch-history", action="store_true", help="Fetch a new Dhan history export instead of replaying saved CSVs.")
    args = parser.parse_args()
    directory = Path(args.evidence_dir)
    saved_report = directory / "latest_backtests.json"
    saved_histories = [
        directory / f"{symbol.lower()}_daily_2025_to_current.csv" for symbol in STOCKS
    ] + [
        directory / f"{symbol.lower()}_{interval}m_last30d.csv"
        for symbol in ("NIFTY", "BANKNIFTY")
        for interval in (1, 15)
    ] + [
        directory / f"sensex_{interval}m_last30d.csv" for interval in (1, 15)
    ]
    if not args.fetch_history and saved_report.exists() and all(path.exists() for path in saved_histories):
        report = refresh_saved_backtest_report(directory)
    else:
        report = run_evidence_backtests(evidence_dir=directory)
    compact = {
        symbol: {
            "status": agent.get("status"),
            "total_trades": agent.get("total_trades"),
            "winning_trades": agent.get("winning_trades"),
            "losing_trades": agent.get("losing_trades"),
            "win_rate": agent.get("win_rate"),
            "total_pnl": agent.get("total_pnl"),
        }
        for symbol, agent in report["agents"].items()
    }
    print(json.dumps({"report": str(Path(args.evidence_dir) / "latest_backtests.json"), "agents": compact, "raw_files": report["retrieval"]["raw_data_files"], "errors": report["retrieval"]["errors"]}, indent=2))


if __name__ == "__main__":
    main()