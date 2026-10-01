"""Research-only selective Bollinger re-entry strategy for XAUUSD."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from agents.base import Signal
from agents.xauusd import (
    ONE_LOT,
    UNITS_PER_LOT,
    XAUUSDResearchAgent,
    _parse_utc,
    entry_holding_exit_reason,
    entry_holding_policy_allows,
    normalize_entry_window,
    within_entry_window,
)


HIGHWIN_RESEARCH_STATUS = "RESEARCH_NOT_VALIDATED"
HIGHWIN_STRATEGY_DEFAULTS: dict[str, Any] = {
    "bar_interval_minutes": 1,
    "rsi_period": 14,
    "rsi_reentry_threshold": 25,
    "bollinger_period": 20,
    "bollinger_stddev": 2.0,
    "regime_fast_ema": 20,
    "regime_slow_ema": 50,
    "max_range_ema_separation_usd": 2.0,
    "stop_loss_usd_per_oz": 2.5,
    "take_profit_usd_per_oz": 4.5,
    "max_hold_minutes": 25,
    "allow_overnight": False,
    "entry_window": {
        "name": "original_utc_16_23",
        "mode": "any",
        "day_timezone": "UTC",
        "clauses": [{"timezone": "UTC", "start": "16:00", "end": "23:00"}],
    },
    "max_trades_per_utc_day": 3,
    "position_quantity_units": UNITS_PER_LOT,
}


def normalize_highwin_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate the small, separately predeclared RSI/Bollinger research space."""
    result = dict(parameters)
    try:
        timeframe = int(result["bar_interval_minutes"])
        rsi_period = int(result["rsi_period"])
        threshold = int(result["rsi_reentry_threshold"])
        band_period = int(result["bollinger_period"])
        fast_ema = int(result["regime_fast_ema"])
        slow_ema = int(result["regime_slow_ema"])
        trade_limit = int(result["max_trades_per_utc_day"])
        stddev = float(result["bollinger_stddev"])
        regime_limit = float(result["max_range_ema_separation_usd"])
        stop = float(result["stop_loss_usd_per_oz"])
        target = float(result["take_profit_usd_per_oz"])
        quantity = int(result.get("position_quantity_units", UNITS_PER_LOT))
        max_hold_minutes = int(result.get("max_hold_minutes", 25))
        allow_overnight = result.get("allow_overnight", False)
        entry_window = normalize_entry_window(result.get("entry_window"))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Incomplete or invalid high-win XAUUSD parameters") from exc
    if (
        timeframe not in (1, 5)
        or not 2 <= rsi_period <= 30
        or threshold not in (20, 30)
        or not 10 <= band_period <= 40
        or not 2 <= fast_ema < slow_ema <= 100
        or trade_limit < 1
        or trade_limit > 10
        or not math.isfinite(stddev)
        or stddev <= 0
        or not math.isfinite(regime_limit)
        or regime_limit <= 0
        or not math.isfinite(stop)
        or not 0 < stop <= 3.0
        or not math.isfinite(target)
        or target <= 0
        or max_hold_minutes != 25
        or allow_overnight is not False
        or quantity != UNITS_PER_LOT
    ):
        raise ValueError("High-win XAUUSD parameters exceed supported risk/data bounds")
    return {
        **result,
        "bar_interval_minutes": timeframe,
        "rsi_period": rsi_period,
        "rsi_reentry_threshold": threshold,
        "bollinger_period": band_period,
        "bollinger_stddev": stddev,
        "regime_fast_ema": fast_ema,
        "regime_slow_ema": slow_ema,
        "max_range_ema_separation_usd": regime_limit,
        "stop_loss_usd_per_oz": stop,
        "take_profit_usd_per_oz": target,
        "max_hold_minutes": max_hold_minutes,
        "allow_overnight": False,
        "entry_window": entry_window,
        "max_trades_per_utc_day": trade_limit,
        "position_quantity_units": quantity,
    }


