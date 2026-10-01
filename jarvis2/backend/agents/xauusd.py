"""Research-selected, completed-minute XAUUSD trend strategy.

The paper-entry gate remains an independent control in the market feeder. This
module produces a strategy signal only after observing and validating a full
minute assembled from distinct, timestamped OANDA bid/ask updates.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agents.base import BaseAgent, Signal


UNITS_PER_LOT = 100
ONE_LOT = 1.0
LOT_SIZE = ONE_LOT
UTC_ENTRY_START = (16, 0)
UTC_ENTRY_END = (23, 0)
RESEARCH_STATUS = "RESEARCH_NOT_VALIDATED"

# The optimizer replaces this configuration only after a walk-forward search
# selects it using training and inner-validation data. Keep runtime defaults
# and replay parameter names identical; never select parameters on the holdout.
STRATEGY_PARAMETERS: dict[str, Any] = {
    "bar_interval_minutes": 1,
    "fast_ema": 12,
    "slow_ema": 26,
    "min_ema_separation_usd": 1.0,
    "confirmation_buffer_usd": 0.5,
    "confirmation_bars": 2,
    "stop_loss_usd_per_oz": 1.5,
    "take_profit_usd_per_oz": 5.0,
    "max_trades_per_utc_day": 3,
    "entry_cooldown_seconds": 30,
    "position_quantity_units": UNITS_PER_LOT,
}

DEFAULT_ENTRY_WINDOW: dict[str, Any] = {
    "name": "original_utc_16_23",
    "mode": "any",
    "day_timezone": "UTC",
    "clauses": [{"timezone": "UTC", "start": "16:00", "end": "23:00"}],
}


def normalize_entry_window(raw_window: Any = None) -> dict[str, Any]:
    """Validate one or more local session windows; absent input preserves 16:00–23:00 UTC."""
    source = DEFAULT_ENTRY_WINDOW if raw_window is None else raw_window
    if not isinstance(source, dict):
        raise ValueError("XAUUSD entry window must be a mapping")
    name = source.get("name")
    mode = source.get("mode", "any")
    day_timezone = source.get("day_timezone", "UTC")
    clauses = source.get("clauses")
    if not isinstance(name, str) or not name.strip() or mode not in ("any", "all"):
        raise ValueError("XAUUSD entry window requires a name and any/all mode")
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("XAUUSD entry window requires at least one local-time clause")
    try:
        ZoneInfo(day_timezone)
    except (ZoneInfoNotFoundError, TypeError) as exc:
        raise ValueError("XAUUSD entry-window day timezone is not an IANA timezone") from exc
    normalized_clauses = []
    for clause in clauses:
        if not isinstance(clause, dict):
            raise ValueError("XAUUSD entry-window clauses must be mappings")
        zone, start, end = clause.get("timezone"), clause.get("start"), clause.get("end")
        try:
            ZoneInfo(zone)
            start_time = time.fromisoformat(start)
            end_time = time.fromisoformat(end)
        except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
            raise ValueError("XAUUSD entry-window clause has invalid timezone or HH:MM time") from exc
        if (
            not isinstance(start, str)
            or not isinstance(end, str)
            or len(start) != 5
            or len(end) != 5
            or start_time.second
            or end_time.second
            or start_time >= end_time
        ):
            raise ValueError("XAUUSD entry-window clauses must be same-day HH:MM ranges")
        normalized_clauses.append(
            {"timezone": zone, "start": start, "end": end}
        )
    return {
        "name": name.strip(),
        "mode": mode,
        "day_timezone": day_timezone,
        "clauses": normalized_clauses,
    }


def entry_window_session_day(observed_at: datetime, raw_window: Any = None) -> date:
    window = normalize_entry_window(raw_window)
    return observed_at.astimezone(ZoneInfo(window["day_timezone"])).date()


def entry_window_intervals_utc(
    session_day: date,
    raw_window: Any = None,
) -> list[tuple[datetime, datetime]]:
    """Convert that session's local schedule to true DST-aware UTC intervals."""
    window = normalize_entry_window(raw_window)
    intervals = []
    for clause in window["clauses"]:
        zone = ZoneInfo(clause["timezone"])
        start_local = datetime.combine(
            session_day, time.fromisoformat(clause["start"]), tzinfo=zone
        )
        end_local = datetime.combine(
            session_day, time.fromisoformat(clause["end"]), tzinfo=zone
        )
        intervals.append(
            (
                start_local.astimezone(timezone.utc),
                end_local.astimezone(timezone.utc),
            )
        )
    if window["mode"] == "all":
        start = max(item[0] for item in intervals)
        end = min(item[1] for item in intervals)
        return [(start, end)] if start < end else []
    merged: list[list[datetime]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(item[0], item[1]) for item in merged]


