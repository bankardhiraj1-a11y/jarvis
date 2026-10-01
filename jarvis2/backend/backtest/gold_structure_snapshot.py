"""Read-only, timestamped XAU/USD trend and structure snapshot from OANDA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from data.oanda_pricing import OandaPricingClient
from backtest.xauusd_evidence import (
    XAUHistoryError,
    _price_bar,
    _read_access_token,
    _timestamp,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DIR = ROOT.parent / "research"
PRACTICE_HOST = "https://api-fxpractice.oanda.com/v3"
INSTRUMENT = "XAU_USD"
TIMEFRAME_REQUESTS = (("H1", 200, timedelta(hours=1)), ("M15", 200, timedelta(minutes=15)), ("D", 5, timedelta(days=1)))


def _fetch_candles(token: str, granularity: str, count: int, session: Any = requests) -> list[dict[str, Any]]:
    """Make one bounded, read-only request; do not log credentials or provider bodies."""
    try:
        response = session.get(
            f"{PRACTICE_HOST}/instruments/{INSTRUMENT}/candles",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params={"granularity": granularity, "count": count, "price": "BA", "smooth": "false"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise XAUHistoryError(f"OANDA {granularity} candle request failed") from exc
    if response.status_code != 200:
        raise XAUHistoryError(f"OANDA {granularity} candle request rejected (HTTP {response.status_code})")
    try:
        payload = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError) as exc:
        raise XAUHistoryError(f"OANDA {granularity} response was not valid JSON") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("instrument") != INSTRUMENT
        or payload.get("granularity") != granularity
        or not isinstance(payload.get("candles"), list)
    ):
        raise XAUHistoryError(f"OANDA {granularity} response failed provenance checks")

    bars = []
    previous: datetime | None = None
    for candle in payload["candles"]:
        if not isinstance(candle, dict) or candle.get("complete") is not True:
            continue
        bar = _price_bar(candle)
        stamp = _timestamp(bar["time"])
        if previous is not None and stamp <= previous:
            raise XAUHistoryError(f"OANDA {granularity} candles are not strictly chronological")
        previous = stamp
        bars.append(bar)
    return bars


def _mid_ohlc(bar: dict[str, Any]) -> dict[str, float]:
    return {
        part: (bar[f"bid_{part}"] + bar[f"ask_{part}"]) / 2
        for part in ("open", "high", "low", "close")
    }


def _ema(values: list[float], period: int) -> float:
    return _ema_series(values, period)[-1]


def _ema_series(values: list[float], period: int) -> list[float]:
    alpha = 2 / (period + 1)
    result = values[0]
    results = [result]
    for value in values[1:]:
        result = value * alpha + result * (1 - alpha)
        results.append(result)
    return results


def _atr14(bars: list[dict[str, Any]]) -> float:
    mids = [_mid_ohlc(bar) for bar in bars]
    ranges = []
    for index, current in enumerate(mids):
        previous_close = mids[index - 1]["close"] if index else current["close"]
        ranges.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous_close),
            abs(current["low"] - previous_close),
        ))
    return sum(ranges[-14:]) / min(14, len(ranges))


def _confirmed_pivots(
    bars: list[dict[str, Any]], kind: str, interval: timedelta = timedelta(minutes=15)
) -> list[dict[str, Any]]:
    """Two-left/two-right pivots; a pivot is only emitted after two later closes."""
    field = "high" if kind == "high" else "low"
    mids = [_mid_ohlc(bar) for bar in bars]
    pivots = []
    for index in range(2, len(bars) - 2):
        value = mids[index][field]
        neighbors = [mids[other][field] for other in range(index - 2, index + 3) if other != index]
        if (value > max(neighbors) if kind == "high" else value < min(neighbors)):
            pivots.append({
                "bar_open_time": bars[index]["time"],
                "confirmed_at": (_timestamp(bars[index + 2]["time"]) + interval).isoformat(),
                "price": value,
            })
    return pivots


def _swing_summary(bars: list[dict[str, Any]], interval: timedelta) -> dict[str, Any]:
    mids = [_mid_ohlc(bar) for bar in bars]
    closes = [bar["close"] for bar in mids]
    if len(bars) < 50:
        return {"status": "insufficient_history", "complete_bars": len(bars)}
    ema20_series = _ema_series(closes, 20)
    ema50 = _ema(closes, 50)
    ema20 = ema20_series[-1]
    slope_lookback = min(5, len(closes) - 1)
    prior_ema20 = ema20_series[-1 - slope_lookback]
    pivots_high = _confirmed_pivots(bars, "high", interval)
    pivots_low = _confirmed_pivots(bars, "low", interval)
    last_two_highs = pivots_high[-2:]
    last_two_lows = pivots_low[-2:]
    higher_swings = (
        len(last_two_highs) == 2
        and len(last_two_lows) == 2
        and last_two_highs[1]["price"] > last_two_highs[0]["price"]
        and last_two_lows[1]["price"] > last_two_lows[0]["price"]
    )
    lower_swings = (
        len(last_two_highs) == 2
        and len(last_two_lows) == 2
        and last_two_highs[1]["price"] < last_two_highs[0]["price"]
        and last_two_lows[1]["price"] < last_two_lows[0]["price"]
    )
    close = closes[-1]
    ema_rising = ema20 > prior_ema20
    ema_falling = ema20 < prior_ema20
    if close > ema20 > ema50 and ema_rising and higher_swings:
        trend = "bullish"
    elif close < ema20 < ema50 and ema_falling and lower_swings:
        trend = "bearish"
    elif close > ema20 > ema50 and ema_rising:
        trend = "bullish_bias"
    elif close < ema20 < ema50 and ema_falling:
        trend = "bearish_bias"
    else:
        trend = "mixed_or_neutral"
    last_bar = bars[-1]
    duration_minutes = int(interval.total_seconds() // 60)
    return {
        "status": "evaluated",
        "timeframe": "H1" if duration_minutes == 60 else "M15",
        "complete_bars": len(bars),
        "last_completed_bar_open": last_bar["time"],
        "last_completed_bar_observed_at": (_timestamp(last_bar["time"]) + interval).isoformat(),
        "midpoint_close_approx_usd_per_troy_oz": close,
        "ema20_midpoint_approx": ema20,
        "ema50_midpoint_approx": ema50,
        "ema20_slope_over_last_5_bars": "rising" if ema_rising else "falling" if ema_falling else "flat",
        "trend": trend,
        "confirmed_pivot_rule": "strict 2 bars left and 2 complete bars right; confirmation is delayed by 2 bars",
        "last_two_confirmed_swing_highs": last_two_highs,
        "last_two_confirmed_swing_lows": last_two_lows,
        "latest_close_position": "above_ema20_and_ema50" if close > max(ema20, ema50) else "below_ema20_and_ema50" if close < min(ema20, ema50) else "between_ema20_and_ema50",
    }


def _cluster_zones(pivots: list[dict[str, Any]], reference: float, tolerance: float, direction: str) -> list[dict[str, Any]]:
    eligible = [
        pivot for pivot in pivots
        if (pivot["price"] < reference if direction == "support" else pivot["price"] > reference)
    ]
    eligible.sort(key=lambda pivot: pivot["price"])
    clusters: list[list[dict[str, Any]]] = []
    for pivot in eligible:
        if not clusters or pivot["price"] - clusters[-1][0]["price"] > tolerance:
            clusters.append([pivot])
        else:
            clusters[-1].append(pivot)
    zones = []
    for cluster in clusters:
        prices = [pivot["price"] for pivot in cluster]
        low, high = min(prices), max(prices)
        center = sum(prices) / len(prices)
        if direction == "support" and center >= reference:
            continue
        if direction == "resistance" and center <= reference:
            continue
        zones.append({
            "zone_low_usd_per_troy_oz": low - tolerance / 2,
            "zone_high_usd_per_troy_oz": high + tolerance / 2,
            "center_usd_per_troy_oz": center,
            "pivot_touches": len(cluster),
            "pivot_times": [pivot["bar_open_time"] for pivot in cluster],
        })
    zones.sort(key=lambda zone: abs(zone["center_usd_per_troy_oz"] - reference))
    return zones[:3]


def _structure(bars: list[dict[str, Any]], daily: list[dict[str, Any]]) -> dict[str, Any]:
    if len(bars) < 20:
        return {"status": "insufficient_history", "complete_bars": len(bars)}
    mids = [_mid_ohlc(bar) for bar in bars]
    reference = mids[-1]["close"]
    atr = _atr14(bars)
    tolerance = 0.15 * atr
    high_pivots = _confirmed_pivots(bars, "high")
    low_pivots = _confirmed_pivots(bars, "low")

    london = ZoneInfo("Europe/London")
    london_date_candidates: dict[str, list[dict[str, Any]]] = {}
    for bar in bars:
        opening = _timestamp(bar["time"])
        local = opening.astimezone(london)
        if local.hour == 8 and local.minute in (0, 15):
            london_date_candidates.setdefault(local.date().isoformat(), []).append(bar)
    london_range = None
    if london_date_candidates:
        for day in sorted(london_date_candidates, reverse=True):
            opening_bars = london_date_candidates[day]
            if {(_timestamp(bar["time"]).astimezone(london).minute) for bar in opening_bars} >= {0, 15}:
                opening_bars.sort(key=lambda bar: _timestamp(bar["time"]))
                opening_mids = [_mid_ohlc(bar) for bar in opening_bars]
                london_range = {
                    "local_date": day,
                    "timezone": "Europe/London (DST-aware)",
                    "bars": [bar["time"] for bar in opening_bars],
                    "range_start_local": f"{day}T08:00:00",
                    "range_end_local": f"{day}T08:30:00",
                    "high_usd_per_troy_oz": max(bar["high"] for bar in opening_mids),
                    "low_usd_per_troy_oz": min(bar["low"] for bar in opening_mids),
                    "status": "observed_from_two_complete_M15_bars",
                }
                break
    if london_range is None:
        london_range = {"status": "unavailable_in_requested_complete_M15_history"}

    previous_daily = None
    if daily:
        daily_bar = daily[-1]
        daily_mid = _mid_ohlc(daily_bar)
        previous_daily = {
            "provider_day_open_time": daily_bar["time"],
            "provider_day_convention": "OANDA D1 provider candle; daily boundary is provider/NY-aligned, not guessed from UTC calendar date",
            "observed_at": (_timestamp(daily_bar["time"]) + timedelta(days=1)).isoformat(),
            "high_usd_per_troy_oz": daily_mid["high"],
            "low_usd_per_troy_oz": daily_mid["low"],
        }

    return {
        "status": "evaluated",
        "basis": "M15 two-left/two-right completed midpoint pivots, clustered at 0.15 x measured M15 ATR(14)",
        "reference_midpoint_close_approx_usd_per_troy_oz": reference,
        "reference_bar_open_time": bars[-1]["time"],
        "reference_observed_at": (_timestamp(bars[-1]["time"]) + timedelta(minutes=15)).isoformat(),
        "m15_atr14_midpoint_approx_usd_per_troy_oz": atr,
        "zone_tolerance_0_15_atr_usd_per_troy_oz": tolerance,
        "supports": _cluster_zones(low_pivots, reference, tolerance, "support"),
        "resistances": _cluster_zones(high_pivots, reference, tolerance, "resistance"),
        "previous_completed_provider_day": previous_daily,
        "london_opening_range_0800_0830": london_range,
    }


def _get_current_quote() -> tuple[dict[str, Any] | None, bool]:
    """Optional fourth request, only when an already configured practice quote client exists."""
    client = OandaPricingClient()
    if client.environment != "practice" or not client.configured:
        client.close()
        return None, False
    try:
        quote = client.get_live_data("XAUUSD")
        if quote.get("stale") or quote.get("status") != "live":
            return None, True
        return {
            key: quote[key] for key in (
                "instrument", "source", "exchange", "currency", "bid", "ask", "close",
                "timestamp", "observed_at", "age_seconds", "timestamp_kind", "environment",
            ) if key in quote
        }, True
    finally:
        client.close()


def build_snapshot(*, session: Any = requests, now: datetime | None = None) -> dict[str, Any]:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    token = _read_access_token()
    if not token:
        return {
            "status": "unavailable",
            "generated_at_utc": generated_at.isoformat(),
            "reason": "Authorized OANDA history token is not configured; no candles were requested.",
        }
    fetched: dict[str, list[dict[str, Any]]] = {}
    for granularity, count, _interval in TIMEFRAME_REQUESTS:
        fetched[granularity] = _fetch_candles(token, granularity, count, session=session)
    # A current bid/ask quote is an optional single fourth call.  It is skipped
    # when the already-provisioned practice pricing client cannot make one call.
    quote, quote_request_used = _get_current_quote()
    intervals = {name: interval for name, _count, interval in TIMEFRAME_REQUESTS}
    analysis = {
        name: _swing_summary(fetched[name], intervals[name])
        for name in ("H1", "M15")
    }
    analysis["structure"] = _structure(fetched["M15"], fetched["D"])
    result = {
        "status": "evaluated",
        "generated_at_utc": generated_at.isoformat(),
        "generated_at_asia_kolkata": generated_at.astimezone(ZoneInfo("Asia/Kolkata")).isoformat(),
        "source": {
            "provider": "OANDA",
            "environment": "practice",
            "instrument": INSTRUMENT,
            "historical_endpoint": "/v3/instruments/XAU_USD/candles",
            "granularities_requested": {"H1": 200, "M15": 200, "D": 5},
            "historical_price_components": "BA (bid and ask OHLC)",
            "complete_only": True,
            "smoothed": False,
            "historical_http_requests": 3,
            "current_quote_http_request_used": quote_request_used,
        },
        "quote": quote,
        "analysis": analysis,
        "methodology": {
            "ohlc_basis": "Midpoints are computed from provider bid/ask OHLC; this is a midpoint approximation, not a tradable side.",
            "ema": "EMA-20 and EMA-50 of completed-bar midpoint closes; approximately seeded from available requested history.",
            "pivot_confirmation": "Strict local high/low with two completed bars on each side; pivot is usable only after the two right-side bars close.",
            "zone_tolerance": "Measured M15 midpoint ATR(14) multiplied by 0.15; no hand-entered price levels.",
            "volume": "Not used; OANDA candle volume is a tick count, not traded gold volume.",
        },
        "limitations": [
            "This is a timestamped market-structure description, not a strategy, entry/exit instruction, forecast, or real-time execution claim.",
            "Candle timestamps identify bar opens; OHLC is not observable until the interval has completed.",
            "Daily high/low is the most recent fully completed OANDA provider D1 candle, whose boundary is provider/NY-aligned.",
            "One user-stated 100 troy-ounce lot would arithmetically gain/lose USD 100 per USD 1/oz move before spread/fees; this does not imply a position or actual trade.",
            "A practice feed establishes neither live-account authorization nor actual fills.",
        ],
    }
    return result


def _markdown(snapshot: dict[str, Any]) -> str:
    if snapshot.get("status") != "evaluated":
        return (
            "# Current XAU/USD structure snapshot\n\n"
            f"- Generated at (UTC): {snapshot.get('generated_at_utc')}\n"
            f"- Status: unavailable — {snapshot.get('reason', 'market data was unavailable')}\n"
        )
    analysis = snapshot["analysis"]
    structure = analysis["structure"]
    quote = snapshot.get("quote")
    lines = [
        "# Current XAU/USD trend and structure",
        "",
        f"- Generated: {snapshot['generated_at_utc']} UTC ({snapshot['generated_at_asia_kolkata']} Asia/Kolkata)",
        "- Source: OANDA practice, XAU_USD, complete unsmoothed BA candles; bid/ask midpoints are approximate analytical OHLC.",
        f"- Current quote: {quote['bid']:.2f} bid / {quote['ask']:.2f} ask USD/oz at {quote['timestamp']} UTC (observed {quote['observed_at']} UTC)." if quote else "- Current quote: unavailable; candle conclusions are timestamped to each latest completed bar, not presented as a live quote.",
        "",
        "## Trend",
    ]
    for timeframe in ("H1", "M15"):
        item = analysis[timeframe]
        if item.get("status") != "evaluated":
            lines.append(f"- {timeframe}: insufficient complete bars ({item.get('complete_bars', 0)}).")
            continue
        lines.append(
            f"- {timeframe}: **{item['trend']}**; midpoint close ≈ {item['midpoint_close_approx_usd_per_troy_oz']:.2f}, "
            f"EMA20 ≈ {item['ema20_midpoint_approx']:.2f}, EMA50 ≈ {item['ema50_midpoint_approx']:.2f}; "
            f"EMA20 {item['ema20_slope_over_last_5_bars']}. Latest complete bar open {item['last_completed_bar_open']}, "
            f"observable {item['last_completed_bar_observed_at']} UTC."
        )
        for label, key in (("confirmed swing highs", "last_two_confirmed_swing_highs"), ("confirmed swing lows", "last_two_confirmed_swing_lows")):
            values = item[key]
            compact = ", ".join(f"{value['price']:.2f} ({value['bar_open_time']})" for value in values) or "not enough confirmed pivots"
            lines.append(f"  - Last {label}: {compact}. (2-bar right-side confirmation lag.)")
    lines.extend(["", "## Support and resistance"])
    if structure.get("status") != "evaluated":
        lines.append("- Not enough complete M15 history to calculate pivot zones.")
    else:
        lines.append(
            f"- Reference midpoint close ≈ {structure['reference_midpoint_close_approx_usd_per_troy_oz']:.2f} "
            f"from bar {structure['reference_bar_open_time']} (observable {structure['reference_observed_at']} UTC)."
        )
        lines.append(
            f"- Zones use confirmed M15 pivots grouped within 0.15 × measured ATR(14) "
            f"(ATR ≈ {structure['m15_atr14_midpoint_approx_usd_per_troy_oz']:.2f}; tolerance ≈ "
            f"{structure['zone_tolerance_0_15_atr_usd_per_troy_oz']:.2f} USD/oz)."
        )
        for label, key in (("Supports", "supports"), ("Resistances", "resistances")):
            values = structure[key]
            if not values:
                lines.append(f"- {label}: no confirmed pivot zones on that side in the requested sample.")
            for zone in values:
                lines.append(
                    f"- {label}: {zone['zone_low_usd_per_troy_oz']:.2f}–{zone['zone_high_usd_per_troy_oz']:.2f} "
                    f"(center {zone['center_usd_per_troy_oz']:.2f}; {zone['pivot_touches']} confirmed pivot(s))."
                )
        daily = structure.get("previous_completed_provider_day")
        if daily:
            lines.append(
                f"- Latest completed provider/NY-aligned D1 range: {daily['low_usd_per_troy_oz']:.2f}–"
                f"{daily['high_usd_per_troy_oz']:.2f} (bar open {daily['provider_day_open_time']}; "
                f"observable {daily['observed_at']} UTC)."
            )
        london = structure["london_opening_range_0800_0830"]
        if london.get("status") == "observed_from_two_complete_M15_bars":
            lines.append(
                f"- London 08:00–08:30 local opening range ({london['timezone']}, {london['local_date']}): "
                f"{london['low_usd_per_troy_oz']:.2f}–{london['high_usd_per_troy_oz']:.2f}."
            )
        else:
            lines.append("- London opening range: unavailable from the requested complete M15 bars.")
    lines.extend([
        "",
        "## Read this cautiously",
        "- “Bullish”/“bearish” is descriptive: it requires EMA alignment, recent EMA20 slope, and two higher/lower confirmed swings; a partial alignment is reported as a bias or mixed/neutral.",
        "- Support/resistance are observed zones, not guaranteed turning points. No trading recommendation or strategy deployment is made.",
        "- Midpoint OHLC is derived from bid/ask, not a tradable execution side. Candle volume is intentionally omitted because provider volume is a tick count.",
        "- 100 oz × USD 1/oz = USD 100 arithmetic per USD 1 move, before spread/fees; this is not a claim that a trade exists.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    try:
        snapshot = build_snapshot(now=stamp)
    except (XAUHistoryError, requests.RequestException) as exc:
        # Only sanitized exception text is emitted: provider payloads, auth, IDs,
        # and request URLs are never logged.
        snapshot = {
            "status": "unavailable",
            "generated_at_utc": stamp.isoformat(),
            "reason": str(exc),
            "provider_body_or_credentials_stored": False,
        }
    (RESEARCH_DIR / "current-gold-structure.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    date_name = stamp.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    (RESEARCH_DIR / f"current-gold-structure-{date_name}.md").write_text(_markdown(snapshot), encoding="utf-8")
    print(f"snapshot_status={snapshot['status']}")
    if snapshot.get("status") == "evaluated":
        for timeframe in ("H1", "M15"):
            entry = snapshot["analysis"][timeframe]
            print(f"{timeframe}_trend={entry.get('trend')} last_bar={entry.get('last_completed_bar_open')}")
        print(f"current_quote_available={snapshot.get('quote') is not None}")
        print(f"support_count={len(snapshot['analysis']['structure'].get('supports', []))}")
        print(f"resistance_count={len(snapshot['analysis']['structure'].get('resistances', []))}")
    else:
        print(f"reason={snapshot.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())