def initial_highwin_state() -> dict[str, Any]:
    """Indicator/context state used unchanged by runtime and chronological replay."""
    return {
        "last_observed_at": None,
        "last_utc_day": None,
        "daily_entry_count": 0,
        "daily_signal_count": 0,
        "last_signal_time": None,
        "previous_close": None,
        "previous_rsi": None,
        "previous_lower_band": None,
        "previous_upper_band": None,
        "closes": [],
        "last_close": None,
        "rsi_seed_gains": [],
        "rsi_seed_losses": [],
        "average_gain": None,
        "average_loss": None,
        "rsi": None,
        "ema_regime_fast": None,
        "ema_regime_slow": None,
        "lower_band": None,
        "middle_band": None,
        "upper_band": None,
    }


def _reset_indicators_after_gap(state: dict[str, Any]) -> None:
    """Reset indicator warmup across an unknown interval but retain UTC-day risk usage."""
    last_day = state.get("last_utc_day")
    daily_entries = state.get("daily_entry_count", 0)
    daily_signals = state.get("daily_signal_count", 0)
    last_signal_time = state.get("last_signal_time")
    state.clear()
    state.update(initial_highwin_state())
    state["last_utc_day"] = last_day
    state["daily_entry_count"] = daily_entries
    state["daily_signal_count"] = daily_signals
    state["last_signal_time"] = last_signal_time


