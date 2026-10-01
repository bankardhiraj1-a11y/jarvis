"""Read-only, completed XAU_USD multi-timeframe candle feed."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from data.oanda_pricing import OandaCandleError


class XauusdFeedError(Exception):
    """Sanitized candle-feed failure; contains no provider response details."""


_INSTRUMENT = "XAU_USD"
_FRAME_CONFIG = {"M1": (1, 240), "M15": (15, 100), "H4": (240, 100)}
_OHLC = ("open", "high", "low", "close")
_LETTERS = {"open": "o", "high": "h", "low": "l", "close": "c"}


def _utc_timestamp(value):
    if not isinstance(value, str):
        raise XauusdFeedError("OANDA candle timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise XauusdFeedError("OANDA candle timestamp is invalid") from None
    if parsed.tzinfo is None:
        raise XauusdFeedError("OANDA candle timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validated_side_ohlc(candle, side):
    quote = candle.get(side)
    if not isinstance(quote, dict):
        raise XauusdFeedError("OANDA candle is missing bid/ask OHLC prices")
    values = {}
    for part in _OHLC:
        try:
            value = float(quote[_LETTERS[part]])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise XauusdFeedError("OANDA candle contains invalid bid/ask OHLC data") from None
        if not math.isfinite(value) or value <= 0:
            raise XauusdFeedError("OANDA candle contains non-positive or non-finite OHLC data")
        values[part] = value
    if (
        values["low"] > min(values["open"], values["close"])
        or values["high"] < max(values["open"], values["close"])
        or values["low"] > values["high"]
    ):
        raise XauusdFeedError("OANDA candle contains malformed OHLC ranges")
    return values


def _validated_candle(candle, granularity, environment):
    if not isinstance(candle, dict):
        raise XauusdFeedError("OANDA candle response contains an invalid candle")
    if candle.get("instrument", _INSTRUMENT) != _INSTRUMENT:
        raise XauusdFeedError("OANDA candle instrument provenance mismatch")
    if candle.get("granularity", granularity) != granularity:
        raise XauusdFeedError("OANDA candle granularity provenance mismatch")
    if candle.get("environment", environment) != environment:
        raise XauusdFeedError("OANDA candle environment provenance mismatch")

    bid = _validated_side_ohlc(candle, "bid")
    ask = _validated_side_ohlc(candle, "ask")
    if any(bid[part] > ask[part] for part in _OHLC):
        raise XauusdFeedError("OANDA candle bid exceeds ask")
    return bid, ask


def _midpoint_bar(bid, ask):
    return {part: (bid[part] + ask[part]) / 2 for part in _OHLC}


class XauusdMultiFrameFeed:
    """Build M3 from contiguous M1 data and pass through completed M15/H4 bars."""

    def __init__(self, client):
        self.client = client

    def _fetch(self, granularity, count):
        try:
            return self.client.get_completed_candles(granularity, count)
        except OandaCandleError as exc:
            raise XauusdFeedError(str(exc)) from None
        except Exception:
            # Do not surface arbitrary transport exceptions, response bodies, or secrets.
            raise XauusdFeedError("OANDA candle refresh failed") from None

    def _records(self, granularity, count, interval, environment, now):
        candles = self._fetch(granularity, count)
        if not isinstance(candles, list):
            raise XauusdFeedError("OANDA candle response is invalid")

        records = []
        previous = None
        for candle in candles:
            if not isinstance(candle, dict):
                raise XauusdFeedError("OANDA candle response contains an invalid candle")
            if candle.get("instrument", _INSTRUMENT) != _INSTRUMENT:
                raise XauusdFeedError("OANDA candle instrument provenance mismatch")
            if candle.get("granularity", granularity) != granularity:
                raise XauusdFeedError("OANDA candle granularity provenance mismatch")
            if candle.get("environment", environment) != environment:
                raise XauusdFeedError("OANDA candle environment provenance mismatch")

            opened = _utc_timestamp(candle.get("time"))
            if previous is not None and opened <= previous:
                raise XauusdFeedError("OANDA candles are duplicate or non-chronological")
            previous = opened

            # OANDA timestamps identify bar opens; malformed off-boundary bars are rejected.
            if (
                opened.second != 0
                or opened.microsecond != 0
                or (interval < 60 and opened.minute % interval != 0)
                or (interval == 240 and (opened.minute != 0 or opened.hour % 4 != 0))
            ):
                raise XauusdFeedError("OANDA candle open time does not match its granularity")

            observed = opened + timedelta(minutes=interval)
            if candle.get("complete") is not True or observed > now:
                continue
            bid, ask = _validated_candle(candle, granularity, environment)
            records.append({"opened": opened, "observed": observed, "bid": bid, "ask": ask})
        return records

    @staticmethod
    def _canonical_bar(opened, observed, bid, ask, interval, environment):
        middle = _midpoint_bar(bid, ask)
        return {
            "bar_open_time": _iso_utc(opened),
            "observed_at": _iso_utc(observed),
            **middle,
            "bid_close": bid["close"],
            "ask_close": ask["close"],
            "complete": True,
            "provider": "OANDA",
            "environment": environment,
            "bar_interval_minutes": interval,
        }

    def _m3_bars(self, records, environment):
        buckets = {}
        for record in records:
            opened = record["opened"]
            bucket = opened.replace(minute=(opened.minute // 3) * 3, second=0, microsecond=0)
            buckets.setdefault(bucket, {})[opened.minute % 3] = record

        bars = []
        for bucket in sorted(buckets):
            minutes = buckets[bucket]
            if set(minutes) != {0, 1, 2}:
                continue
            group = [minutes[offset] for offset in range(3)]
            if any(
                group[index]["opened"] + timedelta(minutes=1) != group[index + 1]["opened"]
                for index in range(2)
            ):
                continue

            bid = {
                "open": group[0]["bid"]["open"],
                "high": max(item["bid"]["high"] for item in group),
                "low": min(item["bid"]["low"] for item in group),
                "close": group[-1]["bid"]["close"],
            }
            ask = {
                "open": group[0]["ask"]["open"],
                "high": max(item["ask"]["high"] for item in group),
                "low": min(item["ask"]["low"] for item in group),
                "close": group[-1]["ask"]["close"],
            }
            if any(bid[part] > ask[part] for part in _OHLC):
                raise XauusdFeedError("OANDA grouped candle bid exceeds ask")
            bars.append(self._canonical_bar(
                bucket, bucket + timedelta(minutes=3), bid, ask, 3, environment
            ))
        return bars

    def _direct_bars(self, granularity, environment, now):
        interval, count = _FRAME_CONFIG[granularity]
        records = self._records(granularity, count, interval, environment, now)
        return [
            self._canonical_bar(
                record["opened"], record["observed"], record["bid"], record["ask"],
                interval, environment,
            )
            for record in records
        ]

    def refresh(self, now=None):
        if now is None:
            cutoff = datetime.now(timezone.utc)
        elif isinstance(now, datetime) and now.tzinfo is not None:
            cutoff = now.astimezone(timezone.utc)
        else:
            raise XauusdFeedError("Refresh time must be a timezone-aware datetime")

        environment = getattr(self.client, "environment", None)
        if environment not in ("practice", "live"):
            raise XauusdFeedError("OANDA environment is unavailable")

        m1_interval, m1_count = _FRAME_CONFIG["M1"]
        m1_records = self._records("M1", m1_count, m1_interval, environment, cutoff)
        m15_bars = self._direct_bars("M15", environment, cutoff)
        h4_bars = self._direct_bars("H4", environment, cutoff)
        return {
            "fetched_at": _iso_utc(cutoff),
            "environment": environment,
            "frames": {
                "M3": self._m3_bars(m1_records, environment),
                "M15": m15_bars,
                "H4": h4_bars,
            },
            "source": "OANDA",
        }