def entry_window_interval_at(
    observed_at: datetime,
    raw_window: Any = None,
) -> tuple[datetime, datetime] | None:
    window = normalize_entry_window(raw_window)
    session_day = observed_at.astimezone(ZoneInfo(window["day_timezone"])).date()
    for start, end in entry_window_intervals_utc(session_day, window):
        if start <= observed_at.astimezone(timezone.utc) < end:
            return start, end
    return None


def within_entry_window(observed_at: datetime, parameters: dict[str, Any]) -> bool:
    return entry_window_interval_at(
        observed_at,
        parameters.get("entry_window"),
    ) is not None


def entry_window_day_coverage_minutes(
    session_day: date,
    raw_window: Any = None,
) -> int:
    return sum(
        int((end - start).total_seconds() // 60)
        for start, end in entry_window_intervals_utc(session_day, raw_window)
    )


def ny17_rollover_cutoff_utc(observed_at: datetime, buffer_minutes: int = 1) -> datetime:
    """The no-carry quote-exit cutoff: one minute before 17:00 New York local time."""
    ny_day = observed_at.astimezone(ZoneInfo("America/New_York")).date()
    rollover = datetime.combine(
        ny_day,
        time(17, 0),
        tzinfo=ZoneInfo("America/New_York"),
    ).astimezone(timezone.utc)
    return rollover - timedelta(minutes=buffer_minutes)


def entry_holding_deadline(
    entry_at: datetime,
    raw_window: Any = None,
    *,
    rollover_buffer_minutes: int = 1,
) -> tuple[datetime, str] | None:
    """Return the earliest no-overnight session-close or NY17 quote-exit deadline."""
    interval = entry_window_interval_at(entry_at, raw_window)
    if interval is None:
        return None
    rollover_cutoff = ny17_rollover_cutoff_utc(
        entry_at,
        buffer_minutes=rollover_buffer_minutes,
    )
    if rollover_cutoff <= interval[1]:
        return rollover_cutoff, "ny17_rollover_buffer_forced_exit"
    return interval[1], "session_close_forced_exit"


def entry_holding_policy_allows(
    entry_at: datetime,
    max_hold_minutes: int,
    raw_window: Any = None,
    *,
    rollover_buffer_minutes: int = 1,
) -> bool:
    deadline = entry_holding_deadline(
        entry_at,
        raw_window,
        rollover_buffer_minutes=rollover_buffer_minutes,
    )
    return bool(
        deadline
        and entry_at + timedelta(minutes=max_hold_minutes) <= deadline[0]
    )


def entry_holding_exit_reason(
    entry_at: datetime,
    observed_at: datetime,
    max_hold_minutes: int,
    raw_window: Any = None,
    *,
    rollover_buffer_minutes: int = 1,
) -> str | None:
    window = normalize_entry_window(raw_window)
    if observed_at < entry_at:
        return None
    if entry_window_session_day(observed_at, window) != entry_window_session_day(entry_at, window):
        return "no_overnight_forced_exit"
    deadline = entry_holding_deadline(
        entry_at,
        window,
        rollover_buffer_minutes=rollover_buffer_minutes,
    )
    if deadline is not None and observed_at >= deadline[0]:
        return deadline[1]
    if observed_at - entry_at >= timedelta(minutes=max_hold_minutes):
        return "maximum_holding_period_exit"
    return None


def normalize_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate the strategy settings shared by production and research code."""
    result = dict(parameters)
    try:
        fast, slow = int(result["fast_ema"]), int(result["slow_ema"])
        confirmations = int(result["confirmation_bars"])
        daily_limit = int(result["max_trades_per_utc_day"])
        bar_interval = int(result.get("bar_interval_minutes", 1))
        signal_model = str(result.get("signal_model", "ema_trend_continuation"))
        breakout_lookback = int(result.get("breakout_lookback", 5))
        values = {
            key: float(result[key])
            for key in (
                "min_ema_separation_usd",
                "confirmation_buffer_usd",
                "stop_loss_usd_per_oz",
                "take_profit_usd_per_oz",
            )
        }
        entry_window = normalize_entry_window(result.get("entry_window"))
        count_signals_toward_daily_entry_cap = result.get(
            "count_signals_toward_daily_entry_cap", True
        )
        emit_signals_after_daily_entry_cap = result.get(
            "emit_signals_after_daily_entry_cap", False
        )
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Incomplete or invalid XAUUSD strategy parameters") from exc
    if (
        fast < 2
        or slow <= fast
        or bar_interval not in (1, 5)
        or signal_model not in {"ema_trend_continuation", "ema_mean_reversion", "ema_range_breakout"}
        or not 3 <= breakout_lookback <= 15
        or confirmations < 1
        or confirmations > 5
        or daily_limit < 1
        or daily_limit > 10
        or any(not math.isfinite(value) or value < 0 for value in values.values())
        or values["stop_loss_usd_per_oz"] <= 0
        or values["take_profit_usd_per_oz"] <= 0
        or not isinstance(count_signals_toward_daily_entry_cap, bool)
        or not isinstance(emit_signals_after_daily_entry_cap, bool)
    ):
        raise ValueError("XAUUSD strategy parameters exceed safe, supported bounds")
    normalized = {
        **result,
        **values,
        "fast_ema": fast,
        "slow_ema": slow,
        "bar_interval_minutes": bar_interval,
        "signal_model": signal_model,
        "breakout_lookback": breakout_lookback,
        "confirmation_bars": confirmations,
        "max_trades_per_utc_day": daily_limit,
        "entry_window": entry_window,
        "count_signals_toward_daily_entry_cap": count_signals_toward_daily_entry_cap,
        "emit_signals_after_daily_entry_cap": emit_signals_after_daily_entry_cap,
    }
    quantity = normalized.get("position_quantity_units", UNITS_PER_LOT)
    if quantity != UNITS_PER_LOT:
        raise ValueError("The research strategy is fixed at one 100-unit XAUUSD lot")
    return normalized


def ema_alpha(period: int) -> float:
    return 2.0 / (int(period) + 1)


def raw_trend_signal(
    close: float,
    fast_ema: float,
    slow_ema: float,
    parameters: dict[str, Any],
) -> str | None:
    """Pure closed-minute signal rule, shared with the historical optimizer."""
    if fast_ema > slow_ema and fast_ema - slow_ema >= parameters["min_ema_separation_usd"]:
        return (
            Signal.BUY.value
            if close > fast_ema + parameters["confirmation_buffer_usd"]
            else None
        )
    if slow_ema > fast_ema and slow_ema - fast_ema >= parameters["min_ema_separation_usd"]:
        return (
            Signal.SELL.value
            if close < fast_ema - parameters["confirmation_buffer_usd"]
            else None
        )
    return None


def raw_strategy_signal(
    close: float,
    fast_ema: float,
    slow_ema: float,
    parameters: dict[str, Any],
    *,
    previous_high: float | None = None,
    previous_low: float | None = None,
) -> str | None:
    """Shared pure signal rule for the trained trend/reversal/breakout families."""
    model = parameters["signal_model"]
    if model == "ema_trend_continuation":
        return raw_trend_signal(close, fast_ema, slow_ema, parameters)

    separation = abs(fast_ema - slow_ema)
    if separation < parameters["min_ema_separation_usd"]:
        return None
    buffer = parameters["confirmation_buffer_usd"]

    if model == "ema_mean_reversion":
        if fast_ema > slow_ema and close < fast_ema - buffer:
            return Signal.SELL.value
        if fast_ema < slow_ema and close > fast_ema + buffer:
            return Signal.BUY.value
        return None

    if model == "ema_range_breakout":
        if fast_ema > slow_ema and previous_high is not None and close > previous_high + buffer:
            return Signal.BUY.value
        if fast_ema < slow_ema and previous_low is not None and close < previous_low - buffer:
            return Signal.SELL.value
    return None


def advance_confirmation(
    raw_signal: str | None, previous_signal: str | None, streak: int, required: int
) -> tuple[str | None, str | None, int]:
    """Return the direction only after the configured consecutive minute closes."""
    if raw_signal not in (Signal.BUY.value, Signal.SELL.value):
        return None, None, 0
    streak = streak + 1 if raw_signal == previous_signal else 1
    if streak >= required:
        return raw_signal, None, 0
    return None, raw_signal, streak


def initial_strategy_state() -> dict[str, Any]:
    """Create the deterministic indicator/context clock shared by runtime and replay."""
    return {
        "ema_fast": None,
        "ema_slow": None,
        "last_utc_day": None,
        "daily_entry_count": 0,
        "daily_signal_count": 0,
        "last_signal_time": None,
        "previous_confirmation": None,
        "confirmation_streak": 0,
        "recent_completed_bars": [],
        "last_observed_at": None,
    }


def advance_completed_bar(
    state: dict[str, Any],
    bar: dict[str, Any],
    parameters: dict[str, Any],
) -> str | None:
    """Single deterministic reducer for each complete runtime/replay strategy bar.

    It advances the EMA and breakout context clock on every chronologically
    completed bar, irrespective of trading session or an externally held
    position. Session/day limits gate signals only; the feeder may independently
    suppress an emitted entry while a portfolio position is already open.
    """
    if not isinstance(bar, dict):
        return None
    observed_at = _parse_utc(bar.get("observed_at"))
    try:
        close = float(bar.get("close"))
    except (TypeError, ValueError, OverflowError):
        return None
    if observed_at is None or not math.isfinite(close) or close <= 0:
        return None

    previous_at = state.get("last_observed_at")
    interval = int(parameters["bar_interval_minutes"])
    if previous_at is not None:
        if observed_at <= previous_at:
            return None
        if observed_at - previous_at != timedelta(minutes=interval):
            state["previous_confirmation"] = None
            state["confirmation_streak"] = 0
            state["recent_completed_bars"].clear()

    if state["ema_fast"] is None or state["ema_slow"] is None:
        state["ema_fast"] = state["ema_slow"] = close
    else:
        fast_alpha = ema_alpha(parameters["fast_ema"])
        slow_alpha = ema_alpha(parameters["slow_ema"])
        state["ema_fast"] = close * fast_alpha + state["ema_fast"] * (1 - fast_alpha)
        state["ema_slow"] = close * slow_alpha + state["ema_slow"] * (1 - slow_alpha)
    state["last_observed_at"] = observed_at

    if observed_at.date() != state["last_utc_day"]:
        state["last_utc_day"] = observed_at.date()
        state["daily_entry_count"] = 0
        state["daily_signal_count"] = 0

    signal = None
    daily_entry_cap_open = (
        parameters["emit_signals_after_daily_entry_cap"]
        or state["daily_entry_count"] < parameters["max_trades_per_utc_day"]
    )
    if within_entry_window(observed_at, parameters) and daily_entry_cap_open:
        lookback = parameters["breakout_lookback"]
        history = state["recent_completed_bars"]
        prior_high = (
            max(item["high"] for item in history[-lookback:])
            if len(history) >= lookback
            else None
        )
        prior_low = (
            min(item["low"] for item in history[-lookback:])
            if len(history) >= lookback
            else None
        )
        raw = raw_strategy_signal(
            close,
            state["ema_fast"],
            state["ema_slow"],
            parameters,
            previous_high=prior_high,
            previous_low=prior_low,
        )
        signal, previous, streak = advance_confirmation(
            raw,
            state["previous_confirmation"],
            state["confirmation_streak"],
            parameters["confirmation_bars"],
        )
        state["previous_confirmation"] = previous
        state["confirmation_streak"] = streak
        if signal is not None:
            state["daily_signal_count"] += 1
            if parameters["count_signals_toward_daily_entry_cap"]:
                state["daily_entry_count"] += 1
            state["last_signal_time"] = observed_at.timestamp()
    else:
        state["previous_confirmation"] = None
        state["confirmation_streak"] = 0

    try:
        high, low = float(bar["high"]), float(bar["low"])
    except (KeyError, TypeError, ValueError, OverflowError):
        state["recent_completed_bars"].clear()
    else:
        if math.isfinite(high) and math.isfinite(low) and high >= low > 0:
            state["recent_completed_bars"].append({"high": high, "low": low})
            del state["recent_completed_bars"][:-parameters["breakout_lookback"]]
        else:
            state["recent_completed_bars"].clear()
    return signal


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _within_utc_entry_window(observed_at: datetime) -> bool:
    minute = observed_at.hour * 60 + observed_at.minute
    return 16 * 60 <= minute < 23 * 60


class XAUUSDResearchAgent(BaseAgent):
    """One-lot EMA continuation strategy driven only by completed sampled M1 bars."""

    MINUTE_MIN_UPDATES = 4
    MINUTE_MIN_SPAN_SECONDS = 35
    MAX_PROVIDER_QUOTE_AGE_SECONDS = 20
    MAX_PROVIDER_FUTURE_SKEW_SECONDS = 2

    def __init__(self, parameters: dict[str, Any] | None = None):
        super().__init__("XAUUSD")
        self.symbols = ["XAUUSD"]
        self.parameters = normalize_parameters(parameters or STRATEGY_PARAMETERS)

        # OANDA XAUUSD is modeled as 100 units/ounces for one gold lot. The
        # trading bridge uses quantity 100; stop/target levels are USD per oz,
        # and the matching trade P&L is USD.
        self.lot_size = ONE_LOT
        self.units_per_lot = UNITS_PER_LOT
        self.position_quantity_units = UNITS_PER_LOT
        self.target_pips = self.parameters["take_profit_usd_per_oz"]
        self.stop_loss_pips = self.parameters["stop_loss_usd_per_oz"]
        self.take_profit_usd_per_oz = self.target_pips
        self.stop_loss_usd_per_oz = self.stop_loss_pips
        self.risk_per_trade = self.stop_loss_pips * UNITS_PER_LOT
        self.max_trades_per_day = self.parameters["max_trades_per_utc_day"]
        self.min_ema_separation = self.parameters["min_ema_separation_usd"]
        self.confirmation_buffer = self.parameters["confirmation_buffer_usd"]
        self.signal_confirmation_count = self.parameters["confirmation_bars"]
        self.entry_cooldown = self.parameters["entry_cooldown_seconds"]

        self._strategy_state = initial_strategy_state()
        self.ema_fast: float | None = None
        self.ema_slow: float | None = None
        self.ema_12 = None
        self.ema_26 = None
        self._last_utc_day: Any = None
        self._daily_entry_count = 0
        self.open_trade_count = 0
        self.last_entry_time = 0.0
        self._previous_confirmation: str | None = None
        self._confirmation_streak = 0

        # At-most-once aggregation state: only unique, recent provider
        # observations contribute. No missing quote is forward-filled.
        self._last_provider_timestamp: datetime | None = None
        self._minute_start: datetime | None = None
        self._minute_open: tuple[float, float] | None = None
        self._minute_high: tuple[float, float] | None = None
        self._minute_low: tuple[float, float] | None = None
        self._minute_close: tuple[float, float] | None = None
        self._minute_first_timestamp: datetime | None = None
        self._minute_last_timestamp: datetime | None = None
        self._minute_updates = 0
        self._recent_completed_bars: list[dict[str, float]] = self._strategy_state["recent_completed_bars"]
        self._strategy_minute_group: list[dict[str, Any]] = []

    def get_symbols(self) -> list[str]:
        return self.symbols

    def analyze_completed_bar(self, bar: dict[str, Any]) -> Signal:
        """Analyze one complete genuine minute; open/high/low are never fabricated."""
        signal = advance_completed_bar(self._strategy_state, bar, self.parameters)
        self.ema_fast = self._strategy_state["ema_fast"]
        self.ema_slow = self._strategy_state["ema_slow"]
        self.ema_12, self.ema_26 = self.ema_fast, self.ema_slow
        self._last_utc_day = self._strategy_state["last_utc_day"]
        self._daily_entry_count = self._strategy_state["daily_entry_count"]
        self.open_trade_count = self._daily_entry_count
        self.last_entry_time = (
            self._strategy_state["last_signal_time"]
            if self._strategy_state["last_signal_time"] is not None
            else self.last_entry_time
        )
        self._previous_confirmation = self._strategy_state["previous_confirmation"]
        self._confirmation_streak = self._strategy_state["confirmation_streak"]
        return Signal(signal) if signal is not None else Signal.HOLD

    def _complete_live_minute(self, boundary: datetime) -> dict[str, Any] | None:
        minute_start = self._minute_start
        first, last = self._minute_first_timestamp, self._minute_last_timestamp
        opn, high, low, close = (
            self._minute_open,
            self._minute_high,
            self._minute_low,
            self._minute_close,
        )
        result = None
        if (
            first is not None
            and last is not None
            and opn is not None
            and high is not None
            and low is not None
            and close is not None
            and self._minute_updates >= self.MINUTE_MIN_UPDATES
            and (last - first).total_seconds() >= self.MINUTE_MIN_SPAN_SECONDS
            and first <= boundary - timedelta(seconds=40)
            and last >= boundary - timedelta(seconds=15)
        ):
            result = {
                "provider": "OANDA",
                "data_source": "OANDA_LIVE_DISTINCT_BID_ASK_UPDATES",
                "complete": True,
                "observed_at": boundary.isoformat(),
                "bar_open_time": minute_start.isoformat() if minute_start else None,
                "open": (opn[0] + opn[1]) / 2,
                "high": (high[0] + high[1]) / 2,
                "low": (low[0] + low[1]) / 2,
                "close": (close[0] + close[1]) / 2,
                "distinct_provider_updates": self._minute_updates,
            }
        self._minute_open = self._minute_high = self._minute_low = self._minute_close = None
        self._minute_first_timestamp = self._minute_last_timestamp = None
        self._minute_updates = 0
        return result

    def _aggregate_strategy_minutes(self, minute_bar: dict[str, Any]) -> dict[str, Any] | None:
        interval = self.parameters["bar_interval_minutes"]
        if interval == 1:
            return minute_bar
        minute_open = _parse_utc(minute_bar.get("bar_open_time"))
        if minute_open is None:
            self._strategy_minute_group.clear()
            return None
        group_start = minute_open.replace(minute=(minute_open.minute // interval) * interval)
        expected_start = group_start
        if minute_open != expected_start + timedelta(minutes=len(self._strategy_minute_group)):
            self._strategy_minute_group.clear()
        if not self._strategy_minute_group and minute_open != group_start:
            return None
        self._strategy_minute_group.append(minute_bar)
        if len(self._strategy_minute_group) < interval:
            return None
        bars = self._strategy_minute_group
        self._strategy_minute_group = []
        if (
            bars[-1].get("observed_at")
            != (group_start + timedelta(minutes=interval)).isoformat()
        ):
            return None
        return {
            **bars[-1],
            "bar_open_time": group_start.isoformat(),
            "open": bars[0]["open"],
            "high": max(bar["high"] for bar in bars),
            "low": min(bar["low"] for bar in bars),
            "close": bars[-1]["close"],
            "source_complete_m1_bars": len(bars),
        }

    def analyze(self, market_data: dict[str, Any]) -> Signal:
        """Aggregate distinct provider quotes into covered M1 bars before analysis."""
        if not isinstance(market_data, dict) or market_data.get("source") != "OANDA":
            return Signal.HOLD
        timestamp = _parse_utc(
            market_data.get("provider_timestamp", market_data.get("timestamp"))
        )
        if timestamp is None:
            return Signal.HOLD
        now = datetime.now(timezone.utc)
        age = (now - timestamp).total_seconds()
        if age > self.MAX_PROVIDER_QUOTE_AGE_SECONDS or age < -self.MAX_PROVIDER_FUTURE_SKEW_SECONDS:
            return Signal.HOLD
        if self._last_provider_timestamp is not None and timestamp <= self._last_provider_timestamp:
            return Signal.HOLD
        try:
            bid, ask = float(market_data["bid"]), float(market_data["ask"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return Signal.HOLD
        if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask):
            return Signal.HOLD
        self._last_provider_timestamp = timestamp

        bucket = timestamp.replace(second=0, microsecond=0)
        completed = None
        if self._minute_start is None:
            self._minute_start = bucket
            self._start_live_minute(timestamp, bid, ask)
            return Signal.HOLD
        if bucket < self._minute_start:
            return Signal.HOLD
        if bucket != self._minute_start:
            boundary = self._minute_start + timedelta(minutes=1)
            if bucket == boundary:
                completed = self._complete_live_minute(boundary)
            self._minute_start = bucket
            self._start_live_minute(timestamp, bid, ask)
            if completed is None:
                # A missing minute/insufficient observations break the
                # confirmation sequence; never bridge an unknown price path.
                self._previous_confirmation = None
                self._confirmation_streak = 0
                self._strategy_minute_group.clear()
                return Signal.HOLD
            strategy_bar = self._aggregate_strategy_minutes(completed)
            if strategy_bar is None:
                return Signal.HOLD
            return self.analyze_completed_bar(strategy_bar)

        self._update_live_minute(timestamp, bid, ask)
        return Signal.HOLD

    def _start_live_minute(self, timestamp: datetime, bid: float, ask: float) -> None:
        self._minute_open = self._minute_high = self._minute_low = self._minute_close = (bid, ask)
        self._minute_first_timestamp = self._minute_last_timestamp = timestamp
        self._minute_updates = 1

    def _update_live_minute(self, timestamp: datetime, bid: float, ask: float) -> None:
        if self._minute_high is None or self._minute_low is None:
            self._start_live_minute(timestamp, bid, ask)
            return
        if self._minute_first_timestamp is not None:
            if (timestamp - self._minute_last_timestamp).total_seconds() > 15:
                # Incomplete coverage: discard this minute instead of inventing
                # a path over a material observation gap.
                self._minute_first_timestamp = None
        self._minute_high = (max(self._minute_high[0], bid), max(self._minute_high[1], ask))
        self._minute_low = (min(self._minute_low[0], bid), min(self._minute_low[1], ask))
        self._minute_close = (bid, ask)
        self._minute_last_timestamp = timestamp
        self._minute_updates += 1


# No candidate met the required training-only rules on the verified history.
# Leave the live-named import on the frozen original strategy rather than
# silently installing an unsupported parameter set. The feeder also has an
# independent unconditional entry gate; this alias never changes it.
from agents.xauusd_baseline import XAUUSDBaselineAgent as XAUUSDAgent