def _advance_rsi(state: dict[str, Any], close: float, period: int) -> float | None:
    previous = state["last_close"]
    state["last_close"] = close
    if previous is None:
        return None
    change = close - previous
    gain, loss = max(change, 0.0), max(-change, 0.0)
    if state["average_gain"] is None or state["average_loss"] is None:
        state["rsi_seed_gains"].append(gain)
        state["rsi_seed_losses"].append(loss)
        if len(state["rsi_seed_gains"]) < period:
            return None
        state["average_gain"] = sum(state["rsi_seed_gains"][-period:]) / period
        state["average_loss"] = sum(state["rsi_seed_losses"][-period:]) / period
        state["rsi_seed_gains"].clear()
        state["rsi_seed_losses"].clear()
    else:
        state["average_gain"] = (
            state["average_gain"] * (period - 1) + gain
        ) / period
        state["average_loss"] = (
            state["average_loss"] * (period - 1) + loss
        ) / period
    avg_gain, avg_loss = state["average_gain"], state["average_loss"]
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def advance_highwin_bar(
    state: dict[str, Any],
    bar: dict[str, Any],
    raw_parameters: dict[str, Any],
) -> str | None:
    """One causal Wilder-RSI/Bollinger re-entry transition on a completed bar."""
    parameters = normalize_highwin_parameters(raw_parameters)
    observed_at = _parse_utc(bar.get("observed_at")) if isinstance(bar, dict) else None
    try:
        close = float(bar["close"])
        high = float(bar["high"])
        low = float(bar["low"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if (
        observed_at is None
        or not all(math.isfinite(value) and value > 0 for value in (close, high, low))
        or high < low
        or not low <= close <= high
    ):
        return None

    previous_at = state["last_observed_at"]
    interval = parameters["bar_interval_minutes"]
    if previous_at is not None:
        if observed_at <= previous_at:
            return None
        if observed_at - previous_at != timedelta(minutes=interval):
            _reset_indicators_after_gap(state)
    state["last_observed_at"] = observed_at
    if observed_at.date() != state["last_utc_day"]:
        state["last_utc_day"] = observed_at.date()
        state["daily_entry_count"] = 0
        state["daily_signal_count"] = 0

    if state["ema_regime_fast"] is None:
        state["ema_regime_fast"] = close
        state["ema_regime_slow"] = close
    else:
        fast_alpha = 2.0 / (parameters["regime_fast_ema"] + 1)
        slow_alpha = 2.0 / (parameters["regime_slow_ema"] + 1)
        state["ema_regime_fast"] = (
            close * fast_alpha + state["ema_regime_fast"] * (1 - fast_alpha)
        )
        state["ema_regime_slow"] = (
            close * slow_alpha + state["ema_regime_slow"] * (1 - slow_alpha)
        )

    prior_close = state["previous_close"]
    prior_rsi = state["rsi"]
    prior_lower = state["lower_band"]
    prior_upper = state["upper_band"]
    rsi = _advance_rsi(state, close, parameters["rsi_period"])
    state["rsi"] = rsi

    closes = state["closes"]
    closes.append(close)
    del closes[:-parameters["bollinger_period"]]
    lower = middle = upper = None
    if len(closes) == parameters["bollinger_period"]:
        middle = sum(closes) / len(closes)
        variance = sum((value - middle) ** 2 for value in closes) / len(closes)
        deviation = math.sqrt(variance) * parameters["bollinger_stddev"]
        lower, upper = middle - deviation, middle + deviation
    state["lower_band"] = lower
    state["middle_band"] = middle
    state["upper_band"] = upper

    signal = None
    if (
        within_entry_window(observed_at, parameters)
        and prior_close is not None
        and prior_rsi is not None
        and rsi is not None
        and prior_lower is not None
        and prior_upper is not None
        and lower is not None
        and upper is not None
        and middle is not None
        and abs(state["ema_regime_fast"] - state["ema_regime_slow"])
        <= parameters["max_range_ema_separation_usd"]
    ):
        if (
            prior_close < prior_lower
            and close > lower
            and prior_rsi <= parameters["rsi_reentry_threshold"]
            and rsi > parameters["rsi_reentry_threshold"]
            and close < middle
        ):
            signal = Signal.BUY.value
        elif (
            prior_close > prior_upper
            and close < upper
            and prior_rsi >= 100 - parameters["rsi_reentry_threshold"]
            and rsi < 100 - parameters["rsi_reentry_threshold"]
            and close > middle
        ):
            signal = Signal.SELL.value
    if signal is not None:
        state["daily_signal_count"] += 1
        state["last_signal_time"] = observed_at.timestamp()
    state["previous_close"] = close
    state["previous_rsi"] = rsi
    state["previous_lower_band"] = lower
    state["previous_upper_band"] = upper
    return signal


def register_highwin_entry(
    state: dict[str, Any],
    entry_time: Any,
    raw_parameters: dict[str, Any],
) -> bool:
    """Count only an actually accepted/fill-modelled entry toward three per day."""
    parameters = normalize_highwin_parameters(raw_parameters)
    if isinstance(entry_time, datetime):
        observed_at = _parse_utc(entry_time.isoformat())
    elif isinstance(entry_time, str):
        observed_at = _parse_utc(entry_time)
    else:
        observed_at = entry_time
    if observed_at is None or not hasattr(observed_at, "date"):
        return False
    day = observed_at.date()
    if day != state["last_utc_day"]:
        state["last_utc_day"] = day
        state["daily_entry_count"] = 0
        state["daily_signal_count"] = 0
    if state["daily_entry_count"] >= parameters["max_trades_per_utc_day"]:
        return False
    state["daily_entry_count"] += 1
    return True


def _entry_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _parse_utc(value.isoformat())
    if isinstance(value, str):
        return _parse_utc(value)
    return None


def highwin_entry_policy_allows(
    entry_time: Any,
    raw_parameters: dict[str, Any],
) -> bool:
    """Reserve the full hold before both the configured close and NY17 minus one minute."""
    parameters = normalize_highwin_parameters(raw_parameters)
    entry_at = _entry_timestamp(entry_time)
    if entry_at is None:
        return False
    return entry_holding_policy_allows(
        entry_at,
        parameters["max_hold_minutes"],
        parameters["entry_window"],
        rollover_buffer_minutes=1,
    )


def highwin_holding_exit_reason(
    entry_time: Any,
    observed_at: Any,
    raw_parameters: dict[str, Any],
) -> str | None:
    """Shared runtime/replay max-hold, session-close, and NY17 no-carry policy."""
    parameters = normalize_highwin_parameters(raw_parameters)
    entry_at = _entry_timestamp(entry_time)
    observation = _entry_timestamp(observed_at)
    if entry_at is None or observation is None or observation < entry_at:
        return None
    return entry_holding_exit_reason(
        entry_at,
        observation,
        parameters["max_hold_minutes"],
        parameters["entry_window"],
        rollover_buffer_minutes=1,
    )


class XAUUSDHighWinResearchAgent(XAUUSDResearchAgent):
    """Research-only signal agent; never bound to the live XAUUSD import."""

    def __init__(self, parameters: dict[str, Any] | None = None):
        highwin = normalize_highwin_parameters(parameters or HIGHWIN_STRATEGY_DEFAULTS)
        # Reuse the timestamp-checked, distinct-quote M1/M5 aggregator. The
        # standard reducer is not used; this subclass calls its own shared
        # RSI/Bollinger reducer on the identical completed-bar clock.
        super().__init__(
            {
                "bar_interval_minutes": highwin["bar_interval_minutes"],
                "fast_ema": highwin["regime_fast_ema"],
                "slow_ema": highwin["regime_slow_ema"],
                "min_ema_separation_usd": 0.0,
                "confirmation_buffer_usd": 0.0,
                "confirmation_bars": 1,
                "stop_loss_usd_per_oz": highwin["stop_loss_usd_per_oz"],
                "take_profit_usd_per_oz": highwin["take_profit_usd_per_oz"],
                "max_trades_per_utc_day": highwin["max_trades_per_utc_day"],
                "entry_window": highwin["entry_window"],
                "entry_cooldown_seconds": 30,
                "position_quantity_units": UNITS_PER_LOT,
            }
        )
        self.highwin_parameters = highwin
        self.highwin_state = initial_highwin_state()
        self._highwin_active_entry_time: datetime | None = None
        self.lot_size = ONE_LOT
        self.position_quantity_units = UNITS_PER_LOT
        self.units_per_lot = UNITS_PER_LOT
        self.stop_loss_pips = highwin["stop_loss_usd_per_oz"]
        self.target_pips = highwin["take_profit_usd_per_oz"]
        self.stop_loss_usd_per_oz = self.stop_loss_pips
        self.take_profit_usd_per_oz = self.target_pips
        self.risk_per_trade = self.stop_loss_pips * UNITS_PER_LOT

    def analyze_completed_bar(self, bar: dict[str, Any]) -> Signal:
        signal = advance_highwin_bar(self.highwin_state, bar, self.highwin_parameters)
        self._daily_entry_count = self.highwin_state["daily_entry_count"]
        self.open_trade_count = self._daily_entry_count
        if self.highwin_state["last_signal_time"] is not None:
            self.last_entry_time = self.highwin_state["last_signal_time"]
        return Signal(signal) if signal is not None else Signal.HOLD

    def register_research_entry(self, entry_time: Any) -> bool:
        """Optional parent integration hook; call only after a paper fill is accepted."""
        if self._highwin_active_entry_time is not None:
            return False
        parsed_entry_time = _entry_timestamp(entry_time)
        accepted = register_highwin_entry(
            self.highwin_state,
            entry_time,
            self.highwin_parameters,
        )
        if accepted:
            self._highwin_active_entry_time = parsed_entry_time
        self._daily_entry_count = self.highwin_state["daily_entry_count"]
        self.open_trade_count = self._daily_entry_count
        return accepted

    def research_entry_policy_allows(self, entry_time: Any) -> bool:
        """Use before entry so max hold fits before session close and NY17 quote cutoff."""
        return highwin_entry_policy_allows(entry_time, self.highwin_parameters)

    def should_force_research_time_exit(self, observed_at: Any) -> bool:
        """Tell the parent when to close using its current genuine OANDA bid/ask quote."""
        if self._highwin_active_entry_time is None:
            return False
        return (
            highwin_holding_exit_reason(
                self._highwin_active_entry_time,
                observed_at,
                self.highwin_parameters,
            )
            is not None
        )

    def mark_research_position_closed(self) -> None:
        """Clear the active research position after its stop, target, or time exit."""
        self._highwin_active_entry_time = None