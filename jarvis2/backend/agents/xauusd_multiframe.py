"""Experimental paper-only XAUUSD multi-timeframe EMA pullback strategy.

The agent consumes externally assembled, completed OANDA candles. It does not
aggregate quotes, synthesize bars, or treat historical test fixtures as market
evidence.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

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
from agents.xauusd_highwin import (
    highwin_entry_policy_allows,
    highwin_holding_exit_reason,
    initial_highwin_state,
    register_highwin_entry,
)


_UTC = timezone.utc
_FRAME_MINUTES = {"M3": 3, "M15": 15, "H4": 240}
_ENTRY_WINDOW = {
    "name": "london_08_17_local",
    "mode": "any",
    "day_timezone": "Europe/London",
    "clauses": [{"timezone": "Europe/London", "start": "08:00", "end": "17:00"}],
}

MULTIFRAME_PARAMETERS: dict[str, Any] = {
    "bar_interval_minutes": 3,
    "timeframes": ["H4", "M15", "M3"],
    "rules": {
        "H4": "completed EMA20/EMA50 alignment; EMA20 rises/falls across the last 3 bars; close is on the direction side of EMA20",
        "M15": "completed EMA20/EMA50 alignment; latest close is on the direction side of EMA20; at least one of the latest 3 completed bars touches its contemporaneous EMA20",
        "M3": "completed directional body closes beyond the immediately previous M3 high/low and on the direction side of EMA20",
        "combination": "H4 and M15 direction must agree with the M3 trigger; mixed or incomplete setup is HOLD",
    },
    "entry_window": _ENTRY_WINDOW,
    "stop_loss_usd_per_oz": 1.50,
    "take_profit_usd_per_oz": 3.75,
    "position_quantity_units": UNITS_PER_LOT,
    "max_trades_per_utc_day": 3,
    "max_hold_minutes": 25,
    "allow_overnight": False,
    "minimum_completed_candles": {"M3": 50, "M15": 50, "H4": 100},
    "max_snapshot_age_seconds": 210,
    "max_quote_age_seconds": 210,
    "quote_future_skew_seconds": 2,
    "research_status": "EXPERIMENTAL_PAPER_ONLY",
}


def _utc_timestamp(value: Any) -> datetime | None:
    """Parse an explicitly UTC ISO timestamp; naive and non-UTC values fail closed."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None
    return parsed.astimezone(_UTC)


def _price(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _atr(bars: list[dict[str, Any]], period: int = 14) -> float | None:
    if len(bars) < period + 1:
        return None
    true_ranges = []
    for index in range(1, len(bars)):
        high, low = bars[index]["high"], bars[index]["low"]
        previous_close = bars[index - 1]["close"]
        true_ranges.append(
            max(high - low, abs(high - previous_close), abs(low - previous_close))
        )
    return sum(true_ranges[-period:]) / period


def _bar_metrics(bars: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [bar["close"] for bar in bars]
    fast = _ema_series(closes, 20)
    slow = _ema_series(closes, 50)
    return {
        "bars": bars,
        "ema20_series": fast,
        "ema50_series": slow,
        "ema20": fast[-1] if fast else None,
        "ema50": slow[-1] if slow else None,
        "ema20_slope_3": fast[-1] - fast[-4] if len(fast) >= 4 else None,
        "close": closes[-1] if closes else None,
        "atr14": _atr(bars),
    }


def _direction(value: str | None) -> str:
    return value if value in (Signal.BUY.value, Signal.SELL.value) else "MIXED"


class XAUUSDMultiframeResearchAgent(XAUUSDResearchAgent):
    """Paper-only H4/M15/M3 agent; only fresh, causal completed bars can signal."""

    MAX_PROVIDER_QUOTE_AGE_SECONDS = 210
    MAX_PROVIDER_FUTURE_SKEW_SECONDS = 2

    def __init__(self, parameters: dict[str, Any] | None = None):
        if parameters:
            fixed = MULTIFRAME_PARAMETERS
            for key, value in parameters.items():
                if key not in fixed or value != fixed[key]:
                    raise ValueError(
                        f"XAUUSD multi-frame rule/risk parameter {key!r} is frozen"
                    )

        # The inherited generic quote aggregator requires a compatibility 1m
        # setting. This does not transform or simulate any supplied candles.
        compatibility_window = normalize_entry_window(_ENTRY_WINDOW)
        super().__init__(
            {
                "bar_interval_minutes": 1,
                "fast_ema": 20,
                "slow_ema": 50,
                "min_ema_separation_usd": 0.0,
                "confirmation_buffer_usd": 0.0,
                "confirmation_bars": 1,
                "stop_loss_usd_per_oz": 1.50,
                "take_profit_usd_per_oz": 3.75,
                "max_trades_per_utc_day": 3,
                "entry_window": compatibility_window,
                "entry_cooldown_seconds": 30,
                "position_quantity_units": UNITS_PER_LOT,
            }
        )
        self.highwin_parameters = dict(MULTIFRAME_PARAMETERS)
        self.highwin_state = initial_highwin_state()
        self._highwin_active_entry_time: datetime | None = None
        self._daily_entry_count = 0
        self.open_trade_count = 0
        self.last_entry_time = 0.0
        self.lot_size = ONE_LOT
        self.position_quantity_units = UNITS_PER_LOT
        self.units_per_lot = UNITS_PER_LOT
        self.stop_loss_pips = 1.50
        self.target_pips = 3.75
        self.stop_loss_usd_per_oz = 1.50
        self.take_profit_usd_per_oz = 3.75
        self.risk_per_trade = 1.50 * UNITS_PER_LOT

        # Existing XAUUSD risk helpers deliberately receive a separate legacy
        # compatibility mapping. Its 1m interval is never used for candle data.
        self._risk_policy_parameters = {
            "bar_interval_minutes": 1,
            "rsi_period": 14,
            "rsi_reentry_threshold": 25,
            "bollinger_period": 20,
            "bollinger_stddev": 2.0,
            "regime_fast_ema": 20,
            "regime_slow_ema": 50,
            "max_range_ema_separation_usd": 2.0,
            "stop_loss_usd_per_oz": 1.50,
            "take_profit_usd_per_oz": 3.75,
            "max_hold_minutes": 25,
            "allow_overnight": False,
            "entry_window": compatibility_window,
            "max_trades_per_utc_day": 3,
            "position_quantity_units": UNITS_PER_LOT,
        }
        self._snapshot: dict[str, Any] | None = None
        self._snapshot_error: str | None = None
        self._last_processed_m3_at: datetime | None = None
        self._startup_historical_call_suppression = False
        self._decision_callback: Callable[[dict[str, Any]], Any] | None = None
        self._latest_decision: dict[str, Any] = {}
        self._last_quote_at: datetime | None = None
        self._counts = {
            "calls": 0,
            "checked": 0,
            "buy": 0,
            "sell": 0,
            "actionable": 0,
            "accepted_trades": 0,
        }
        self._latest_diagnostics: dict[str, Any] = {
            "latest_decision_timestamp": None,
            "h4_direction": "UNKNOWN",
            "m15_direction": "UNKNOWN",
            "m3_direction": "UNKNOWN",
            "reasons": ["awaiting_valid_candle_snapshot"],
        }

    def get_symbols(self) -> list[str]:
        return ["XAUUSD"]

    @property
    def last_utc_day(self) -> date | None:
        return self.highwin_state.get("last_utc_day")

    @last_utc_day.setter
    def last_utc_day(self, value: Any) -> None:
        if isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return
        if isinstance(value, date):
            self.highwin_state["last_utc_day"] = value

    @property
    def daily_entry_count(self) -> int:
        return int(self.highwin_state.get("daily_entry_count", 0))

    @daily_entry_count.setter
    def daily_entry_count(self, value: Any) -> None:
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 3:
            self.highwin_state["daily_entry_count"] = value
            self._daily_entry_count = value
            self.open_trade_count = value

    def set_decision_callback(
        self, callback: Callable[[dict[str, Any]], Any] | None
    ) -> None:
        self._decision_callback = callback

    def _validate_bar(
        self, raw_bar: Any, frame: str, environment: str, fetched_at: datetime
    ) -> dict[str, Any]:
        if not isinstance(raw_bar, dict):
            raise ValueError(f"{frame} candle must be a mapping")
        interval = _FRAME_MINUTES[frame]
        if raw_bar.get("complete") is not True:
            raise ValueError(f"{frame} candle is not explicitly complete")
        if raw_bar.get("provider") != "OANDA":
            raise ValueError(f"{frame} candle provider must be OANDA")
        if raw_bar.get("environment") != environment:
            raise ValueError(f"{frame} candle environment does not match snapshot")
        raw_interval = raw_bar.get("bar_interval_minutes")
        if isinstance(raw_interval, bool) or raw_interval != interval:
            raise ValueError(f"{frame} candle interval must be {interval} minutes")
        opened_at = _utc_timestamp(raw_bar.get("bar_open_time"))
        observed_at = _utc_timestamp(raw_bar.get("observed_at"))
        if opened_at is None or observed_at is None:
            raise ValueError(f"{frame} candle timestamps must be ISO UTC")
        if observed_at != opened_at + timedelta(minutes=interval):
            raise ValueError(f"{frame} observed_at must be its close timestamp")
        if observed_at > fetched_at + timedelta(seconds=2):
            raise ValueError(f"{frame} candle observation is in the snapshot future")

        prices = {
            name: _price(raw_bar.get(name))
            for name in ("open", "high", "low", "close", "bid_close", "ask_close")
        }
        if any(value is None for value in prices.values()):
            raise ValueError(f"{frame} candle has an invalid or missing price")
        opening, high, low, close = (
            prices["open"],
            prices["high"],
            prices["low"],
            prices["close"],
        )
        if (
            high < low
            or high < max(opening, close)
            or low > min(opening, close)
            or prices["bid_close"] > prices["ask_close"]
        ):
            raise ValueError(f"{frame} candle has inconsistent OHLC or bid/ask prices")
        return {
            **raw_bar,
            "bar_open_time": opened_at,
            "observed_at": observed_at,
            **prices,
        }

    def update_candles(self, snapshot: dict[str, Any]) -> bool:
        """Validate and atomically replace completed external M3/M15/H4 candles."""
        self._snapshot = None
        self._snapshot_error = None
        if not isinstance(snapshot, dict):
            self._snapshot_error = "snapshot_must_be_a_mapping"
            return False
        fetched_at = _utc_timestamp(snapshot.get("fetched_at"))
        environment = snapshot.get("environment")
        frames = snapshot.get("frames")
        now = datetime.now(_UTC)
        if fetched_at is None:
            self._snapshot_error = "fetched_at_must_be_an_ISO_UTC_timestamp"
        elif environment not in ("practice", "live"):
            self._snapshot_error = "environment_must_be_practice_or_live"
        elif not isinstance(frames, dict) or set(frames) != set(_FRAME_MINUTES):
            self._snapshot_error = "frames_must_contain_exactly_M3_M15_H4"
        elif (now - fetched_at).total_seconds() > 210:
            self._snapshot_error = "candle_snapshot_stale"
        elif (fetched_at - now).total_seconds() > 2:
            self._snapshot_error = "candle_snapshot_timestamp_in_future"
        if self._snapshot_error:
            self._refresh_wait_diagnostics()
            return False

        try:
            validated: dict[str, list[dict[str, Any]]] = {}
            for frame in ("M3", "M15", "H4"):
                source = frames[frame]
                if not isinstance(source, list):
                    raise ValueError(f"{frame} frame must be a list")
                bars = [
                    self._validate_bar(bar, frame, environment, fetched_at)
                    for bar in source
                ]
                observations = [bar["observed_at"] for bar in bars]
                if observations != sorted(observations) or len(set(observations)) != len(
                    observations
                ):
                    raise ValueError(f"{frame} candles must be unique and chronological")
                validated[frame] = bars
        except ValueError as exc:
            self._snapshot_error = str(exc)
            self._refresh_wait_diagnostics()
            return False

        self._snapshot = {
            "fetched_at": fetched_at,
            "environment": environment,
            "frames": validated,
        }
        self._refresh_wait_diagnostics()
        return True

    def _causal_frames(
        self, decision_at: datetime, quote_at: datetime
    ) -> dict[str, list[dict[str, Any]]]:
        assert self._snapshot is not None
        latest_allowed = min(decision_at, quote_at + timedelta(seconds=2))
        return {
            frame: [
                bar
                for bar in self._snapshot["frames"][frame]
                if bar["observed_at"] <= latest_allowed
            ]
            for frame in _FRAME_MINUTES
        }

    def _get_quote(self, market_data: Any) -> tuple[datetime, float, float] | None:
        if not isinstance(market_data, dict) or market_data.get("source") != "OANDA":
            self._latest_diagnostics["reasons"] = ["fresh_OANDA_quote_required"]
            return None
        quote_at = _utc_timestamp(
            market_data.get("provider_timestamp", market_data.get("timestamp"))
        )
        if quote_at is None:
            self._latest_diagnostics["reasons"] = ["quote_timestamp_must_be_ISO_UTC"]
            return None
        now = datetime.now(_UTC)
        age = (now - quote_at).total_seconds()
        if age > 210 or age < -2:
            self._latest_diagnostics["reasons"] = ["OANDA_quote_stale_or_future"]
            return None
        if (
            self._snapshot is None
            or market_data.get("environment") != self._snapshot["environment"]
        ):
            self._latest_diagnostics["reasons"] = ["quote_snapshot_environment_mismatch"]
            return None
        bid, ask = _price(market_data.get("bid")), _price(market_data.get("ask"))
        if bid is None or ask is None or bid > ask:
            self._latest_diagnostics["reasons"] = ["invalid_OANDA_bid_ask"]
            return None
        fetched_at = self._snapshot["fetched_at"]
        if fetched_at > quote_at + timedelta(seconds=2):
            self._latest_diagnostics["reasons"] = [
                "snapshot_observation_later_than_quote"
            ]
            return None
        self._last_quote_at = quote_at
        return quote_at, bid, ask

    @staticmethod
    def _directions(
        frames: dict[str, list[dict[str, Any]]]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
        metrics = {frame: _bar_metrics(frames[frame]) for frame in _FRAME_MINUTES}
        h4, m15, m3 = (metrics[key] for key in ("H4", "M15", "M3"))
        reasons: list[str] = []
        h4_direction = None
        if h4["ema20"] is not None and h4["ema50"] is not None:
            slope = h4["ema20_slope_3"]
            if h4["ema20"] > h4["ema50"] and h4["close"] > h4["ema20"] and slope > 0:
                h4_direction = Signal.BUY.value
            elif (
                h4["ema20"] < h4["ema50"]
                and h4["close"] < h4["ema20"]
                and slope < 0
            ):
                h4_direction = Signal.SELL.value
        metrics["H4"]["direction"] = _direction(h4_direction)
        if h4_direction is None:
            reasons.append("H4_alignment_slope_or_close_mixed")

        m15_direction = None
        if m15["ema20"] is not None and m15["ema50"] is not None:
            if m15["ema20"] > m15["ema50"] and m15["close"] > m15["ema20"]:
                m15_direction = Signal.BUY.value
            elif m15["ema20"] < m15["ema50"] and m15["close"] < m15["ema20"]:
                m15_direction = Signal.SELL.value
        metrics["M15"]["direction"] = _direction(m15_direction)
        if m15_direction is None:
            reasons.append("M15_alignment_or_close_mixed")

        m15_touch = False
        if len(m15["bars"]) >= 3:
            series = m15["ema20_series"]
            for bar, ema in zip(m15["bars"][-3:], series[-3:]):
                if bar["low"] <= ema <= bar["high"]:
                    m15_touch = True
                    break
        metrics["M15"]["pullback_touch"] = m15_touch
        if m15_direction is not None and not m15_touch:
            reasons.append("M15_latest_three_bars_have_no_EMA20_touch")

        m3_direction = None
        if len(m3["bars"]) >= 2 and m3["ema20"] is not None:
            current, previous = m3["bars"][-1], m3["bars"][-2]
            if (
                current["close"] > current["open"]
                and current["close"] > previous["high"]
                and current["close"] > m3["ema20"]
            ):
                m3_direction = Signal.BUY.value
            elif (
                current["close"] < current["open"]
                and current["close"] < previous["low"]
                and current["close"] < m3["ema20"]
            ):
                m3_direction = Signal.SELL.value
        metrics["M3"]["direction"] = _direction(m3_direction)
        if m3_direction is None:
            reasons.append("M3_directional_breakout_not_confirmed")

        matched = (
            h4_direction is not None
            and h4_direction == m15_direction == m3_direction
            and m15_touch
        )
        candidate = h4_direction if matched else None
        if (
            h4_direction is not None
            and m15_direction is not None
            and h4_direction != m15_direction
        ):
            reasons.append("H4_M15_directions_disagree")
        if m3_direction is not None and m3_direction != h4_direction:
            reasons.append("M3_trigger_disagrees_with_H4")
        if matched:
            reasons.append("all_three_timeframes_confirmed_" + candidate)
        return metrics["H4"], metrics["M15"], metrics["M3"], reasons

    def _sync_utc_day(self, timestamp: datetime) -> None:
        day = timestamp.astimezone(_UTC).date()
        if self.highwin_state.get("last_utc_day") != day:
            self.highwin_state["last_utc_day"] = day
            self.highwin_state["daily_entry_count"] = 0
            self.highwin_state["daily_signal_count"] = 0
        self._daily_entry_count = int(self.highwin_state.get("daily_entry_count", 0))
        self.open_trade_count = self._daily_entry_count

    def _refresh_wait_diagnostics(self) -> None:
        if self._snapshot_error:
            reasons = [self._snapshot_error]
            self._latest_diagnostics["reasons"] = reasons
            self._latest_diagnostics["status"] = "WAIT"
            return
        if self._snapshot is None:
            self._latest_diagnostics["reasons"] = ["awaiting_valid_candle_snapshot"]
            self._latest_diagnostics["status"] = "WAIT"
            return
        now = datetime.now(_UTC)
        if (now - self._snapshot["fetched_at"]).total_seconds() > 210:
            self._latest_diagnostics["reasons"] = ["candle_snapshot_stale"]
            self._latest_diagnostics["status"] = "WAIT"
            return
        frames = self._snapshot["frames"]
        min_counts = MULTIFRAME_PARAMETERS["minimum_completed_candles"]
        missing = [
            f"{frame}_warmup_{len(frames[frame])}_{min_counts[frame]}"
            for frame in ("M3", "M15", "H4")
            if len(frames[frame]) < min_counts[frame]
        ]
        if missing:
            self._latest_diagnostics["reasons"] = missing
            self._latest_diagnostics["status"] = "WARMUP"
            return
        m3 = frames["M3"][-1]["observed_at"] if frames["M3"] else None
        if m3 and (now - m3).total_seconds() > 210:
            self._latest_diagnostics["reasons"] = ["latest_M3_close_stale"]
            self._latest_diagnostics["status"] = "WAIT"
            return
        self._latest_diagnostics["status"] = "READY"
        if not self._latest_diagnostics.get("reasons"):
            self._latest_diagnostics["reasons"] = ["awaiting_fresh_OANDA_quote"]

    def analyze(self, market_data: dict[str, Any]) -> Signal:
        """Evaluate one new completed M3 close using a fresh genuine OANDA quote."""
        self._counts["calls"] += 1
        quote = self._get_quote(market_data)
        if quote is None:
            self._refresh_wait_diagnostics()
            return Signal.HOLD
        quote_at, _bid, _ask = quote
        assert self._snapshot is not None
        m3_candidates = [
            bar
            for bar in self._snapshot["frames"]["M3"]
            if bar["observed_at"] <= quote_at + timedelta(seconds=2)
        ]
        if not m3_candidates:
            self._latest_diagnostics["reasons"] = ["no_completed_M3_close_before_quote"]
            self._latest_diagnostics["status"] = "WAIT"
            return Signal.HOLD
        latest_m3 = m3_candidates[-1]
        decision_at = latest_m3["observed_at"]
        if (datetime.now(_UTC) - decision_at).total_seconds() > 210:
            self._latest_diagnostics["reasons"] = ["latest_M3_close_stale"]
            self._latest_diagnostics["status"] = "WAIT"
            return Signal.HOLD
        if decision_at > quote_at + timedelta(seconds=2):
            self._latest_diagnostics["reasons"] = ["M3_observation_later_than_quote"]
            self._latest_diagnostics["status"] = "WAIT"
            return Signal.HOLD
        if self._last_processed_m3_at == decision_at:
            self._latest_diagnostics["reasons"] = ["M3_close_already_evaluated"]
            self._latest_diagnostics["status"] = (
                "READY" if self._latest_diagnostics.get("status") != "WARMUP" else "WARMUP"
            )
            return Signal.HOLD
        if (
            self._last_processed_m3_at is not None
            and decision_at < self._last_processed_m3_at
        ):
            self._latest_diagnostics["reasons"] = ["out_of_order_M3_close"]
            self._latest_diagnostics["status"] = "WAIT"
            return Signal.HOLD

        self._last_processed_m3_at = decision_at
        self._counts["checked"] += 1
        self._sync_utc_day(decision_at)
        selected = self._causal_frames(decision_at, quote_at)
        h4, m15, m3, reasons = self._directions(selected)
        required = MULTIFRAME_PARAMETERS["minimum_completed_candles"]
        warmup_reasons = [
            f"{frame}_warmup_{len(selected[frame])}_{required[frame]}"
            for frame in ("M3", "M15", "H4")
            if len(selected[frame]) < required[frame]
        ]
        candidate = None
        if not warmup_reasons:
            if h4["direction"] == m15["direction"] == m3["direction"]:
                if h4["direction"] in (Signal.BUY.value, Signal.SELL.value):
                    if m15["pullback_touch"]:
                        candidate = h4["direction"]
                    elif "M15_latest_three_bars_have_no_EMA20_touch" not in reasons:
                        reasons.append("M15_latest_three_bars_have_no_EMA20_touch")
            else:
                if "no_complete_multiframe_setup" not in reasons:
                    reasons.append("no_complete_multiframe_setup")
        else:
            reasons.extend(warmup_reasons)

        if candidate == Signal.BUY.value:
            self._counts["buy"] += 1
            self.highwin_state["daily_signal_count"] += 1
        elif candidate == Signal.SELL.value:
            self._counts["sell"] += 1
            self.highwin_state["daily_signal_count"] += 1

        blockers: list[str] = []
        is_bootstrap = not self._startup_historical_call_suppression
        if is_bootstrap:
            self._startup_historical_call_suppression = True
            blockers.append("startup_historical_M3_signal_suppressed")
        if warmup_reasons:
            blockers.extend(warmup_reasons)
        if candidate is None:
            blockers.extend(reason for reason in reasons if reason not in blockers)
            if not reasons:
                blockers.append("no_setup")
        if candidate is not None and not within_entry_window(
            decision_at, self._risk_policy_parameters
        ):
            blockers.append("outside_London_08_17_entry_window")
        if candidate is not None and self.daily_entry_count >= 3:
            blockers.append("three_accepted_entries_already_used_today")
        if candidate is not None and self._highwin_active_entry_time is not None:
            blockers.append("research_position_already_open")
        if candidate is not None and not highwin_entry_policy_allows(
            decision_at, self._risk_policy_parameters
        ):
            blockers.append("25_minute_hold_does_not_fit_session_or_NY17_buffer")
        if self._snapshot["environment"] != "practice":
            blockers.append("paper_agent_rejects_live_environment")

        actionable = candidate is not None and not blockers
        returned = Signal(candidate) if actionable else Signal.HOLD
        if actionable:
            self._counts["actionable"] += 1
        decision_id = f"xauusd-multiframe:{decision_at.isoformat()}"
        decision = {
            "decision_id": decision_id,
            "timestamp": decision_at.isoformat(),
            "decision_timestamp": decision_at.isoformat(),
            "candidate_signal": candidate or Signal.HOLD.value,
            "actionable_signal": returned.value,
            "blockers": blockers,
            "h4_direction": h4["direction"],
            "m15_direction": m15["direction"],
            "m3_direction": m3["direction"],
            "startup_historical_call_suppressed": is_bootstrap,
            "real_timeframe_minutes": 3,
        }
        self._latest_decision = decision
        self._latest_diagnostics = {
            **decision,
            "latest_decision_timestamp": decision_at.isoformat(),
            "status": "WARMUP" if warmup_reasons else ("READY" if candidate else "WAIT"),
            "h4_ema20": h4["ema20"],
            "h4_ema50": h4["ema50"],
            "h4_ema20_slope_3": h4["ema20_slope_3"],
            "h4_close": h4["close"],
            "h4_atr14": h4["atr14"],
            "m15_ema20": m15["ema20"],
            "m15_ema50": m15["ema50"],
            "m15_close": m15["close"],
            "m15_atr14": m15["atr14"],
            "m15_pullback_touch": m15.get("pullback_touch", False),
            "m3_ema20": m3["ema20"],
            "m3_ema50": m3["ema50"],
            "m3_close": m3["close"],
            "m3_atr14": m3["atr14"],
            "reasons": blockers if blockers else reasons,
            "checked_count": self._counts["checked"],
            "buy_count": self._counts["buy"],
            "sell_count": self._counts["sell"],
            "actionable_count": self._counts["actionable"],
            "calls": self._counts["calls"],
            "accepted_trades": self._counts["accepted_trades"],
            "real_timeframe_minutes": 3,
            "startup_historical_call_suppression": self._startup_historical_call_suppression,
        }
        if self._decision_callback is not None:
            try:
                self._decision_callback(dict(decision))
            except Exception as exc:  # durable logging failure must remain diagnosable
                self._latest_diagnostics["callback_error"] = str(exc)
        return returned

    def _risk_helper_parameters(self) -> dict[str, Any]:
        """Explicit 1m compatibility shape accepted by legacy highwin risk helpers."""
        return dict(self._risk_policy_parameters)

    def research_entry_policy_allows(self, entry_time: Any) -> bool:
        return highwin_entry_policy_allows(
            entry_time, self._risk_helper_parameters()
        )

    def register_research_entry(self, entry_time: Any) -> bool:
        """Count a real accepted paper fill, not a signal or a strategy review."""
        if self._highwin_active_entry_time is not None:
            return False
        parsed = _parse_utc(entry_time.isoformat()) if isinstance(
            entry_time, datetime
        ) else _parse_utc(entry_time) if isinstance(entry_time, str) else None
        if (
            parsed is None
            or not within_entry_window(parsed, self._risk_policy_parameters)
            or not self.research_entry_policy_allows(parsed)
        ):
            return False
        accepted = register_highwin_entry(
            self.highwin_state,
            parsed,
            self._risk_helper_parameters(),
        )
        if accepted:
            self._highwin_active_entry_time = parsed
            self._counts["accepted_trades"] += 1
        self._daily_entry_count = self.daily_entry_count
        self.open_trade_count = self.daily_entry_count
        return accepted

    def should_force_research_time_exit(self, observed_at: Any) -> bool:
        if self._highwin_active_entry_time is None:
            return False
        return (
            highwin_holding_exit_reason(
                self._highwin_active_entry_time,
                observed_at,
                self._risk_helper_parameters(),
            )
            is not None
        )

    def mark_research_position_closed(self) -> None:
        self._highwin_active_entry_time = None

    def get_history_status(self) -> dict[str, Any]:
        self._refresh_wait_diagnostics()
        if self._snapshot_error:
            status = "INVALID"
        elif self._snapshot is None:
            status = "WAIT"
        elif self._latest_diagnostics.get("status") == "WARMUP":
            status = "WARMUP"
        else:
            status = self._latest_diagnostics.get("status", "WAIT")
        return {
            "status": status,
            "real_timeframe_minutes": 3,
            "minimum_completed_candles": dict(
                MULTIFRAME_PARAMETERS["minimum_completed_candles"]
            ),
            "reasons": list(self._latest_diagnostics.get("reasons", [])),
        }

    def get_diagnostics(self) -> dict[str, Any]:
        self._refresh_wait_diagnostics()
        result = dict(self._latest_diagnostics)
        result.update(
            {
                "latest_decision_timestamp": (
                    self._last_processed_m3_at.isoformat()
                    if self._last_processed_m3_at
                    else None
                ),
                "h4_direction": result.get("h4_direction", "UNKNOWN"),
                "m15_direction": result.get("m15_direction", "UNKNOWN"),
                "m3_direction": result.get("m3_direction", "UNKNOWN"),
                "calls": self._counts["calls"],
                "checked": self._counts["checked"],
                "checked_count": self._counts["checked"],
                "BUY": self._counts["buy"],
                "SELL": self._counts["sell"],
                "buy_count": self._counts["buy"],
                "sell_count": self._counts["sell"],
                "actionable": self._counts["actionable"],
                "actionable_count": self._counts["actionable"],
                "accepted_trades": self._counts["accepted_trades"],
                "bar_interval_minutes": 3,
                "timeframes": ["H4", "M15", "M3"],
                "startup_historical_call_suppression": self._startup_historical_call_suppression,
                "snapshot_error": self._snapshot_error,
            }
        )
        if self._snapshot is not None:
            result["snapshot_age_seconds"] = max(
                0.0,
                (datetime.now(_UTC) - self._snapshot["fetched_at"]).total_seconds(),
            )
            m3_bars = self._snapshot["frames"]["M3"]
            result["latest_m3_close_age_seconds"] = (
                max(0.0, (datetime.now(_UTC) - m3_bars[-1]["observed_at"]).total_seconds())
                if m3_bars
                else None
            )
        return result
